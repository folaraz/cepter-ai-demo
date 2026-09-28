"""The `lens eval` table."""

from typing import Any

from app.domain.evals import EvalRun

LABELS = {
    "extraction": "Extraction (facts and edges)",
    "conflicts": "Conflicts",
    "checks": "Checks",
    "corrections": "Corrections held",
    "citation_validity": "Citation validity",
    "retrieval_recall": "Retrieval recall@top_k",
    "answer_accuracy": "Answer accuracy",
    "abstention": "Abstention",
}
LABEL, VALUE = 32, 18


def _row(label: str, value: str) -> str:
    return f"{label:<{LABEL}}{value:>{VALUE}}"


def format_report(run: EvalRun) -> str:
    m: dict[str, Any] = run.metrics  # type: ignore[assignment]
    if run.state == "error":
        return f"eval {run.id}: error\n  {run.error}"
    rule = "-" * (LABEL + VALUE)
    lines = [_row("Metric", "Result"), rule]
    for key, label in LABELS.items():
        if key not in m:
            continue  # Ask metrics are absent with --no-ask
        r = m[key]
        total = r.get("total", 0)
        cell = f"{r['passed']}/{total}" if total else "no items"
        if key == "citation_validity" and total:
            cell = f"{100 * r['passed'] / total:.0f}%"
        if key == "corrections" and total:
            cell += f" ({m['learned']['passed']} learned)"
        lines.append(_row(label, cell))
        lines += [f"    not met: {f}" for f in r.get("failures", [])[:10]]
    if "routing" in m:
        lines += [
            rule,
            _row("Routing (reported)", f"{m['routing']['passed']}/{m['routing']['total']}"),
            _row("Keyword-only recall", _pair(m["keyword_only_recall"])),
            _row("Vector-only recall", _pair(m["vector_only_recall"])),
            _row("Sentences dropped", str(m["dropped_sentences"])),
        ]
    lines += [
        rule,
        _row("Verifier rejection rate", f"{100 * m.get('verifier_rejection_rate', 0):.1f}%"),
        _row("Model calls", str(m.get("llm_calls", 0))),
        _row("Cost if run live", f"£{float(run.cost_gbp or 0):.4f}"),
        rule,
        _row("Score", f"{float(run.score or 0):.3f}"),
        _row("Gate", f"{float(run.gate):.2f}"),
        _row("State", run.state.upper()),
    ]
    return "\n".join(lines)


def _pair(r: dict[str, Any]) -> str:
    return f"{r['passed']}/{r['total']}"
