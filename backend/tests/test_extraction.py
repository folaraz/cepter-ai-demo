"""C4: the extraction schema, prompt, pass 1 and `lens run` replay. No network: model
answers come from a fake transport through the real record/replay adapter."""

from pathlib import Path
from typing import Any

import psycopg
import pytest
from pydantic import ValidationError

from app.domain.documents import Document, Paragraph
from app.domain.extraction import ExtractionResult
from app.domain.ontology import load_ontology
from app.extract.pass1 import to_drafts
from app.extract.prompt import PROMPT_VERSION, system_prompt, user_message
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient, ToolCall
from app.llm.client import MissingRecording
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer
from app.pipeline import run_pipeline


def result(**overrides: Any) -> dict[str, Any]:
    """A small valid answer for the grid offer."""
    base: dict[str, Any] = {
        "asset_properties": [
            {
                "name": "export_capacity_mw",
                "value": 45,
                "paragraph_id": "grid_offer:p2:¶3",
                "quote": "Maximum Export Capacity at the Point of Connection shall be 45 MW",
            }
        ],
        "entities": [
            {
                "local_id": "gc",
                "type": "GridConnection",
                "name": None,
                "properties": [
                    {
                        "name": "connection_date",
                        "value": "2029-10-01",
                        "paragraph_id": "grid_offer:p2:¶3",
                        "quote": "1 October 2029",
                    }
                ],
            },
            {
                "local_id": "fdn",
                "type": "Party",
                "name": "Fenland Distribution Networks plc",
                "properties": [
                    {
                        "name": "name",
                        "value": "Fenland Distribution Networks plc",
                        "paragraph_id": "grid_offer:p1:¶2",
                        "quote": "Fenland Distribution Networks plc",
                    }
                ],
            },
        ],
        "relations": [
            {
                "type": "PARTY_TO",
                "source_local_id": "fdn",
                "target_local_id": "gc",
                "role": "network_operator",
                "paragraph_id": "grid_offer:p1:¶2",
                "quote": "made by Fenland Distribution Networks plc",
            }
        ],
    }
    return base | overrides


def entity(local_id: str, type_: str, *props: tuple[str, Any]) -> dict[str, Any]:
    return {
        "local_id": local_id,
        "type": type_,
        "name": None,
        "properties": [
            {"name": n, "value": v, "paragraph_id": "p", "quote": "q"} for n, v in props
        ],
    }


def relation(type_: str, source: str, target: str, role: str | None = None) -> dict[str, Any]:
    return {
        "type": type_,
        "source_local_id": source,
        "target_local_id": target,
        "role": role,
        "paragraph_id": "p",
        "quote": "q",
    }


# ---------- schema ----------


def test_a_valid_answer_passes() -> None:
    ExtractionResult.model_validate(result())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"entities": [entity("gc", "GridConnection", ("export_capacity_mw", 45))]}, "no property"),
        ({"entities": [entity("c1", "Condition", ("condition_type", "sunset"))]}, "is not one of"),
        ({"entities": [entity("l", "Lease", ("start_date", "1 January 2026"))]}, "ISO date"),
        ({"entities": [entity("l", "Lease", ("term_years", "35"))]}, "not a number"),
        ({"entities": [entity("asset", "Lease")]}, "reserved"),
        ({"entities": [entity("x", "Lease"), entity("x", "Permit")]}, "used twice"),
        ({"relations": [relation("COVERS", "lease", "p14")]}, "unknown local_id"),
        (
            {
                "entities": [entity("l", "Lease"), entity("p", "Permit")],
                "relations": [relation("COVERS", "p", "l")],
            },
            "source must be",
        ),
        (
            {
                "entities": [entity("a", "Party"), entity("l", "Lease")],
                "relations": [relation("PARTY_TO", "a", "l")],
            },
            "role must be one of",
        ),
        (
            {
                "entities": [entity("l", "Lease"), entity("p14", "LandParcel")],
                "relations": [relation("COVERS", "l", "p14", role="tenant")],
            },
            "only PARTY_TO has a role",
        ),
        (
            {
                "asset_properties": [
                    {"name": "technology", "value": "solar_pv", "paragraph_id": "p", "quote": "q"}
                ]
            },
            "takes a list",
        ),
    ],
)
def test_answers_that_break_the_ontology_are_rejected(change: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        ExtractionResult.model_validate(result(**change))


def test_asset_can_source_site_relations() -> None:
    ExtractionResult.model_validate(
        result(
            asset_properties=[
                {
                    "name": "technology",
                    "value": ["solar_pv", "bess"],
                    "paragraph_id": "p",
                    "quote": "q",
                }
            ],
            entities=[entity("p14", "LandParcel", ("number", "14"))],
            relations=[relation("CABLE_CROSSES", "asset", "p14")],
        )
    )


# ---------- prompt ----------

DOC = Document(
    id="grid",
    file_name="grid_offer.pdf",
    title="Grid connection offer",
    noun="the grid offer",
    paragraph_prefix="grid_offer",
    pages=3,
    sha256="0" * 64,
)
PARAS = [
    Paragraph(
        id="grid_offer:p2:¶3",
        document_id="grid",
        page=2,
        ordinal=3,
        heading="4. Connection",
        text="The Maximum Export Capacity at the Point of Connection shall be 45 MW.",
    ),
    Paragraph(id="grid_offer:p3:¶9", document_id="grid", page=3, ordinal=9, heading=None, text="x"),
]


def test_user_message_lists_title_then_one_line_per_paragraph() -> None:
    assert user_message(DOC, PARAS).splitlines() == [
        "Document: Grid connection offer",
        "",
        "[grid_offer:p2:¶3] (4. Connection) The Maximum Export Capacity at the Point of "
        "Connection shall be 45 MW.",
        "[grid_offer:p3:¶9] x",
    ]


def test_system_prompt_carries_the_rules_and_the_whole_ontology() -> None:
    prompt = system_prompt(load_ontology())
    assert prompt == system_prompt(load_ontology())  # deterministic: it is in the key
    for phrase in [
        "copied character for character",
        "the shortest",
        'local_id is "asset"',
        "An import capacity is not an export capacity",
        "Each land parcel is its own LandParcel entity",
        "ISO YYYY-MM-DD",
        "never record that\n   something is absent",
    ]:
        assert phrase in prompt
    for node_type, spec in load_ontology().nodes.items():
        assert node_type in prompt
        for name in spec.properties:
            assert f"    {name}: " in prompt
    assert "PARTY_TO: Party -> Lease" in prompt


# ---------- pass 1 ----------


def test_drafts_flatten_properties_and_relations() -> None:
    drafts = to_drafts("grid", ExtractionResult.model_validate(result()))
    assert [(d.kind, d.property or d.edge_type) for d in drafts] == [
        ("property", "export_capacity_mw"),
        ("property", "connection_date"),
        ("property", "name"),
        ("edge", "PARTY_TO"),
    ]
    asset, date_, _, party_to = drafts
    assert asset.local_ref == {"local_id": "asset", "type": "Asset", "name": None}
    assert date_.local_ref == {"local_id": "gc", "type": "GridConnection", "name": None}
    assert party_to.local_ref["name"] == "Fenland Distribution Networks plc"
    assert party_to.target_ref == {"local_id": "gc", "type": "GridConnection", "name": None}
    assert party_to.value == "network_operator"
    assert {d.document_id for d in drafts} == {"grid"}


class OneAnswer:
    """Returns the same valid answer for every document."""

    def __init__(self) -> None:
        self.calls = 0

    def call(self, **_: Any) -> ToolCall:
        self.calls += 1
        return ToolCall(input=result(), input_tokens=5000, output_tokens=900)


class NoNetwork:
    def call(self, **_: Any) -> ToolCall:
        raise AssertionError("replay must not call the API")


@pytest.mark.db
def test_run_replays_recorded_extraction_identically(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    ingest_dataroom(conn)
    store = RecordingStore(tmp_path)
    recorder = AnthropicLLMClient(trace=db_tracer(conn), store=store, transport=OneAnswer())
    recorded = run_pipeline(conn, recorder, mode="record")
    assert len(list(tmp_path.glob("*.json"))) == 5  # one recording per document

    replayer = AnthropicLLMClient(trace=db_tracer(conn), store=store, transport=NoNetwork())
    first = run_pipeline(conn, replayer, mode="replay")
    second = run_pipeline(conn, replayer, mode="replay")

    assert first.drafts == second.drafts == recorded.drafts
    assert list(first.drafts) == ["grid", "lease", "planning", "ppa", "site"]
    run = conn.execute(
        "SELECT status, prompt_versions FROM runs WHERE id = %s", (first.run_id,)
    ).fetchone()
    assert run == ("succeeded", {"extract": PROMPT_VERSION})
    purposes = conn.execute(
        "SELECT purpose FROM llm_calls WHERE run_id = %s ORDER BY id", (first.run_id,)
    ).fetchall()
    assert [p[0] for p in purposes] == [f"extract:{d}" for d in first.drafts]


@pytest.mark.db
def test_run_without_recordings_fails_the_run(tmp_path: Path, conn: psycopg.Connection) -> None:
    ingest_dataroom(conn)
    llm = AnthropicLLMClient(
        trace=db_tracer(conn), store=RecordingStore(tmp_path), transport=NoNetwork()
    )
    with pytest.raises(MissingRecording):
        run_pipeline(conn, llm, mode="replay")
    status = conn.execute("SELECT status, error FROM runs").fetchone()
    assert status is not None and status[0] == "failed" and "MissingRecording" in status[1]


@pytest.mark.db
def test_publishing_makes_the_run_live(tmp_path: Path, conn: psycopg.Connection) -> None:
    ingest_dataroom(conn)
    store = RecordingStore(tmp_path)
    llm = AnthropicLLMClient(trace=db_tracer(conn), store=store, transport=OneAnswer())
    run_pipeline(conn, llm, mode="record")
    published = run_pipeline(conn, llm, kind="published", mode="replay", publish=True)
    live = conn.execute(
        "SELECT id FROM runs WHERE kind = 'published' AND status = 'succeeded'"
    ).fetchone()
    assert live == (published.run_id,)
