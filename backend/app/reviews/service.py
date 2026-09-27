"""Recording and undoing a reviewer's decision on a finding (C9)."""

import uuid

from psycopg import Connection

from app.db.repositories import reviews as reviews_repo
from app.domain.reviews import NewReview, Review
from app.published import Published, evidence_of
from app.reviews.fingerprint import evidence_fingerprint
from app.reviews.golden import next_correction_id


class ReviewError(ValueError):
    """The request can't be recorded as asked; the message says why, in plain words."""


class UnknownFinding(LookupError):
    pass


def submit_review(
    conn: Connection,
    published: Published,
    session_id: str,
    finding_id: str,
    action: str,
    reason: str | None,
    corrected_result: str | None,
) -> Review:
    finding = published.finding(finding_id)
    if finding is None:
        raise UnknownFinding(finding_id)
    reason = " ".join(reason.split()) if reason else None
    if action in ("reject", "correct") and not reason:
        raise ReviewError("A reason is required")
    if action == "correct" and corrected_result is None:
        raise ReviewError("Choose the corrected result")
    if action != "correct" and corrected_result is not None:
        raise ReviewError("Only a correction takes a corrected result")

    golden_id = None
    if action in ("reject", "correct"):
        golden_id = next_correction_id(reviews_repo.list_visible_reviews(conn, session_id))
    return reviews_repo.insert_review(
        conn,
        NewReview(
            session_id=session_id,
            finding_id=finding.id,
            check_id=finding.check_id,
            action=action,  # type: ignore[arg-type]
            corrected_result=corrected_result,  # type: ignore[arg-type]
            reason=reason,
            evidence_fingerprint=evidence_fingerprint(evidence_of(finding)),
            golden_item_id=golden_id,
            undo_token=uuid.uuid4().hex,
        ),
    )


def undo_review(conn: Connection, session_id: str, undo_token: str) -> Review:
    """Revert the session's own review. Its golden item goes with it: the golden set is
    derived from the reviews that are still visible."""
    review = reviews_repo.revert_review(conn, undo_token, session_id)
    if review is None:
        raise UnknownFinding(undo_token)
    return review
