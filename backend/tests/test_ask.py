"""C14: Ask, through the API, on the real data room and retrieval index.

The model's two calls are answered by tests/perfect_ask.py (through the real record /
replay adapter), so everything else, including every check on what the model says, is
the production code.
"""

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
import yaml
from fastapi.testclient import TestClient

from app.api.models import AskResponse
from app.ask.answer import verify_draft
from app.ask.router import validate
from app.ask.service import RetrievalDrift, ask
from app.config import BACKEND_DIR, DATAROOM_DIR, REPO_ROOT
from app.db.migrate import migrate
from app.db.pool import connect
from app.domain.ask import AnswerDraft, RouteDecision, ask_config
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient, ToolCall
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer
from app.pipeline import run_pipeline
from app.published import load_published
from app.retrieval.calibrate import read_ask_golden
from app.retrieval.index import build_index
from app.reviews.seed import apply_seed
from tests.conftest import ClientFor
from tests.test_consolidate import PerfectTransport

pytestmark = pytest.mark.db

GOLDEN = read_ask_golden()
FIXTURES = REPO_ROOT / "design" / "api" / "fixtures" / "ask"


class NoNetwork:
    def call(self, **_: Any) -> ToolCall:
        raise AssertionError("no model call may be made here")


def factory(store: RecordingStore, transport: Any) -> Any:
    def make(trace: Any) -> AnthropicLLMClient:
        return AnthropicLLMClient(trace=trace, store=store, transport=transport)

    return make


@pytest.fixture(scope="module")
def world(
    tmp_path_factory: pytest.TempPathFactory, db_server: str
) -> Iterator[tuple[str, RecordingStore]]:
    """A published, indexed, seeded data room with every golden question recorded, as
    `lens record --ask` leaves it."""
    import uuid

    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    name = f"lens_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(db_server, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = make_conninfo("", **{**conninfo_to_dict(db_server), "dbname": name})
    store = RecordingStore(tmp_path_factory.mktemp("recordings"))
    try:
        migrate(url)
        with connect(url) as conn:
            ingest_dataroom(conn)
            llm = AnthropicLLMClient(
                trace=db_tracer(conn), store=store, transport=PerfectTransport()
            )
            result = run_pipeline(conn, llm, kind="published", mode="record", publish=True)
            build_index(conn)
            apply_seed(conn, result.run_id)
            for item in GOLDEN:
                ask(
                    conn,
                    item["question"],
                    session_id=None,
                    policy="record",
                    store=False,
                    llm_factory=factory(store, PerfectTransport()),
                    recordings=store,
                )
        yield url, store
    finally:
        with psycopg.connect(db_server, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def api(world: tuple[str, RecordingStore], client_for: ClientFor) -> Iterator[TestClient]:
    url, store = world
    with client_for(url) as client:
        client.app.state.ask_llm = factory(store, NoNetwork())  # type: ignore[attr-defined]
        yield client
        del client.app.state.ask_llm  # type: ignore[attr-defined]


def post(client: TestClient, question: str) -> dict[str, Any]:
    response = client.post("/api/ask", json={"question": question})
    assert response.status_code == 200, response.text
    return dict(response.json())


def text_of(answer: dict[str, Any]) -> str:
    return " ".join(s["text"] for s in answer["sentences"])


def cited(answer: dict[str, Any]) -> set[str]:
    return {c["citation"]["paragraph_id"] for s in answer["sentences"] for c in s["citations"]}


# ---------- every golden question, replayed through the API ----------


@pytest.mark.parametrize("item", GOLDEN, ids=lambda i: i["id"])
def test_golden_question(api: TestClient, item: dict[str, Any]) -> None:
    answer = post(api, item["question"])
    AskResponse.model_validate(answer)
    assert answer["mode"] in ("replay", "cache") and answer["cost_gbp"] == 0
    assert answer["route"] == item["route"]
    if item["expect"] == "abstain":
        assert answer["status"] == "abstained"
        assert (
            answer["sentences"] == []
            and answer["message"] in ask_config().messages.model_dump().values()
        )
        return
    assert answer["status"] == "answered", answer
    assert set(item["paragraphs"]) <= cited(answer)
    for s in item.get("answer_contains", []):
        assert s in text_of(answer)
    for s in item.get("answer_excludes", []):
        assert s not in text_of(answer)
    for key in ("related_finding_id", "related_rfi_id"):
        if key in item:
            assert answer[key] == item[key], key
    for sentence in answer["sentences"]:
        assert sentence["citations"] or sentence["finding_id"]
        for c in sentence["citations"]:
            assert c["paragraph_text"][c["quote_start"] : c["quote_end"]] == c["citation"]["quote"]
            assert c["role"] == "cited in answer"


def _check_ask_render() -> Any:
    sys.path.insert(0, str(BACKEND_DIR / "tools"))
    import check_ask

    planted = yaml.safe_load((DATAROOM_DIR / "planted_facts.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((DATAROOM_DIR / "manifest.yaml").read_text(encoding="utf-8"))
    ask_yaml = yaml.safe_load((BACKEND_DIR / "ask.yaml").read_text(encoding="utf-8"))
    return lambda q, params: check_ask.render(q, params, planted, manifest, ask_yaml)[0]


@pytest.mark.parametrize(
    "item", [i for i in GOLDEN if i["route"] == "relationship"], ids=lambda i: i["id"]
)
def test_relationship_answers_are_the_templates(api: TestClient, item: dict[str, Any]) -> None:
    render = _check_ask_render()
    assert text_of(post(api, item["question"])) == render(item["graph_query"], item["params"])


def test_absence_sentences_link_their_finding(api: TestClient) -> None:
    answer = post(api, "Does the project have rights over every parcel the cable crosses?")
    [absence] = [s for s in answer["sentences"] if not s["citations"]]
    assert absence["finding_id"] == "F-01" and "RFI-01" in absence["text"]


@pytest.mark.parametrize("fixture", ["r01", "r03", "r04", "a01", "x01"])
def test_the_ui_fixtures_match_the_api(api: TestClient, fixture: str) -> None:
    want = json.loads((FIXTURES / f"{fixture}.json").read_text(encoding="utf-8"))
    got = post(api, want["question"])
    for key in ("route", "status", "message", "related_finding_id", "related_rfi_id"):
        assert got[key] == want[key], key
    if want["route"] == "relationship":
        assert text_of(got) == text_of(want)
    assert cited(got) == cited(want)


# ---------- the cache, live questions and limits ----------


def test_a_repeated_question_is_served_from_the_cache(api: TestClient) -> None:
    first = post(api, "What price does the PPA pay per MWh?")
    again = post(api, "what price does the ppa pay per MWh")
    assert again["mode"] == "cache"
    assert text_of(again) == text_of(first) and again["id"] != first["id"]


def test_free_form_is_unavailable_with_live_off(api: TestClient) -> None:
    answer = post(api, "Who signed the grid offer on behalf of the customer?")
    assert answer["status"] == "unavailable" and answer["route"] is None
    assert answer["message"] == ask_config().messages.unavailable_live_off
    # A suggested question still answers, from its recording.
    assert post(api, "What is the target commercial operation date?")["status"] == "answered"


def test_live_answers_are_capped_and_never_recorded(
    world: tuple[str, RecordingStore],
    client_for: ClientFor,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    url, _ = world
    empty = RecordingStore(tmp_path)  # nothing recorded: every call must go live
    monkeypatch.setenv("ASK_LIVE", "true")
    with connect(url) as conn:
        conn.execute("DELETE FROM asks")  # no cached answers either
    with client_for(url) as client:
        client.app.state.ask_llm = factory(empty, PerfectTransport())  # type: ignore[attr-defined]
        try:
            live = post(client, "When will the grid connection be made?")
            assert (live["mode"], live["status"]) == ("live", "answered")
            assert live["cost_gbp"] > 0
            assert list(tmp_path.glob("*.json")) == []  # live answers are never recorded

            with connect(url) as conn:
                conn.execute(
                    "INSERT INTO asks (id, session_id, question, question_norm, status, mode, "
                    "response, latency_ms) SELECT 'cap-' || g, %s, 'Earlier question?', "
                    "'earlier question', 'answered', 'live', '{}', 1 "
                    "FROM generate_series(1, 20) g",
                    (client.cookies["lens_session"],),
                )
            capped = post(client, "How much rent does the tenant pay?")
            assert capped["status"] == "unavailable"
            assert capped["message"] == ask_config().messages.unavailable_limit
        finally:
            del client.app.state.ask_llm  # type: ignore[attr-defined]


def test_every_question_is_stored(api: TestClient, world: tuple[str, RecordingStore]) -> None:
    post(api, "How much rent does the tenant pay?")
    with connect(world[0]) as conn:
        row = conn.execute(
            "SELECT route, status, retrieved FROM asks WHERE question = %s "
            "AND mode <> 'cache' ORDER BY created_at DESC LIMIT 1",
            ("How much rent does the tenant pay?",),
        ).fetchone()
    assert row is not None and row[:2] in (("lookup", "answered"),)
    assert any(r["paragraph_id"] == "lease:p1:¶4" for r in row[2])


@pytest.mark.parametrize("question", ["hi", "x" * 501])
def test_questions_outside_3_to_500_characters_are_a_400(api: TestClient, question: str) -> None:
    assert api.post("/api/ask", json={"question": question}).status_code == 400


def test_suggestions_are_the_suggested_golden_questions(api: TestClient) -> None:
    want = json.loads((FIXTURES / "suggestions.json").read_text(encoding="utf-8"))
    assert api.get("/api/ask/suggestions").json() == want


# ---------- replay integrity ----------


def test_changed_retrieval_raises_retrieval_drift(
    world: tuple[str, RecordingStore], tmp_path: Path
) -> None:
    url, store = world
    local = RecordingStore(tmp_path)
    for path in store.directory.glob("*.json"):
        (tmp_path / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    question = "What is the maximum import capacity?"
    [key] = [
        p.stem
        for p in tmp_path.glob("*.json")
        if (r := local.load(p.stem))
        and r.purpose == "ask:answer"
        and r.metadata["question"] == question
    ]
    recording = local.load(key)
    assert recording is not None
    local.save(
        recording.model_copy(
            update={"key": "other", "metadata": {**recording.metadata, "retrieved": ["x"]}}
        )
    )
    (tmp_path / f"{key}.json").unlink()
    with connect(url) as conn, pytest.raises(RetrievalDrift):
        ask(
            conn,
            question,
            session_id=None,
            policy="replay",
            store=False,
            llm_factory=factory(local, NoNetwork()),
            recordings=local,
        )


# ---------- answer verification (step 6) ----------


def draft(*sentences: tuple[str, list[tuple[str, str]]]) -> AnswerDraft:
    return AnswerDraft.model_validate(
        {
            "sentences": [
                {"text": t, "citations": [{"paragraph_id": p, "quote": q} for p, q in cites]}
                for t, cites in sentences
            ],
            "abstain": False,
            "abstain_reason": None,
        }
    )


@pytest.fixture
def published(world: tuple[str, RecordingStore]) -> Iterator[Any]:
    with connect(world[0]) as conn:
        yield load_published(conn, None)


RETRIEVED = {"lease:p1:¶5", "grid_offer:p2:¶3"}


def test_verification_keeps_a_supported_sentence(published: Any) -> None:
    ok = verify_draft(
        published, draft(("The term is 35 years.", [("lease:p1:¶5", "35 years")])), RETRIEVED
    )
    assert (len(ok.sentences), ok.dropped) == (1, 0)
    [c] = ok.sentences[0].citations
    assert c.paragraph_text[c.quote_start : c.quote_end] == "35 years"


def test_verification_drops_a_tampered_quote(published: Any) -> None:
    result = verify_draft(
        published,
        draft(("The term is 35 years.", [("lease:p1:¶5", "thirty-five years")])),
        RETRIEVED,
    )
    assert (result.sentences, result.dropped) == ([], 1)


def test_verification_drops_a_citation_that_was_not_retrieved(published: Any) -> None:
    result = verify_draft(
        published, draft(("Rent is £1,150.", [("lease:p1:¶4", "£1,150")])), RETRIEVED
    )
    assert (result.sentences, result.dropped) == ([], 1)


def test_verification_drops_an_unsupported_number(published: Any) -> None:
    result = verify_draft(
        published,
        draft(
            ("The lease runs for 40 years.", [("lease:p1:¶5", "35 years")]),
            ("The connection date is 1 October 2029.", [("grid_offer:p2:¶3", "1 October 2029")]),
            ("It connects on 2 October 2029.", [("grid_offer:p2:¶3", "1 October 2029")]),
        ),
        RETRIEVED,
    )
    assert [s.text for s in result.sentences] == ["The connection date is 1 October 2029."]
    assert result.dropped == 2


def test_verification_caps_the_number_of_sentences(published: Any) -> None:
    one = ("The term is 35 years.", [("lease:p1:¶5", "35 years")])
    result = verify_draft(published, draft(*[one] * 6), RETRIEVED)
    assert (len(result.sentences), result.dropped) == (ask_config().max_sentences, 2)


# ---------- routing ----------


def decision(route: str, query: str | None = None, **params: Any) -> RouteDecision:
    return RouteDecision(route=route, graph_query=query, params=params)  # type: ignore[arg-type]


def test_routing_is_checked_against_ask_yaml() -> None:
    assert validate(decision("relationship", "parties", agreement="Lease")).graph_query == "parties"
    assert validate(decision("relationship", "parties")).params == {"agreement": None}
    assert validate(decision("relationship", "no_such_query")).route == "lookup"
    assert validate(decision("relationship", "parties", agreement="Mortgage")).route == "lookup"
    assert validate(decision("relationship", "property_sources")).route == "lookup"  # param needed
    assert validate(decision("relationship", "parties", extra="x")).route == "lookup"
    assert validate(decision("out_of_scope")).route == "out_of_scope"
