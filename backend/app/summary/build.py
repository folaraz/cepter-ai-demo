"""GET /api/summary, assembled from the published run by backend/summary_view.yaml.

Deterministic: every value is a verified fact from the graph or a check result, and a
fact with no verified quote is left out rather than shown with a guessed value.
"""

from datetime import date
from typing import Any

import yaml

from app.api.models import (
    Asset,
    DateClash,
    DateMark,
    DateWindow,
    DocumentSummary,
    EvalStatus,
    ExpectedDocument,
    Fact,
    FindingRow,
    LongHorizonNote,
    PassedCheck,
    QuoteStatus,
    RunInfo,
    Summary,
)
from app.checks.impl._values import add_years, as_number
from app.checks.render import capitalise, format_number, number_word, short_date
from app.checks.runner import SEVERITY_RANK
from app.config import BACKEND_DIR
from app.domain.findings import FindingRecord
from app.domain.graph import Node, PropertyGroup
from app.ingest.manifest import load_asset, load_manifest
from app.published import Published, evidence_of

SUMMARY_VIEW = BACKEND_DIR / "summary_view.yaml"
_WEAKEST: list[QuoteStatus] = ["conflict", "verified", "corroborated"]


def build_summary(p: Published, eval_status: EvalStatus) -> Summary:
    view_spec = yaml.safe_load(SUMMARY_VIEW.read_text(encoding="utf-8"))
    finding_of = {spec_id: f"F-{spec.order:02d}" for spec_id, spec in p.specs.items()}

    flagged = [f for f in p.findings if p.state[f.id].result != "pass"]
    flagged.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.id))
    dates = _dates(p, view_spec["dates"], finding_of)

    return Summary(
        asset=Asset(**load_asset()),
        run=RunInfo(id=p.run.id, at=p.run_at, checks_total=len(p.findings)),
        headline=_headline(p, flagged, view_spec["headline"]),
        facts=_facts(p, view_spec["facts"], finding_of),
        dates=dates,
        date_window=_window([date.fromisoformat(d.date) for d in dates]),
        clash=_clash(p, view_spec["clash"]),
        long_horizon=_long_horizon(p, view_spec["long_horizon"]),
        findings=[finding_row(f, p) for f in flagged],
        passed=[
            PassedCheck(check_id=f.check_id, title=_passed_title(f, p))
            for f in p.findings
            if p.state[f.id].result == "pass"
        ],
        documents=_documents(p),
        missing_documents=_missing_documents(p),
        eval=eval_status,
    )


def finding_row(f: FindingRecord, p: Published) -> FindingRow:
    evidence = evidence_of(f)
    quotes = [e for e in evidence if e["kind"] == "quote"]
    titles: list[str] = []
    for e in quotes:
        if e["document_title"] not in titles:
            titles.append(e["document_title"])
    state = p.state[f.id]
    return FindingRow(
        id=f.id,
        check_id=f.check_id,
        title=f.title,
        severity=f.severity,
        result=state.result,  # type: ignore[arg-type]
        review=state.review,  # type: ignore[arg-type]
        quote_count=len(quotes),
        gap_count=len(evidence) - len(quotes),
        source_titles=titles,
    )


# ---------- headline ----------


def _headline(p: Published, flagged: list[FindingRecord], spec: dict[str, Any]) -> str:
    if not flagged:
        return f"All {len(p.findings)} checks passed."
    count = capitalise(number_word(len(flagged)))
    critical = [p.specs[f.check_id] for f in flagged if f.severity == "critical"]
    clauses = spec["critical_clause"]
    if not critical:
        clause = clauses["none"]
    elif len(critical) == 1:
        clause = clauses["one"].format(phrase=critical[0].headline_phrase)
    else:
        clause = clauses["many"].format(
            n_word=capitalise(number_word(len(critical))),
            phrases="; ".join(c.headline_phrase for c in critical),
        )
    headline = spec["template"].format(count_word=count, critical_clause=clause)
    return headline.replace("One findings.", "One finding.")


# ---------- facts ----------


def _facts(p: Published, specs: list[dict[str, Any]], finding_of: dict[str, str]) -> list[Fact]:
    facts = []
    for spec in specs:
        value_status = _fact_value(p, spec)
        if value_status is None:
            continue  # no verified quote: omitted, never guessed
        value, status = value_status
        facts.append(
            Fact(
                key=spec["key"],
                label=spec["label"],
                value=value,
                status=status,
                finding_id=finding_of[spec["finding"]],
            )
        )
    return facts


def _fact_value(p: Published, spec: dict[str, Any]) -> tuple[str, QuoteStatus] | None:
    source = spec["source"]
    if "party_role" in source:
        # YAML 1.1 reads the bare key `on` as the boolean True.
        on = source.get("on", source.get(True))
        party = _party(p, source["party_role"], on)
        if party is None or not party.name:
            return None
        rows = p.view.identity_rows(party)
        corroborated = len({r.document_id for r in rows}) >= 2
        return party.name, "corroborated" if corroborated else "verified"

    qualified = source.get("property_group") or source["property"]
    props = qualified if isinstance(qualified, list) else [qualified]
    groups: dict[str, PropertyGroup] = {}
    for q in props:
        node_type, prop = q.split(".")
        group = _group(p, node_type, prop)
        if group is None:
            return None
        groups[prop] = group

    statuses = {_status(g) for g in groups.values()}
    status = next(s for s in _WEAKEST if s in statuses)
    match spec["format"]:
        case "date_short":
            [group] = groups.values()
            return _joined(group, lambda v: short_date(date.fromisoformat(str(v)))), status
        case "as_is":
            [group] = groups.values()
            return _joined(group, str), status
    if spec["key"] == "export_capacity":
        [group] = groups.values()
        return _joined(group, lambda v: format_number(float(v))) + " MW", status
    if spec["key"] == "lease_term":
        term, start = groups["term_years"].value, groups["start_date"].value
        if term is None or start is None:
            return None
        return f"{format_number(float(term))} years from {str(start)[:4]}", status  # type: ignore[arg-type]
    raise ValueError(f"fact {spec['key']}: unknown format {spec['format']!r}")


def _joined(group: PropertyGroup, fmt: Any) -> str:
    """One value, or every value majority first when the documents disagree: "49.9 / 45"."""
    if not group.conflict:
        return str(fmt(group.values[0].value))
    return " / ".join(str(fmt(v.value)) for v in group.values)


def _status(group: PropertyGroup) -> QuoteStatus:
    if group.conflict:
        return "conflict"
    return "corroborated" if group.values[0].status == "corroborated" else "verified"


def _group(p: Published, node_type: str, prop: str) -> PropertyGroup | None:
    for node in p.view.nodes_of(node_type):
        group = p.view.group(node, prop)
        if group is not None:
            return group
    return None


def _party(p: Published, role: str, on: str) -> Node | None:
    for edge in p.view.edges:
        target = p.view.node(edge.target_id)
        if edge.type == "PARTY_TO" and edge.props.get("role") == role and target.type == on:
            return p.view.node(edge.source_id)
    return None


# ---------- dates ----------


def _dates(p: Published, specs: list[dict[str, Any]], finding_of: dict[str, str]) -> list[DateMark]:
    marks = []
    for spec in specs:
        when = _date_value(p, spec["source"])
        if when is None:
            continue
        marks.append(
            DateMark(
                key=spec["key"],
                label=spec["label"],
                date=when.isoformat(),
                tone=_tone(p, spec["tone"]),
                finding_id=finding_of[spec["finding"]],
            )
        )
    return marks


def _date_value(p: Published, source: dict[str, Any]) -> date | None:
    if "derived" in source:  # the commencement deadline
        decided = _group(p, "Permit", "decision_date")
        years = next(
            (
                p.view.group(n, "years")
                for n in p.view.nodes_of("Condition")
                if (t := p.view.group(n, "condition_type")) and t.value == "time_limit"
            ),
            None,
        )
        n_years = as_number(years.value) if years else None
        if decided is None or decided.value is None or n_years is None:
            return None
        return add_years(date.fromisoformat(str(decided.value)), int(n_years))
    node_type, prop = source["property"].split(".")
    group = _group(p, node_type, prop)
    if group is None or group.value is None:
        return None
    return date.fromisoformat(str(group.value))


def _tone(p: Published, tone: str | dict[str, str]) -> Any:
    if isinstance(tone, str):
        return tone
    ((rule, check_id),) = [(k, v) for k, v in tone.items() if k != "else"]
    return rule.split("_if_")[0] if p.result_of(check_id) != "pass" else tone["else"]


def _window(dates: list[date]) -> DateWindow:
    """From 1 Jan of the earliest year to 30 Jun of the year after the latest."""
    if not dates:
        return DateWindow(from_="", to="")
    return DateWindow(
        from_=date(min(dates).year, 1, 1).isoformat(),
        to=date(max(dates).year + 1, 6, 30).isoformat(),
    )


# ---------- clash, long horizon, passes, documents ----------


def _clash(p: Published, spec: dict[str, Any]) -> DateClash | None:
    check_id = spec["when_fails"]
    if p.result_of(check_id) == "pass":
        return None
    finding = p.by_check(check_id)
    days = finding.context.get("days")
    if not isinstance(days, int):
        return None
    return DateClash(
        from_key=spec["from_key"],
        to_key=spec["to_key"],
        days=days,
        label=spec["label"].format(days=days),
        finding_id=finding.id,
    )


def _long_horizon(p: Published, spec: dict[str, Any]) -> LongHorizonNote | None:
    check_id = spec["when_fails"]
    if p.result_of(check_id) == "pass":
        return None
    finding = p.by_check(check_id)
    block = getattr(p.specs[check_id], "long_horizon", None) or {}
    try:
        text = block["text"].format(**finding.context)
        flag = block["flag"].format(**finding.context)
    except KeyError:
        return None
    return LongHorizonNote(text=text, flag=flag, finding_id=finding.id)


def _passed_title(f: FindingRecord, p: Published) -> str:
    """The stored title for a pass; a finding corrected to pass takes the passed title."""
    if f.result == "pass":
        return f.title
    try:
        return p.specs[f.check_id].title.passed.format(**f.context)
    except KeyError:
        return f.title


def _documents(p: Published) -> list[DocumentSummary]:
    return [
        DocumentSummary(id=d.id, title=doc.title, file_name=doc.file_name, pages=doc.pages)
        for d in load_manifest()
        if (doc := p.view.documents.get(d.id)) is not None
    ]


def _missing_documents(p: Published) -> list[ExpectedDocument]:
    """One entry per missing-evidence finding whose check names the document it expects."""
    out = []
    for f in p.findings:  # by finding ID
        spec = p.specs[f.check_id]
        if p.state[f.id].result != "missing_evidence" or spec.missing is None or not f.rfi_id:
            continue
        try:
            label = spec.missing.document_label.format(**f.context)
        except KeyError:
            continue
        out.append(
            ExpectedDocument(label=label, expected_by=f.check_id, rfi_id=f.rfi_id, finding_id=f.id)
        )
    return out
