"""`lens seed`: apply backend/seed/reviews.yaml so the demo opens in the fixtures' state.

Seed reviews have no session, so every visitor sees them. Applying twice changes nothing.
"""

from pathlib import Path

import yaml
from psycopg import Connection

from app.config import BACKEND_DIR
from app.db.repositories import findings as findings_repo
from app.db.repositories import reviews as reviews_repo
from app.domain.reviews import NewReview
from app.reviews.fingerprint import evidence_fingerprint

SEED_YAML = BACKEND_DIR / "seed" / "reviews.yaml"


def apply_seed(conn: Connection, run_id: str, path: Path = SEED_YAML) -> int:
    """Insert the seed reviews not yet present, fingerprinted against the run's findings.
    Returns how many were added."""
    existing = {r.undo_token for r in reviews_repo.list_visible_reviews(conn, None)}
    added = 0
    for item in yaml.safe_load(path.read_text(encoding="utf-8"))["reviews"]:
        token = f"seed:{item['finding_id']}:{item['action']}"
        if token in existing:
            continue
        finding = findings_repo.get_finding(conn, run_id, item["finding_id"])
        if finding is None:
            raise ValueError(f"seed review for {item['finding_id']}: no such finding in {run_id}")
        reviews_repo.insert_review(
            conn,
            NewReview(
                session_id=None,
                finding_id=item["finding_id"],
                check_id=item["check_id"],
                action=item["action"],
                corrected_result=item.get("corrected_result"),
                reason=" ".join(item["reason"].split()) if item.get("reason") else None,
                evidence_fingerprint=evidence_fingerprint(finding.evidence),  # type: ignore[arg-type]
                golden_item_id=item.get("golden_item_id"),
                reviewer=item.get("reviewer", "Demo reviewer"),
                undo_token=token,
            ),
            created_at=item.get("created_at"),
        )
        added += 1
    return added
