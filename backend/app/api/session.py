"""Visitor sessions. The demo is public but each visitor's reviews and questions are
private: a `lens_session` cookie (a random ID, 7 days) scopes them."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.config import get_settings

SESSION_COOKIE = "lens_session"
SESSION_DAYS = 7


async def session_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Give a first-time visitor a session ID, usable within the same request."""
    existing = request.cookies.get(SESSION_COOKIE)
    request.state.session_id = existing or str(uuid.uuid4())
    response = await call_next(request)
    if existing is None:
        response.set_cookie(
            SESSION_COOKIE,
            request.state.session_id,
            max_age=SESSION_DAYS * 24 * 60 * 60,
            httponly=True,
            samesite="lax",
            secure=get_settings().cookie_secure,
        )
    return response


def session_id(request: Request) -> str:
    return str(request.state.session_id)
