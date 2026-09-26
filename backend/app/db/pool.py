"""Connection pool. Plain psycopg 3; the pgvector adapter is registered on every connection."""

from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg_pool import ConnectionPool


def _configure(conn: Connection) -> None:
    # Needs the vector extension, which `lens migrate` creates.
    register_vector(conn)


def create_pool(database_url: str) -> ConnectionPool:
    """A closed pool; the caller opens it. Opening doesn't wait for the database, so the
    app starts (and /api/health reports it) even when Postgres is down."""
    return ConnectionPool(
        database_url,
        min_size=1,
        max_size=10,
        configure=_configure,
        open=False,
        kwargs={"autocommit": True},
    )
