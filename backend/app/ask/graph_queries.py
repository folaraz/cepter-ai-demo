"""Relationship answers (SPEC C14 step 4): a closed set of graph queries over a run,
rendered from the templates in backend/ask.yaml. No model writes these sentences.

Citations come from provenance (status from provenance, role "cited in answer"), one per
paragraph. A sentence that states an absence can't be quoted, so it links to the
finding that established it instead.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.api.models import AskSentence, QuoteEvidence
from app.checks.render import format_number, short_date
from app.consolidate.graph import CONTRACTING_ROLES
from app.domain.ask import ask_config
from app.domain.findings import FindingRecord
from app.domain.graph import Provenance
from app.published import Published

_WEAKEST = ["conflict", "verified", "corroborated"]


@dataclass
class Answer:
    sentences: list[AskSentence] = field(default_factory=list)
    related_finding_id: str | None = None
    related_rfi_id: str | None = None


def run_graph_query(p: Published, query_id: str, params: dict[str, Any]) -> Answer:
    query = ask_config().graph_queries[query_id]
    if "context_from_check" in query:
        answer = _from_check(p, query)
    elif query_id == "parties":
        answer = _parties(p, query, params.get("agreement"))
    elif query_id == "property_sources":
        answer = _property_sources(p, query, params["property"])
    else:
        raise KeyError(f"no renderer for graph query {query_id}")
    if "related_finding" in query:
        finding = p.by_check(query["related_finding"])
        answer.related_finding_id, answer.related_rfi_id = finding.id, finding.rfi_id
    return answer


# ---------- citations ----------


def citations(p: Published, rows: list[Provenance]) -> list[QuoteEvidence]:
    """One citation per paragraph, spanning every quote in it, in first-seen order."""
    by_paragraph: dict[str, list[Provenance]] = {}
    for row in rows:
        by_paragraph.setdefault(row.paragraph_id, []).append(row)
    out = []
    for pid, group in by_paragraph.items():
        paragraph = p.view.paragraphs[pid]
        document = p.view.documents[group[0].document_id]
        start = min(r.quote_start for r in group)
        end = max(r.quote_end for r in group)
        statuses = {r.status for r in group}
        out.append(
            QuoteEvidence.model_validate(
                {
                    "kind": "quote",
                    "citation": {
                        "document_id": document.id,
                        "paragraph_id": pid,
                        "page": paragraph.page,
                        "quote": paragraph.text[start:end],
                    },
                    "document_title": document.title,
                    "file_name": document.file_name,
                    "role": "cited in answer",
                    "heading": paragraph.heading or "",
                    "paragraph_text": paragraph.text,
                    "quote_start": start,
                    "quote_end": end,
                    "status": next(s for s in _WEAKEST if s in statuses),
                }
            )
        )
    return out


def _rows(p: Published, ids: list[int]) -> list[Provenance]:
    by_id = {r.id: r for r in p.view.all_rows()}
    return [by_id[i] for i in ids if i in by_id]


def _sentence(
    p: Published,
    template: dict[str, Any],
    context: dict[str, Any],
    rows: list[Provenance],
    finding: FindingRecord | None = None,
) -> AskSentence | None:
    if "when" in template and not context.get(template["when"]):
        return None
    text = template["text"].format(**context)
    if template.get("finding"):
        assert finding is not None
        return AskSentence(text=text, citations=[], finding_id=finding.id)
    return AskSentence(text=text, citations=citations(p, rows), finding_id=None)


# ---------- the queries ----------


def _from_check(p: Published, query: dict[str, Any]) -> Answer:
    """Reuse a check's inputs and context: cable_route_rights, pre_commencement_conditions."""
    finding = p.by_check(query["context_from_check"])
    context = {k: v for k, v in finding.context.items() if k != "inputs"}
    context["all_covered"] = finding.result == "pass"
    inputs: dict[str, list[int]] = finding.context.get("inputs", {})  # type: ignore[assignment]
    answer = Answer()
    for template in query["sentences"]:
        rows = [r for key in template.get("cite", []) for r in _rows(p, inputs.get(key, []))]
        sentence = _sentence(p, template, context, rows, finding)
        if sentence is not None:
            answer.sentences.append(sentence)
    return answer


def _parties(p: Published, query: dict[str, Any], agreement: str | None) -> Answer:
    agreements = list(query["agreement_phrases"])
    roles = list(query["role_labels"])
    edges = [
        e
        for e in p.view.edges
        if e.type == "PARTY_TO"
        and (agreement is None or p.view.node(e.target_id).type == agreement)
    ]

    def order(e: Any) -> tuple[int, bool, int]:
        target = p.view.node(e.target_id).type
        role = e.props.get("role")
        return (
            agreements.index(target) if target in agreements else len(agreements),
            role not in CONTRACTING_ROLES,  # contracting roles before mentions
            roles.index(role) if role in roles else len(roles),
        )

    [template] = query["sentences"]
    answer = Answer()
    for edge in sorted(edges, key=order):
        party = p.view.node(edge.source_id)
        context = {
            "party": party.name or party.key,
            "role_label": query["role_labels"].get(edge.props.get("role"), edge.props.get("role")),
            "agreement_phrase": query["agreement_phrases"].get(
                p.view.node(edge.target_id).type, ""
            ),
        }
        sentence = _sentence(p, template, context, p.view.edge_rows(edge))
        if sentence is not None:
            answer.sentences.append(sentence)
    return answer


def _property_sources(p: Published, query: dict[str, Any], qualified: str) -> Answer:
    spec = query["params"]["property"]["allowed"][qualified]
    node_type, prop = qualified.split(".")
    answer = Answer()
    for node in p.view.nodes_of(node_type):
        group = p.view.group(node, prop)
        if group is None:
            continue
        rank = {_key(v.value): i for i, v in enumerate(group.values)}  # corroborated first
        rows = sorted(
            p.view.property_rows(node, prop),
            key=lambda r: (rank.get(_key(r.value), 99), p.view.doc_rank(r.document_id)),
        )
        seen: set[tuple[str, Any]] = set()
        each, conflict_sentence = query["sentences"]
        for row in rows:
            if (row.document_id, _key(row.value)) in seen:
                continue
            seen.add((row.document_id, _key(row.value)))
            context = {
                "document_title_lower": p.view.documents[row.document_id].title.lower(),
                "value_text": _format(row.value, spec),
            }
            same = [
                r
                for r in rows
                if r.document_id == row.document_id and _key(r.value) == _key(row.value)
            ]
            sentence = _sentence(p, each, context, same)
            if sentence is not None:
                answer.sentences.append(sentence)
        finding = p.by_check(spec["check"])
        closing = _sentence(p, conflict_sentence, {"conflict": group.conflict}, [], finding)
        if closing is not None:
            answer.sentences.append(closing)
        answer.related_finding_id, answer.related_rfi_id = finding.id, finding.rfi_id
        break
    return answer


def _key(value: Any) -> Any:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else value


def _format(value: Any, spec: dict[str, Any]) -> str:
    if spec["format"] == "date_short":
        text = short_date(date.fromisoformat(str(value)))
    elif spec["format"] == "number":
        text = format_number(float(value))
    else:
        text = str(value)
    return f"{text} {spec['unit']}".strip()
