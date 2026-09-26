"""`lens ingest`: load every PDF in the manifest into `documents` and `paragraphs`."""

from dataclasses import dataclass
from pathlib import Path

from psycopg import Connection

from app.config import DATAROOM_DIR
from app.db.repositories import documents
from app.domain.documents import Document
from app.ingest.manifest import load_manifest
from app.ingest.pdf import parse_pdf


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    paragraphs: int
    changed: bool  # False: nothing was written


def ingest_dataroom(conn: Connection, room: Path = DATAROOM_DIR) -> list[IngestResult]:
    """Ingest every document in the manifest, one transaction per document. A document
    whose PDF sha256 and manifest entry are unchanged since the last ingest is left alone."""
    results: list[IngestResult] = []
    for entry in load_manifest(room):
        parsed = parse_pdf(room / "pdf" / entry.file, entry.id, entry.paragraph_prefix)
        doc = Document(
            id=entry.id,
            file_name=entry.file,
            title=entry.title,
            noun=entry.noun,
            paragraph_prefix=entry.paragraph_prefix,
            pages=parsed.pages,
            sha256=parsed.sha256,
        )
        stored = documents.get_document(conn, entry.id)
        if stored == doc:
            results.append(IngestResult(entry.id, len(parsed.paragraphs), changed=False))
            continue
        with conn.transaction():
            documents.upsert_document(conn, doc)
            documents.replace_paragraphs(conn, entry.id, parsed.paragraphs)
        results.append(IngestResult(entry.id, len(parsed.paragraphs), changed=True))
    return results
