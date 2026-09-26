"""Database connections. Plain psycopg 3; the pgvector adapter is registered on every one,
so `vector` columns read and write as vectors. Both need the extension `lens migrate`
creates."""

from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg_pool import ConnectionPool


def _configure(conn: Connection) -> None:
    register_vector(conn)


def connect(database_url: str) -> Connection:
    """A single autocommit connection, for the CLI and tests."""
    conn = Connection.connect(database_url, autocommit=True)
    _configure(conn)
    return conn


def create_pool(database_url: str) -> ConnectionPool:
    """A closed pool for the app; the caller opens it. Opening doesn't wait for the
    database, so the app starts (and /api/health reports it) even when Postgres is down."""
    return ConnectionPool(
        database_url,
        min_size=1,
        max_size=10,
        configure=_configure,
        open=False,
        kwargs={"autocommit": True},
    )
