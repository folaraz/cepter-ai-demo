"""C8/C10 contract test: a fresh database, the pipeline, the seed reviews, then every GET
endpoint compared with design/api/fixtures/ under the rules in its README.

The pipeline runs on the perfect extraction (tests/perfect_extraction.py) so this holds
without recordings; test_contract_on_the_recorded_extraction repeats it on the recorded
model answers once they exist.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import REPO_ROOT
from app.db.pool import connect
from app.evals.harness import run_eval
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer
from app.pipeline import run_pipeline
from app.reviews.seed import apply_seed
from tests.conftest import ClientFor
from tests.test_consolidate import PerfectTransport

pytestmark = pytest.mark.db

EXPECTED = REPO_ROOT / "design" / "api" / "fixtures"


def expected(name: str) -> Any:
    return json.loads((EXPECTED / name).read_text(encoding="utf-8"))


@pytest.fixture
def api(tmp_path: Path, empty_database: str, client_for: ClientFor) -> Iterator[TestClient]:
    """The API over a freshly published run with the seed reviews applied."""
    from app.db.migrate import migrate

    migrate(empty_database)
    with connect(empty_database) as conn:
        ingest_dataroom(conn)
        llm = AnthropicLLMClient(
            trace=db_tracer(conn), store=RecordingStore(tmp_path), transport=PerfectTransport()
        )
        result = run_pipeline(conn, llm, kind="published", mode="record", publish=True)
        apply_seed(conn, result.run_id)
        # The release step ends with `lens eval`, so a deployed Summary has a measured eval.
        run_eval(conn, llm, session_id=None, gate=0.90)
    with client_for(empty_database) as client:
        yield client


# ---------- comparison rules (design/api/fixtures/README.md) ----------

ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def assert_evidence(got: list[dict[str, Any]], want: list[dict[str, Any]]) -> None:
    """Exact, except the quote: the model chooses the span, so it may differ, but it must
    be the paragraph's own characters at its offsets."""
    assert len(got) == len(want)
    for g, w in zip(got, want, strict=True):
        if w["kind"] == "missing":
            assert g == w
            continue
        g, w = dict(g), dict(w)
        gq, wq = dict(g.pop("citation")), dict(w.pop("citation"))
        start, end = g.pop("quote_start"), g.pop("quote_end")
        w.pop("quote_start"), w.pop("quote_end")
        assert g["paragraph_text"][start:end] == gq.pop("quote")
        wq.pop("quote")
        assert (g, gq) == (w, wq)


def test_summary(api: TestClient) -> None:
    got, want = api.get("/api/summary").json(), expected("summary.json")

    run = got.pop("run")
    assert isinstance(run["id"], str) and ISO_DATETIME.match(run["at"])
    assert run["checks_total"] == want.pop("run")["checks_total"]

    ev = got.pop("eval")
    want.pop("eval")
    assert set(ev) == set(expected("eval-latest.json"))
    assert 0 <= ev["score"] <= 1 and 0 <= ev["citation_validity"] <= 1
    assert ev["gate"] == 0.9 and ISO_DATETIME.match(ev["last_run_at"])
    assert (ev["state"], ev["golden_count"]) == ("passing", 20)
    assert (ev["corrections_held"], ev["corrections_total"]) == (1, 1)

    for key in want:
        assert got[key] == want[key], key
    assert set(got) == set(want)


@pytest.mark.parametrize("finding_id", [f"F-0{n}" for n in range(1, 9)])
def test_findings(api: TestClient, finding_id: str) -> None:
    got, want = (
        api.get(f"/api/findings/{finding_id}").json(),
        expected(f"findings/{finding_id}.json"),
    )
    assert_evidence(got.pop("evidence"), want.pop("evidence"))
    assert got == want


DOCUMENT_IDS = ["lease", "planning", "grid", "ppa", "site"]


def test_documents(api: TestClient) -> None:
    assert api.get("/api/documents").json() == expected("documents.json")


@pytest.mark.parametrize("document_id", DOCUMENT_IDS)
def test_document(api: TestClient, document_id: str) -> None:
    got = api.get(f"/api/documents/{document_id}").json()
    assert got == expected(f"documents/{document_id}.json")
    text = {q["id"]: q["text"] for page in got["pages"] for q in page["paragraphs"]}
    for note in got["notes"]:  # every note marks a real span of its own paragraph
        assert 0 <= note["quote_start"] < note["quote_end"] <= len(text[note["paragraph_id"]])


def test_an_unknown_document_is_a_404(api: TestClient) -> None:
    assert api.get("/api/documents/deed").status_code == 404


def test_rfi(api: TestClient) -> None:
    assert api.get("/api/rfi").json() == expected("rfi.json")


def test_rfi_markdown_is_for_the_seller(api: TestClient) -> None:
    response = api.get("/api/rfi.md")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    text = response.text
    assert text.startswith("# Requests for information: Brackenfield Solar & Storage\n")
    assert "### RFI-01: Cable route rights (Critical)" in text
    assert "**Request.** Please provide the executed deed(s) of easement" in text
    assert "- Title plans for Parcels 14 and 15" in text
    # Nothing internal reaches the seller.
    for internal in ("cable_route_rights", "F-01", "Blocks check"):
        assert internal not in text, internal
    assert not re.search(r"\br-\d", text)  # no run IDs


def test_passed_and_unknown_findings(api: TestClient) -> None:
    passed = api.get("/api/findings/F-06").json()
    assert passed["result"] == "pass" and passed["review"] == "ai_extracted"
    corrected = api.get("/api/findings/F-07").json()  # seed correction to pass: corr-001
    assert (corrected["result"], corrected["review"]) == ("pass", "corrected")
    missing = api.get("/api/findings/F-99")
    assert missing.status_code == 404


def test_seeding_twice_adds_nothing(empty_database: str, api: TestClient) -> None:
    with connect(empty_database) as conn:
        run_id = conn.execute("SELECT id FROM runs WHERE status = 'succeeded'").fetchone()
        assert run_id is not None
        assert apply_seed(conn, run_id[0]) == 0


def test_no_published_run_is_a_clear_503(
    empty_database: str, client_for: ClientFor, conn: psycopg.Connection
) -> None:
    with client_for(empty_database) as client:
        response = client.get("/api/summary")
    assert response.status_code == 503
    assert response.json() == {"detail": "No published run yet"}


def test_contract_on_the_recorded_extraction(empty_database: str, client_for: ClientFor) -> None:
    from tests.test_verifier import _recorded_results

    if not _recorded_results():
        pytest.skip("no extraction recordings yet: run `lens record`")
    from app.db.migrate import migrate

    migrate(empty_database)
    with connect(empty_database) as conn:
        ingest_dataroom(conn)
        llm = AnthropicLLMClient(trace=db_tracer(conn), default_mode="replay")
        result = run_pipeline(conn, llm, kind="published", publish=True)
        apply_seed(conn, result.run_id)
        run_eval(conn, llm, session_id=None, gate=0.90)
    with client_for(empty_database) as client:
        test_summary(client)
        for fid in ("F-01", "F-02", "F-03", "F-04", "F-05"):
            test_findings(client, fid)
        test_rfi(client)


def test_a_sessions_own_review_changes_only_what_it_sees(
    empty_database: str, api: TestClient
) -> None:
    from app.db.repositories import reviews
    from app.domain.reviews import NewReview

    with connect(empty_database) as conn:
        reviews.insert_review(
            conn,
            NewReview(
                session_id="s-1",
                finding_id="F-03",
                check_id="export_capacity_consistent",
                action="correct",
                corrected_result="fail",
                reason="Grid import and export limits are different things.",
                evidence_fingerprint="sha256:x",
                golden_item_id="corr-002",
                undo_token="t-1",
            ),
        )
    api.cookies.set("lens_session", "s-1")
    mine = api.get("/api/findings/F-03").json()
    assert (mine["result"], mine["review"]) == ("fail", "corrected")
    # Corrected to a plain fail, the export-capacity question is withdrawn from the RFIs.
    assert [r["id"] for r in api.get("/api/rfi").json()] == ["RFI-01", "RFI-02"]

    api.cookies.clear()
    theirs = api.get("/api/findings/F-03").json()
    assert (theirs["result"], theirs["review"]) == ("conflict", "needs_review")


def test_rfi_markdown_matches_the_ui_export_format(api: TestClient) -> None:
    text = api.get("/api/rfi.md").text
    lines = text.split("\n")
    assert lines[:4] == [
        "# Requests for information: Brackenfield Solar & Storage",
        "",
        "### RFI-01: Cable route rights (Critical)",
        "",
    ]
    assert lines[4].startswith("**Request.** Please provide the executed deed(s)")
    assert lines[5:8] == [
        "",
        "**Why.** Without these rights the site cannot physically connect to the grid.",
        "",
    ]
    assert lines[8:12] == [
        "**Documents expected.**",
        "- Deed of easement",
        "- Title plans for Parcels 14 and 15",
        "- HM Land Registry registration",
    ]
    assert text.endswith("- Correspondence with the network operator on capacity\n")
