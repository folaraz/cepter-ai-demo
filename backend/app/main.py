from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import findings, health, rfi, summary
from app.config import get_settings
from app.db.pool import create_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = create_pool(get_settings().database_url)
    pool.open(wait=False)
    app.state.pool = pool
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title="DataRoom Lens", lifespan=lifespan)
for router in (health.router, summary.router, findings.router, rfi.router):
    app.include_router(router, prefix="/api")
