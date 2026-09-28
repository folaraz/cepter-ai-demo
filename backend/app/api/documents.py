from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from psycopg import Connection

from app.api.deps import connection, published
from app.api.models import DocumentDetail, DocumentListItem
from app.documents.build import document_detail, list_documents

router = APIRouter()


@router.get("/documents", response_model=list[DocumentListItem])
def get_documents(
    request: Request, conn: Annotated[Connection, Depends(connection)]
) -> list[DocumentListItem]:
    return list_documents(published(conn, request))


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str, request: Request, conn: Annotated[Connection, Depends(connection)]
) -> DocumentDetail:
    detail = document_detail(published(conn, request), document_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such document")
    return detail
