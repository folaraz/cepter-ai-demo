import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import findings, health, reviews, rfi, summary
from app.api.session import session_middleware
from app.config import get_settings
from app.db.pool import create_pool
from app.reviews.housekeeping import purge_expired_sessions

log = logging.getLogger("lens")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = create_pool(get_settings().database_url)
    pool.open(wait=False)
    app.state.pool = pool
    try:
        with pool.connection(timeout=5) as conn:
            log.info("expired session state removed: %s", purge_expired_sessions(conn))
    except Exception:  # the database may not be up yet; /api/health will say so
        log.warning("housekeeping skipped: database unavailable")
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title="DataRoom Lens", lifespan=lifespan)
app.middleware("http")(session_middleware)
for router in (health.router, summary.router, findings.router, reviews.router, rfi.router):
    app.include_router(router, prefix="/api")
