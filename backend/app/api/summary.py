from typing import Annotated

from fastapi import APIRouter, Depends, Request
from psycopg import Connection

from app.api.deps import connection, published
from app.api.models import Summary
from app.evals.status import current_eval_status
from app.summary.build import build_summary

router = APIRouter()


@router.get("/summary", response_model=Summary, response_model_by_alias=True)
def get_summary(request: Request, conn: Annotated[Connection, Depends(connection)]) -> Summary:
    p = published(conn, request)
    return build_summary(p, current_eval_status(p.run_at))
