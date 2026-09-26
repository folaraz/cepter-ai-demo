"""Apply backend/schema.sql. Every statement in it is idempotent, so this is safe to rerun."""

from pathlib import Path

import psycopg

from app.config import SCHEMA_SQL


def migrate(database_url: str, schema: Path = SCHEMA_SQL) -> None:
    sql = schema.read_text(encoding="utf-8")
    # One transaction: a failure (e.g. no pgvector on the server) leaves nothing half-applied.
    # With no parameters psycopg sends the script as one simple query, statements and all.
    with psycopg.connect(database_url) as conn:
        conn.execute(sql.encode())
