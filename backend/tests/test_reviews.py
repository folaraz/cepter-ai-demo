"""C9: reviews, sessions and undo, through the API."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db.migrate import migrate
from app.db.pool import connect
from app.db.repositories import reviews as reviews_repo
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer
from app.pipeline import run_pipeline
from app.reviews.fingerprint import evidence_fingerprint
from app.reviews.golden import GOLDEN, export_session_corrections, read_golden
from app.reviews.housekeeping import purge_expired_sessions
from app.reviews.seed import apply_seed
from tests.conftest import ClientFor
from tests.test_consolidate import PerfectTransport

pytestmark = pytest.mark.db

REASON = "Grid import and export limits are different things; the 45 MW is the grid limit."


@pytest.fixture
def published_db(tmp_path: Path, empty_database: str) -> str:
    migrate(empty_database)
    with connect(empty_database) as conn:
        ingest_dataroom(conn)
        llm = AnthropicLLMClient(
            trace=db_tracer(conn), store=RecordingStore(tmp_path), transport=PerfectTransport()
        )
        result = run_pipeline(conn, llm, kind="published", mode="record", publish=True)
        apply_seed(conn, result.run_id)
    return empty_database


@pytest.fixture
def visitor(published_db: str, client_for: ClientFor) -> Iterator[TestClient]:
    with client_for(published_db) as client:
        yield client


def row(client: TestClient, finding_id: str) -> dict[str, Any]:
    return next(f for f in client.get("/api/summary").json()["findings"] if f["id"] == finding_id)


def correct_f03(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/findings/F-03/review",
        json={"action": "correct", "corrected_result": "fail", "reason": REASON},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


# ---------- the demo sequence ----------


def test_the_demo_sequence(visitor: TestClient) -> None:
    assert (row(visitor, "F-03")["result"], row(visitor, "F-03")["review"]) == (
        "conflict",
        "needs_review",
    )

    reviewed = correct_f03(visitor)
    assert reviewed["golden_item_id"] == "corr-002"
    assert reviewed["eval"]["state"] == "stale"
    assert (reviewed["finding"]["result"], reviewed["finding"]["review"]) == ("fail", "corrected")
    assert (row(visitor, "F-03")["result"], row(visitor, "F-03")["review"]) == ("fail", "corrected")
    # Corrected to a plain fail, the export-capacity RFI is withdrawn for this visitor.
    assert [r["id"] for r in visitor.get("/api/rfi").json()] == ["RFI-01", "RFI-02"]

    # (C11 adds: run the eval here and see passing with 2 of 2 corrections held.)

    # Another visitor (a separate cookie jar on the same running app) sees none of it...
    other = TestClient(visitor.app)
    assert (row(other, "F-03")["result"], row(other, "F-03")["review"]) == (
        "conflict",
        "needs_review",
    )
    assert len(other.get("/api/rfi").json()) == 3
    # ...and can't undo it.
    stranger_undo = other.post("/api/reviews/undo", json={"undo_token": reviewed["undo_token"]})
    assert stranger_undo.status_code == 404

    undone = visitor.post("/api/reviews/undo", json={"undo_token": reviewed["undo_token"]})
    assert undone.status_code == 200
    assert (undone.json()["result"], undone.json()["review"]) == ("conflict", "needs_review")
    assert (row(visitor, "F-03")["result"], row(visitor, "F-03")["review"]) == (
        "conflict",
        "needs_review",
    )
    # Undoing twice finds nothing to undo.
    again = visitor.post("/api/reviews/undo", json={"undo_token": reviewed["undo_token"]})
    assert again.status_code == 404


# ---------- the three actions ----------


def test_accept_marks_it_lawyer_verified_with_no_golden_item(visitor: TestClient) -> None:
    body = visitor.post("/api/findings/F-02/review", json={"action": "accept"}).json()
    assert body["golden_item_id"] is None
    assert (body["finding"]["result"], body["finding"]["review"]) == ("fail", "lawyer_verified")


def test_reject_keeps_the_result(visitor: TestClient) -> None:
    body = visitor.post(
        "/api/findings/F-02/review", json={"action": "reject", "reason": "Dates are indicative."}
    ).json()
    assert body["golden_item_id"] == "corr-002"
    assert (body["finding"]["result"], body["finding"]["review"]) == ("fail", "rejected")


def test_corrections_are_numbered_after_every_visible_one(visitor: TestClient) -> None:
    first = correct_f03(visitor)
    second = visitor.post(
        "/api/findings/F-01/review", json={"action": "reject", "reason": "Easement is on file."}
    ).json()
    assert (first["golden_item_id"], second["golden_item_id"]) == ("corr-002", "corr-003")
    visitor.post("/api/reviews/undo", json={"undo_token": second["undo_token"]})
    third = visitor.post(
        "/api/findings/F-05/review", json={"action": "reject", "reason": "Discharged in 2025."}
    ).json()
    assert third["golden_item_id"] == "corr-003"  # the undone item is gone with its review


def test_the_latest_review_wins(visitor: TestClient) -> None:
    correct_f03(visitor)
    visitor.post("/api/findings/F-03/review", json={"action": "accept"})
    assert (row(visitor, "F-03")["result"], row(visitor, "F-03")["review"]) == (
        "conflict",
        "lawyer_verified",
    )


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"action": "reject"}, "A reason is required"),
        ({"action": "reject", "reason": "   "}, "A reason is required"),
        ({"action": "correct", "reason": "x"}, "Choose the corrected result"),
        ({"action": "accept", "corrected_result": "pass"}, "Only a correction"),
    ],
)
def test_invalid_reviews_are_refused_with_a_plain_message(
    visitor: TestClient, body: dict[str, Any], message: str
) -> None:
    response = visitor.post("/api/findings/F-03/review", json=body)
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_unknown_finding(visitor: TestClient) -> None:
    assert visitor.post("/api/findings/F-99/review", json={"action": "accept"}).status_code == 404


def test_the_review_stores_the_evidence_fingerprint(visitor: TestClient, published_db: str) -> None:
    correct_f03(visitor)
    finding = visitor.get("/api/findings/F-03").json()
    with connect(published_db) as conn:
        [review] = [
            r
            for r in reviews_repo.list_visible_reviews(conn, visitor.cookies["lens_session"])
            if r.session_id
        ]
    assert review.evidence_fingerprint == evidence_fingerprint(finding["evidence"])
    assert review.reason == REASON


# ---------- sessions ----------


def test_first_request_sets_a_private_session_cookie(visitor: TestClient) -> None:
    response = visitor.get("/api/health")
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("lens_session=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=604800" in cookie
    assert "Secure" not in cookie
    # Only once: the next request carries it.
    assert "set-cookie" not in visitor.get("/api/health").headers


def test_cookie_is_secure_when_configured(
    published_db: str, client_for: ClientFor, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COOKIE_SECURE", "true")
    with client_for(published_db) as client:
        assert "Secure" in client.get("/api/health").headers["set-cookie"]


# ---------- housekeeping ----------


def test_housekeeping_drops_week_old_session_state_only(published_db: str) -> None:
    with connect(published_db) as conn:
        conn.execute(
            "INSERT INTO reviews (session_id, finding_id, check_id, action, evidence_fingerprint, "
            "undo_token, created_at) VALUES "
            "('old', 'F-02', 'grid_before_cod', 'accept', 'x', 'old-1', now() - interval '8 days'),"
            "('new', 'F-02', 'grid_before_cod', 'accept', 'x', 'new-1', now() - interval '6 days')"
        )
        conn.execute(
            "UPDATE reviews SET created_at = now() - interval '30 days' WHERE session_id IS NULL"
        )
        deleted = purge_expired_sessions(conn)
        tokens = {r[0] for r in conn.execute("SELECT undo_token FROM reviews").fetchall()}
    assert deleted["reviews"] == 1
    assert "old-1" not in tokens and "new-1" in tokens
    assert {t for t in tokens if t.startswith("seed:")} == {"seed:F-04:accept", "seed:F-07:correct"}


# ---------- promoting corrections to CI ----------


def test_golden_export_appends_the_sessions_corrections(
    visitor: TestClient, published_db: str, tmp_path: Path
) -> None:
    golden = tmp_path / "golden.jsonl"
    golden.write_text(GOLDEN.read_text(encoding="utf-8"), encoding="utf-8")
    correct_f03(visitor)
    visitor.post("/api/findings/F-02/review", json={"action": "accept"})  # not a golden item

    with connect(published_db) as conn:
        session = visitor.cookies["lens_session"]
        written = export_session_corrections(conn, session, golden)
        again = export_session_corrections(conn, session, golden)

    assert again == []
    [item] = written
    assert item["id"] == "corr-002" and item["kind"] == "correction"
    assert (item["check_id"], item["finding_id"], item["expect"], item["was"]) == (
        "export_capacity_consistent",
        "F-03",
        "fail",
        "conflict",
    )
    assert item["evidence_fingerprint"].startswith("sha256:")
    items = read_golden(golden)
    assert items[:-1] == read_golden(GOLDEN) and items[-1] == item
    assert set(item) == set(next(i for i in items if i["id"] == "corr-001"))
    assert json.loads(golden.read_text(encoding="utf-8").splitlines()[-1]) == item


def test_seed_correction_matches_its_golden_item(published_db: str) -> None:
    """corr-001's fingerprint is what the seed review stores: the override holds."""
    with connect(published_db) as conn:
        [seed] = [r for r in reviews_repo.list_visible_reviews(conn, None) if r.golden_item_id]
    corr_001 = next(i for i in read_golden() if i["id"] == "corr-001")
    assert seed.evidence_fingerprint == corr_001["evidence_fingerprint"]
