"""C7: the check playbook reproduces planted_facts.yaml and the expected finding wording."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
import pytest
import yaml

from app.checks.render import (
    format_number,
    join_prose,
    noun_list,
    number_word,
    parcel_prose,
    range_dash,
    range_short,
    short_date,
)
from app.checks.runner import (
    CheckSpec,
    assign_rfi_ids,
    initial_review_state,
    load_checks,
    run_checks,
)
from app.checks.view import GraphView
from app.config import BACKEND_DIR, DATAROOM_DIR
from app.db.repositories import findings as findings_repo
from app.db.repositories import graph as graph_repo
from app.domain.claims import Claim
from app.domain.documents import Document
from app.domain.findings import FindingRecord
from app.domain.graph import Provenance
from app.extract.pass1 import to_drafts
from app.ingest.manifest import load_manifest
from app.ingest.pdf import parse_pdf
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer
from app.pipeline import run_pipeline
from tests.perfect_extraction import PERFECT as PERFECT_DRAFTS
from tests.test_consolidate import (
    ORDER,
    PARAGRAPHS,
    PerfectTransport,
    as_claims,
    build,
    flatten,
    perfect_claims,
)

EXPECTED = BACKEND_DIR / "tests" / "contract" / "expected"
PLANTED = yaml.safe_load((DATAROOM_DIR / "planted_facts.yaml").read_text(encoding="utf-8"))
AS_OF = date(2026, 9, 21)


def _documents() -> list[Document]:
    docs = []
    for d in load_manifest():
        parsed = parse_pdf(DATAROOM_DIR / "pdf" / d.file, d.id, d.paragraph_prefix)
        docs.append(
            Document(
                id=d.id,
                file_name=d.file,
                title=d.title,
                noun=d.noun,
                paragraph_prefix=d.paragraph_prefix,
                pages=parsed.pages,
                sha256=parsed.sha256,
            )
        )
    return docs


DOCUMENTS = _documents()


def view_of(claims: list[Claim]) -> GraphView:
    nodes, edges, rows = flatten(build(claims))
    provenance = [Provenance(**r.model_dump(), id=i) for i, r in enumerate(rows, start=1)]
    return GraphView(nodes, edges, provenance, DOCUMENTS, list(PARAGRAPHS.values()), ORDER, AS_OF)


@pytest.fixture(scope="module")
def findings() -> dict[str, FindingRecord]:
    return {f.check_id: f for f in run_checks(view_of(perfect_claims()), "r-test")}


def template_context(f: FindingRecord) -> dict[str, Any]:
    return {k: v for k, v in f.context.items() if k != "inputs"}


def cards(f: FindingRecord) -> list[dict[str, Any]]:
    """Evidence as plain dicts (it is stored as JSON)."""
    return [dict(e) for e in f.evidence]


def evidence_ids(f: FindingRecord) -> list[str]:
    return [e["citation"]["paragraph_id"] if e["kind"] == "quote" else "missing" for e in cards(f)]


# ---------- against the answer key ----------


def test_results_ids_evidence_and_context_match_the_answer_key(
    findings: dict[str, FindingRecord],
) -> None:
    assert [f.id for f in findings.values()] == [f"F-{i:02d}" for i in range(1, 9)]
    for check_id, key in PLANTED["checks"].items():
        f = findings[check_id]
        assert f.result == key["result"], check_id
        assert template_context(f) == key["context"], check_id
        if "finding" in key:
            assert f.id == key["finding"]
            assert evidence_ids(f) == key["evidence"], check_id
    flagged = [f for f in findings.values() if f.result != "pass"]
    assert (len(flagged), len(findings) - len(flagged)) == (5, 3)


def test_rfis_are_numbered_missing_evidence_first(findings: dict[str, FindingRecord]) -> None:
    raised = sorted((f.rfi_id, f.check_id) for f in findings.values() if f.rfi_id)
    assert [f"{rfi} {check}" for rfi, check in raised] == PLANTED["rfi_order"]


# ---------- against the expected wording ----------

CARD_FIELDS = ("kind", "document_title", "file_name", "role", "heading", "paragraph_text", "status")


@pytest.mark.parametrize(
    "path", sorted((EXPECTED / "findings").glob("F-*.json")), ids=lambda p: p.stem
)
def test_rendered_findings_match_the_expected_json(
    path: Path, findings: dict[str, FindingRecord]
) -> None:
    want = json.loads(path.read_text(encoding="utf-8"))
    got = findings[want["check_id"]]
    for field in ("id", "check_id", "severity", "result", "title", "why", "how"):
        assert getattr(got, field) == want[field], field

    assert len(got.evidence) == len(want["evidence"])
    for g, w in zip(cards(got), want["evidence"], strict=True):
        if w["kind"] == "missing":
            assert g == w
            continue
        for field in CARD_FIELDS:
            assert g[field] == w[field], (w["citation"]["paragraph_id"], field)
        gc, wc = g["citation"], w["citation"]
        assert {k: gc[k] for k in ("document_id", "paragraph_id", "page")} == {
            k: wc[k] for k in ("document_id", "paragraph_id", "page")
        }
        # The model chooses the span, so the quote may differ from the fixture; it must be
        # the paragraph's own characters at the stated offsets.
        start, end = g["quote_start"], g["quote_end"]
        assert g["paragraph_text"][start:end] == gc["quote"]


def test_passed_titles_match_the_summary(findings: dict[str, FindingRecord]) -> None:
    summary = json.loads((EXPECTED / "summary.json").read_text(encoding="utf-8"))
    for passed in summary["passed"]:
        assert findings[passed["check_id"]].title == passed["title"]


def test_initial_review_state_matches_the_fixtures_before_any_review(
    findings: dict[str, FindingRecord],
) -> None:
    # F-04 is lawyer_verified in the fixture only because of a seed review (C9).
    for path in sorted((EXPECTED / "findings").glob("F-*.json")):
        want = json.loads(path.read_text(encoding="utf-8"))
        if want["id"] == "F-04":
            continue
        got = findings[want["check_id"]]
        assert initial_review_state(got.severity, got.result) == want["review"], want["id"]


# ---------- refusing to guess ----------


def claims_without(check: str) -> list[Claim]:
    drafts = [d for doc, result in PERFECT_DRAFTS.items() for d in to_drafts(doc, result)]
    return as_claims([d for d in drafts if d.property != check])


def test_a_missing_required_input_is_missing_evidence_with_a_plain_title() -> None:
    results = {f.check_id: f for f in run_checks(view_of(claims_without("connection_date")), "r")}
    f = results["grid_before_cod"]
    assert f.result == "missing_evidence"
    assert f.title == "Grid before cod could not be evaluated: connection date not evidenced"
    assert "{" not in f.title + f.why + f.how
    # The lease check needs the connection date too (first export), and says so.
    assert results["lease_covers_operating_life"].result == "missing_evidence"


def test_a_missing_signature_is_missing_evidence_with_the_missing_card() -> None:
    results = {f.check_id: f for f in run_checks(view_of(claims_without("signed_date")), "r")}
    f = results["offtaker_identified"]
    assert f.result == "missing_evidence"
    assert f.title == "No signed offtake agreement evidenced"
    assert cards(f)[-1]["label"] == "Signed power purchase agreement"
    # Missing evidence first by severity: critical cable route, then this (high), then the
    # medium planning condition; the export-capacity conflict comes last.
    assert {r.check_id: r.rfi_id for r in results.values() if r.rfi_id} == {
        "cable_route_rights": "RFI-01",
        "offtaker_identified": "RFI-02",
        "pre_commencement_conditions": "RFI-03",
        "export_capacity_consistent": "RFI-04",
    }


def test_a_template_key_the_check_did_not_fill_raises() -> None:
    [spec] = [s for s in load_checks() if s.id == "grid_before_cod"]
    broken = spec.model_copy(update={"how": "{connection_date_short} vs {no_such_key}"})
    with pytest.raises(KeyError, match="no_such_key"):
        run_checks(view_of(perfect_claims()), "r", [broken])


def test_initial_review_state() -> None:
    assert initial_review_state("critical", "missing_evidence") == "needs_review"
    assert initial_review_state("high", "conflict") == "needs_review"
    assert initial_review_state("high", "fail") == "ai_extracted"
    assert initial_review_state("medium", "pass") == "ai_extracted"


def test_rfi_ids_skip_plain_fails_and_checks_without_an_rfi() -> None:
    specs = {s.id: s for s in load_checks()}
    ids = assign_rfi_ids(
        [
            (specs["export_capacity_consistent"], "conflict"),
            (specs["grid_before_cod"], "fail"),  # no rfi block
            (specs["pre_commencement_conditions"], "missing_evidence"),
            (specs["cable_route_rights"], "missing_evidence"),
            (specs["offtaker_identified"], "pass"),
        ]
    )
    assert ids == {
        "cable_route_rights": "RFI-01",
        "pre_commencement_conditions": "RFI-02",
        "export_capacity_consistent": "RFI-03",
    }


def test_checks_load_in_order_with_unique_finding_ids() -> None:
    specs: list[CheckSpec] = load_checks()
    assert [s.order for s in specs] == list(range(1, 9))
    assert len({s.finding_id for s in specs}) == 8


# ---------- wording helpers ----------


def test_wording_helpers() -> None:
    assert short_date(date(2029, 10, 1)) == "1 Oct 2029"
    assert short_date(date(2027, 6, 12)) == "12 Jun 2027"
    assert parcel_prose([14]) == "Parcel 14"
    assert parcel_prose([15, 14]) == "Parcels 14 and 15"
    assert parcel_prose([14, 15, 16]) == "Parcels 14, 15 and 16"
    assert range_short([9, 10, 11]) == "9 to 11"
    assert range_short([9, 10, 12]) == "9, 10 and 12"
    assert range_dash([14, 15]) == "14–15"
    assert range_dash([3, 4, 5, 9]) == "3–5 and 9"
    assert number_word(9) == "nine" and number_word(3) == "three" and number_word(42) == "42"
    assert noun_list(["planning", "the PPA"]) == "Planning and the PPA"
    assert noun_list(["the grid offer"]) == "The grid offer"
    assert join_prose(["A", "B", "C"]) == "A, B and C"
    assert format_number(49.9) == "49.9" and format_number(45.0) == "45"


# ---------- through the pipeline ----------


@pytest.mark.db
def test_pipeline_stores_a_finding_per_check(tmp_path: Path, conn: psycopg.Connection) -> None:
    ingest_dataroom(conn)
    llm = AnthropicLLMClient(
        trace=db_tracer(conn), store=RecordingStore(tmp_path), transport=PerfectTransport()
    )
    result = run_pipeline(conn, llm, mode="record")

    stored = findings_repo.list_findings(conn, result.run_id)
    assert stored == result.findings
    assert {f.check_id: f.result for f in stored} == {
        c: k["result"] for c, k in PLANTED["checks"].items()
    }
    # Each finding keeps the provenance behind each input, for Ask's graph queries.
    provenance_ids = {r.id for r in graph_repo.list_provenance(conn, result.run_id)}
    for f in stored:
        inputs = f.context["inputs"]
        assert isinstance(inputs, dict)
        for ids in inputs.values():
            assert isinstance(ids, list) and set(ids) <= provenance_ids


# ---------- the recorded extraction ----------


def test_checks_over_the_recorded_extraction_match_the_answer_key() -> None:
    from tests.test_verifier import _recorded_results

    results = _recorded_results()
    if not results:
        pytest.skip("no extract.v1 recordings yet: run `lens record`")
    claims = as_claims([d for doc, r in results.items() for d in to_drafts(doc, r)])
    found = {f.check_id: f for f in run_checks(view_of(claims), "r-test")}
    for check_id, key in PLANTED["checks"].items():
        assert found[check_id].result == key["result"], check_id
        assert template_context(found[check_id]) == key["context"], check_id


def test_a_pass_keeps_only_whole_sentences() -> None:
    # With one export figure the check passes; its why/how need the disagreeing values.
    drafts = [d for doc, r in PERFECT_DRAFTS.items() for d in to_drafts(doc, r)]
    agreed = as_claims(
        [d for d in drafts if not (d.document_id == "grid" and d.property == "export_capacity_mw")]
    )
    f = {x.check_id: x for x in run_checks(view_of(agreed), "r")}["export_capacity_consistent"]
    assert f.result == "pass"
    assert f.title == "Export capacity is consistent across documents"
    assert f.why == ""
    assert "{" not in f.how
