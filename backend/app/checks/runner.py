"""The check playbook: load backend/checks/*.yaml, decide each check, write its finding.

For each check, in `order`:
1. Resolve its inputs against the graph (app/checks/view.py).
2. Refuse to guess: a required input with no verified provenance makes the result
   `missing_evidence`; a required input whose values disagree makes it `conflict`.
   Otherwise the check's registered implementation decides from its `logic`.
3. Number the RFIs (missing evidence first, then conflicts, each by severity and order),
   because missing-evidence notes quote them.
4. Render title, why, how and the missing card with str.format; for a flagged finding a
   missing context key raises rather than leaving a sentence half filled.
5. Build evidence: one card per paragraph in input order (first input wins), then the
   missing card.
Every check gets a finding row, passes included, with ID F-{order:02d}.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.checks.view import GraphView, Input
from app.config import BACKEND_DIR
from app.domain.findings import FindingRecord, Result, Severity
from app.domain.graph import Provenance, ProvenanceStatus

CHECKS_DIR = BACKEND_DIR / "checks"
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ---------- check specs (the YAML) ----------


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    select: dict[str, Any]
    role: str | None = None
    role_by_document: dict[str, str] | None = None
    evidence: bool = True  # False: used in wording only, no card
    required: bool = True  # False: never blocks the check
    order: str | None = None  # "majority_first" (documentation; property_group does it)


class Titles(BaseModel):
    flagged: str
    passed: str


class MissingSpec(BaseModel):
    label: str
    note: str
    document_label: str


class RfiSpec(BaseModel):
    title: str
    request: str
    why: str
    documents_expected: list[str]


class CheckSpec(BaseModel):
    model_config = ConfigDict(extra="allow")  # summary-only blocks such as long_horizon

    id: str
    order: int
    severity: Severity
    headline_phrase: str
    inputs: list[InputSpec]
    logic: str
    context: dict[str, str] = Field(default_factory=dict)
    title: Titles
    why: str
    how: str
    missing: MissingSpec | None = None
    rfi: RfiSpec | None = None

    @property
    def finding_id(self) -> str:
        return f"F-{self.order:02d}"


def load_checks(directory: Path = CHECKS_DIR) -> list[CheckSpec]:
    specs = [
        CheckSpec.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        for p in sorted(directory.glob("*.yaml"))
    ]
    return sorted(specs, key=lambda s: s.order)


# ---------- implementations ----------


@dataclass(frozen=True)
class Outcome:
    result: Result
    context: dict[str, Any]


Implementation = Callable[[dict[str, Input], GraphView], Outcome]
_REGISTRY: dict[str, Implementation] = {}


def check(check_id: str) -> Callable[[Implementation], Implementation]:
    """Register the Python half of a check. Implementations fill in as much context as
    the graph allows even when inputs are missing: the runner may still render with it."""

    def register(fn: Implementation) -> Implementation:
        _REGISTRY[check_id] = fn
        return fn

    return register


# ---------- running ----------


@dataclass(frozen=True)
class Decided:
    spec: CheckSpec
    inputs: dict[str, Input]
    outcome: Outcome
    blocked_by: str | None  # the input that made the runner refuse to guess


def run_checks(
    view: GraphView, run_id: str, specs: list[CheckSpec] | None = None
) -> list[FindingRecord]:
    import app.checks.impl  # noqa: F401  (registers the implementations)

    decided = [_decide(spec, view) for spec in (specs or load_checks())]
    rfi_ids = assign_rfi_ids([(d.spec, d.outcome.result) for d in decided])
    return [_finding(d, rfi_ids.get(d.spec.id), view, run_id) for d in decided]


def _decide(spec: CheckSpec, view: GraphView) -> Decided:
    implementation = _REGISTRY.get(spec.id)
    if implementation is None:
        raise KeyError(f"no implementation registered for check {spec.id}")
    inputs = {i.key: view.select(i.key, i.select) for i in spec.inputs}
    outcome = implementation(inputs, view)

    blocked_by, forced = None, None
    for i in spec.inputs:
        if not i.required:
            continue
        if not inputs[i.key].present:
            blocked_by, forced = i.key, "missing_evidence"
            break
        if inputs[i.key].conflict:
            blocked_by, forced = i.key, "conflict"
            break
    if forced is not None:
        outcome = Outcome(forced, outcome.context)  # type: ignore[arg-type]
    return Decided(spec, inputs, outcome, blocked_by)


def assign_rfi_ids(results: list[tuple[CheckSpec, Result]]) -> dict[str, str]:
    """RFI-01 onwards, for flagged checks that define an RFI and are missing evidence or
    in conflict: missing evidence first, then conflicts, each by (severity, order). A
    plain fail raises no RFI: the facts are known, the question is commercial."""
    raised = [
        (spec, result)
        for spec, result in results
        if spec.rfi is not None and result in ("missing_evidence", "conflict")
    ]
    raised.sort(
        key=lambda sr: (sr[1] != "missing_evidence", SEVERITY_RANK[sr[0].severity], sr[0].order)
    )
    return {spec.id: f"RFI-{i:02d}" for i, (spec, _) in enumerate(raised, start=1)}


def initial_review_state(severity: Severity, result: Result) -> str:
    """Before anyone reviews it: critical findings and conflicts need a lawyer's eye."""
    return "needs_review" if severity == "critical" or result == "conflict" else "ai_extracted"


def _finding(d: Decided, rfi_id: str | None, view: GraphView, run_id: str) -> FindingRecord:
    spec, result = d.spec, d.outcome.result
    context = dict(d.outcome.context)
    if spec.rfi is not None:
        context["rfi_id"] = rfi_id or ""

    flagged = result != "pass"
    try:
        title = (spec.title.flagged if flagged else spec.title.passed).format(**context)
        if flagged:
            why, how = spec.why.format(**context), spec.how.format(**context)
        else:
            # A pass shows only its title. Its why/how are written for the flagged case
            # and may need values a pass never computes, so they are kept only if whole.
            why, how = _whole(spec.why, context), _whole(spec.how, context)
    except KeyError:
        if d.blocked_by is None:
            raise
        # Refused to guess before the context could be filled: say what is missing
        # instead of rendering a half-filled sentence.
        subject = spec.rfi.title if spec.rfi else spec.id.replace("_", " ").capitalize()
        missing_input = d.blocked_by.replace("_", " ")
        title = f"{subject} could not be evaluated: {missing_input} not evidenced"
        why = ""
        how = f"The check needs {missing_input}, and the data room does not evidence it."

    evidence = _evidence(spec, d.inputs, context, view)
    if result == "missing_evidence" and spec.missing is not None:
        evidence.append(
            {
                "kind": "missing",
                "label": _safe_format(spec.missing.label, context),
                "note": _safe_format(spec.missing.note, context),
                "expected_by": spec.id,
                "rfi_id": rfi_id,
            }
        )

    inputs = {key: [row.id for row in i.rows] for key, i in d.inputs.items()}
    return FindingRecord(
        run_id=run_id,
        id=spec.finding_id,
        check_id=spec.id,
        severity=spec.severity,
        result=result,
        title=title,
        why=why,
        how=how,
        context={**context, "inputs": inputs},
        evidence=evidence,
        rfi_id=rfi_id,
    )


def _whole(template: str, context: dict[str, Any]) -> str:
    """The rendered sentence, or "" if any value is missing: never half a sentence."""
    try:
        return template.format(**context)
    except KeyError:
        return ""


def _safe_format(template: str, context: dict[str, Any]) -> str:
    try:
        return template.format(**context)
    except KeyError:
        return template.split("{")[0].rstrip(" ,:")


# ---------- evidence ----------

_WEAKEST: list[ProvenanceStatus] = ["conflict", "verified", "corroborated"]


def _evidence(
    spec: CheckSpec, inputs: dict[str, Input], context: dict[str, Any], view: GraphView
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for input_spec in spec.inputs:
        if not input_spec.evidence:
            continue
        by_paragraph: dict[str, list[Provenance]] = {}
        for row in inputs[input_spec.key].rows:
            if row.paragraph_id not in seen:
                by_paragraph.setdefault(row.paragraph_id, []).append(row)
        for paragraph_id, rows in by_paragraph.items():
            seen.add(paragraph_id)
            cards.append(_quote_card(rows, input_spec, context, view))
    return cards


def _quote_card(
    rows: list[Provenance], input_spec: InputSpec, context: dict[str, Any], view: GraphView
) -> dict[str, Any]:
    """One paragraph. Several facts from the same paragraph share a card whose quote spans
    all of them, e.g. "for a term of 35 years from and including 1 January 2026"."""
    first = rows[0]
    paragraph = view.paragraphs[first.paragraph_id]
    document = view.documents[first.document_id]
    start = min(r.quote_start for r in rows)
    end = max(r.quote_end for r in rows)
    statuses = {r.status for r in rows}
    status = next(s for s in _WEAKEST if s in statuses)
    if input_spec.role_by_document:
        role = input_spec.role_by_document.get(first.document_id, "")
    else:
        role = (input_spec.role or "").format(**context)
    return {
        "kind": "quote",
        "citation": {
            "document_id": first.document_id,
            "paragraph_id": first.paragraph_id,
            "page": paragraph.page,
            "quote": paragraph.text[start:end],
        },
        "document_title": document.title,
        "file_name": document.file_name,
        "role": role,
        "heading": paragraph.heading or "",
        "paragraph_text": paragraph.text,
        "quote_start": start,
        "quote_end": end,
        "status": status,
    }
