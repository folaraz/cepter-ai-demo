"""Shared request plumbing for the endpoints."""

from collections.abc import Iterator

from fastapi import HTTPException, Request, status
from psycopg import Connection

from app.api.session import session_id
from app.published import NoPublishedRun, Published, load_published


def connection(request: Request) -> Iterator[Connection]:
    with request.app.state.pool.connection() as conn:
        yield conn


def published(conn: Connection, request: Request) -> Published:
    try:
        return load_published(conn, session_id(request))
    except NoPublishedRun:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No published run yet") from None
