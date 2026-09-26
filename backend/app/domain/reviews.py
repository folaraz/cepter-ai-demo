"""Reviewer decisions on findings (`reviews`)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.findings import Result

ReviewAction = Literal["accept", "reject", "correct"]


class NewReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str | None  # None: a seed review everyone sees
    finding_id: str
    check_id: str
    action: ReviewAction
    corrected_result: Result | None  # set exactly when the action is correct
    reason: str | None  # required for reject and correct
    evidence_fingerprint: str  # sha256 of the finding's cited paragraphs at review time
    golden_item_id: str | None  # "corr-002", for reject and correct
    reviewer: str = "Demo reviewer"
    undo_token: str


class Review(NewReview):
    id: int
    reverted_at: datetime | None
    created_at: datetime
