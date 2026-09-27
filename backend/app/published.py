"""The published run as one visitor sees it: its graph, its findings, and the review
state each finding is in for that visitor's session. Every read endpoint starts here."""

from dataclasses import dataclass
from datetime import UTC
from typing import Any

from psycopg import Connection

from app.checks.runner import CheckSpec, load_checks
from app.checks.view import GraphView
from app.db.repositories import findings as findings_repo
from app.db.repositories import runs
from app.domain.findings import FindingRecord
from app.domain.runs import Run
from app.ingest.manifest import load_manifest
from app.reviews.state import Effective, effective, latest_reviews


class NoPublishedRun(Exception):
    """Nothing has been published yet (`lens run --publish`)."""


@dataclass(frozen=True)
class Published:
    run: Run
    view: GraphView
    specs: dict[str, CheckSpec]  # by check ID
    findings: list[FindingRecord]  # in check order
    state: dict[str, Effective]  # by finding ID, after this session's reviews

    def finding(self, finding_id: str) -> FindingRecord | None:
        return next((f for f in self.findings if f.id == finding_id), None)

    def by_check(self, check_id: str) -> FindingRecord:
        return next(f for f in self.findings if f.check_id == check_id)

    def result_of(self, check_id: str) -> str:
        return self.state[self.by_check(check_id).id].result

    @property
    def run_at(self) -> str:
        at = self.run.finished_at or self.run.started_at
        return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_published(
    conn: Connection, session_id: str | None, run_id: str | None = None
) -> Published:
    """The published run, or `run_id` (an eval run, for Ask's accuracy check)."""
    run = runs.get_run(conn, run_id) if run_id else runs.get_published_run(conn)
    if run is None:
        raise NoPublishedRun
    order = [d.id for d in load_manifest()]
    stored = findings_repo.list_findings(conn, run.id)
    reviews = latest_reviews(conn, session_id)
    return Published(
        run=run,
        view=GraphView.load(conn, run.id, order, run.as_of),
        specs={s.id: s for s in load_checks()},
        findings=stored,
        state={f.id: effective(f, reviews.get(f.id)) for f in stored},
    )


def evidence_of(finding: FindingRecord) -> list[dict[str, Any]]:
    return [dict(e) for e in finding.evidence]  # type: ignore[arg-type]
