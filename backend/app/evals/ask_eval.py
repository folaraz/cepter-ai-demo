"""Ask's part of the accuracy check (SPEC C11 and C14).

Every question in evals/ask_golden.jsonl goes through Ask against the eval run, replaying
the recorded model answers:

    retrieval recall   lookups expected to answer: every expected paragraph is in the top
                       top_k by hybrid search (no model involved)
    answer accuracy    questions expected to answer: answered, cites every expected
                       paragraph, contains every `answer_contains` and no `answer_excludes`,
                       and the related finding and RFI match when given
    abstention         questions expected to abstain: abstained

Every quote Ask serves also counts toward citation validity. Reported, not gated: routing
accuracy, keyword-only and vector-only recall, sentences dropped by verification.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from psycopg import Connection

from app.api.models import AskResponse
from app.ask.service import ask
from app.evals.ratio import Ratio
from app.llm.anthropic_client import AnthropicLLMClient
from app.retrieval.calibrate import read_ask_golden
from app.retrieval.config import retrieval_config
from app.retrieval.search import keyword_search, search, vector_search

AskRunner = Callable[[Connection, str, str], AskResponse]  # (conn, question, run_id)


def replay_runner(conn: Connection, question: str, run_id: str) -> AskResponse:
    """Ask in replay mode: a missing recording raises, so the eval errors instead of
    calling the model."""
    return ask(
        conn,
        question,
        session_id=None,
        policy="replay",
        run_id=run_id,
        store=False,
        llm_factory=lambda trace: AnthropicLLMClient(trace=trace),
    )


@dataclass
class AskScores:
    ratios: dict[str, Ratio]
    citations: Ratio
    report: dict[str, Any] = field(default_factory=dict)


def score_ask(conn: Connection, run_id: str, runner: AskRunner) -> AskScores:
    top_k = retrieval_config().top_k
    recall, keyword_recall, vector_recall = Ratio(), Ratio(), Ratio()
    accuracy, abstention, citations, routing = Ratio(), Ratio(), Ratio(), Ratio()
    dropped = 0

    for item in read_ask_golden():
        question = item["question"]
        expected = set(item.get("paragraphs") or [])
        if item["route"] == "lookup" and item["expect"] == "answer":
            hybrid = {h.paragraph_id for h in search(conn, question).hits}
            recall.add(expected <= hybrid, item["id"])
            keyword = {pid for pid, _ in keyword_search(conn, question, top_k)}
            keyword_recall.add(expected <= keyword, item["id"])
            vector = {pid for pid, _, _ in vector_search(conn, question, top_k)}
            vector_recall.add(expected <= vector, item["id"])

        answer = runner(conn, question, run_id)
        routing.add(answer.route == item["route"], item["id"])
        dropped += answer.dropped_sentences
        for sentence in answer.sentences:
            for c in sentence.citations:
                ok = c.paragraph_text[c.quote_start : c.quote_end] == c.citation.quote
                citations.add(ok, f"{item['id']} {c.citation.paragraph_id}")
        if item["expect"] == "abstain":
            abstention.add(answer.status == "abstained", item["id"])
        else:
            accuracy.add(_accurate(answer, item), item["id"])

    return AskScores(
        ratios={
            "retrieval_recall": recall,
            "answer_accuracy": accuracy,
            "abstention": abstention,
        },
        citations=citations,
        report={
            "routing": {"passed": routing.passed, "total": routing.total},
            "keyword_only_recall": {"passed": keyword_recall.passed, "total": keyword_recall.total},
            "vector_only_recall": {"passed": vector_recall.passed, "total": vector_recall.total},
            "dropped_sentences": dropped,
        },
    )


def _accurate(answer: AskResponse, item: dict[str, Any]) -> bool:
    if answer.status != "answered":
        return False
    text = " ".join(s.text for s in answer.sentences)
    cited = {c.citation.paragraph_id for s in answer.sentences for c in s.citations}
    return (
        set(item["paragraphs"]) <= cited
        and all(s in text for s in item.get("answer_contains", []))
        and not any(s in text for s in item.get("answer_excludes", []))
        and item.get("related_finding_id", answer.related_finding_id) == answer.related_finding_id
        and item.get("related_rfi_id", answer.related_rfi_id) == answer.related_rfi_id
    )
