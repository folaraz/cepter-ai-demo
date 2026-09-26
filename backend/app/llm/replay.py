"""Recorded model responses, one JSON file per call in backend/fixtures/llm/{key}.json.
They are committed, so tests, CI and the deployed demo run without an API key."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import RECORDINGS_DIR


class Recording(BaseModel):
    key: str
    purpose: str
    model: str
    prompt_version: str
    output: dict[str, Any]  # the tool input the model produced
    input_tokens: int
    output_tokens: int
    latency_ms: int
    metadata: dict[str, Any]  # whatever the caller passed, e.g. Ask's retrieved paragraph IDs


class RecordingStore:
    def __init__(self, directory: Path = RECORDINGS_DIR) -> None:
        self.directory = directory

    def path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def load(self, key: str) -> Recording | None:
        path = self.path(key)
        if not path.exists():
            return None
        return Recording.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, recording: Recording) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        # Stable formatting so re-recording an unchanged answer produces no diff.
        text = json.dumps(recording.model_dump(), indent=2, sort_keys=True, ensure_ascii=False)
        self.path(recording.key).write_text(text + "\n", encoding="utf-8")
