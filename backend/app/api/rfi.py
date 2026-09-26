from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from psycopg import Connection

from app.api.deps import connection, published
from app.api.models import Rfi
from app.ingest.manifest import load_asset
from app.rfi.build import build_rfis
from app.rfi.markdown import rfis_to_markdown

router = APIRouter()


@router.get("/rfi", response_model=list[Rfi])
def get_rfis(request: Request, conn: Annotated[Connection, Depends(connection)]) -> list[Rfi]:
    return build_rfis(published(conn, request))


@router.get("/rfi.md", response_class=PlainTextResponse)
def get_rfi_markdown(
    request: Request, conn: Annotated[Connection, Depends(connection)]
) -> PlainTextResponse:
    text = rfis_to_markdown(build_rfis(published(conn, request)), load_asset()["name"])
    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="requests-for-information.md"'},
    )
