from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from psycopg import Connection

from app.api.deps import connection, published
from app.api.models import Finding
from app.published import evidence_of
from app.summary.build import finding_row

router = APIRouter()


@router.get("/findings/{finding_id}", response_model=Finding)
def get_finding(
    finding_id: str, request: Request, conn: Annotated[Connection, Depends(connection)]
) -> Finding:
    p = published(conn, request)
    record = p.finding(finding_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such finding")
    row = finding_row(record, p)
    return Finding.model_validate(
        {**row.model_dump(), "why": record.why, "how": record.how, "evidence": evidence_of(record)}
    )
