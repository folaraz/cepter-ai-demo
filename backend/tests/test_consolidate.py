"""C6: consolidation reproduces data/dataroom/planted_facts.yaml.

The same assertions run three ways: on a perfect extraction in memory, through the whole
pipeline into the database, and on the recorded extraction once it exists.
"""

from pathlib import Path
from typing import Any

import psycopg
import pytest
import yaml

from app.config import DATAROOM_DIR
from app.consolidate.graph import ConsolidatedGraph, _canonical, consolidate
from app.consolidate.names import name_key, without_suffix
from app.db.repositories import graph as graph_repo
from app.domain.claims import Claim
from app.domain.documents import Paragraph
from app.domain.extraction import ClaimDraft
from app.domain.graph import Edge, NewProvenance, Node, PropertyGroup
from app.domain.ontology import load_ontology
from app.extract.pass1 import to_drafts
from app.ingest.manifest import load_manifest
from app.ingest.pdf import parse_pdf
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient, ToolCall
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer
from app.pipeline import run_pipeline
from app.verify.verifier import verify_claims
from tests.perfect_extraction import PERFECT

PLANTED = yaml.safe_load((DATAROOM_DIR / "planted_facts.yaml").read_text(encoding="utf-8"))
ORDER = [d.id for d in load_manifest()]
PARAGRAPHS: dict[str, Paragraph] = {
    p.id: p
    for d in load_manifest()
    for p in parse_pdf(DATAROOM_DIR / "pdf" / d.file, d.id, d.paragraph_prefix).paragraphs
}
RUN = "r-test"


def as_claims(drafts: list[ClaimDraft]) -> list[Claim]:
    checked = verify_claims(drafts, PARAGRAPHS, load_ontology(), RUN)
    return [Claim(**c.model_dump(), id=i) for i, c in enumerate(checked, start=1)]


def build(claims: list[Claim]) -> ConsolidatedGraph:
    return consolidate(
        RUN, claims, PARAGRAPHS, load_ontology(), "Brackenfield Solar & Storage", ORDER
    )


def flatten(graph: ConsolidatedGraph) -> tuple[list[Node], list[Edge], list[NewProvenance]]:
    """The in-memory graph in the shape it is stored, with edge IDs assigned."""
    edges, rows = [], list(graph.provenance)
    for i, (edge, supporting) in enumerate(graph.edges, start=1):
        edges.append(Edge(**edge.model_dump(), id=i))
        for claim, status in supporting:
            rows.append(
                NewProvenance(
                    run_id=RUN,
                    node_id=None,
                    edge_id=i,
                    property=None,
                    value=claim.value,
                    claim_id=claim.id,
                    document_id=claim.document_id,
                    paragraph_id=claim.paragraph_id,
                    quote=claim.quote,
                    quote_start=claim.quote_start or 0,
                    quote_end=claim.quote_end or 0,
                    status=status,
                )
            )
    return graph.nodes, edges, rows


# ---------- the answer key ----------


def assert_planted(nodes: list[Node], edges: list[Edge], rows: list[Any]) -> None:
    by_id = {n.id: n for n in nodes}

    def only(node_type: str) -> Node:
        found = [n for n in nodes if n.type == node_type]
        assert len(found) == 1, f"expected one {node_type}, got {[n.key for n in found]}"
        return found[0]

    def node(label: str) -> Node:
        if label.startswith("Condition "):
            return next(n for n in nodes if n.type == "Condition" and n.name == label)
        return only(label)

    def party(name: str) -> Node:
        return next(n for n in nodes if n.type == "Party" and n.key == name_key(name))

    def parcel(number: int) -> Node:
        return next(n for n in nodes if n.type == "LandParcel" and n.key == str(number))

    for fact in PLANTED["facts"]:
        target = node(fact["node"])
        assert any(
            r.node_id == target.id
            and r.property == fact["property"]
            and _canonical(r.value) == _canonical(fact["value"])
            and r.paragraph_id == fact["paragraph"]
            for r in rows
        ), f"missing fact {fact}"

    def edge_cited(edge_type: str, source: Node, target: Node, paragraph: str, role: Any = None):
        matching = [
            e
            for e in edges
            if e.type == edge_type
            and e.source_id == source.id
            and e.target_id == target.id
            and e.props.get("role") == role
        ]
        assert matching, f"missing {edge_type} {source.key} -> {target.key} ({role})"
        assert any(
            r.edge_id == e.id and r.paragraph_id == paragraph for e in matching for r in rows
        ), f"{edge_type} {source.key} -> {target.key} not cited at {paragraph}"

    for e in PLANTED["edges"]:
        match e["type"]:
            case "PARTY_TO":
                edge_cited("PARTY_TO", party(e["from"]), only(e["to"]), e["paragraph"], e["role"])
            case "COVERS" | "SITE_INCLUDES" | "CABLE_CROSSES":
                for n in e["to"]:
                    edge_cited(e["type"], only(e["from"]), parcel(n), e["paragraph"])
            case "HAS_CONDITION":
                for n, paragraph in zip(e["to"], e["paragraphs"], strict=True):
                    edge_cited("HAS_CONDITION", only("Permit"), node(f"Condition {n}"), paragraph)

    # absent
    assert not [n for n in nodes if n.type == "Easement"]
    assert "discharged_on" not in node("Condition 5").props
    export = PropertyGroup.model_validate(only("Asset").props["export_capacity_mw"])
    assert 20 not in [v.value for v in export.values]

    # consolidation: merges
    for merge in PLANTED["consolidation"]["merges"]:
        assert len({name_key(v) for v in merge["variants"]}) == 1
        merged = party(merge["canonical"])
        identity = [r for r in rows if r.node_id == merged.id and r.property is None]
        assert len({r.document_id for r in identity}) >= 2, f"{merge['canonical']} not merged"
        assert {r.status for r in identity} == {"corroborated"}
    assert party("John Hartley").name == "John Hartley"
    assert party("Brackenfield Solar Limited").name == without_suffix("Brackenfield Solar Limited")

    # consolidation: conflicts
    for conflict in PLANTED["consolidation"]["conflicts"]:
        node_label, prop = conflict["property"].split(".")
        group = PropertyGroup.model_validate(only(node_label).props[prop])
        assert group.conflict
        assert group.value == conflict["corroborated"]["value"]
        support = {_canonical(v.value): v for v in group.values}
        winner = support[_canonical(conflict["corroborated"]["value"])]
        loser = support[_canonical(conflict["conflicting"]["value"])]
        assert (winner.status, winner.documents) == (
            "corroborated",
            conflict["corroborated"]["documents"],
        )
        assert (loser.status, loser.documents) == ("conflict", conflict["conflicting"]["documents"])

    for n in nodes:
        assert n.id in by_id


# ---------- the perfect extraction ----------


def perfect_claims() -> list[Claim]:
    return as_claims([d for doc, result in PERFECT.items() for d in to_drafts(doc, result)])


def test_the_perfect_extraction_fully_verifies() -> None:
    rejected = [c for c in perfect_claims() if c.status == "rejected"]
    assert rejected == [], [(c.paragraph_id, c.quote, c.rejection_reason) for c in rejected]


def test_consolidating_the_perfect_extraction_matches_the_answer_key() -> None:
    assert_planted(*flatten(build(perfect_claims())))


def test_graph_shape() -> None:
    nodes, edges, _ = flatten(build(perfect_claims()))
    counts: dict[str, int] = {}
    for n in nodes:
        counts[n.type] = counts.get(n.type, 0) + 1
    assert counts == {
        "Asset": 1,
        "Condition": 5,
        "GridConnection": 1,
        "LandParcel": 5,  # 9, 10, 11 merged across the lease and site plan; 14, 15
        "Lease": 1,
        "OfftakeAgreement": 1,
        "Party": 4,  # Hartley, Brackenfield, Fenland, Northwind
        "Permit": 1,
    }
    assert nodes[0].type == "Asset" and nodes[0].name == "Brackenfield Solar & Storage"
    conditions = sorted(n.name or "" for n in nodes if n.type == "Condition")
    assert conditions == [f"Condition {i}" for i in range(1, 6)]
    assert len(edges) == 8 + 3 + 3 + 2 + 5


def test_technology_is_a_union_never_a_conflict() -> None:
    nodes, _, _ = flatten(build(perfect_claims()))
    tech = PropertyGroup.model_validate(nodes[0].props["technology"])
    assert not tech.conflict
    assert {(v.value, v.status) for v in tech.values} == {
        ("solar_pv", "corroborated"),
        ("bess", "corroborated"),
    }
    assert tech.values[0].documents == ["lease", "planning", "ppa"]


# ---------- grouping rules ----------


def asset_capacity(*values: tuple[str, float]) -> list[Claim]:
    """Verified export-capacity claims, one per (document, value)."""
    return [
        Claim(
            id=i,
            run_id=RUN,
            document_id=doc,
            kind="property",
            local_ref={"local_id": "asset", "type": "Asset", "name": None},
            property="export_capacity_mw",
            edge_type=None,
            target_ref=None,
            value=value,
            paragraph_id="planning:p1:¶4",
            quote="49.9MW",
            status="verified",
            rejection_reason=None,
            quote_start=0,
            quote_end=6,
        )
        for i, (doc, value) in enumerate(values, start=1)
    ]


def capacity_group(*values: tuple[str, float]) -> PropertyGroup:
    [asset] = [n for n in build(asset_capacity(*values)).nodes if n.type == "Asset"]
    return PropertyGroup.model_validate(asset.props["export_capacity_mw"])


def statuses(group: PropertyGroup) -> list[tuple[Any, str, list[str]]]:
    return [(v.value, v.status, v.documents) for v in group.values]


def test_one_document_is_verified() -> None:
    group = capacity_group(("planning", 49.9))
    assert statuses(group) == [(49.9, "verified", ["planning"])] and not group.conflict


def test_one_document_saying_it_twice_counts_once() -> None:
    assert statuses(capacity_group(("planning", 49.9), ("planning", 49.9)))[0][1] == "verified"


def test_two_documents_corroborate() -> None:
    group = capacity_group(("planning", 49.9), ("ppa", 49.90))
    assert statuses(group) == [(49.9, "corroborated", ["planning", "ppa"])]


def test_a_majority_of_two_or_more_wins_and_the_rest_conflict() -> None:
    group = capacity_group(("grid", 45), ("planning", 49.9), ("ppa", 49.9))
    assert group.conflict and group.value == 49.9
    assert statuses(group) == [
        (49.9, "corroborated", ["planning", "ppa"]),
        (45, "conflict", ["grid"]),
    ]


def test_a_tie_is_all_conflict() -> None:
    group = capacity_group(("planning", 49.9), ("grid", 45))
    assert group.conflict and group.value is None
    assert {s for _, s, _ in statuses(group)} == {"conflict"}


def test_rejected_claims_never_reach_the_graph() -> None:
    claims = asset_capacity(("planning", 49.9), ("grid", 45))
    claims[1] = claims[1].model_copy(
        update={"status": "rejected", "rejection_reason": "value_not_in_quote"}
    )
    group = capacity_group_from(claims)
    assert statuses(group) == [(49.9, "verified", ["planning"])]


def capacity_group_from(claims: list[Claim]) -> PropertyGroup:
    [asset] = [n for n in build(claims).nodes if n.type == "Asset"]
    return PropertyGroup.model_validate(asset.props["export_capacity_mw"])


def test_an_unverified_party_name_keeps_its_own_node() -> None:
    # The planning Party's name claim is rejected and it has no verified edge, so it must
    # not merge with anyone by a name nobody checked.
    drafts = to_drafts("planning", PERFECT["planning"])
    drafts = [
        d.model_copy(update={"quote": "Mr J Hartley"})
        if d.property == "name" and d.local_ref["local_id"] == "hartley"
        else d
        for d in drafts
        if not (d.edge_type == "PARTY_TO" and d.local_ref["local_id"] == "hartley")
    ]
    nodes = build(as_claims(drafts)).nodes
    assert not [n for n in nodes if n.type == "Party" and n.key == "hartley:j"]


# ---------- through the pipeline and the database ----------


DOCUMENT_BY_TITLE = {d.title: d.id for d in load_manifest()}


class PerfectTransport:
    """Answers every model call as a perfect model would: extraction with the perfect
    extraction, Ask's routing and drafting from the Ask golden set."""

    def call(self, *, user: str, tool: dict[str, Any], **_: Any) -> ToolCall:
        from tests import perfect_ask

        if tool["name"] == "RouteDecision":
            return ToolCall(input=perfect_ask.route(user), input_tokens=900, output_tokens=40)
        if tool["name"] == "AnswerDraft":
            return ToolCall(input=perfect_ask.draft(user), input_tokens=2500, output_tokens=120)
        title = user.splitlines()[0].removeprefix("Document: ")
        answer = PERFECT[DOCUMENT_BY_TITLE[title]].model_dump()
        return ToolCall(input=answer, input_tokens=4000, output_tokens=1500)


@pytest.mark.db
def test_pipeline_writes_the_answer_key_to_the_database(
    tmp_path: Path, conn: psycopg.Connection
) -> None:
    ingest_dataroom(conn)
    llm = AnthropicLLMClient(
        trace=db_tracer(conn), store=RecordingStore(tmp_path), transport=PerfectTransport()
    )
    result = run_pipeline(conn, llm, mode="record")

    assert {c.status for c in result.claims} == {"verified"}
    nodes = graph_repo.list_nodes(conn, result.run_id)
    edges = graph_repo.list_edges(conn, result.run_id)
    rows = graph_repo.list_provenance(conn, result.run_id)
    assert (len(nodes), len(edges)) == (result.nodes, result.edges)
    assert_planted(nodes, edges, rows)
    # Every provenance row points at the document's own characters.
    for r in rows:
        assert PARAGRAPHS[r.paragraph_id].text[r.quote_start : r.quote_end] == r.quote


# ---------- the recorded extraction ----------


def test_consolidating_the_recorded_extraction_matches_the_answer_key() -> None:
    from tests.test_verifier import _recorded_results

    results = _recorded_results()
    if not results:
        pytest.skip("no extract.v1 recordings yet: run `lens record`")
    claims = as_claims([d for doc, result in results.items() for d in to_drafts(doc, result)])
    assert_planted(*flatten(build(claims)))
