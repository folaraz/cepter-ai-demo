"""`lens ask calibrate`: how retrieval does on every golden Ask question (SPEC C13)."""

import json
from dataclasses import dataclass
from typing import Any

from psycopg import Connection

from app.config import REPO_ROOT
from app.retrieval.config import retrieval_config
from app.retrieval.search import keyword_search, search, vector_search

ASK_GOLDEN = REPO_ROOT / "evals" / "ask_golden.jsonl"


@dataclass(frozen=True)
class Ranks:
    paragraph_id: str
    vector: int | None
    keyword: int | None
    hybrid: int | None


@dataclass(frozen=True)
class Calibration:
    item: dict[str, Any]
    best_similarity: float
    keyword_found: bool
    ranks: list[Ranks]

    @property
    def recalled(self) -> bool:
        """Every expected paragraph is in the hybrid top_k."""
        top_k = retrieval_config().top_k
        return all(r.hybrid is not None and r.hybrid <= top_k for r in self.ranks)


def read_ask_golden() -> list[dict[str, Any]]:
    lines = ASK_GOLDEN.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def measure(conn: Connection, item: dict[str, Any]) -> Calibration:
    n = retrieval_config().candidates_per_method
    question = item["question"]
    vector = [pid for pid, _, _ in vector_search(conn, question, n)]
    keyword = [pid for pid, _ in keyword_search(conn, question, n)]
    fused = search(conn, question, top_k=0)
    hybrid = [h.paragraph_id for h in fused.hits]

    def rank(ids: list[str], pid: str) -> int | None:
        return ids.index(pid) + 1 if pid in ids else None

    return Calibration(
        item=item,
        best_similarity=fused.best_similarity,
        keyword_found=fused.keyword_found,
        ranks=[
            Ranks(pid, rank(vector, pid), rank(keyword, pid), rank(hybrid, pid))
            for pid in item.get("paragraphs") or []
        ],
    )


def calibrate(conn: Connection) -> str:
    config = retrieval_config()

    def cell(r: int | None) -> str:
        return "-" if r is None else str(r)

    lines = [
        f"{'id':<5}{'route':<14}{'best sim':>9}  {'kw':<3} expected paragraph        "
        f"{'vector':>7}{'keyword':>8}{'hybrid':>7}",
    ]
    for item in read_ask_golden():
        c = measure(conn, item)
        head = f"{item['id']:<5}{item['route']:<14}{c.best_similarity:>9.3f}  "
        head += f"{'yes' if c.keyword_found else 'no':<3} "
        if not c.ranks:
            lines.append(head + "(expected to abstain)")
        for i, r in enumerate(c.ranks):
            prefix = head if i == 0 else " " * len(head)
            lines.append(
                f"{prefix}{r.paragraph_id:<26}{cell(r.vector):>7}{cell(r.keyword):>8}"
                f"{cell(r.hybrid):>7}"
            )
    lines.append(
        f"min_similarity is {config.min_similarity}; hybrid recall counts ranks <= top_k "
        f"({config.top_k})."
    )
    return "\n".join(lines)
