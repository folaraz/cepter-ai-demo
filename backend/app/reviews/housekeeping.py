"""Visitors' state is kept for a week: reviews, questions and eval runs tied to a
session are deleted after that. Seed reviews and CI or deploy evals have no session and
stay."""

from psycopg import Connection

_PURGE = {
    "reviews": "DELETE FROM reviews WHERE session_id IS NOT NULL "
    "AND created_at < now() - interval '7 days'",
    "asks": "DELETE FROM asks WHERE session_id IS NOT NULL "
    "AND created_at < now() - interval '7 days'",
    "eval_runs": "DELETE FROM eval_runs WHERE session_id IS NOT NULL "
    "AND started_at < now() - interval '7 days'",
}


def purge_expired_sessions(conn: Connection) -> dict[str, int]:
    """Rows deleted per table."""
    return {table: conn.execute(query).rowcount for table, query in _PURGE.items()}
