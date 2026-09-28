"""A read-only view of one run's graph, and the input selectors checks are written in.

Selectors, as they appear under `inputs[].select` in backend/checks/*.yaml:

    {edge: CABLE_CROSSES, from: Asset}                  edges, optionally by endpoint type
    {edge: PARTY_TO, to: Lease, role: tenant}           ... and by role
    {property: GridConnection.substation}               a property of every node of a type
    {property: [Lease.start_date, Lease.term_years]}    several properties
    {property: Condition.years, where: {condition_type: temporary_period}}
    {property_group: Asset.export_capacity_mw}          every value, conflicts included
    {node: Condition, where: {condition_type: pre_commencement}}
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from psycopg import Connection

from app.db.repositories import documents as documents_repo
from app.db.repositories import graph as graph_repo
from app.domain.documents import Document, Paragraph
from app.domain.graph import Edge, Node, PropertyGroup, Provenance


class GraphView:
    def __init__(
        self,
        nodes: list[Node],
        edges: list[Edge],
        provenance: list[Provenance],
        documents: list[Document],
        paragraphs: list[Paragraph],
        document_order: list[str],
        as_of: date,
    ) -> None:
        self.as_of = as_of
        self.nodes = nodes
        self._node = {n.id: n for n in nodes}
        self.edges = edges
        self.documents = {d.id: d for d in documents}
        self.paragraphs = {p.id: p for p in paragraphs}
        self.document_order = document_order
        self._provenance = provenance
        self._by_node_prop: dict[tuple[str, str | None], list[Provenance]] = defaultdict(list)
        self._by_edge: dict[int, list[Provenance]] = defaultdict(list)
        for row in provenance:
            if row.edge_id is not None:
                self._by_edge[row.edge_id].append(row)
            elif row.node_id is not None:
                self._by_node_prop[(row.node_id, row.property)].append(row)

    @classmethod
    def load(
        cls, conn: Connection, run_id: str, document_order: list[str], as_of: date
    ) -> "GraphView":
        return cls(
            graph_repo.list_nodes(conn, run_id),
            graph_repo.list_edges(conn, run_id),
            graph_repo.list_provenance(conn, run_id),
            documents_repo.list_documents(conn),
            documents_repo.list_paragraphs(conn),
            document_order,
            as_of,
        )

    def node(self, node_id: str) -> Node:
        return self._node[node_id]

    def nodes_of(self, node_type: str) -> list[Node]:
        return [n for n in self.nodes if n.type == node_type]

    def group(self, node: Node, prop: str) -> PropertyGroup | None:
        raw = node.props.get(prop)
        return PropertyGroup.model_validate(raw) if raw is not None else None

    def property_rows(self, node: Node, prop: str) -> list[Provenance]:
        return self._by_node_prop.get((node.id, prop), [])

    def all_rows(self) -> list[Provenance]:
        return self._provenance

    def identity_rows(self, node: Node) -> list[Provenance]:
        """A party's name claims: who it is, per document."""
        return self._by_node_prop.get((node.id, None), [])

    def node_rows(self, node: Node) -> list[Provenance]:
        return [r for (nid, _), rows in self._by_node_prop.items() if nid == node.id for r in rows]

    def edge_rows(self, edge: Edge) -> list[Provenance]:
        return self._by_edge.get(edge.id, [])

    def doc_rank(self, document_id: str) -> int:
        order = self.document_order
        return order.index(document_id) if document_id in order else len(order)

    # ---------- selectors ----------

    def select(self, key: str, spec: dict[str, Any]) -> "Input":
        if "edge" in spec:
            return self._select_edges(key, spec)
        if "property_group" in spec:
            return self._select_properties(key, [spec["property_group"]], {}, majority_first=True)
        if "property" in spec:
            props = spec["property"] if isinstance(spec["property"], list) else [spec["property"]]
            return self._select_properties(key, props, spec.get("where", {}))
        if "node" in spec:
            nodes = self._where(self.nodes_of(spec["node"]), spec.get("where", {}))
            rows = [r for n in nodes for r in self.node_rows(n)]
            return Input(key, rows=rows, nodes=nodes)
        raise ValueError(f"input {key}: unknown selector {spec}")

    def _select_edges(self, key: str, spec: dict[str, Any]) -> "Input":
        sources, targets = _as_list(spec.get("from")), _as_list(spec.get("to"))
        edges = [
            e
            for e in self.edges
            if e.type == spec["edge"]
            and (not sources or self.node(e.source_id).type in sources)
            and (not targets or self.node(e.target_id).type in targets)
            and ("role" not in spec or e.props.get("role") == spec["role"])
        ]
        return Input(key, rows=[r for e in edges for r in self.edge_rows(e)], edges=edges)

    def _select_properties(
        self, key: str, props: list[str], where: dict[str, Any], majority_first: bool = False
    ) -> "Input":
        selected = Input(key)
        missing_prop = False
        for qualified in props:
            node_type, prop = qualified.split(".")
            nodes = self._where(self.nodes_of(node_type), where)
            found = False
            for node in nodes:
                group = self.group(node, prop)
                if group is None:
                    continue
                found = True
                if node not in selected.nodes:
                    selected.nodes.append(node)
                selected.groups[prop] = group
                rows = self.property_rows(node, prop)
                if majority_first:
                    rank = {_key(v.value): i for i, v in enumerate(group.values)}
                    rows = sorted(
                        rows,
                        key=lambda r: (rank.get(_key(r.value), 99), self.doc_rank(r.document_id)),
                    )
                selected.rows += rows
            missing_prop = missing_prop or not found
        selected.incomplete = missing_prop
        return selected

    def _where(self, nodes: list[Node], where: dict[str, Any]) -> list[Node]:
        def matches(node: Node) -> bool:
            for prop, wanted in where.items():
                group = self.group(node, prop)
                if group is None or wanted not in [v.value for v in group.values]:
                    return False
            return True

        return [n for n in nodes if matches(n)]


@dataclass
class Input:
    """What one selector found: the provenance behind it, and the nodes, groups and edges
    a check's logic reads values from."""

    key: str
    rows: list[Provenance] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    groups: dict[str, PropertyGroup] = field(default_factory=dict)
    incomplete: bool = False  # a listed property had no verified value

    @property
    def present(self) -> bool:
        return bool(self.rows) and not self.incomplete

    @property
    def conflict(self) -> bool:
        return any(g.conflict for g in self.groups.values())

    def value(self, prop: str) -> Any:
        """The property's agreed value, or None if missing or disputed."""
        group = self.groups.get(prop)
        return group.value if group else None


def _as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _key(value: Any) -> Any:
    return float(value) if isinstance(value, int | float) else value
