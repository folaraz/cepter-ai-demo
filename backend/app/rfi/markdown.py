"""GET /api/rfi.md: the RFI list as Markdown, sent to the seller.

Mirrors frontend/src/api/markdown.ts so fixture mode and the API export the same file.
No internal references (check IDs, finding IDs): the seller never sees them.
"""

from app.api.models import Rfi

SEVERITY_WORD = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}


def rfis_to_markdown(rfis: list[Rfi], asset_name: str) -> str:
    blocks = [
        "\n".join(
            [
                f"### {r.id}: {r.title} ({SEVERITY_WORD[r.severity]})",
                "",
                f"**Request.** {r.request}",
                "",
                f"**Why.** {r.why}",
                "",
                "**Documents expected.**",
                *[f"- {d}" for d in r.documents_expected],
            ]
        )
        for r in rfis
    ]
    parts = [f"# Requests for information: {asset_name}", ""]
    for block in blocks:
        parts += [block, ""]
    return "\n".join(parts)
