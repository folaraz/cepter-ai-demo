"""Check outcomes as stored in `findings`: one row per check per run, passes included."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

Severity = Literal["critical", "high", "medium", "low"]
Result = Literal["fail", "conflict", "missing_evidence", "pass"]


class FindingRecord(BaseModel):
    """Named apart from the API's Finding, which adds the caller's review state."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    id: str  # "F-03": from the check's order, so stable across runs
    check_id: str
    severity: Severity
    result: Result
    title: str
    why: str
    how: str
    context: dict[str, JsonValue]  # the template context
    evidence: list[dict[str, JsonValue]]  # Evidence[] exactly as the API serves it
    rfi_id: str | None
