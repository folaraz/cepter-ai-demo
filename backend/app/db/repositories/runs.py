"""`runs` and `llm_calls`."""

from datetime import date

from psycopg import Connection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from app.db.repositories import params
from app.domain.runs import LLMCall, NewLLMCall, Run, RunKind, RunStatus


def create_run(
    conn: Connection,
    run_id: str,
    kind: RunKind,
    as_of: date,
    *,
    session_id: str | None = None,
    prompt_versions: dict[str, str] | None = None,
) -> Run:
    with conn.cursor(row_factory=class_row(Run)) as cur:
        cur.execute(
            "INSERT INTO runs (id, kind, session_id, as_of, status, prompt_versions) "
            "VALUES (%s, %s, %s, %s, 'running', %s) RETURNING *",
            (run_id, kind, session_id, as_of, Jsonb(prompt_versions or {})),
        )
        run = cur.fetchone()
    assert run is not None
    return run


def get_run(conn: Connection, run_id: str) -> Run | None:
    with conn.cursor(row_factory=class_row(Run)) as cur:
        cur.execute("SELECT * FROM runs WHERE id = %s", (run_id,))
        return cur.fetchone()


def finish_run(conn: Connection, run_id: str, status: RunStatus, error: str | None = None) -> None:
    conn.execute(
        "UPDATE runs SET status = %s, error = %s, finished_at = now() WHERE id = %s",
        (status, error, run_id),
    )


def get_published_run(conn: Connection) -> Run | None:
    """The one live published run, if any."""
    with conn.cursor(row_factory=class_row(Run)) as cur:
        cur.execute("SELECT * FROM runs WHERE kind = 'published' AND status = 'succeeded'")
        return cur.fetchone()


def publish_run(conn: Connection, run_id: str) -> None:
    """Make a finished published run the live one, superseding the previous one."""
    with conn.transaction():
        conn.execute(
            "UPDATE runs SET status = 'superseded' "
            "WHERE kind = 'published' AND status = 'succeeded' AND id <> %s",
            (run_id,),
        )
        conn.execute(
            "UPDATE runs SET status = 'succeeded', finished_at = coalesce(finished_at, now()) "
            "WHERE id = %s AND kind = 'published'",
            (run_id,),
        )


def insert_llm_call(conn: Connection, call: NewLLMCall) -> LLMCall:
    with conn.cursor(row_factory=class_row(LLMCall)) as cur:
        cur.execute(
            """
            INSERT INTO llm_calls (run_id, purpose, model, prompt_version, request_hash,
                                   input_tokens, output_tokens, latency_ms, cost_gbp, replayed)
            VALUES (%(run_id)s, %(purpose)s, %(model)s, %(prompt_version)s, %(request_hash)s,
                    %(input_tokens)s, %(output_tokens)s, %(latency_ms)s, %(cost_gbp)s,
                    %(replayed)s)
            RETURNING *
            """,
            params(call),
        )
        row = cur.fetchone()
    assert row is not None
    return row


def list_llm_calls(conn: Connection, run_id: str) -> list[LLMCall]:
    with conn.cursor(row_factory=class_row(LLMCall)) as cur:
        cur.execute("SELECT * FROM llm_calls WHERE run_id = %s ORDER BY id", (run_id,))
        return cur.fetchall()
