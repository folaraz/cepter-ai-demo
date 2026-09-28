import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from app import web
from app.api import ask, documents, evals, findings, health, reviews, rfi, summary
from app.api.session import session_middleware
from app.config import get_settings
from app.db.pool import create_pool
from app.logs import configure_logging, request_logging
from app.reviews.housekeeping import purge_expired_sessions

configure_logging()
log = logging.getLogger("lens")


def _housekeeping(pool: ConnectionPool) -> None:
    """Off the startup path, so the app serves at once even if Postgres is slow."""
    try:
        with pool.connection(timeout=30) as conn:
            log.info("expired session state removed: %s", purge_expired_sessions(conn))
    except Exception:  # the database may not be up; /api/health will say so
        log.warning("housekeeping skipped: database unavailable")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()  # again: uvicorn installs its own handlers after importing us
    pool = create_pool(get_settings().database_url)
    pool.open(wait=False)
    app.state.pool = pool
    threading.Thread(target=_housekeeping, args=(pool,), daemon=True).start()
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title="DataRoom Lens", lifespan=lifespan)
app.middleware("http")(session_middleware)
app.middleware("http")(request_logging)  # added last, so it wraps everything
for router in (
    health.router,
    summary.router,
    findings.router,
    documents.router,
    reviews.router,
    rfi.router,
    evals.router,
    ask.router,
):
    app.include_router(router, prefix="/api")
app.include_router(web.router)  # last: its catch-all must not shadow the API
