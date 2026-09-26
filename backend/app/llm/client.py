"""The one way the pipeline talks to a model: ask for a Pydantic object, get one back.

Every call goes through a mode:

- replay:        load the recorded response; a missing recording raises MissingRecording.
                 Never falls back to the API.
- record:        call the API and write the recording.
- live:          call the API without writing a recording.
- replay_first:  use a recording when one exists, otherwise call the API (Ask only).

A recording is keyed by what the model saw (see recording_key), so changing a prompt,
its version, the schema or the model makes the old recording unreachable.
"""

import hashlib
import json
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel

Mode = Literal["replay", "record", "live", "replay_first"]
T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def structured(
        self,
        *,
        schema: type[T],
        system: str,
        user: str,
        purpose: str,
        prompt_version: str,
        run_id: str,
        mode: Mode | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> T: ...


class LLMError(Exception):
    """The model didn't return a usable answer."""


class MissingRecording(LLMError):
    def __init__(self, purpose: str, key: str) -> None:
        self.purpose = purpose
        self.key = key
        super().__init__(
            f"no recording for {purpose} (key {key}); run `lens record` with an API key"
        )


def recording_key(
    *, model: str, prompt_version: str, system: str, user: str, schema: dict[str, Any]
) -> str:
    """sha256 of the canonical JSON of everything that shapes the model's answer."""
    payload = {
        "model": model,
        "prompt_version": prompt_version,
        "system": system,
        "user": user,
        "schema": schema,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
