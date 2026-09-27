"""One pipeline run: record it in `runs`, run the passes, mark it finished.

Pass 1 (extraction), pass 2 (verification), pass 3 (consolidation), then the check
playbook, which writes one finding per check.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime

from psycopg import Connection

from app.checks.runner import run_checks
from app.checks.view import GraphView
from app.consolidate.graph import consolidate, write_graph
from app.db.repositories import claims, documents, findings, runs
from app.domain.claims import Claim
from app.domain.findings import FindingRecord
from app.domain.ontology import load_ontology
from app.domain.runs import RunKind
from app.extract.pass1 import run_pass1
from app.extract.prompt import PROMPT_VERSION
from app.ingest.manifest import load_as_of, load_asset_name, load_manifest
from app.llm.client import LLMClient, Mode
from app.logs import run_context
from app.verify.verifier import verify_claims

log = logging.getLogger("lens.pipeline")


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    claims: list[Claim]  # verified and rejected, in document order
    nodes: int
    edges: int
    findings: list[FindingRecord]


def new_run_id(now: datetime | None = None) -> str:
    return f"r-{(now or datetime.now()):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"


def run_pipeline(
    conn: Connection,
    llm: LLMClient,
    *,
    kind: RunKind = "eval",
    mode: Mode | None = None,
    publish: bool = False,
    session_id: str | None = None,  # set for eval runs started from the UI
) -> PipelineResult:
    run = runs.create_run(
        conn,
        new_run_id(),
        kind,
        load_as_of(),
        session_id=session_id,
        prompt_versions={"extract": PROMPT_VERSION},
    )
    with run_context(run.id):
        log.info("pipeline started", extra={"kind": kind})
        result = _run_passes(conn, llm, run.id, run.as_of, mode, publish)
        log.info(
            "pipeline finished",
            extra={"claims": len(result.claims), "findings": len(result.findings)},
        )
        return result


def _run_passes(
    conn: Connection, llm: LLMClient, run_id: str, as_of: date, mode: Mode | None, publish: bool
) -> PipelineResult:
    try:
        drafts = run_pass1(conn, llm, run_id, mode)
        paragraphs = {p.id: p for p in documents.list_paragraphs(conn)}
        checked = verify_claims(
            (d for doc in drafts.values() for d in doc), paragraphs, load_ontology(), run_id
        )
        stored = claims.insert_claims(conn, checked)
        graph = consolidate(
            run_id,
            stored,
            paragraphs,
            load_ontology(),
            load_asset_name(),
            [d.id for d in load_manifest()],
        )
        write_graph(conn, graph)
        order = [d.id for d in load_manifest()]
        view = GraphView.load(conn, run_id, order, as_of)
        results = run_checks(view, run_id)
        findings.insert_findings(conn, results)
    except Exception as err:
        runs.finish_run(conn, run_id, "failed", f"{type(err).__name__}: {err}")
        raise
    if publish:
        runs.publish_run(conn, run_id)
    else:
        runs.finish_run(conn, run_id, "succeeded")
    return PipelineResult(run_id, stored, len(graph.nodes), len(graph.edges), results)
