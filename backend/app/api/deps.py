"""Shared request plumbing for the read endpoints."""

from collections.abc import Iterator

from fastapi import HTTPException, Request, status
from psycopg import Connection

from app.published import NoPublishedRun, Published, load_published

SESSION_COOKIE = "lens_session"


def connection(request: Request) -> Iterator[Connection]:
    with request.app.state.pool.connection() as conn:
        yield conn


def session_id(request: Request) -> str | None:
    # The cookie is set by the session middleware (C9); until then reads use seed reviews.
    return request.cookies.get(SESSION_COOKIE)


def published(conn: Connection, request: Request) -> Published:
    try:
        return load_published(conn, session_id(request))
    except NoPublishedRun:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No published run yet") from None
