"""`chunks`, the Ask retrieval index."""

from pgvector import Vector
from psycopg import Connection
from psycopg.rows import dict_row

from app.domain.chunks import Chunk

_COLUMNS = "paragraph_id, document_id, content, embedding, embedding_model"


def upsert_chunks(conn: Connection, chunks: list[Chunk]) -> None:
    """Insert or replace. `tsv` is generated from `content` by Postgres."""
    with conn.cursor() as cur:
        cur.executemany(
            f"""
            INSERT INTO chunks ({_COLUMNS})
            VALUES (%(paragraph_id)s, %(document_id)s, %(content)s, %(embedding)s,
                    %(embedding_model)s)
            ON CONFLICT (paragraph_id) DO UPDATE SET
                document_id = EXCLUDED.document_id,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model
            """,
            [{**c.model_dump(), "embedding": Vector(c.embedding)} for c in chunks],
        )


def list_chunks(conn: Connection) -> list[Chunk]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_COLUMNS} FROM chunks ORDER BY paragraph_id")
        rows = cur.fetchall()
    # pgvector reads a vector column as its own Vector type.
    return [Chunk(**{**r, "embedding": r["embedding"].to_list()}) for r in rows]
