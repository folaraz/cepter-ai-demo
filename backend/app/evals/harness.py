"""`lens eval` and POST /api/evals/run: re-run the pipeline and score it (SPEC C11).

1. Run the whole pipeline in replay mode into a new `eval` run.
2. Score each kind of golden item as a ratio:
     extraction         fact and edge items: a verified provenance row has that node,
                        property or edge, value and paragraph
     conflicts          the property group is in conflict with the same values and documents
     checks             the pipeline's result equals `expect`
     corrections held   the effective result equals `expect`
     citation validity  every quote served in findings and facts is the paragraph's own text
   A correction's effective result is the pipeline's, overridden by the lawyer's only while
   the finding's evidence fingerprint is the one the lawyer reviewed. When a cited
   paragraph changes, the override lapses and the correction is no longer held.
3. Report, without gating: corrections the pipeline already agrees with ("learned"), the
   verifier's rejection rate, model calls and their cost.
4. Passing needs every golden item to pass (extraction, conflicts, checks, corrections,
   and Ask's answers and abstentions) and citation validity of 100%. An average can hide
   a broken check, so each item is its own gate: everything replays deterministically,
   so anything under 100% is a regression, not noise. `score` (the mean of the ratios)
   is reported and shown in the UI. `gate` is also applied to it, for later evals against
   a live model where some variance is expected.
5. Write an eval_runs row.

Ask's three metrics (retrieval recall, answer accuracy, abstention) join in C14.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from psycopg import Connection

from app.checks.view import GraphView
from app.consolidate.names import name_key
from app.db.repositories import claims as claims_repo
from app.db.repositories import evals as evals_repo
from app.db.repositories import findings as findings_repo
from app.db.repositories import runs
from app.domain.evals import EvalOutcome, EvalRun, NewEvalRun
from app.domain.findings import FindingRecord
from app.domain.graph import Node
from app.evals.ask_eval import AskRunner, score_ask
from app.evals.golden import GoldenSet, golden_set
from app.evals.ratio import Ratio
from app.ingest.manifest import load_manifest
from app.llm.client import LLMClient
from app.pipeline import run_pipeline
from app.published import evidence_of
from app.reviews.fingerprint import evidence_fingerprint


def start_eval(conn: Connection, *, session_id: str | None, gate: float) -> EvalRun:
    """Record a running eval against the session's current golden set."""
    golden = golden_set(conn, session_id)
    return evals_repo.start_eval_run(
        conn,
        NewEvalRun(
            session_id=session_id,
            run_id=None,
            gate=Decimal(str(gate)),
            golden_hash=golden.hash,
            golden_count=len(golden.items),
        ),
    )


def complete_eval(
    conn: Connection, llm: LLMClient, started: EvalRun, ask_runner: AskRunner | None = None
) -> EvalRun:
    """Run the pipeline and score it against the golden set the eval started with, and
    Ask's golden questions against the new run unless `ask_runner` is None."""
    golden = golden_set(conn, started.session_id)
    try:
        if golden.hash != started.golden_hash:
            raise RuntimeError("the golden set changed while the eval was starting")
        result = run_pipeline(conn, llm, kind="eval", session_id=started.session_id)
        outcome = score_run(conn, result.run_id, golden, float(started.gate), ask_runner)
        return evals_repo.finish_eval_run(conn, started.id, outcome, result.run_id)
    except Exception as err:
        failed = EvalOutcome(
            state="error",
            score=None,
            metrics={},
            corrections_held=None,
            corrections_total=None,
            citation_validity=None,
            cost_gbp=None,
            error=f"{type(err).__name__}: {err}",
        )
        return evals_repo.finish_eval_run(conn, started.id, failed)


def run_eval(
    conn: Connection,
    llm: LLMClient,
    *,
    session_id: str | None,
    gate: float,
    ask_runner: AskRunner | None = None,
) -> EvalRun:
    started = start_eval(conn, session_id=session_id, gate=gate)
    return complete_eval(conn, llm, started, ask_runner)


def score_run(
    conn: Connection,
    run_id: str,
    golden: GoldenSet,
    gate: float,
    ask_runner: AskRunner | None = None,
) -> EvalOutcome:
    run = runs.get_run(conn, run_id)
    assert run is not None
    view = GraphView.load(conn, run_id, [d.id for d in load_manifest()], run.as_of)
    findings = {f.check_id: f for f in findings_repo.list_findings(conn, run_id)}

    ratios = {
        "extraction": _extraction(golden, view),
        "conflicts": _conflicts(golden, view),
        "checks": _checks(golden, findings),
        "corrections": (corrections := _corrections(golden, findings))[0],
        "citation_validity": _citations(view, findings),
    }
    learned = corrections[1]
    ask_report: dict[str, Any] = {}
    if ask_runner is not None:
        scores = score_ask(conn, run_id, ask_runner)
        ratios |= scores.ratios
        ratios["citation_validity"].passed += scores.citations.passed
        ratios["citation_validity"].total += scores.citations.total
        ratios["citation_validity"].failures += scores.citations.failures
        ask_report = scores.report
    values = [r.value for r in ratios.values() if r.value is not None]
    score = sum(values) / len(values) if values else 0.0
    citation = ratios["citation_validity"].value
    held = ratios["corrections"]
    every_item = all(r.passed == r.total for r in ratios.values())
    passing = every_item and score >= gate

    claims = claims_repo.list_claims(conn, run_id)
    calls = runs.list_llm_calls(conn, run_id)
    cost = sum((c.cost_gbp for c in calls), Decimal(0))
    metrics: dict[str, Any] = {
        name: {"passed": r.passed, "total": r.total, "failures": r.failures}
        for name, r in ratios.items()
    }
    metrics["learned"] = {"passed": learned.passed, "total": learned.total}
    metrics["verifier_rejection_rate"] = (
        sum(c.status == "rejected" for c in claims) / len(claims) if claims else 0.0
    )
    metrics["llm_calls"] = len(calls)
    metrics |= ask_report
    return EvalOutcome(
        state="passing" if passing else "failing",
        score=Decimal(str(round(score, 4))),
        metrics=metrics,
        corrections_held=held.passed,
        corrections_total=held.total,
        citation_validity=Decimal(str(round(citation, 4))) if citation is not None else None,
        cost_gbp=cost,
        error=None,
    )


# ---------- extraction: facts and edges ----------


def _nodes(view: GraphView, spec: Any) -> list[Node]:
    """Nodes a golden item names: "Lease", {"Party": "John Hartley"},
    {"LandParcel": ["9", "10"]}."""
    if isinstance(spec, str):
        return view.nodes_of(spec)
    ((node_type, wanted),) = spec.items()
    nodes = view.nodes_of(node_type)
    if node_type == "Party":
        return [n for n in nodes if n.key == name_key(str(wanted))]
    wanted = wanted if isinstance(wanted, list) else [wanted]
    return [n for n in nodes if n.key.rsplit("/", 1)[-1] in {str(w) for w in wanted}]


def _edge_cited(view: GraphView, item: dict[str, Any], sources: set[str], target: Node) -> bool:
    return any(
        e.type == item["type"]
        and e.source_id in sources
        and e.target_id == target.id
        and e.props.get("role") == item.get("role")
        and any(r.paragraph_id == item["paragraph_id"] for r in view.edge_rows(e))
        for e in view.edges
    )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, int | float) and isinstance(b, int | float):
        return abs(float(a) - float(b)) < 1e-9
    if isinstance(a, list) and isinstance(b, list):
        return sorted(map(str, a)) == sorted(map(str, b))
    return a == b


def _extraction(golden: GoldenSet, view: GraphView) -> Ratio:
    ratio = Ratio()
    for item in golden.of("fact"):
        spec = {item["node"]: item["key"]} if "key" in item else item["node"]
        ok = any(
            r.paragraph_id == item["paragraph_id"] and _same(r.value, item["value"])
            for node in _nodes(view, spec)
            for r in view.property_rows(node, item["property"])
        )
        ratio.add(ok, item["id"])
    for item in golden.of("edge"):
        sources = {n.id for n in _nodes(view, item["from"])}
        reached = [t for t in _nodes(view, item["to"]) if _edge_cited(view, item, sources, t)]
        # {"LandParcel": ["9", "10", "11"]} needs an edge to each; "Lease" needs one.
        if isinstance(item["to"], dict):
            ok = len(reached) >= len(_as_list(next(iter(item["to"].values()))))
        else:
            ok = bool(reached)
        ratio.add(ok, item["id"])
    return ratio


# ---------- conflicts, checks, corrections ----------


def _conflicts(golden: GoldenSet, view: GraphView) -> Ratio:
    ratio = Ratio()
    for item in golden.of("conflict"):
        node_type, prop = item["property"].split(".")
        groups = [g for n in view.nodes_of(node_type) if (g := view.group(n, prop))]
        ok = False
        for group in groups:
            got = {_label(v.value): sorted(v.documents) for v in group.values}
            want = {_label(k): sorted(v) for k, v in item["values"].items()}
            ok = ok or (group.conflict and got == want)
        ratio.add(ok, item["id"])
    return ratio


def _label(value: Any) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _checks(golden: GoldenSet, findings: dict[str, FindingRecord]) -> Ratio:
    ratio = Ratio()
    for item in golden.of("check"):
        finding = findings.get(item["check_id"])
        ratio.add(finding is not None and finding.result == item["expect"], item["id"])
    return ratio


def effective_result(item: dict[str, Any], finding: FindingRecord) -> str:
    """The lawyer's answer while the evidence they reviewed is unchanged; otherwise the
    pipeline's. Overrides never carry over to changed text."""
    if evidence_fingerprint(evidence_of(finding)) == item["evidence_fingerprint"]:
        return str(item["expect"])
    return finding.result


def _corrections(golden: GoldenSet, findings: dict[str, FindingRecord]) -> tuple[Ratio, Ratio]:
    held, learned = Ratio(), Ratio()
    for item in golden.of("correction"):
        finding = findings.get(item["check_id"])
        if finding is None:
            held.add(False, item["id"])
            learned.add(False, item["id"])
            continue
        held.add(effective_result(item, finding) == item["expect"], item["id"])
        learned.add(finding.result == item["expect"], item["id"])
    return held, learned


# ---------- citations ----------


def _citations(view: GraphView, findings: dict[str, FindingRecord]) -> Ratio:
    """An independent check that every quote served is the paragraph's own text at its
    offsets: evidence cards on findings, and every fact's provenance."""
    ratio = Ratio()
    for finding in findings.values():
        for e in evidence_of(finding):
            if e["kind"] != "quote":
                continue
            paragraph = view.paragraphs.get(e["citation"]["paragraph_id"])
            ok = (
                paragraph is not None
                and paragraph.text == e["paragraph_text"]
                and paragraph.text[e["quote_start"] : e["quote_end"]] == e["citation"]["quote"]
            )
            ratio.add(ok, f"{finding.id} {e['citation']['paragraph_id']}")
    for node in view.nodes:
        for row in view.node_rows(node) + view.identity_rows(node):
            paragraph = view.paragraphs.get(row.paragraph_id)
            ok = (
                paragraph is not None
                and paragraph.text[row.quote_start : row.quote_end] == row.quote
            )
            ratio.add(ok, f"{node.key} {row.paragraph_id}")
    return ratio


LLMFactory = Callable[[Connection], LLMClient]
