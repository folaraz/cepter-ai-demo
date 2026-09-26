"""C1: the production ingester reproduces the reference ingester exactly."""

import re
import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from app.config import BACKEND_DIR, DATAROOM_DIR
from app.db.migrate import migrate
from app.db.repos import documents as repo
from app.domain.documents import Paragraph
from app.ingest.manifest import load_manifest
from app.ingest.pdf import parse_pdf
from app.ingest.service import ingest_dataroom

sys.path.insert(0, str(BACKEND_DIR / "tools"))
import check_dataroom as reference

EXPECTED_COUNTS = {"lease": 11, "planning": 16, "grid": 10, "ppa": 13, "site": 5}


def ingest_all() -> list[Paragraph]:
    return [
        p
        for d in load_manifest()
        for p in parse_pdf(DATAROOM_DIR / "pdf" / d.file, d.id, d.paragraph_prefix).paragraphs
    ]


@pytest.fixture(scope="module")
def paragraphs() -> list[Paragraph]:
    return ingest_all()


def test_matches_the_reference_paragraph_for_paragraph(paragraphs: list[Paragraph]) -> None:
    ref = list(reference.ingest_all().values())
    assert [p.model_dump() for p in paragraphs] == [vars(r) for r in ref]


def test_paragraph_counts(paragraphs: list[Paragraph]) -> None:
    counts: dict[str, int] = {}
    for p in paragraphs:
        counts[p.document_id] = counts.get(p.document_id, 0) + 1
    assert counts == EXPECTED_COUNTS
    assert len(paragraphs) == 55


def test_two_runs_are_identical(paragraphs: list[Paragraph]) -> None:
    assert ingest_all() == paragraphs


def test_line_broken_after_a_hyphen_keeps_the_hyphen(paragraphs: list[Paragraph]) -> None:
    by_id = {p.id: p for p in paragraphs}
    assert '(the "Long-Stop Date")' in by_id["ppa:p4:¶2"].text


def test_running_header_and_footer_are_skipped(paragraphs: list[Paragraph]) -> None:
    for p in paragraphs:
        assert "SYNTHETIC DOCUMENT" not in p.text, p.id
        assert not re.search(r"\bPage \d+ of \d+\b", p.text), p.id


def test_ids_count_per_page_from_one(paragraphs: list[Paragraph]) -> None:
    for p in paragraphs:
        prefix = p.id.split(":")[0]
        assert p.id == f"{prefix}:p{p.page}:¶{p.ordinal}"
    first_on_page = {(p.document_id, p.page): p.ordinal for p in reversed(paragraphs)}
    assert set(first_on_page.values()) == {1}


# ---------- lens ingest ----------


@pytest.fixture
def conn(empty_database: str) -> Iterator[psycopg.Connection]:
    migrate(empty_database)
    with psycopg.connect(empty_database, autocommit=True) as conn:
        yield conn


@pytest.mark.db
def test_ingest_stores_documents_and_paragraphs(
    conn: psycopg.Connection, paragraphs: list[Paragraph]
) -> None:
    results = ingest_dataroom(conn)
    assert {r.document_id: r.paragraphs for r in results} == EXPECTED_COUNTS
    assert all(r.changed for r in results)

    docs = {d.id: d for d in repo.list_documents(conn)}
    assert {d: docs[d].pages for d in docs} == {
        "lease": 3,
        "planning": 3,
        "grid": 3,
        "ppa": 5,
        "site": 2,
    }
    assert all(re.fullmatch(r"[0-9a-f]{64}", d.sha256) for d in docs.values())
    stored = repo.list_paragraphs(conn)
    assert sorted(stored, key=lambda p: p.id) == sorted(paragraphs, key=lambda p: p.id)


@pytest.mark.db
def test_ingest_skips_unchanged_documents(conn: psycopg.Connection) -> None:
    ingest_dataroom(conn)
    assert not any(r.changed for r in ingest_dataroom(conn))


@pytest.mark.db
def test_ingest_redoes_a_document_whose_pdf_changed(conn: psycopg.Connection) -> None:
    ingest_dataroom(conn)
    conn.execute("UPDATE documents SET sha256 = 'stale' WHERE id = 'ppa'")
    conn.execute("UPDATE paragraphs SET text = 'edited' WHERE id = 'ppa:p4:¶2'")
    conn.execute(
        "INSERT INTO paragraphs (id, document_id, page, ordinal, text) "
        "VALUES ('ppa:p9:¶1', 'ppa', 9, 1, 'gone after re-ingest')"
    )

    changed = {r.document_id for r in ingest_dataroom(conn) if r.changed}

    assert changed == {"ppa"}
    ppa = {p.id: p for p in repo.list_paragraphs(conn, "ppa")}
    assert "ppa:p9:¶1" not in ppa
    assert '"Long-Stop Date"' in ppa["ppa:p4:¶2"].text
    doc = repo.get_document(conn, "ppa")
    assert doc is not None and doc.sha256 != "stale"


def test_manifest_lists_the_five_documents() -> None:
    assert [d.id for d in load_manifest()] == list(EXPECTED_COUNTS)
    for d in load_manifest():
        assert Path(DATAROOM_DIR / "pdf" / d.file).is_file()
