"""Hybrid retrieval over the chunks (SPEC C13).

- vector:  the top `candidates_per_method` by cosine distance to the question's
           embedding; similarity = 1 - distance.
- keyword: an OR query over the English full-text index, so a natural question matches
           on any content word (plainto_tsquery alone ANDs every word and usually finds
           nothing), ranked by ts_rank_cd, then paragraph ID.
- fusion:  reciprocal rank fusion, score = sum over methods of 1 / (rrf_k + rank), ties
           broken by paragraph ID; the top `top_k` are kept.
"""

from dataclasses import dataclass

from pgvector import Vector
from psycopg import Connection

from app.retrieval.config import retrieval_config
from app.retrieval.embed import embed_query

_KEYWORD_QUERY = "replace(plainto_tsquery('english', %(q)s)::text, '&', '|')::tsquery"


@dataclass(frozen=True)
class Hit:
    paragraph_id: str
    document_id: str
    vector_rank: int | None  # 1-based; None if not in the vector candidates
    keyword_rank: int | None  # 1-based; None if keyword search didn't find it
    similarity: float  # cosine similarity to the question
    rrf: float


@dataclass(frozen=True)
class Retrieval:
    hits: list[Hit]  # the fused top_k, best first
    best_similarity: float  # over all vector candidates
    keyword_found: bool  # keyword search matched anything at all


def vector_search(
    conn: Connection, question: str, limit: int, query: list[float] | None = None
) -> list[tuple[str, str, float]]:
    """(paragraph_id, document_id, similarity), most similar first."""
    rows = conn.execute(
        "SELECT paragraph_id, document_id, 1 - (embedding <=> %(v)s) AS similarity "
        "FROM chunks ORDER BY embedding <=> %(v)s, paragraph_id LIMIT %(n)s",
        {"v": Vector(query or embed_query(question)), "n": limit},
    ).fetchall()
    return [(r[0], r[1], float(r[2])) for r in rows]


def keyword_search(conn: Connection, question: str, limit: int) -> list[tuple[str, str]]:
    """(paragraph_id, document_id), best match first."""
    rows = conn.execute(
        f"SELECT paragraph_id, document_id FROM chunks, (SELECT {_KEYWORD_QUERY} AS q) AS query "
        "WHERE tsv @@ query.q ORDER BY ts_rank_cd(tsv, query.q) DESC, paragraph_id "
        "LIMIT %(n)s",
        {"q": question, "n": limit},
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def search(conn: Connection, question: str, top_k: int | None = None) -> Retrieval:
    """The fused top `top_k` (default from ask.yaml; 0 keeps every candidate)."""
    config = retrieval_config()
    keep = config.top_k if top_k is None else top_k
    query = embed_query(question)
    vector = vector_search(conn, question, config.candidates_per_method, query)
    keyword = keyword_search(conn, question, config.candidates_per_method)

    vector_rank = {pid: i for i, (pid, _, _) in enumerate(vector, start=1)}
    keyword_rank = {pid: i for i, (pid, _) in enumerate(keyword, start=1)}
    similarity = {pid: sim for pid, _, sim in vector}
    document = {pid: doc for pid, doc, _ in vector} | {pid: doc for pid, doc in keyword}

    def fused(pid: str) -> float:
        ranks = [r for r in (vector_rank.get(pid), keyword_rank.get(pid)) if r is not None]
        return sum(1 / (config.rrf_k + r) for r in ranks)

    missing = [pid for pid in document if pid not in similarity]
    similarity |= _similarities(conn, query, missing)
    ranked = sorted(document, key=lambda pid: (-fused(pid), pid))
    ranked = ranked[:keep] if keep else ranked
    hits = [
        Hit(
            paragraph_id=pid,
            document_id=document[pid],
            vector_rank=vector_rank.get(pid),
            keyword_rank=keyword_rank.get(pid),
            similarity=similarity[pid],
            rrf=fused(pid),
        )
        for pid in ranked
    ]
    return Retrieval(
        hits=hits,
        best_similarity=max((s for _, _, s in vector), default=0.0),
        keyword_found=bool(keyword),
    )


def _similarities(conn: Connection, query: list[float], ids: list[str]) -> dict[str, float]:
    """Similarity for keyword-only hits, so every hit reports one."""
    if not ids:
        return {}
    rows = conn.execute(
        "SELECT paragraph_id, 1 - (embedding <=> %(v)s) FROM chunks "
        "WHERE paragraph_id = ANY(%(ids)s)",
        {"v": Vector(query), "ids": ids},
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows}
