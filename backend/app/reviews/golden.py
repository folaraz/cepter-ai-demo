"""Reviewer corrections as golden items: the regression tests a lawyer's decision becomes.

A reject says the check should not have flagged (the item expects `pass`); a correct
says what the result should have been. C11 derives each session's golden set from the
base file plus these; `lens golden export` appends a session's to the file for CI.
"""

import json
import re
from datetime import UTC
from pathlib import Path
from typing import Any

from psycopg import Connection

from app.config import REPO_ROOT
from app.db.repositories import findings as findings_repo
from app.db.repositories import reviews as reviews_repo
from app.db.repositories import runs
from app.domain.findings import FindingRecord
from app.domain.reviews import Review

GOLDEN = REPO_ROOT / "evals" / "golden.jsonl"
_CORR = re.compile(r"^corr-(\d+)$")


def read_golden(path: Path = GOLDEN) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def next_correction_id(visible: list[Review], path: Path = GOLDEN) -> str:
    """corr-{NNN} after every correction already in the golden file or visible to the
    session, so the first new one in the demo is corr-002."""
    taken = [item["id"] for item in read_golden(path)] + [r.golden_item_id or "" for r in visible]
    numbers = [int(m.group(1)) for t in taken if (m := _CORR.match(t))]
    return f"corr-{max(numbers, default=0) + 1:03d}"


def correction_item(review: Review, finding: FindingRecord) -> dict[str, Any]:
    """The golden item a reject or correct review stands for, in the file's format."""
    assert review.golden_item_id is not None and review.reason is not None
    expect = review.corrected_result if review.action == "correct" else "pass"
    return {
        "id": review.golden_item_id,
        "kind": "correction",
        "check_id": review.check_id,
        "finding_id": review.finding_id,
        "expect": expect,
        "was": finding.result,
        "reason": review.reason,
        "source": "reviewer",
        "reviewer": review.reviewer,
        "created_at": review.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence_fingerprint": review.evidence_fingerprint,
    }


def append_items(items: list[dict[str, Any]], path: Path = GOLDEN) -> list[dict[str, Any]]:
    """Append items whose ID isn't in the file yet; returns the ones written."""
    existing = {item["id"] for item in read_golden(path)}
    new = [i for i in items if i["id"] not in existing]
    if new:
        text = path.read_text(encoding="utf-8")
        lines = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in new)
        path.write_text(
            text + ("" if text.endswith("\n") or not text else "\n") + lines, encoding="utf-8"
        )
    return new


def export_session_corrections(
    conn: Connection, session_id: str, path: Path = GOLDEN
) -> list[dict[str, Any]]:
    """The session's visible rejects and corrections, as items appended to the file."""
    run = runs.get_published_run(conn)
    if run is None:
        return []
    items = []
    for review in reviews_repo.list_visible_reviews(conn, session_id):
        if review.session_id != session_id or review.golden_item_id is None:
            continue
        finding = findings_repo.get_finding(conn, run.id, review.finding_id)
        if finding is not None:
            items.append(correction_item(review, finding))
    return append_items(items, path)
