"""Serve the built UI (frontend/dist) at /, so one service hosts the app and its API.

A path that names a file in dist is served as that file; any other non-API path gets
index.html and the UI routes it. /api/* never falls back: an unknown API path is a 404.
Hashed assets are cached for a year; index.html is always revalidated so a deploy shows
up on the next load.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter()

NO_CACHE = {"Cache-Control": "no-cache"}
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}


def _file_in(dist: Path, path: str) -> Path | None:
    """The file `path` names inside dist, or None (never anything outside dist)."""
    if not path:
        return None
    candidate = (dist / path).resolve()
    if dist.resolve() not in candidate.parents or not candidate.is_file():
        return None
    return candidate


@router.get("/{path:path}", include_in_schema=False)
def spa(path: str) -> FileResponse:
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    dist = get_settings().frontend_dist
    index = dist / "index.html"
    if not index.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The UI has not been built")
    file = _file_in(dist, path)
    if file is not None:
        headers = IMMUTABLE if path.startswith("assets/") else NO_CACHE
        return FileResponse(file, headers=headers)
    return FileResponse(index, headers=NO_CACHE)
