"""Pass 3: merge verified claims from every document into one graph.

1. The Asset node comes from the manifest.
2. Every other entity a verified claim is about is resolved to a node by its type's merge
   rule in ontology.yaml (a party's normalised name, a parcel's number, a permit's
   reference, one agreement per document). The value a key is built from must itself be
   verified; otherwise the entity keeps a node of its own ("{document}:{local_id}").
3. Verified values are grouped by (node, property) into PropertyGroups, each document
   counting once per value.
4. Each supporting claim becomes a provenance row carrying its value's status.

Pure: consolidate() builds the graph in memory, write_graph() stores it.
"""

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from psycopg import Connection
from pydantic import JsonValue

from app.consolidate.names import is_company, name_key, person_name, without_suffix
from app.db.repositories import graph as graph_repo
from app.domain.claims import Claim
from app.domain.documents import Paragraph
from app.domain.graph import (
    NewEdge,
    NewProvenance,
    Node,
    PropertyGroup,
    ProvenanceStatus,
    ValueSupport,
)
from app.domain.ontology import ASSET, ASSET_LOCAL_ID, Ontology

# Roles in which a person signs, so the name there is how they are shown.
CONTRACTING_ROLES = {"landlord", "tenant", "buyer", "generator", "customer", "network_operator"}
IDENTITY_PROPERTY = "name"  # a Party's name claims are its identity, not a property
_CONDITION_HEADING = re.compile(r"\bCondition (\d+)\b")

EntityRef = tuple[str, str]  # (document_id, local_id)


@dataclass
class ConsolidatedGraph:
    nodes: list[Node]
    provenance: list[NewProvenance]  # node provenance; edge provenance is in `edges`
    edges: list[tuple[NewEdge, list[tuple[Claim, ProvenanceStatus]]]]


@dataclass
class _Entity:
    document_id: str
    local_id: str
    type: str
    name: str | None = None
    claims: list[Claim] = field(default_factory=list)  # verified property claims about it


def consolidate(
    run_id: str,
    claims: Iterable[Claim],
    paragraphs: Mapping[str, Paragraph],
    ontology: Ontology,
    asset_name: str,
    document_order: list[str],
) -> ConsolidatedGraph:
    verified = [c for c in claims if c.status == "verified"]
    entities = _entities(verified)
    keys = _Keys(entities, verified, paragraphs, ontology)
    rank = {doc: i for i, doc in enumerate(document_order)}

    def node_id(ref: EntityRef) -> str:
        entity = entities[ref]
        return f"{run_id}:{entity.type}:{keys.of(ref)}"

    members: dict[str, list[_Entity]] = defaultdict(list)
    for ref, entity in entities.items():
        members[node_id(ref)].append(entity)

    # Property groups, and the provenance rows that support them.
    by_property: dict[tuple[str, str], list[Claim]] = defaultdict(list)
    identity: dict[str, list[Claim]] = defaultdict(list)
    for claim in verified:
        if claim.kind != "property":
            continue
        ref = (claim.document_id, str(claim.local_ref["local_id"]))
        if entities[ref].type == "Party" and claim.property == IDENTITY_PROPERTY:
            identity[node_id(ref)].append(claim)
        else:
            by_property[(node_id(ref), str(claim.property))].append(claim)

    props: dict[str, dict[str, JsonValue]] = defaultdict(dict)
    provenance: list[NewProvenance] = []
    for (nid, prop), group_claims in by_property.items():
        node_type = members[nid][0].type
        many = ontology.nodes[node_type].properties[prop].many
        group, status_of = _group(group_claims, many, rank)
        props[nid][prop] = group.model_dump()
        provenance += [_provenance(run_id, c, nid, prop, status_of(c)) for c in group_claims]

    for nid, name_claims in identity.items():
        docs = {c.document_id for c in name_claims}
        status: ProvenanceStatus = "corroborated" if len(docs) >= 2 else "verified"
        provenance += [_provenance(run_id, c, nid, None, status) for c in name_claims]

    nodes = [
        Node(
            id=nid,
            run_id=run_id,
            type=group[0].type,
            key=keys.of((group[0].document_id, group[0].local_id)),
            name=asset_name
            if group[0].type == ASSET
            else _display_name(group[0].type, group, identity.get(nid, []), verified, keys),
            props=props.get(nid, {}),
        )
        for nid, group in members.items()
    ]
    asset_id = f"{run_id}:{ASSET}:{ASSET_LOCAL_ID}"
    if asset_id not in members:  # the Asset exists even if no document states a fact about it
        nodes.append(
            Node(
                id=asset_id,
                run_id=run_id,
                type=ASSET,
                key=ASSET_LOCAL_ID,
                name=asset_name,
                props={},
            )
        )

    # Edges: one per (type, source, target, role), however many claims support it.
    edge_claims: dict[tuple[str, str, str, str | None], list[Claim]] = defaultdict(list)
    for claim in verified:
        if claim.kind != "edge":
            continue
        source = node_id((claim.document_id, str(claim.local_ref["local_id"])))
        target = node_id((claim.document_id, str((claim.target_ref or {})["local_id"])))
        role = claim.value if isinstance(claim.value, str) else None
        edge_claims[(str(claim.edge_type), source, target, role)].append(claim)

    edges = []
    for (edge_type, source, target, role), supporting in edge_claims.items():
        docs = {c.document_id for c in supporting}
        edge_status: ProvenanceStatus = "corroborated" if len(docs) >= 2 else "verified"
        edge = NewEdge(
            run_id=run_id,
            type=edge_type,
            source_id=source,
            target_id=target,
            props={"role": role} if role else {},
        )
        edges.append((edge, [(c, edge_status) for c in supporting]))

    nodes.sort(key=lambda n: (n.type != ASSET, n.type, n.key))
    return ConsolidatedGraph(nodes=nodes, provenance=provenance, edges=edges)


def write_graph(conn: Connection, graph: ConsolidatedGraph) -> None:
    graph_repo.insert_nodes(conn, graph.nodes)
    rows = list(graph.provenance)
    for edge, supporting in graph.edges:
        stored = graph_repo.insert_edge(conn, edge)
        rows += [
            _provenance(edge.run_id, claim, None, None, status, edge_id=stored.id)
            for claim, status in supporting
        ]
    graph_repo.insert_provenance(conn, rows)


# ---------- entities and keys ----------


def _entities(verified: list[Claim]) -> dict[EntityRef, _Entity]:
    """Every entity a verified claim is about or connects, by (document, local_id)."""
    entities: dict[EntityRef, _Entity] = {}

    def add(document_id: str, ref: Mapping[str, JsonValue]) -> _Entity:
        key = (document_id, str(ref["local_id"]))
        if key not in entities:
            name = ref.get("name")
            entities[key] = _Entity(
                document_id, key[1], str(ref["type"]), name if isinstance(name, str) else None
            )
        return entities[key]

    for claim in verified:
        entity = add(claim.document_id, claim.local_ref)
        if claim.kind == "property":
            entity.claims.append(claim)
        elif claim.target_ref is not None:
            add(claim.document_id, claim.target_ref)
    return entities


class _Keys:
    """Merge keys by the ontology's merge rules, built only from verified values."""

    def __init__(
        self,
        entities: dict[EntityRef, _Entity],
        verified: list[Claim],
        paragraphs: Mapping[str, Paragraph],
        ontology: Ontology,
    ) -> None:
        self._entities = entities
        self._verified = verified
        self._paragraphs = paragraphs
        self._rules = ontology.merge
        self._cache: dict[EntityRef, str] = {}

    def of(self, ref: EntityRef) -> str:
        if ref not in self._cache:
            self._cache[ref] = self._key(self._entities[ref])
        return self._cache[ref]

    def _key(self, e: _Entity) -> str:
        if e.type == ASSET:
            return ASSET_LOCAL_ID
        fallback = f"{e.document_id}:{e.local_id}"
        match self._rules.get(e.type):
            case "one_per_document":
                return e.document_id
            case "name":
                name = self.party_name(e)
                return name_key(name) if name else fallback
            case "reference":
                ref = _first_value(e, "reference")
                return " ".join(str(ref).split()) if ref is not None else fallback
            case "number" if e.type == "LandParcel":
                number = self._parcel_number(e)
                return number or fallback
            case "number" if e.type == "Condition":
                number = self._condition_number(e)
                return f"{self._permit_scope(e.document_id)}/{number}" if number else fallback
            case _:
                return fallback

    def party_name(self, e: _Entity) -> str | None:
        """From its own verified name claim, else from a verified PARTY_TO edge it is the
        source of (the verifier checked the name against that edge's quote)."""
        stated = _first_value(e, IDENTITY_PROPERTY)
        if isinstance(stated, str):
            return stated
        for c in self._edges_touching(e, as_source=True):
            if c.edge_type == "PARTY_TO" and e.name:
                return e.name
        return None

    def _parcel_number(self, e: _Entity) -> str | None:
        """From its verified number claim, else from its name when a verified edge points
        at it (the verifier checked that number against the edge's quote)."""
        source = _first_value(e, "number")
        if source is None and any(self._edges_touching(e, as_source=False)):
            source = e.name
        digits = re.sub(r"\D", "", str(source)) if source is not None else ""
        return digits or None

    def _condition_number(self, e: _Entity) -> str | None:
        """From its verified number claim, else from the headings of the paragraphs its
        verified claims cite ("Condition 3: Temporary permission"): planning decisions
        number conditions in headings, which quotes cannot reach."""
        stated = _first_value(e, "number")
        if isinstance(stated, int | float):
            return str(int(stated))
        cited = [c.paragraph_id for c in e.claims]
        cited += [c.paragraph_id for c in self._edges_touching(e, as_source=False)]
        numbers = set()
        for pid in cited:
            heading = self._paragraphs[pid].heading if pid in self._paragraphs else None
            match = _CONDITION_HEADING.search(heading or "")
            if match:
                numbers.add(match.group(1))
        return numbers.pop() if len(numbers) == 1 else None

    def _permit_scope(self, document_id: str) -> str:
        """Conditions are numbered within their permit: the permit in the same document."""
        for ref, e in self._entities.items():
            if ref[0] == document_id and e.type == "Permit":
                return self.of(ref)
        return document_id

    def _edges_touching(self, e: _Entity, *, as_source: bool) -> Iterable[Claim]:
        for c in self._verified:
            if c.kind != "edge" or c.document_id != e.document_id:
                continue
            ref = c.local_ref if as_source else (c.target_ref or {})
            if ref.get("local_id") == e.local_id:
                yield c


def _first_value(e: _Entity, prop: str) -> JsonValue:
    return next((c.value for c in e.claims if c.property == prop), None)


# ---------- property groups ----------


def _canonical(value: JsonValue) -> Any:
    """Equal values compare equal: 49.9 == 49.90, "a  b" == "a b", lists ignore order."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return tuple(sorted(_canonical(v) for v in value))
    return repr(value)


def _group(claims: list[Claim], many: bool, rank: Mapping[str, int]) -> tuple[PropertyGroup, Any]:
    """The property group, and a function giving each claim's status within it."""
    first_value: dict[Any, JsonValue] = {}
    docs: dict[Any, set[str]] = defaultdict(set)
    for c in claims:
        items = c.value if many and isinstance(c.value, list) else [c.value]
        for v in items:
            key = _canonical(v)
            first_value.setdefault(key, v)
            docs[key].add(c.document_id)

    def count(key: Any) -> int:
        return len(docs[key])

    status: dict[Any, ProvenanceStatus] = {}
    if many or len(docs) == 1:
        for key in docs:
            status[key] = "corroborated" if count(key) >= 2 else "verified"
        conflict = False
    else:
        top = max(count(k) for k in docs)
        leaders = [k for k in docs if count(k) == top]
        winner = leaders[0] if len(leaders) == 1 and top >= 2 else None
        for key in docs:
            status[key] = "corroborated" if key == winner else "conflict"
        conflict = True

    order = {"corroborated": 0, "verified": 1, "conflict": 2}
    ordered = sorted(
        docs,
        key=lambda k: (order[status[k]], -count(k), min(rank.get(d, 99) for d in docs[k])),
    )
    group = PropertyGroup(
        values=[
            ValueSupport(
                value=first_value[k],
                status=status[k],
                documents=sorted(docs[k], key=lambda d: rank.get(d, 99)),
            )
            for k in ordered
        ],
        conflict=conflict,
    )

    def status_of(claim: Claim) -> ProvenanceStatus:
        items = claim.value if many and isinstance(claim.value, list) else [claim.value]
        statuses = {status[_canonical(v)] for v in items}
        for s in ("conflict", "verified", "corroborated"):
            if s in statuses:
                return s  # a claim is only as strong as its weakest value
        return "verified"

    return group, status_of


def _provenance(
    run_id: str,
    claim: Claim,
    node_id: str | None,
    prop: str | None,
    status: ProvenanceStatus,
    edge_id: int | None = None,
) -> NewProvenance:
    assert claim.quote_start is not None and claim.quote_end is not None
    return NewProvenance(
        run_id=run_id,
        node_id=node_id,
        edge_id=edge_id,
        property=prop,
        value=claim.value,
        claim_id=claim.id,
        document_id=claim.document_id,
        paragraph_id=claim.paragraph_id,
        quote=claim.quote,
        quote_start=claim.quote_start,
        quote_end=claim.quote_end,
        status=status,
    )


# ---------- display names ----------


def _display_name(
    node_type: str,
    members: list[_Entity],
    name_claims: list[Claim],
    verified: list[Claim],
    keys: _Keys,
) -> str | None:
    if node_type == "LandParcel":
        return f"Parcel {keys.of((members[0].document_id, members[0].local_id))}"
    if node_type == "Condition":
        key = keys.of((members[0].document_id, members[0].local_id))
        number = key.rsplit("/", 1)[-1]
        return f"Condition {number}" if number.isdigit() else None
    if node_type != "Party":
        return None

    names = [str(c.value) for c in name_claims] or [n for m in members if (n := keys.party_name(m))]
    if not names:
        return None
    if is_company(names[0]):
        return without_suffix(names[0])
    # A person is shown as named where they sign: landlord, tenant, buyer...
    contracting_docs = {
        c.document_id
        for c in verified
        if c.edge_type == "PARTY_TO"
        and c.value in CONTRACTING_ROLES
        and any(
            c.local_ref.get("local_id") == m.local_id and c.document_id == m.document_id
            for m in members
        )
    }
    signed = [str(c.value) for c in name_claims if c.document_id in contracting_docs]
    chosen = (signed or names)[0]
    person = person_name(chosen)
    words = chosen.split() if person is None else _without_honorific(chosen).split()
    return " ".join(w if w.isupper() and len(w) <= 2 else w.capitalize() for w in words)


def _without_honorific(name: str) -> str:
    return re.sub(r"^(?:mr|mrs|ms|dr|sir)\.?\s+", "", name.strip(), flags=re.IGNORECASE)
