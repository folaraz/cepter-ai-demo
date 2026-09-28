"""`asks`."""

from decimal import Decimal

from psycopg import Connection
from psycopg.rows import class_row

from app.db.repositories import params
from app.domain.asks import AskRecord, NewAsk


def insert_ask(conn: Connection, ask: NewAsk) -> AskRecord:
    with conn.cursor(row_factory=class_row(AskRecord)) as cur:
        cur.execute(
            """
            INSERT INTO asks (id, session_id, run_id, question, question_norm, route, status,
                              mode, retrieved, response, dropped, cost_gbp, latency_ms)
            VALUES (%(id)s, %(session_id)s, %(run_id)s, %(question)s, %(question_norm)s,
                    %(route)s, %(status)s, %(mode)s, %(retrieved)s, %(response)s,
                    %(dropped)s, %(cost_gbp)s, %(latency_ms)s)
            RETURNING *
            """,
            params(ask, "retrieved", "response"),
        )
        row = cur.fetchone()
    assert row is not None
    return row


def get_ask(conn: Connection, ask_id: str) -> AskRecord | None:
    with conn.cursor(row_factory=class_row(AskRecord)) as cur:
        cur.execute("SELECT * FROM asks WHERE id = %s", (ask_id,))
        return cur.fetchone()


def cached_answer(
    conn: Connection, run_id: str, question_norm: str, hours: int
) -> AskRecord | None:
    """The latest answer (not an unavailable) to the same question on the same run."""
    with conn.cursor(row_factory=class_row(AskRecord)) as cur:
        cur.execute(
            "SELECT * FROM asks WHERE run_id = %s AND question_norm = %s "
            "AND status IN ('answered', 'abstained') "
            "AND created_at > now() - make_interval(hours => %s) "
            "ORDER BY created_at DESC LIMIT 1",
            (run_id, question_norm, hours),
        )
        return cur.fetchone()


def live_questions_today(conn: Connection, session_id: str | None) -> int:
    row = conn.execute(
        "SELECT count(*) FROM asks WHERE mode = 'live' "
        "AND session_id IS NOT DISTINCT FROM %s AND created_at >= date_trunc('day', now())",
        (session_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def live_ask_spend_today(conn: Connection) -> Decimal:
    """What live Ask model calls cost today, across every session (replays cost nothing)."""
    row = conn.execute(
        "SELECT coalesce(sum(cost_gbp), 0) FROM llm_calls WHERE purpose LIKE 'ask:%%' "
        "AND NOT replayed AND created_at >= date_trunc('day', now())"
    ).fetchone()
    return Decimal(row[0]) if row else Decimal(0)
