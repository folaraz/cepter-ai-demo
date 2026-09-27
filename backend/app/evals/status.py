"""The accuracy-check status shown on the Summary and after a review (SPEC C11).

The session's latest eval, or else the latest one run without a session (at deploy or in
CI). It is stale when the session's golden set is no longer the one that eval measured:
a review added or undone a correction since. Undoing back to the measured set makes it
current again.
"""

from datetime import UTC

from psycopg import Connection

from app.api.models import EvalState, EvalStatus
from app.config import get_settings
from app.db.repositories import evals as evals_repo
from app.domain.evals import EvalRun
from app.evals.golden import golden_set


def eval_status(conn: Connection, session_id: str | None) -> EvalStatus:
    golden = golden_set(conn, session_id)
    held_total = len(golden.of("correction"))
    running = evals_repo.running_eval(conn, session_id)
    latest = evals_repo.latest_eval(conn, session_id)
    finished = latest if latest is None or latest.state != "running" else None
    if finished is None and running is not None:
        finished = _previous(conn, session_id, running)

    if finished is None:  # nothing has been measured yet
        state: EvalState = "running" if running else "stale"
        return EvalStatus(
            state=state,
            score=0.0,
            gate=get_settings().eval_gate,
            golden_count=len(golden.items),
            corrections_held=0,
            corrections_total=held_total,
            citation_validity=0.0,
            cost_gbp=0.0,
            last_run_at=_iso(running) if running else "",
        )

    if running is not None:
        state = "running"
    elif finished.golden_hash != golden.hash:
        state = "stale"
    else:
        state = "passing" if finished.state == "passing" else "failing"
    return EvalStatus(
        state=state,
        score=float(finished.score or 0),
        gate=float(finished.gate),
        golden_count=len(golden.items),
        corrections_held=finished.corrections_held or 0,
        corrections_total=held_total if state == "stale" else finished.corrections_total or 0,
        citation_validity=float(finished.citation_validity or 0),
        cost_gbp=float(finished.cost_gbp or 0),
        last_run_at=_iso(finished),
    )


def _previous(conn: Connection, session_id: str | None, running: EvalRun) -> EvalRun | None:
    """While a run is going, show the numbers from the one before it."""
    rows = conn.execute(
        "SELECT id FROM eval_runs WHERE state <> 'running' AND id <> %s "
        "AND (session_id IS NOT DISTINCT FROM %s OR session_id IS NULL) "
        "ORDER BY (session_id IS NULL), started_at DESC LIMIT 1",
        (running.id, session_id),
    ).fetchone()
    return evals_repo.get_eval_run(conn, rows[0]) if rows else None


def _iso(run: EvalRun) -> str:
    at = run.finished_at or run.started_at
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
