"""GET /api/documents and GET /api/documents/{id}: each document in the data room, read
page by page, with every statement taken from it as a note beside its quote.

Deterministic, like the summary: notes come from the published run's provenance and are
worded by backend/documents_view.yaml. Nothing here is written by a model.
"""

from dataclasses import dataclass, field
from datetime import date
from functools import cache
from string import Formatter
from typing import Any

import yaml

from app.api.models import (
    DocumentDate,
    DocumentDetail,
    DocumentListItem,
    DocumentNote,
    DocumentPage,
    DocumentParagraph,
    DocumentParty,
    QuoteStatus,
)
from app.checks.render import capitalise, format_number, join_prose, range_short, short_date
from app.config import BACKEND_DIR
from app.domain.ask import ask_config
from app.domain.documents import Paragraph
from app.domain.findings import FindingRecord
from app.domain.graph import Provenance
from app.published import Published

DOCUMENTS_VIEW = BACKEND_DIR / "documents_view.yaml"

# A note folding several rows shows the one a reviewer most needs to see.
_STATUS_ORDER: list[QuoteStatus] = ["conflict", "verified", "corroborated"]


@cache
def _spec() -> dict[str, Any]:
    return yaml.safe_load(DOCUMENTS_VIEW.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@dataclass
class _Note:
    paragraph_id: str
    start: int
    end: int
    label: str
    values: list[str] = field(default_factory=list)  # one value, or parcel numbers
    parcels: bool = False
    statuses: set[str] = field(default_factory=set)


def list_documents(p: Published) -> list[DocumentListItem]:
    return [_item(p, doc_id, _notes(p, doc_id)) for doc_id in _document_ids(p)]


def document_detail(p: Published, doc_id: str) -> DocumentDetail | None:
    if doc_id not in _document_ids(p):
        return None
    notes = _notes(p, doc_id)
    return DocumentDetail(document=_item(p, doc_id, notes), pages=_pages(p, doc_id), notes=notes)


# ---------- the list row ----------


def _document_ids(p: Published) -> list[str]:
    return [d for d in p.view.document_order if d in p.view.documents]


def _item(p: Published, doc_id: str, notes: list[DocumentNote]) -> DocumentListItem:
    document = p.view.documents[doc_id]
    paragraphs = {q.id for q in _paragraphs(p, doc_id)}
    return DocumentListItem(
        id=doc_id,
        title=document.title,
        file_name=document.file_name,
        pages=document.pages,
        parties=_parties(p, doc_id),
        date=_date(p, doc_id),
        finding_ids=[
            f.id for f in p.findings if any(pid in paragraphs for pid, _, _ in _quotes(f))
        ],
        note_count=len(notes),
    )


def _parties(p: Published, doc_id: str) -> list[DocumentParty]:
    labels: dict[str, str] = ask_config().graph_queries["parties"]["role_labels"]
    seen: set[str] = set()
    out = []
    for row in _rows(p, doc_id):
        edge = _edge(p, row)
        if edge is None or edge.type != "PARTY_TO":
            continue
        name = p.view.node(edge.source_id).name or ""
        if name in seen:
            continue
        seen.add(name)
        role = str(edge.props.get("role", ""))
        out.append(DocumentParty(name=name, role=labels.get(role, role)))
    return out


def _date(p: Published, doc_id: str) -> DocumentDate | None:
    spec = (_spec()["documents"].get(doc_id) or {}).get("date")
    if spec is None:
        return None
    for row in _rows(p, doc_id):
        if row.node_id and _qualified(p, row) == spec["property"]:
            return DocumentDate(
                label=spec["label"], value=short_date(date.fromisoformat(str(row.value)))
            )
    return None


# ---------- pages ----------


def _paragraphs(p: Published, doc_id: str) -> list[Paragraph]:
    return sorted(
        (q for q in p.view.paragraphs.values() if q.document_id == doc_id),
        key=lambda q: (q.page, q.ordinal),
    )


def _pages(p: Published, doc_id: str) -> list[DocumentPage]:
    pages: dict[int, list[DocumentParagraph]] = {}
    for q in _paragraphs(p, doc_id):
        pages.setdefault(q.page, []).append(
            DocumentParagraph(id=q.id, heading=q.heading or "", text=q.text)
        )
    return [DocumentPage(number=n, paragraphs=paras) for n, paras in pages.items()]


# ---------- notes ----------


def _notes(p: Published, doc_id: str) -> list[DocumentNote]:
    spec = _spec()
    folded: dict[tuple[str, int, int, str], _Note] = {}
    for row in _rows(p, doc_id):
        described = _describe(p, row, spec)
        if described is None:
            continue
        label, value, parcels = described
        key = (row.paragraph_id, row.quote_start, row.quote_end, label)
        note = folded.setdefault(
            key, _Note(row.paragraph_id, row.quote_start, row.quote_end, label, parcels=parcels)
        )
        if value not in note.values:
            note.values.append(value)
        note.statuses.add(row.status)

    order = {q.id: i for i, q in enumerate(_paragraphs(p, doc_id))}
    notes = [*folded.values(), *_condition_notes(p, doc_id, spec["conditions"])]
    ordered = sorted(notes, key=lambda n: (order[n.paragraph_id], n.start, n.end))
    return [
        DocumentNote(
            id=f"n{i}",
            paragraph_id=n.paragraph_id,
            quote_start=n.start,
            quote_end=n.end,
            label=n.label,
            value=_parcels(n.values) if n.parcels else n.values[0],
            status=next(s for s in _STATUS_ORDER if s in n.statuses),
            finding_ids=_findings_quoting(p, n.paragraph_id, n.start, n.end),
        )
        for i, n in enumerate(ordered, start=1)
    ]


def _describe(p: Published, row: Provenance, spec: dict[str, Any]) -> tuple[str, str, bool] | None:
    """(label, value, is_parcels), or None for a row another row already says."""
    edge = _edge(p, row)
    if edge is not None:
        edge_spec = spec["edges"].get(edge.type)
        if edge_spec is None:
            return None  # HAS_CONDITION: the condition's type row says it
        if edge_spec["value"] == "party":
            labels: dict[str, str] = ask_config().graph_queries["parties"]["role_labels"]
            role = str(edge.props.get("role", ""))
            return capitalise(labels.get(role, role)), p.view.node(edge.source_id).name or "", False
        return edge_spec["label"], p.view.node(edge.target_id).key, True
    if row.property is None:
        return None  # a party's name: its PARTY_TO row quotes it too
    if p.view.node(row.node_id or "").type == "Condition":
        return None  # one note per condition: see _condition_notes
    prop_spec = spec["properties"].get(_qualified(p, row))
    if prop_spec is None:
        return None  # a parcel's number: its parcel edge says it
    node = p.view.node(row.node_id or "")
    label = prop_spec["label"].format(name=node.name or "")
    return label, _format(row.value, prop_spec, row.property, spec["enums"]), False


def _format(value: Any, prop_spec: dict[str, Any], prop: str, enums: dict[str, Any]) -> str:
    unit = prop_spec.get("unit", "")
    match prop_spec["format"]:
        case "date":
            text = short_date(date.fromisoformat(str(value)))
        case "number":
            text = format_number(float(value))
        case "money":
            text = f"£{float(value):,.2f}"
        case "enum":
            labels = enums[prop]
            values = value if isinstance(value, list) else [value]
            text = capitalise(join_prose([labels.get(v, v) for v in values]))
        case _:
            text = str(value)
    return f"{text} {unit}".strip()


def _condition_notes(p: Published, doc_id: str, spec: dict[str, Any]) -> list[_Note]:
    """One note per planning condition, worded as what it asks of the project: its type,
    years and requirement folded into one sentence, marked across every span they quote."""
    rows_of: dict[str, list[Provenance]] = {}
    for row in _rows(p, doc_id):
        if row.edge_id is None and row.node_id and p.view.node(row.node_id).type == "Condition":
            rows_of.setdefault(row.node_id, []).append(row)
    notes = []
    for node_id, rows in rows_of.items():
        values = {r.property: r.value for r in rows}
        kind = values.get("condition_type")
        if kind is None:
            continue  # nothing says what the condition is
        text = condition_text(str(kind), values, spec)
        paragraph = next(r.paragraph_id for r in rows if r.property == "condition_type")
        same = [r for r in rows if r.paragraph_id == paragraph]
        notes.append(
            _Note(
                paragraph,
                min(r.quote_start for r in same),
                max(r.quote_end for r in same),
                p.view.node(node_id).name or "Condition",
                values=[text],
                statuses={r.status for r in same},
            )
        )
    return notes


def condition_text(kind: str, values: dict[str | None, Any], spec: dict[str, Any]) -> str:
    """The obligation a condition puts on the project, from its own verified values. A
    sentence that needs a value that wasn't quoted uses its `without` wording instead."""
    wording = spec.get(kind, spec["other"])
    known: dict[str, Any] = {"requires": values.get("requires")}
    if values.get("years") is not None:
        known["years"] = format_number(float(values["years"]))
    needed = {name for _, name, _, _ in Formatter().parse(wording["text"]) if name}
    if all(known.get(n) is not None for n in needed):
        text: str = wording["text"].format(**known)
    else:
        text = wording.get("without", wording["text"])
    if values.get("discharged_on") is not None:
        done = short_date(date.fromisoformat(str(values["discharged_on"])))
        text = f"{text}. {spec['discharged'].format(date=done)}"
    return text


def _parcels(numbers: list[str]) -> str:
    ordered = sorted(int(n) for n in numbers)
    return f"Parcel {ordered[0]}" if len(ordered) == 1 else f"Parcels {range_short(ordered)}"


def _findings_quoting(p: Published, paragraph_id: str, start: int, end: int) -> list[str]:
    return [
        f.id
        for f in p.findings
        if any(pid == paragraph_id and s < end and start < e for pid, s, e in _quotes(f))
    ]


# ---------- helpers ----------


def _rows(p: Published, doc_id: str) -> list[Provenance]:
    return [r for r in p.view.all_rows() if r.document_id == doc_id]


def _edge(p: Published, row: Provenance) -> Any:
    if row.edge_id is None:
        return None
    return next(e for e in p.view.edges if e.id == row.edge_id)


def _qualified(p: Published, row: Provenance) -> str:
    return f"{p.view.node(row.node_id or '').type}.{row.property}"


def _quotes(finding: FindingRecord) -> list[tuple[str, int, int]]:
    """(paragraph_id, quote_start, quote_end) for each quote in a finding's evidence."""
    out = []
    for e in finding.evidence:
        citation = e.get("citation")
        if e.get("kind") == "quote" and isinstance(citation, dict):
            start, end = e["quote_start"], e["quote_end"]
            assert isinstance(start, int) and isinstance(end, int)
            out.append((str(citation["paragraph_id"]), start, end))
    return out
