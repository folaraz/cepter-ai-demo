"""The golden set a session is measured against (SPEC C11).

evals/golden.jsonl, plus a correction item for every reject or correct review visible to
the session (seed reviews and its own, not reverted). A correction supersedes any `check`
item for the same check: the lawyer wins. The set is derived, never stored, so undoing a
review removes its item.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from psycopg import Connection

from app.db.repositories import findings as findings_repo
from app.db.repositories import reviews as reviews_repo
from app.db.repositories import runs
from app.reviews.golden import correction_item, read_golden


@dataclass(frozen=True)
class GoldenSet:
    items: list[dict[str, Any]]  # by ID

    @property
    def hash(self) -> str:
        """sha256 of the sorted items: a different set means a different hash."""
        canonical = json.dumps(self.items, sort_keys=True, ensure_ascii=False)
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    def of(self, kind: str) -> list[dict[str, Any]]:
        return [i for i in self.items if i["kind"] == kind]


def golden_set(conn: Connection, session_id: str | None) -> GoldenSet:
    items = {i["id"]: i for i in read_golden()}
    published = runs.get_published_run(conn)
    if published is not None:
        for review in reviews_repo.list_visible_reviews(conn, session_id):
            if review.golden_item_id is None or review.golden_item_id in items:
                continue
            finding = findings_repo.get_finding(conn, published.id, review.finding_id)
            if finding is not None:
                items[review.golden_item_id] = correction_item(review, finding)

    corrected = {i["check_id"] for i in items.values() if i["kind"] == "correction"}
    kept = [i for i in items.values() if not (i["kind"] == "check" and i["check_id"] in corrected)]
    return GoldenSet(sorted(kept, key=lambda i: i["id"]))
