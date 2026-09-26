"""One pipeline run: record it in `runs`, run the passes, mark it finished.

Pass 1 (extraction) and pass 2 (verification) are here now. Consolidation (C6) and the
checks (C7) join them as they are built.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from psycopg import Connection

from app.db.repositories import claims, documents, runs
from app.domain.claims import Claim
from app.domain.ontology import load_ontology
from app.domain.runs import RunKind
from app.extract.pass1 import run_pass1
from app.extract.prompt import PROMPT_VERSION
from app.ingest.manifest import load_as_of
from app.llm.client import LLMClient, Mode
from app.verify.verifier import verify_claims


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    claims: list[Claim]  # verified and rejected, in document order


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
        paragraphs = {p.id: p for p in documents.list_paragraphs(conn)}
        checked = verify_claims(
            (d for doc in drafts.values() for d in doc), paragraphs, load_ontology(), run.id
        )
        stored = claims.insert_claims(conn, checked)
    except Exception as err:
        runs.finish_run(conn, run.id, "failed", f"{type(err).__name__}: {err}")
        raise
    if publish:
        runs.publish_run(conn, run.id)
    else:
        runs.finish_run(conn, run.id, "succeeded")
    return PipelineResult(run.id, stored)
