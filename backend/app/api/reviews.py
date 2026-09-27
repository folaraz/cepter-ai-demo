from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from psycopg import Connection

from app.api.deps import connection, published
from app.api.models import FindingRow, ReviewRequest, ReviewResponse, UndoRequest
from app.api.session import session_id
from app.evals.status import current_eval_status
from app.published import load_published
from app.reviews.service import ReviewError, UnknownFinding, submit_review, undo_review
from app.summary.build import finding_row

router = APIRouter()


@router.post("/findings/{finding_id}/review", response_model=ReviewResponse)
def post_review(
    finding_id: str,
    body: ReviewRequest,
    request: Request,
    conn: Annotated[Connection, Depends(connection)],
) -> ReviewResponse:
    session = session_id(request)
    p = published(conn, request)
    try:
        review = submit_review(
            conn, p, session, finding_id, body.action, body.reason, body.corrected_result
        )
    except UnknownFinding:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such finding") from None
    except ReviewError as err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(err)) from None

    after = load_published(conn, session)  # the finding as this session now sees it
    record = after.finding(review.finding_id)
    assert record is not None
    return ReviewResponse(
        finding=finding_row(record, after),
        golden_item_id=review.golden_item_id,
        eval=current_eval_status(after.run_at),
        undo_token=review.undo_token,
    )


@router.post("/reviews/undo", response_model=FindingRow)
def post_undo(
    body: UndoRequest, request: Request, conn: Annotated[Connection, Depends(connection)]
) -> FindingRow:
    session = session_id(request)
    try:
        review = undo_review(conn, session, body.undo_token)
    except UnknownFinding:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nothing to undo") from None
    after = published(conn, request)
    record = after.finding(review.finding_id)
    assert record is not None
    return finding_row(record, after)
