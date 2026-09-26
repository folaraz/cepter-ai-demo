from pathlib import Path

import yaml

from app.config import DATAROOM_DIR
from app.domain.documents import ManifestDocument


def load_manifest(room: Path = DATAROOM_DIR) -> list[ManifestDocument]:
    """The data room's documents, in manifest order."""
    manifest = yaml.safe_load((room / "manifest.yaml").read_text(encoding="utf-8"))
    return [ManifestDocument.model_validate(d) for d in manifest["documents"]]
