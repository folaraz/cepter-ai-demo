"""POST /api/ask (SPEC C14): answer a question about the data room, or say it can't.

1. Validate (3-500 characters) and normalise the question.
2. Serve a cached answer for the same question on the same run within cache_hours.
3. Route it (model, checked against ask.yaml).
4. relationship: render a graph query's templates; no model writes the words.
5. lookup: retrieve; abstain early when nothing is similar and no keyword matched;
   otherwise draft with the model and verify every sentence (app/ask/answer.py).
6. out_of_scope: abstain with the out-of-scope message, without retrieval.
7. Model calls use a recording when one exists. Without one, a call goes live only when
   ASK_LIVE is on and the session's and the day's limits allow; otherwise the answer is
   "unavailable". Live responses are never written as recordings.
8. Every question is stored in `asks`.

Policies: "serve" (the API, as above), "record" (`lens record --ask`: call the API and
write recordings), "replay" (the accuracy check: recordings only, a missing one raises).
"""

import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, TypeVar

from psycopg import Connection
from pydantic import BaseModel

from app.api.models import AskResponse, AskSentence
from app.ask.answer import in_document_order, prompt, related, verify_draft
from app.ask.graph_queries import run_graph_query
from app.ask.prompts import route_system
from app.ask.router import Route, validate
from app.config import get_settings
from app.db.repositories import asks as asks_repo
from app.db.repositories import runs
from app.domain.ask import AnswerDraft, RouteDecision, ask_config
from app.domain.asks import NewAsk
from app.domain.runs import NewLLMCall
from app.llm.client import LLMClient, MissingRecording, Mode
from app.llm.replay import RecordingStore
from app.published import Published, load_published
from app.retrieval.config import retrieval_config
from app.retrieval.search import Retrieval, search

log = logging.getLogger("lens.ask")
Policy = Literal["serve", "record", "replay"]
T = TypeVar("T", bound=BaseModel)
LLMFactory = Callable[[Callable[[NewLLMCall], None]], LLMClient]


class InvalidQuestion(ValueError):
    pass


class RetrievalDrift(RuntimeError):
    """Replay found a recording for this question made with different paragraphs: the
    index or ranking changed since recording. Re-record rather than guess."""

    def __init__(self, question: str, expected: list[str], got: list[str]) -> None:
        self.question, self.expected, self.got = question, expected, got
        super().__init__(
            f"retrieval changed for {question!r}: recorded {expected}, now {got}; "
            "run `lens record --ask`"
        )


class _Unavailable(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


def normalise(question: str) -> str:
    """Casefold, strip punctuation, collapse spaces: the cache key."""
    return " ".join(re.sub(r"[^\w\s]", " ", question.casefold()).split())


@dataclass
class _Calls:
    """Model calls made for one question, and what they cost live."""

    made: list[NewLLMCall] = field(default_factory=list)

    @property
    def live(self) -> list[NewLLMCall]:
        return [c for c in self.made if not c.replayed]


def ask(
    conn: Connection,
    question: str,
    *,
    session_id: str | None,
    llm_factory: LLMFactory,
    policy: Policy = "serve",
    run_id: str | None = None,
    store: bool = True,
    recordings: RecordingStore | None = None,
) -> AskResponse:
    started = time.monotonic()
    question = question.strip()
    limits = ask_config().limits.question_chars
    if not limits["min"] <= len(question) <= limits["max"]:
        raise InvalidQuestion(f"Questions are {limits['min']} to {limits['max']} characters")
    norm = normalise(question)
    published = load_published(conn, session_id, run_id)

    if policy == "serve" and (cached := _cached(conn, published.run.id, norm)) is not None:
        response = cached.model_copy(
            update={
                "id": uuid.uuid4().hex,
                "question": question,
                "mode": "cache",
                "cost_gbp": 0.0,
                "latency_ms": _ms(started),
            }
        )
        if store:
            _store(conn, response, norm, published, session_id, [], started)
        return response

    calls = _Calls()

    def trace(call: NewLLMCall) -> None:
        runs.insert_llm_call(conn, call)
        calls.made.append(call)

    answerer = _Answerer(
        conn,
        published,
        session_id,
        llm_factory(trace),
        policy,
        calls,
        recordings or RecordingStore(),
    )
    retrieved: list[dict[str, Any]] = []
    try:
        response, retrieved = answerer.answer(question)
    except _Unavailable as unavailable:
        response = _build(question, None, "unavailable", [], unavailable.message, 0)

    response = response.model_copy(
        update={
            "mode": "live" if calls.live else "replay",
            "cost_gbp": float(sum((c.cost_gbp for c in calls.live), Decimal(0))),
            "latency_ms": _ms(started),
        }
    )
    if store:
        _store(conn, response, norm, published, session_id, retrieved, started)
    return response


class _Answerer:
    def __init__(
        self,
        conn: Connection,
        published: Published,
        session_id: str | None,
        llm: LLMClient,
        policy: Policy,
        calls: _Calls,
        recordings: RecordingStore,
    ) -> None:
        self.conn, self.p, self.session_id = conn, published, session_id
        self.llm, self.policy, self.calls, self.recordings = llm, policy, calls, recordings

    def answer(self, question: str) -> tuple[AskResponse, list[dict[str, Any]]]:
        config = ask_config()
        decision = self._model(
            RouteDecision,
            route_system(),
            question,
            "ask:route",
            config.route_prompt_version,
            {"question": question},
        )
        route = validate(decision)
        if route.route == "out_of_scope":
            return _abstained(question, "out_of_scope", config.messages.out_of_scope), []
        if route.route == "relationship":
            return self._relationship(question, route), []
        return self._lookup(question)

    def _relationship(self, question: str, route: Route) -> AskResponse:
        assert route.graph_query is not None
        try:
            answer = run_graph_query(self.p, route.graph_query, route.params)
        except (KeyError, StopIteration):
            log.warning("graph query failed; answering as a lookup", exc_info=True)
            return self._lookup(question)[0]
        if not answer.sentences:
            return _abstained(question, "relationship", ask_config().messages.abstain_not_found)
        return _answered(
            question,
            "relationship",
            answer.sentences,
            dropped=0,
            finding_id=answer.related_finding_id,
            rfi_id=answer.related_rfi_id,
        )

    def _lookup(self, question: str) -> tuple[AskResponse, list[dict[str, Any]]]:
        messages = ask_config().messages
        found: Retrieval = search(self.conn, question)
        retrieved = [
            {
                "paragraph_id": h.paragraph_id,
                "vector_rank": h.vector_rank,
                "keyword_rank": h.keyword_rank,
                "similarity": round(h.similarity, 4),
                "rrf": round(h.rrf, 6),
            }
            for h in found.hits
        ]
        # Nothing similar and no keyword in common: abstain without calling the model.
        if found.best_similarity < retrieval_config().min_similarity and not found.keyword_found:
            return _abstained(question, "lookup", messages.abstain_not_found), retrieved

        paragraphs = in_document_order(self.p, found.hits)
        ids = [p.id for p in paragraphs]
        system, user = prompt(question, paragraphs)
        draft = self._model(
            AnswerDraft,
            system,
            user,
            "ask:answer",
            ask_config().answer_prompt_version,
            {"question": question, "retrieved": ids},
        )
        if draft.abstain:
            return _abstained(question, "lookup", messages.abstain_not_found), retrieved
        verified = verify_draft(self.p, draft, set(ids))
        if not verified.sentences:
            message = messages.abstain_unverified
            return _abstained(question, "lookup", message, verified.dropped), retrieved
        cited = {c.citation.paragraph_id for s in verified.sentences for c in s.citations}
        finding_id, rfi_id = related(self.p, cited)
        answered = _answered(
            question,
            "lookup",
            verified.sentences,
            dropped=verified.dropped,
            finding_id=finding_id,
            rfi_id=rfi_id,
        )
        return answered, retrieved

    # ---------- model calls ----------

    def _model(
        self,
        schema: type[T],
        system: str,
        user: str,
        purpose: str,
        prompt_version: str,
        metadata: dict[str, Any],
    ) -> T:
        def call(mode: Mode) -> T:
            return self.llm.structured(
                schema=schema,
                system=system,
                user=user,
                purpose=purpose,
                prompt_version=prompt_version,
                run_id=self.p.run.id,
                mode=mode,
                metadata=metadata,
            )

        if self.policy == "record":
            return call("record")
        try:
            return call("replay")
        except MissingRecording:
            if purpose == "ask:answer":
                self._check_drift(metadata)
            if self.policy == "replay":
                raise
        refusal = self._live_refusal()
        if refusal is not None:
            raise _Unavailable(refusal)
        return call("live")

    def _check_drift(self, metadata: dict[str, Any]) -> None:
        for path in sorted(self.recordings.directory.glob("*.json")):
            recording = self.recordings.load(path.stem)
            if (
                recording is not None
                and recording.purpose == "ask:answer"
                and recording.metadata.get("question") == metadata["question"]
                and recording.metadata.get("retrieved") != metadata["retrieved"]
            ):
                drift = RetrievalDrift(
                    metadata["question"],
                    recording.metadata.get("retrieved", []),
                    metadata["retrieved"],
                )
                if self.policy == "replay":
                    raise drift
                log.warning(str(drift))

    def _live_refusal(self) -> str | None:
        """None if a live call is allowed, else the message saying why not."""
        messages, limits = ask_config().messages, ask_config().limits
        if not get_settings().ask_live:
            return messages.unavailable_live_off
        asked = asks_repo.live_questions_today(self.conn, self.session_id)
        spent = asks_repo.live_ask_spend_today(self.conn)
        if asked >= limits.live_questions_per_session_per_day or spent >= Decimal(
            str(limits.live_daily_budget_gbp)
        ):
            return messages.unavailable_limit
        return None


# ---------- responses and storage ----------


def _abstained(question: str, route: str, message: str, dropped: int = 0) -> AskResponse:
    return _build(question, route, "abstained", [], message, dropped)


def _answered(
    question: str,
    route: str,
    sentences: list[AskSentence],
    *,
    dropped: int,
    finding_id: str | None,
    rfi_id: str | None,
) -> AskResponse:
    return _build(question, route, "answered", sentences, None, dropped, finding_id, rfi_id)


def _build(
    question: str,
    route: str | None,
    status: str,
    sentences: list[AskSentence],
    message: str | None,
    dropped: int,
    finding_id: str | None = None,
    rfi_id: str | None = None,
) -> AskResponse:
    return AskResponse.model_validate(
        {
            "id": uuid.uuid4().hex,
            "question": question,
            "route": route,
            "status": status,
            "sentences": [s.model_dump() for s in sentences],
            "message": message,
            "related_finding_id": finding_id,
            "related_rfi_id": rfi_id,
            "dropped_sentences": dropped,
            "mode": "replay",
            "latency_ms": 0,
            "cost_gbp": 0.0,
        }
    )


def _cached(conn: Connection, run_id: str, norm: str) -> AskResponse | None:
    row = asks_repo.cached_answer(conn, run_id, norm, ask_config().limits.cache_hours)
    return AskResponse.model_validate(row.response) if row else None


def _store(
    conn: Connection,
    response: AskResponse,
    norm: str,
    published: Published,
    session_id: str | None,
    retrieved: list[dict[str, Any]],
    started: float,
) -> None:
    asks_repo.insert_ask(
        conn,
        NewAsk(
            id=response.id,
            session_id=session_id,
            run_id=published.run.id,
            question=response.question,
            question_norm=norm,
            route=response.route,
            status=response.status,
            mode=response.mode,
            retrieved=retrieved,  # type: ignore[arg-type]
            response=response.model_dump(mode="json"),
            dropped=response.dropped_sentences,
            cost_gbp=Decimal(str(response.cost_gbp)),
            latency_ms=_ms(started),
        ),
    )


def _ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
