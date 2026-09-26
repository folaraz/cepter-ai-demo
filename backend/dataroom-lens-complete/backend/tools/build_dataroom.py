"""Render the synthetic data room from Markdown to PDF.

Usage (from the repo root):
    python backend/tools/build_dataroom.py

Needs: pip install weasyprint markdown pyyaml

The built PDFs are committed to data/dataroom/pdf/, so ingestion never depends on the
fonts installed on a given machine. Re-run this only when a source .md file changes,
then run backend/tools/check_dataroom.py and commit the PDFs.

Source conventions:
    # Title                -> document title (a heading, never a paragraph)
    ## Heading             -> clause heading (a heading, never a paragraph)
    plain text             -> one paragraph
    <!-- pagebreak -->     -> start a new page
"""

from __future__ import annotations

import html
from pathlib import Path

import markdown
import yaml
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[2]
ROOM = ROOT / "data" / "dataroom"

CSS = """
@page {
  size: A4;
  margin: 28mm 24mm 26mm 24mm;
  @top-left { content: "%(title)s"; font: 8pt "DejaVu Sans", sans-serif; color: #555; }
  @top-right { content: "SYNTHETIC DOCUMENT - NOT A REAL AGREEMENT"; font: 8pt "DejaVu Sans", sans-serif; color: #555; }
  @bottom-center { content: "Page " counter(page) " of " counter(pages); font: 8pt "DejaVu Sans", sans-serif; color: #555; }
}
body {
  font-family: "DejaVu Serif", "Liberation Serif", Georgia, serif;
  font-size: 11pt;
  line-height: 1.45;
  font-variant-ligatures: none;
  font-kerning: normal;
  hyphens: manual;
  color: #111;
}
h1 { font-size: 16pt; font-weight: bold; margin: 0 0 16pt; }
h2 { font-size: 11pt; font-weight: bold; margin: 14pt 0 5pt; }
p  { margin: 0 0 9pt; text-align: left; }
.pagebreak { break-before: page; height: 0; }
"""


def render(doc: dict) -> Path:
    src = (ROOM / doc["source"]).read_text(encoding="utf-8")
    src = src.replace("<!-- pagebreak -->", '<div class="pagebreak"></div>')
    body = markdown.markdown(src, output_format="html5")
    css = CSS % {"title": html.escape(doc["title"])}
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(doc['title'])}</title><style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )
    out = ROOM / "pdf" / doc["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=page, base_url=str(ROOM)).write_pdf(out)
    return out


def main() -> None:
    manifest = yaml.safe_load((ROOM / "manifest.yaml").read_text(encoding="utf-8"))
    for doc in manifest["documents"]:
        print("built", render(doc).relative_to(ROOT))


if __name__ == "__main__":
    main()
