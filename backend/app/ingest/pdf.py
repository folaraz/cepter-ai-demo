"""Split a data-room PDF into paragraphs.

A port of the reference ingester in backend/tools/check_dataroom.py. The rules must not
drift from it: tests/test_ingest.py compares the two paragraph for paragraph.

- Text blocks come from `page.get_text("dict", sort=True)`, sorted by (y, x).
- Blocks starting within 70pt of the top or bottom edge are the running header and
  footer, and are skipped.
- A block whose non-empty spans are all bold is a heading: it becomes the current heading
  (carried across pages) and is not a paragraph.
- A block's lines are joined with a space, except after a line ending in "-": that is a
  compound word broken at its hyphen ("Long-" + "Stop"), so the hyphen stays and no space
  is added.
- Text is NFKC-normalised (undoing ligatures) and whitespace is collapsed.
- IDs are "{paragraph_prefix}:p{page}:¶{n}", n counting paragraphs per page from 1.
"""

import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf

from app.domain.documents import Paragraph

MARGIN_PT = 70
BOLD_FLAG = 16

Block = dict[str, Any]  # a text block from PyMuPDF's "dict" output


@dataclass(frozen=True)
class ParsedPdf:
    sha256: str
    pages: int
    paragraphs: list[Paragraph]


def clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def join_lines(block: Block) -> str:
    out = ""
    for line in block["lines"]:
        text = "".join(span["text"] for span in line["spans"]).strip()
        if not text:
            continue
        if out and not out.endswith("-"):
            out += " "
        out += text
    return out


def is_heading(block: Block) -> bool:
    spans = [s for line in block["lines"] for s in line["spans"] if s["text"].strip()]
    return bool(spans) and all((s["flags"] & BOLD_FLAG) or "Bold" in s["font"] for s in spans)


def _body_blocks(page: pymupdf.Page) -> list[Block]:
    height = page.rect.height
    blocks = [
        b
        for b in page.get_text("dict", sort=True)["blocks"]
        if b["type"] == 0 and MARGIN_PT <= b["bbox"][1] <= height - MARGIN_PT
    ]
    blocks.sort(key=lambda b: (round(b["bbox"][1], 1), round(b["bbox"][0], 1)))
    return blocks


def parse_pdf(path: Path, document_id: str, paragraph_prefix: str) -> ParsedPdf:
    data = path.read_bytes()
    paragraphs: list[Paragraph] = []
    heading: str | None = None
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        pages = doc.page_count
        for page_no, page in enumerate(doc, start=1):
            ordinal = 0
            for block in _body_blocks(page):
                text = clean(join_lines(block))
                if not text:
                    continue
                if is_heading(block):
                    heading = text
                    continue
                ordinal += 1
                paragraphs.append(
                    Paragraph(
                        id=f"{paragraph_prefix}:p{page_no}:¶{ordinal}",
                        document_id=document_id,
                        page=page_no,
                        ordinal=ordinal,
                        heading=heading,
                        text=text,
                    )
                )
    return ParsedPdf(sha256=hashlib.sha256(data).hexdigest(), pages=pages, paragraphs=paragraphs)
