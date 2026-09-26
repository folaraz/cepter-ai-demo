"""One pipeline run: record it in `runs`, run the passes, mark it finished.

Pass 1 (extraction) is here now. The verifier (C5), consolidation (C6) and checks (C7)
join it as they are built.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from psycopg import Connection

from app.db.repositories import runs
from app.domain.extraction import ClaimDraft
from app.domain.runs import RunKind
from app.extract.pass1 import run_pass1
from app.extract.prompt import PROMPT_VERSION
from app.ingest.manifest import load_as_of
from app.llm.client import LLMClient, Mode


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    drafts: dict[str, list[ClaimDraft]]  # per document


def new_run_id(now: datetime | None = None) -> str:
    return f"r-{(now or datetime.now()):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"


def run_pipeline(
    conn: Connection,
    llm: LLMClient,
    *,
    kind: RunKind = "eval",
    mode: Mode | None = None,
    publish: bool = False,
) -> PipelineResult:
    run = runs.create_run(
        conn, new_run_id(), kind, load_as_of(), prompt_versions={"extract": PROMPT_VERSION}
    )
    try:
        drafts = run_pass1(conn, llm, run.id, mode)
    except Exception as err:
        runs.finish_run(conn, run.id, "failed", f"{type(err).__name__}: {err}")
        raise
    if publish:
        runs.publish_run(conn, run.id)
    else:
        runs.finish_run(conn, run.id, "succeeded")
    return PipelineResult(run.id, drafts)
