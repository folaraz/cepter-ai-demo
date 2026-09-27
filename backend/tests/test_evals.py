"""C11: the eval harness, the gate and the eval endpoints."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.checks import runner
from app.checks.runner import Outcome
from app.db.migrate import migrate
from app.db.pool import connect
from app.domain.evals import EvalRun
from app.evals.golden import golden_set
from app.evals.harness import run_eval
from app.evals.report import format_report
from app.evals.status import eval_status
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.client import LLMClient
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer
from app.pipeline import run_pipeline
from app.published import load_published
from app.reviews.seed import apply_seed
from app.reviews.service import submit_review, undo_review
from tests.conftest import ClientFor
from tests.test_consolidate import PerfectTransport

pytestmark = pytest.mark.db

REASON = "The 45 MW is the grid's limit, a different thing from permitted capacity."


def perfect_llm(tmp_path: Path) -> Any:
    """The pipeline's model calls answered by the perfect extraction, so evals run
    without recordings."""

    def factory(conn: psycopg.Connection) -> LLMClient:
        return AnthropicLLMClient(
            trace=db_tracer(conn),
            store=RecordingStore(tmp_path),
            transport=PerfectTransport(),
            default_mode="record",
        )

    return factory


@pytest.fixture
def db(tmp_path: Path, empty_database: str) -> Iterator[psycopg.Connection]:
    migrate(empty_database)
    with connect(empty_database) as conn:
        ingest_dataroom(conn)
        result = run_pipeline(conn, perfect_llm(tmp_path)(conn), kind="published", publish=True)
        apply_seed(conn, result.run_id)
        yield conn


def metric(run: EvalRun, name: str) -> tuple[int, int]:
    m: dict[str, Any] = run.metrics[name]  # type: ignore[assignment]
    return m["passed"], m["total"]


def failures(run: EvalRun, name: str) -> list[str]:
    m: dict[str, Any] = run.metrics[name]  # type: ignore[assignment]
    return list(m["failures"])


def correct_f03(conn: psycopg.Connection, session: str) -> str:
    review = submit_review(
        conn, load_published(conn, session), session, "F-03", "correct", REASON, "fail"
    )
    return review.undo_token


# ---------- the harness ----------


def test_the_pipeline_meets_every_target(db: psycopg.Connection, tmp_path: Path) -> None:
    run = run_eval(db, perfect_llm(tmp_path)(db), session_id=None, gate=0.90)
    assert run.state == "passing", format_report(run)
    assert metric(run, "extraction") == (15, 15)
    assert metric(run, "conflicts") == (1, 1)
    assert metric(run, "checks") == (3, 3)
    assert metric(run, "corrections") == (1, 1)
    assert metric(run, "learned") == (1, 1)  # corr-001: name normalisation fixed it
    assert run.citation_validity == 1 and run.score == 1
    assert run.golden_count == 20 and run.run_id is not None
    assert run.metrics["llm_calls"] == 5 and run.cost_gbp is not None and run.cost_gbp > 0


def test_a_broken_check_is_reported(
    db: psycopg.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flipping grid_before_cod loses a check item. Note the spec's gate alone does not
    fail on it (mean of five ratios is 0.93 > 0.90); the C7 tests are what fail in CI."""
    monkeypatch.setitem(
        runner._REGISTRY, "grid_before_cod", lambda inputs, view: Outcome("pass", {})
    )
    run = run_eval(db, perfect_llm(tmp_path)(db), session_id=None, gate=0.90)
    assert metric(run, "checks") == (2, 3)
    assert failures(run, "checks") == ["g-c03"]
    assert float(run.score or 0) == pytest.approx(0.9333, abs=1e-4)
    # A stricter gate catches it.
    strict = run_eval(db, perfect_llm(tmp_path)(db), session_id=None, gate=0.95)
    assert strict.state == "failing"


def test_an_edited_cited_paragraph_makes_the_correction_lapse(
    db: psycopg.Connection, tmp_path: Path
) -> None:
    correct_f03(db, "s-1")
    held = run_eval(db, perfect_llm(tmp_path)(db), session_id="s-1", gate=0.90)
    assert metric(held, "corrections") == (2, 2) and held.state == "passing"

    # The grid offer's capacity paragraph changes after the lawyer reviewed it.
    db.execute(
        "UPDATE paragraphs SET text = text || ' This figure is under review.' "
        "WHERE id = 'grid_offer:p2:¶3'"
    )
    lapsed = run_eval(db, perfect_llm(tmp_path)(db), session_id="s-1", gate=0.90)
    assert metric(lapsed, "corrections") == (1, 2)
    assert failures(lapsed, "corrections") == ["corr-002"]
    assert lapsed.state == "failing"


def test_a_citation_that_is_not_verbatim_fails_the_gate(
    db: psycopg.Connection, tmp_path: Path
) -> None:
    run = run_eval(db, perfect_llm(tmp_path)(db), session_id=None, gate=0.90)
    db.execute(
        "UPDATE provenance SET quote = 'tampered' WHERE id = "
        "(SELECT min(id) FROM provenance WHERE run_id = %s)",
        (run.run_id,),
    )
    from app.evals.harness import score_run

    assert run.run_id is not None
    outcome = score_run(db, run.run_id, golden_set(db, None), 0.90)
    assert outcome.citation_validity is not None and outcome.citation_validity < 1
    assert outcome.state == "failing"


def test_a_missing_recording_is_an_error_not_a_pass(db: psycopg.Connection, tmp_path: Path) -> None:
    replay_only = AnthropicLLMClient(
        trace=db_tracer(db), store=RecordingStore(tmp_path / "empty"), default_mode="replay"
    )
    run = run_eval(db, replay_only, session_id=None, gate=0.90)
    assert run.state == "error" and "MissingRecording" in (run.error or "")
    assert eval_status(db, None).state == "failing"


# ---------- the golden set ----------


def test_the_golden_set_is_the_file_plus_the_sessions_corrections(
    db: psycopg.Connection,
) -> None:
    base = golden_set(db, None)
    assert len(base.items) == 20
    token = correct_f03(db, "s-1")
    mine = golden_set(db, "s-1")
    assert len(mine.items) == 21 and mine.hash != base.hash
    assert golden_set(db, "s-2").hash == base.hash  # another session is unaffected
    undo_review(db, "s-1", token)
    assert golden_set(db, "s-1").hash == base.hash


def test_a_correction_supersedes_the_check_item_for_its_check(db: psycopg.Connection) -> None:
    submit_review(
        db, load_published(db, "s-1"), "s-1", "F-02", "reject", "Dates are indicative.", None
    )
    ids = {i["id"] for i in golden_set(db, "s-1").items}
    assert "g-c03" not in ids and "corr-002" in ids  # the lawyer wins


# ---------- status ----------


def test_status_goes_stale_and_back(db: psycopg.Connection, tmp_path: Path) -> None:
    assert eval_status(db, "s-1").state == "stale"  # nothing measured yet
    run_eval(db, perfect_llm(tmp_path)(db), session_id="s-1", gate=0.90)
    assert eval_status(db, "s-1").state == "passing"

    token = correct_f03(db, "s-1")
    stale = eval_status(db, "s-1")
    assert (stale.state, stale.golden_count, stale.corrections_total) == ("stale", 21, 2)

    undo_review(db, "s-1", token)  # back to the set the last eval measured
    assert eval_status(db, "s-1").state == "passing"


def test_a_session_without_evals_sees_the_deploy_eval(
    db: psycopg.Connection, tmp_path: Path
) -> None:
    run_eval(db, perfect_llm(tmp_path)(db), session_id=None, gate=0.90)
    status = eval_status(db, "new-visitor")
    assert (status.state, status.corrections_held, status.corrections_total) == ("passing", 1, 1)


# ---------- the demo sequence through the API ----------


@pytest.fixture
def api(
    db: psycopg.Connection, empty_database: str, client_for: ClientFor, tmp_path: Path
) -> Iterator[TestClient]:
    with client_for(empty_database) as client:
        client.app.state.eval_llm = perfect_llm(tmp_path)  # type: ignore[attr-defined]
        yield client
        del client.app.state.eval_llm  # type: ignore[attr-defined]


def f03(client: TestClient) -> tuple[str, str]:
    row = client.get("/api/findings/F-03").json()
    return row["result"], row["review"]


def test_the_demo_sequence(api: TestClient) -> None:
    reviewed = api.post(
        "/api/findings/F-03/review",
        json={"action": "correct", "corrected_result": "fail", "reason": REASON},
    ).json()
    assert reviewed["golden_item_id"] == "corr-002"
    assert reviewed["eval"]["state"] == "stale"

    started = api.post("/api/evals/run").json()
    assert started["state"] == "running"
    latest = api.get("/api/evals/latest").json()  # the test client finishes the task first
    assert latest["state"] == "passing"
    assert (latest["corrections_held"], latest["corrections_total"]) == (2, 2)
    assert latest["golden_count"] == 21
    assert api.get("/api/summary").json()["eval"] == latest

    undone = api.post("/api/reviews/undo", json={"undo_token": reviewed["undo_token"]})
    assert (undone.json()["result"], undone.json()["review"]) == ("conflict", "needs_review")
    assert f03(api) == ("conflict", "needs_review")
    assert api.get("/api/evals/latest").json()["state"] == "stale"  # measured with corr-002

    other = TestClient(api.app)  # a second visitor
    assert f03(other) == ("conflict", "needs_review")
    theirs = other.get("/api/evals/latest").json()
    assert (theirs["state"], theirs["golden_count"]) == ("stale", 20)  # nothing run for them


def test_one_running_eval_per_session(api: TestClient, db: psycopg.Connection) -> None:
    api.get("/api/health")
    session = api.cookies["lens_session"]
    db.execute(
        "INSERT INTO eval_runs (session_id, state, gate, golden_hash, golden_count) "
        "VALUES (%s, 'running', 0.9, 'x', 20)",
        (session,),
    )
    assert api.post("/api/evals/run").json()["state"] == "running"
    count = db.execute("SELECT count(*) FROM eval_runs WHERE session_id = %s", (session,))
    assert count.fetchone() == (1,)


# ---------- the report ----------


def test_the_report_table(db: psycopg.Connection, tmp_path: Path) -> None:
    run = run_eval(db, perfect_llm(tmp_path)(db), session_id=None, gate=0.90)
    table = format_report(run)
    for label, value in (
        ("Extraction (facts and edges)", "15/15"),
        ("Conflicts", "1/1"),
        ("Checks", "3/3"),
        ("Corrections held", "1/1 (1 learned)"),
        ("Citation validity", "100%"),
        ("State", "PASSING"),
    ):
        assert f"{label:<32}{value:>18}" in table, table
