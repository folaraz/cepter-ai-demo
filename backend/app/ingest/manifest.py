from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.config import DATAROOM_DIR
from app.domain.documents import ManifestDocument


def _read(room: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((room / "manifest.yaml").read_text(encoding="utf-8"))
    return data


def load_manifest(room: Path = DATAROOM_DIR) -> list[ManifestDocument]:
    """The data room's documents, in manifest order."""
    return [ManifestDocument.model_validate(d) for d in _read(room)["documents"]]


def load_as_of(room: Path = DATAROOM_DIR) -> date:
    """The date checks treat as today, fixed so results never drift with the calendar."""
    return date.fromisoformat(str(_read(room)["run"]["as_of"]))
