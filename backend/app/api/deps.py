"""Shared request plumbing for the endpoints."""

from collections.abc import Iterator

from fastapi import HTTPException, Request, status
from psycopg import Connection
from psycopg_pool import PoolTimeout

from app.api.session import session_id
from app.published import NoPublishedRun, Published, load_published

DB_WAIT_SECONDS = 5


def connection(request: Request) -> Iterator[Connection]:
    """A pooled connection, or a 503 within a few seconds when the database is down
    (rather than a 500 after the pool's 30-second default)."""
    pool = request.app.state.pool
    try:
        conn = pool.getconn(timeout=DB_WAIT_SECONDS)
    except PoolTimeout:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "The database is unavailable"
        ) from None
    try:
        yield conn
    finally:
        pool.putconn(conn)


def published(conn: Connection, request: Request) -> Published:
    try:
        return load_published(conn, session_id(request))
    except NoPublishedRun:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No published run yet") from None
