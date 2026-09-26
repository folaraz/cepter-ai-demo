"""`eval_runs`."""

from psycopg import Connection
from psycopg.rows import class_row

from app.db.repositories import params
from app.domain.evals import EvalOutcome, EvalRun, NewEvalRun


def start_eval_run(conn: Connection, run: NewEvalRun) -> EvalRun:
    with conn.cursor(row_factory=class_row(EvalRun)) as cur:
        cur.execute(
            "INSERT INTO eval_runs (session_id, run_id, state, gate, golden_hash, golden_count) "
            "VALUES (%(session_id)s, %(run_id)s, 'running', %(gate)s, %(golden_hash)s, "
            "%(golden_count)s) RETURNING *",
            params(run),
        )
        row = cur.fetchone()
    assert row is not None
    return row


def finish_eval_run(conn: Connection, eval_id: int, outcome: EvalOutcome) -> EvalRun:
    with conn.cursor(row_factory=class_row(EvalRun)) as cur:
        cur.execute(
            """
            UPDATE eval_runs SET state = %(state)s, score = %(score)s, metrics = %(metrics)s,
                corrections_held = %(corrections_held)s,
                corrections_total = %(corrections_total)s,
                citation_validity = %(citation_validity)s, cost_gbp = %(cost_gbp)s,
                error = %(error)s, finished_at = now()
            WHERE id = %(id)s
            RETURNING *
            """,
            {**params(outcome, "metrics"), "id": eval_id},
        )
        row = cur.fetchone()
    assert row is not None
    return row


def get_eval_run(conn: Connection, eval_id: int) -> EvalRun | None:
    with conn.cursor(row_factory=class_row(EvalRun)) as cur:
        cur.execute("SELECT * FROM eval_runs WHERE id = %s", (eval_id,))
        return cur.fetchone()
