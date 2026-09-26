"""`asks`."""

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
