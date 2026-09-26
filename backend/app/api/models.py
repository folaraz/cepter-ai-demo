"""API response models. Everything in design/api/types.ts is mirrored here (C10)."""

from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    """Operational status; not part of the UI contract."""

    status: Literal["ok", "degraded"]  # degraded: the database is unreachable
    published_run: str | None  # id of the live published run, if any
    recordings: int  # committed model recordings in backend/fixtures/llm/
    embedding_model: str
    ask_live: bool
