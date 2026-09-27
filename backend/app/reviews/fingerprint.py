"""What a review was looking at: a hash of the finding's cited paragraphs.

A correction only holds while the text it was made against is unchanged (SPEC C11): if a
cited paragraph changes, the fingerprint changes and the override lapses.
"""

import hashlib
from typing import Any


def evidence_fingerprint(evidence: list[dict[str, Any]]) -> str:
    """sha256 of the sorted "{paragraph_id}\\t{paragraph text}" lines of the quote cards,
    the recipe behind corr-001 in evals/golden.jsonl."""
    lines = sorted(
        {
            f"{e['citation']['paragraph_id']}\t{e['paragraph_text']}"
            for e in evidence
            if e["kind"] == "quote"
        }
    )
    return "sha256:" + hashlib.sha256("\n".join(lines).encode()).hexdigest()
