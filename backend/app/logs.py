"""JSON-lines logging with the request ID and pipeline run ID on every line (SPEC C12).

{"ts": "...", "level": "info", "logger": "lens.http", "msg": "request",
 "request_id": "3f2a...", "run_id": null, "method": "GET", "path": "/api/summary", ...}
"""

import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, Response

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
run_id: ContextVar[str | None] = ContextVar("run_id", default=None)

# Attributes every LogRecord has; anything else was passed with extra={...}.
_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "color_message"}
REQUEST_HEADER = "X-Request-ID"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id.get(),
            "run_id": run_id.get(),
        }
        line |= {k: v for k, v in vars(record).items() if k not in _STANDARD}
        if record.exc_info:
            line["error"] = self.formatException(record.exc_info)
        return json.dumps(line, default=str, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Route everything, uvicorn included, through one JSON handler on stdout. Called at
    import and again once uvicorn has installed its own handlers."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    # Requests are logged by request_logging below, with their request ID.
    logging.getLogger("uvicorn.access").disabled = True


@contextmanager
def run_context(value: str) -> Iterator[None]:
    """Tag every log line inside with this pipeline run's ID."""
    token = run_id.set(value)
    try:
        yield
    finally:
        run_id.reset(token)


_http = logging.getLogger("lens.http")


async def request_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """One line per request, and the request ID echoed back for support."""
    rid = request.headers.get(REQUEST_HEADER) or uuid.uuid4().hex
    token = request_id.set(rid)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        _http.exception(
            "request failed", extra={"method": request.method, "path": request.url.path}
        )
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
    _http.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers[REQUEST_HEADER] = rid
    request_id.reset(token)
    return response
