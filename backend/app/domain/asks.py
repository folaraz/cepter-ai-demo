"""Stored Ask questions (`asks`). The table is also the answer cache and the rate-limit log."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

AskRoute = Literal["lookup", "relationship", "out_of_scope"]
AskStatus = Literal["answered", "abstained", "unavailable"]
AskMode = Literal["replay", "live", "cache"]


class NewAsk(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    session_id: str | None
    run_id: str | None  # the published run the question was answered against
    question: str
    question_norm: str  # casefolded, punctuation stripped, spaces collapsed
    route: AskRoute | None
    status: AskStatus
    mode: AskMode
    retrieved: list[dict[str, JsonValue]]  # [{paragraph_id, vector_rank, keyword_rank, ...}]
    response: dict[str, JsonValue]  # the AskResponse as served
    dropped: int  # answer sentences removed by verification
    cost_gbp: Decimal
    latency_ms: int


class AskRecord(NewAsk):
    """Named apart from the API's AskResponse."""

    created_at: datetime
