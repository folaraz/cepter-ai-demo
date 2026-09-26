"""A finding as a reviewer sees it: its result and review state after visible reviews.

Visible reviews are the seed reviews plus the caller's session's, not reverted; the
latest for a finding wins. Without one, a finding starts in its initial state.
"""

from dataclasses import dataclass

from psycopg import Connection

from app.checks.runner import initial_review_state
from app.db.repositories import reviews as reviews_repo
from app.domain.findings import FindingRecord, Result
from app.domain.reviews import Review

REVIEW_STATE = {"accept": "lawyer_verified", "reject": "rejected", "correct": "corrected"}


@dataclass(frozen=True)
class Effective:
    result: Result
    review: str


def latest_reviews(conn: Connection, session_id: str | None) -> dict[str, Review]:
    """The latest visible review per finding ID."""
    latest: dict[str, Review] = {}
    for review in reviews_repo.list_visible_reviews(conn, session_id):  # oldest first
        latest[review.finding_id] = review
    return latest


def effective(finding: FindingRecord, review: Review | None) -> Effective:
    """A correction changes the result; a rejection leaves it (the lawyer says the check
    should not have flagged, which the golden set records, C9)."""
    if review is None:
        return Effective(finding.result, initial_review_state(finding.severity, finding.result))
    result = (
        review.corrected_result
        if review.action == "correct" and review.corrected_result
        else finding.result
    )
    return Effective(result, REVIEW_STATE[review.action])
