"""Accuracy-check runs (`eval_runs`)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

EvalState = Literal["running", "passing", "failing", "error"]


class NewEvalRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str | None  # None for CI and deploy runs
    run_id: str | None  # the pipeline run it evaluated
    gate: Decimal
    golden_hash: str  # of the golden items evaluated; a different current hash means stale
    golden_count: int


class EvalOutcome(BaseModel):
    """What a finished eval writes back."""

    model_config = ConfigDict(frozen=True)

    state: EvalState
    score: Decimal | None
    metrics: dict[str, JsonValue]
    corrections_held: int | None
    corrections_total: int | None
    citation_validity: Decimal | None
    cost_gbp: Decimal | None
    error: str | None


class EvalRun(NewEvalRun):
    id: int
    state: EvalState
    score: Decimal | None
    metrics: dict[str, JsonValue]
    corrections_held: int | None
    corrections_total: int | None
    citation_validity: Decimal | None
    cost_gbp: Decimal | None
    error: str | None
    started_at: datetime
    finished_at: datetime | None
