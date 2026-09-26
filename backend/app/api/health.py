from functools import cache

import yaml
from fastapi import APIRouter, Request, Response, status
from psycopg_pool import ConnectionPool

from app.api.models import Health
from app.config import ASK_YAML, RECORDINGS_DIR, get_settings
from app.db.repositories import runs

router = APIRouter()


@cache
def _embedding_model() -> str:
    ask = yaml.safe_load(ASK_YAML.read_text(encoding="utf-8"))
    return str(ask["retrieval"]["embedding_model"])


def _published_run(pool: ConnectionPool) -> str | None:
    with pool.connection(timeout=2) as conn:
        run = runs.get_published_run(conn)
    return run.id if run else None


@router.get("/health", response_model=Health)
def health(request: Request, response: Response) -> Health:
    ok = True
    try:
        published_run = _published_run(request.app.state.pool)
    except Exception:
        ok, published_run = False, None
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return Health(
        status="ok" if ok else "degraded",
        published_run=published_run,
        recordings=sum(1 for _ in RECORDINGS_DIR.glob("*.json")),
        embedding_model=_embedding_model(),
        ask_live=get_settings().ask_live,
    )
