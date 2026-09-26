"""C5: the verifier accepts only claims the documents support, against real paragraphs."""

from collections import Counter
from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import JsonValue

from app.config import DATAROOM_DIR
from app.consolidate.names import is_company, name_key, without_suffix
from app.domain.claims import NewClaim
from app.domain.documents import Document, Paragraph
from app.domain.extraction import ClaimDraft, ExtractionResult
from app.domain.ontology import load_ontology
from app.extract.pass1 import extract_document, to_drafts
from app.ingest.manifest import load_manifest
from app.ingest.pdf import parse_pdf
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.client import MissingRecording
from app.verify.normalise import dates_in, find_quote, numbers_in
from app.verify.verifier import verify_claims

PARAGRAPHS: dict[str, Paragraph] = {
    p.id: p
    for d in load_manifest()
    for p in parse_pdf(DATAROOM_DIR / "pdf" / d.file, d.id, d.paragraph_prefix).paragraphs
}

DOCUMENT_OF_PREFIX = {d.paragraph_prefix: d.id for d in load_manifest()}


def document_of(paragraph_id: str) -> str:
    return DOCUMENT_OF_PREFIX[paragraph_id.split(":")[0]]


LEASE = {"local_id": "lease", "type": "Lease", "name": None}
ASSET = {"local_id": "asset", "type": "Asset", "name": None}


def prop(
    ref: Mapping[str, Any], name: str, value: JsonValue, paragraph_id: str, quote: str
) -> ClaimDraft:
    return ClaimDraft(
        document_id=document_of(paragraph_id),
        kind="property",
        local_ref=dict(ref),
        property=name,
        edge_type=None,
        target_ref=None,
        value=value,
        paragraph_id=paragraph_id,
        quote=quote,
    )


def edge(
    edge_type: str,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    paragraph_id: str,
    quote: str,
    role: str | None = None,
) -> ClaimDraft:
    return ClaimDraft(
        document_id=document_of(paragraph_id),
        kind="edge",
        local_ref=dict(source),
        property=None,
        edge_type=edge_type,
        target_ref=dict(target),
        value=role,
        paragraph_id=paragraph_id,
        quote=quote,
    )


def verify(*drafts: ClaimDraft) -> list[NewClaim]:
    return verify_claims(drafts, PARAGRAPHS, load_ontology(), "r-test")


def one(draft: ClaimDraft) -> NewClaim:
    [claim] = verify(draft)
    return claim


# ---------- the cases named in the spec ----------


def test_a_paraphrased_quote_is_rejected() -> None:
    claim = one(prop(LEASE, "term_years", 35, "lease:p1:¶5", "a thirty-five year term"))
    assert (claim.status, claim.rejection_reason) == ("rejected", "quote_not_verbatim")
    assert claim.quote_start is None and claim.quote == "a thirty-five year term"


def test_a_real_quote_with_the_wrong_value_is_rejected() -> None:
    claim = one(prop(LEASE, "term_years", 40, "lease:p1:¶5", "35 years"))
    assert (claim.status, claim.rejection_reason) == ("rejected", "value_not_in_quote")


def test_a_made_up_paragraph_is_rejected() -> None:
    claim = one(prop(LEASE, "term_years", 35, "lease:p9:¶1", "35 years"))
    assert (claim.status, claim.rejection_reason) == ("rejected", "no_such_paragraph")


def test_a_paragraph_from_another_document_is_rejected() -> None:
    # The quote is real, but in the grid offer: the lease's extraction never saw it.
    claim = prop(LEASE, "term_years", 45, "grid_offer:p2:¶3", "45 MW")
    claim = claim.model_copy(update={"document_id": "lease"})
    assert one(claim).rejection_reason == "no_such_paragraph"


def test_number_words_verify() -> None:
    condition = {"local_id": "c1", "type": "Condition", "name": None}
    claim = one(prop(condition, "years", 3, "planning:p2:¶2", "three years"))
    assert claim.status == "verified"


def test_a_unit_run_into_the_number_verifies() -> None:
    claim = one(prop(ASSET, "export_capacity_mw", 49.9, "planning:p1:¶4", "49.9MW"))
    assert claim.status == "verified"


def test_the_hyphenated_long_stop_date_verifies() -> None:
    ppa = {"local_id": "ppa", "type": "OfftakeAgreement", "name": None}
    quote = 'by 31 December 2029 (the "Long-Stop Date")'
    claim = one(prop(ppa, "long_stop_date", "2029-12-31", "ppa:p4:¶2", quote))
    assert claim.status == "verified"


def test_offsets_point_at_the_documents_own_characters() -> None:
    text = PARAGRAPHS["lease:p1:¶5"].text
    claim = one(prop(LEASE, "start_date", "2026-01-01", "lease:p1:¶5", "1 January  2026"))
    assert claim.status == "verified"
    assert claim.quote_start is not None and claim.quote_end is not None
    assert text[claim.quote_start : claim.quote_end] == claim.quote == "1 January 2026"
    assert claim.quote_start == text.index("1 January 2026")


# ---------- quote matching ----------


def test_quote_matching_forgives_only_form_not_content() -> None:
    text = PARAGRAPHS["ppa:p4:¶2"].text
    assert find_quote("“Long-Stop Date”", text) == find_quote('"Long-Stop Date"', text)
    assert find_quote("31\nDecember   2029", text) == find_quote("31 December 2029", text)
    assert find_quote("long-stop date", text) is None  # case is content
    assert find_quote("   ", text) is None


# ---------- value extractors (Ask reuses these) ----------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("49.9MW", [49.9]),
        ("£4,850,000", [4850000.0]),
        ("three years", [3.0]),
        ("a term of 35 years", [35.0]),
        ("Forty years", [40.0]),
        ("the 33 kV busbar", [33.0]),
    ],
)
def test_numbers_in(text: str, expected: list[float]) -> None:
    assert numbers_in(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 October 2029", ["2029-10-01"]),
        ("on the 3rd March 2025", ["2025-03-03"]),
        ("2029-03-31", ["2029-03-31"]),
        ("31 February 2029", []),
        ("in March 2029", []),
    ],
)
def test_dates_in(text: str, expected: list[str]) -> None:
    assert dates_in(text) == expected


# ---------- the other verify kinds ----------


def test_text_is_case_insensitive() -> None:
    grid = {"local_id": "gc", "type": "GridConnection", "name": None}
    quote = "Wickham Primary Substation"
    assert (
        one(
            prop(grid, "substation", "wickham primary substation", "grid_offer:p2:¶3", quote)
        ).status
        == "verified"
    )


def test_keywords_must_support_every_value() -> None:
    quote = "solar photovoltaic array and battery energy storage system"
    both = prop(ASSET, "technology", ["solar_pv", "bess"], "planning:p1:¶4", quote)
    wind = prop(ASSET, "technology", ["solar_pv", "wind"], "planning:p1:¶4", quote)
    assert [c.status for c in verify(both, wind)] == ["verified", "rejected"]


def test_condition_type_keywords() -> None:
    c5 = {"local_id": "c5", "type": "Condition", "name": None}
    quote = "No development shall commence until a Construction Traffic Management Plan"
    right = prop(c5, "condition_type", "pre_commencement", "planning:p3:¶6", quote)
    wrong = prop(c5, "condition_type", "decommissioning", "planning:p3:¶6", quote)
    assert [c.status for c in verify(right, wrong)] == ["verified", "rejected"]


# ---------- names ----------


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("Brackenfield Solar Limited", "brackenfield solar"),
        ("Brackenfield Solar Ltd", "brackenfield solar"),
        ("Brackenfield Solar Ltd.", "brackenfield solar"),
        ("Fenland Distribution Networks plc", "fenland distribution networks"),
        ("JOHN HARTLEY", "hartley:j"),
        ("Mr J. Hartley", "hartley:j"),
        ("John Hartley", "hartley:j"),
    ],
)
def test_name_keys(name: str, key: str) -> None:
    assert name_key(name) == key


def test_company_display_drops_only_the_suffix() -> None:
    assert is_company("Northwind Energy Supply Limited")
    assert without_suffix("Northwind Energy Supply Limited") == "Northwind Energy Supply"
    assert not is_company("John Hartley")


def party(local_id: str, name: str) -> dict[str, JsonValue]:
    return {"local_id": local_id, "type": "Party", "name": name}


def test_person_names_verify_by_surname_and_first_name_or_initial() -> None:
    quote = "Landowner: Mr J. Hartley"
    same = prop(party("h", "John Hartley"), "name", "John Hartley", "planning:p1:¶2", quote)
    other = prop(party("h", "Jane Hartley"), "name", "Jane Hartley", "planning:p1:¶2", quote)
    wrong = prop(party("h", "Peter Hartley"), "name", "Peter Hartley", "planning:p1:¶2", quote)
    assert [c.status for c in verify(same, other, wrong)] == ["verified", "verified", "rejected"]


def test_company_names_verify_without_their_suffix() -> None:
    quote = "Applicant: Brackenfield Solar Ltd"
    claim = prop(
        party("b", "Brackenfield Solar Limited"),
        "name",
        "Brackenfield Solar Limited",
        "planning:p1:¶2",
        quote,
    )
    assert one(claim).status == "verified"


# ---------- edges ----------

PERMIT = {"local_id": "permit", "type": "Permit", "name": None}


def test_party_to_needs_the_name_and_the_role_keyword() -> None:
    hartley = party("h", "JOHN HARTLEY")
    quote = 'JOHN HARTLEY of Bracken Farm, Wickham (the "Landlord")'
    landlord = edge("PARTY_TO", hartley, LEASE, "lease:p1:¶1", quote, role="landlord")
    tenant = edge("PARTY_TO", hartley, LEASE, "lease:p1:¶1", quote, role="tenant")
    stranger = edge(
        "PARTY_TO", party("x", "Mary Smith"), LEASE, "lease:p1:¶1", quote, role="landlord"
    )
    assert [c.status for c in verify(landlord, tenant, stranger)] == [
        "verified",
        "rejected",
        "rejected",
    ]


def test_party_to_uses_the_partys_own_name_claim() -> None:
    # The entity's name field is empty, but the same document states its name.
    fdn = {"local_id": "fdn", "type": "Party", "name": None}
    name = prop(
        fdn,
        "name",
        "Fenland Distribution Networks plc",
        "grid_offer:p1:¶2",
        "Fenland Distribution Networks plc",
    )
    gc = {"local_id": "gc", "type": "GridConnection", "name": None}
    rel = edge(
        "PARTY_TO",
        fdn,
        gc,
        "grid_offer:p1:¶2",
        "made by Fenland Distribution Networks plc",
        role="network_operator",
    )
    assert [c.status for c in verify(name, rel)] == ["verified", "verified"]


def parcel(number: str) -> dict[str, JsonValue]:
    return {"local_id": f"p{number}", "type": "LandParcel", "name": f"Parcel {number}"}


def test_parcel_edges_need_the_parcel_number_as_a_whole_number() -> None:
    quote = "across Parcels 14 and 15"
    p14 = edge("CABLE_CROSSES", ASSET, parcel("14"), "site_plan:p1:¶2", quote)
    p1 = edge("CABLE_CROSSES", ASSET, parcel("1"), "site_plan:p1:¶2", quote)
    p16 = edge("CABLE_CROSSES", ASSET, parcel("16"), "site_plan:p1:¶2", quote)
    assert [c.status for c in verify(p14, p1, p16)] == ["verified", "rejected", "rejected"]


def test_has_condition_needs_only_a_real_quote() -> None:
    c5 = {"local_id": "c5", "type": "Condition", "name": None}
    quote = "No development shall commence until"
    real = edge("HAS_CONDITION", PERMIT, c5, "planning:p3:¶6", quote)
    fake = edge("HAS_CONDITION", PERMIT, c5, "planning:p3:¶6", "Condition 5 is discharged")
    assert [c.rejection_reason for c in verify(real, fake)] == [None, "quote_not_verbatim"]


# ---------- over the recorded extraction ----------


def _recorded_results() -> dict[str, ExtractionResult]:
    """Pass 1's recorded answers for each document, or {} if they aren't recorded yet."""
    llm = AnthropicLLMClient(trace=lambda _: None, default_mode="replay")
    out: dict[str, ExtractionResult] = {}
    for d in load_manifest():
        parsed = parse_pdf(DATAROOM_DIR / "pdf" / d.file, d.id, d.paragraph_prefix)
        doc = Document(
            id=d.id,
            file_name=d.file,
            title=d.title,
            noun=d.noun,
            paragraph_prefix=d.paragraph_prefix,
            pages=parsed.pages,
            sha256=parsed.sha256,
        )
        try:
            out[d.id] = extract_document(llm, doc, parsed.paragraphs, "r-test")
        except MissingRecording:
            return {}
    return out


def test_verifier_over_the_recorded_extraction(capsys: pytest.CaptureFixture[str]) -> None:
    results = _recorded_results()
    if not results:
        pytest.skip("no extract.v1 recordings yet: run `lens record`")
    drafts = [d for doc, result in results.items() for d in to_drafts(doc, result)]
    claims = verify(*drafts)
    reasons = Counter(c.rejection_reason for c in claims if c.status == "rejected")
    with capsys.disabled():
        print(f"\nverifier: {len(claims)} claims, {sum(reasons.values())} rejected {dict(reasons)}")
        for c in claims:
            if c.status == "rejected":
                what = c.property or c.edge_type
                print(f"  {c.rejection_reason}: {c.paragraph_id} {what} {c.quote!r}")
    for c in claims:
        if c.status == "verified":
            assert c.quote_start is not None and c.quote_end is not None
            assert PARAGRAPHS[c.paragraph_id].text[c.quote_start : c.quote_end] == c.quote
