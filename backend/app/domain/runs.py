"""Pipeline runs (`runs`) and the model calls made during them (`llm_calls`)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

RunKind = Literal["published", "eval"]
RunStatus = Literal["running", "succeeded", "failed", "superseded"]


class Run(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: RunKind
    session_id: str | None  # set for eval runs started from the UI
    as_of: date  # the date the checks treat as "today"
    status: RunStatus
    prompt_versions: dict[str, str]  # {"extract": "extract.v1", ...}
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class NewLLMCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    purpose: str  # "extract:lease", "ask:route", "ask:answer"
    model: str
    prompt_version: str
    request_hash: str  # the recording key
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_gbp: Decimal  # what the call costs live, even when replayed
    replayed: bool


class LLMCall(NewLLMCall):
    id: int
    created_at: datetime
