"""`reviews`."""

from psycopg import Connection
from psycopg.rows import class_row

from app.db.repositories import params
from app.domain.reviews import NewReview, Review


def insert_review(conn: Connection, review: NewReview) -> Review:
    with conn.cursor(row_factory=class_row(Review)) as cur:
        cur.execute(
            """
            INSERT INTO reviews (session_id, finding_id, check_id, action, corrected_result,
                                 reason, evidence_fingerprint, golden_item_id, reviewer,
                                 undo_token)
            VALUES (%(session_id)s, %(finding_id)s, %(check_id)s, %(action)s,
                    %(corrected_result)s, %(reason)s, %(evidence_fingerprint)s,
                    %(golden_item_id)s, %(reviewer)s, %(undo_token)s)
            RETURNING *
            """,
            params(review),
        )
        row = cur.fetchone()
    assert row is not None
    return row


def list_visible_reviews(conn: Connection, session_id: str | None) -> list[Review]:
    """Seed reviews plus this session's, not reverted, oldest first."""
    with conn.cursor(row_factory=class_row(Review)) as cur:
        cur.execute(
            "SELECT * FROM reviews WHERE reverted_at IS NULL "
            "AND (session_id IS NULL OR session_id = %s) ORDER BY created_at, id",
            (session_id,),
        )
        return cur.fetchall()


def revert_review(conn: Connection, undo_token: str, session_id: str | None) -> Review | None:
    """Undo a session's own review. None if the token is unknown, not the session's, or
    already reverted."""
    with conn.cursor(row_factory=class_row(Review)) as cur:
        cur.execute(
            "UPDATE reviews SET reverted_at = now() "
            "WHERE undo_token = %s AND session_id IS NOT DISTINCT FROM %s "
            "AND reverted_at IS NULL RETURNING *",
            (undo_token, session_id),
        )
        return cur.fetchone()
