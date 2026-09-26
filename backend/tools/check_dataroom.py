"""Prove the synthetic data room reproduces the UI fixtures.

Usage (from the repo root):
    python backend/tools/check_dataroom.py

Needs: pip install pymupdf pyyaml

What it checks, using a minimal reference implementation of the paragraph rules in
specs/SPEC.md (component 4). The production ingester must produce the same IDs,
headings and text as this script; tests/test_ingest.py should import or mirror it.

  1. Every paragraph cited in design/api/fixtures/findings/*.json (or the copy in
     backend/tests/contract/expected/findings/) exists at the same paragraph ID,
     under the same heading, with exactly the same text.
  2. Every fixture quote is a verbatim substring of that paragraph at the same offsets.
  3. Two ingestions produce identical IDs (determinism).
  4. Known extraction traps are handled: a line broken after a hyphen
     (ppa:p4:¶2 "Long-Stop Date") and the running header/footer on every page.

Exit code 0 when all checks pass.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pymupdf
import yaml

ROOT = Path(__file__).resolve().parents[2]
ROOM = ROOT / "data" / "dataroom"
EXPECTED = ROOT / "backend" / "tests" / "contract" / "expected" / "findings"

MARGIN_PT = 70  # blocks starting inside the top or bottom 70pt are running header/footer


@dataclass(frozen=True)
class Paragraph:
    id: str
    document_id: str
    page: int
    ordinal: int
    heading: str | None
    text: str


def clean(text: str) -> str:
    """Normalise extracted text: Unicode NFKC (undo ligatures), collapse whitespace."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def join_lines(block: dict) -> str:
    """Join a block's lines. A line ending in '-' is a compound word broken at the
    hyphen ("Long-" + "Stop"), so keep the hyphen and add no space."""
    out = ""
    for line in block["lines"]:
        text = "".join(s["text"] for s in line["spans"]).strip()
        if not text:
            continue
        if out and not out.endswith("-"):
            out += " "
        out += text
    return out


def is_heading(block: dict) -> bool:
    spans = [s for line in block["lines"] for s in line["spans"] if s["text"].strip()]
    return bool(spans) and all((s["flags"] & 16) or "Bold" in s["font"] for s in spans)


def ingest(pdf_path: Path, document_id: str, prefix: str) -> list[Paragraph]:
    out: list[Paragraph] = []
    heading: str | None = None
    with pymupdf.open(pdf_path) as doc:
        for page_no, page in enumerate(doc, start=1):
            height = page.rect.height
            blocks = [
                b
                for b in page.get_text("dict", sort=True)["blocks"]
                if b["type"] == 0 and MARGIN_PT <= b["bbox"][1] <= height - MARGIN_PT
            ]
            blocks.sort(key=lambda b: (round(b["bbox"][1], 1), round(b["bbox"][0], 1)))
            ordinal = 0
            for b in blocks:
                text = clean(join_lines(b))
                if not text:
                    continue
                if is_heading(b):
                    heading = text
                    continue
                ordinal += 1
                out.append(
                    Paragraph(
                        id=f"{prefix}:p{page_no}:¶{ordinal}",
                        document_id=document_id,
                        page=page_no,
                        ordinal=ordinal,
                        heading=heading,
                        text=text,
                    )
                )
    return out


def ingest_all() -> dict[str, Paragraph]:
    manifest = yaml.safe_load((ROOM / "manifest.yaml").read_text(encoding="utf-8"))
    paras: dict[str, Paragraph] = {}
    for d in manifest["documents"]:
        for p in ingest(ROOM / "pdf" / d["file"], d["id"], d["paragraph_prefix"]):
            paras[p.id] = p
    return paras


def main() -> int:
    first = ingest_all()
    second = ingest_all()
    failures: list[str] = []
    if list(first) != list(second) or any(first[k] != second[k] for k in first):
        failures.append("ingestion is not deterministic")

    fixture_dir = EXPECTED if EXPECTED.exists() else ROOT / "design" / "api" / "fixtures" / "findings"
    checked = 0
    for f in sorted(fixture_dir.glob("F-*.json")):
        finding = json.loads(f.read_text(encoding="utf-8"))
        for ev in finding["evidence"]:
            if ev["kind"] != "quote":
                continue
            checked += 1
            cit = ev["citation"]
            pid = cit["paragraph_id"]
            p = first.get(pid)
            where = f"{finding['id']} {pid}"
            if p is None:
                failures.append(f"{where}: paragraph not found")
                continue
            if p.document_id != cit["document_id"]:
                failures.append(f"{where}: document_id {p.document_id!r} != {cit['document_id']!r}")
            if p.page != cit["page"]:
                failures.append(f"{where}: page {p.page} != {cit['page']}")
            if p.heading != ev["heading"]:
                failures.append(f"{where}: heading {p.heading!r} != {ev['heading']!r}")
            if p.text != ev["paragraph_text"]:
                failures.append(f"{where}: text differs\n   got:  {p.text}\n   want: {ev['paragraph_text']}")
            start = p.text.find(cit["quote"])
            if start < 0:
                failures.append(f"{where}: quote not verbatim in paragraph")
            elif (start, start + len(cit["quote"])) != (ev["quote_start"], ev["quote_end"]):
                failures.append(f"{where}: quote offsets {start} != {ev['quote_start']}")

    traps = {
        "ppa:p4:¶2": '(the "Long-Stop Date")',
    }
    for pid, needle in traps.items():
        if pid not in first or needle not in first[pid].text:
            failures.append(f"{pid}: expected text {needle!r} (hyphenated line break)")
    if any("SYNTHETIC DOCUMENT" in p.text or p.text.startswith("Page ") for p in first.values()):
        failures.append("running header or footer leaked into paragraphs")

    by_doc: dict[str, int] = {}
    for p in first.values():
        by_doc[p.document_id] = by_doc.get(p.document_id, 0) + 1
    print(f"ingested {len(first)} paragraphs: " + ", ".join(f"{k} {v}" for k, v in by_doc.items()))
    print(f"checked {checked} cited paragraphs against {fixture_dir.relative_to(ROOT)}")
    if failures:
        print("FAIL")
        for msg in failures:
            print(" -", msg)
        return 1
    print("PASS: every fixture citation is reproduced exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
