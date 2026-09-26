"""`documents` and `paragraphs`."""

from psycopg import Connection
from psycopg.rows import class_row

from app.domain.documents import Document, Paragraph


def get_document(conn: Connection, document_id: str) -> Document | None:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            "SELECT id, file_name, title, noun, paragraph_prefix, pages, sha256 "
            "FROM documents WHERE id = %s",
            (document_id,),
        )
        return cur.fetchone()


def list_documents(conn: Connection) -> list[Document]:
    with conn.cursor(row_factory=class_row(Document)) as cur:
        cur.execute(
            "SELECT id, file_name, title, noun, paragraph_prefix, pages, sha256 "
            "FROM documents ORDER BY id"
        )
        return cur.fetchall()


def upsert_document(conn: Connection, doc: Document) -> None:
    conn.execute(
        """
        INSERT INTO documents (id, file_name, title, noun, paragraph_prefix, pages, sha256)
        VALUES (%(id)s, %(file_name)s, %(title)s, %(noun)s, %(paragraph_prefix)s,
                %(pages)s, %(sha256)s)
        ON CONFLICT (id) DO UPDATE SET
            file_name = EXCLUDED.file_name,
            title = EXCLUDED.title,
            noun = EXCLUDED.noun,
            paragraph_prefix = EXCLUDED.paragraph_prefix,
            pages = EXCLUDED.pages,
            sha256 = EXCLUDED.sha256,
            ingested_at = now()
        """,
        doc.model_dump(),
    )


def replace_paragraphs(conn: Connection, document_id: str, paragraphs: list[Paragraph]) -> None:
    """Make the document's paragraphs exactly `paragraphs`. Rows whose ID is kept are
    updated in place; rows no longer present are deleted, which fails loudly if a stored
    run still cites them."""
    ids = [p.id for p in paragraphs]
    conn.execute(
        "DELETE FROM paragraphs WHERE document_id = %s AND NOT (id = ANY(%s))",
        (document_id, ids),
    )
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO paragraphs (id, document_id, page, ordinal, heading, text)
            VALUES (%(id)s, %(document_id)s, %(page)s, %(ordinal)s, %(heading)s, %(text)s)
            ON CONFLICT (id) DO UPDATE SET
                document_id = EXCLUDED.document_id,
                page = EXCLUDED.page,
                ordinal = EXCLUDED.ordinal,
                heading = EXCLUDED.heading,
                text = EXCLUDED.text
            """,
            [p.model_dump() for p in paragraphs],
        )


def list_paragraphs(conn: Connection, document_id: str | None = None) -> list[Paragraph]:
    """Paragraphs in reading order (document, page, ordinal)."""
    with conn.cursor(row_factory=class_row(Paragraph)) as cur:
        cur.execute(
            "SELECT id, document_id, page, ordinal, heading, text FROM paragraphs "
            "WHERE %(doc)s::text IS NULL OR document_id = %(doc)s "
            "ORDER BY document_id, page, ordinal",
            {"doc": document_id},
        )
        return cur.fetchall()
