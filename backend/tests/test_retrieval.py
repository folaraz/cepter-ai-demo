"""C13: the retrieval index and hybrid search, on the real data room and model."""

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from app.db.migrate import migrate
from app.db.pool import connect
from app.db.repositories import chunks as chunks_repo
from app.ingest.service import ingest_dataroom
from app.retrieval.calibrate import calibrate, measure, read_ask_golden
from app.retrieval.config import retrieval_config
from app.retrieval.index import build_index
from app.retrieval.search import keyword_search, search

pytestmark = pytest.mark.db

LOOKUPS = [i for i in read_ask_golden() if i["route"] == "lookup" and i["expect"] == "answer"]
TOP_K = 6


@pytest.fixture(scope="module")
def indexed(db_server: str) -> Iterator[psycopg.Connection]:
    """One indexed data room for the whole module: embedding is the slow part."""
    import uuid

    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    name = f"lens_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(db_server, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = make_conninfo("", **{**conninfo_to_dict(db_server), "dbname": name})
    try:
        migrate(url)
        with connect(url) as conn:
            ingest_dataroom(conn)
            build_index(conn)
            yield conn
    finally:
        with psycopg.connect(db_server, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


# ---------- the index ----------


def test_one_chunk_per_paragraph_in_the_configured_form(indexed: psycopg.Connection) -> None:
    chunks = {c.paragraph_id: c for c in chunks_repo.list_chunks(indexed)}
    assert len(chunks) == 55
    lease_term = chunks["lease:p1:¶5"]
    assert lease_term.content.startswith("Lease, Bracken Farm — 3. Term: The Landlord lets")
    assert lease_term.embedding_model == retrieval_config().embedding_model
    assert len(lease_term.embedding) == retrieval_config().dimensions
    for c in chunks.values():
        assert sum(x * x for x in c.embedding) == pytest.approx(1.0, abs=1e-5)


def test_indexing_again_changes_nothing(indexed: psycopg.Connection) -> None:
    result = build_index(indexed)
    assert (result.written, result.unchanged) == (0, 55)


def test_a_changed_paragraph_is_re_embedded(indexed: psycopg.Connection) -> None:
    before = {c.paragraph_id: c for c in chunks_repo.list_chunks(indexed)}["lease:p1:¶4"]
    indexed.execute("UPDATE paragraphs SET text = text || ' Revised.' WHERE id = 'lease:p1:¶4'")
    try:
        assert build_index(indexed).written == 1
        after = {c.paragraph_id: c for c in chunks_repo.list_chunks(indexed)}["lease:p1:¶4"]
        assert after.content.endswith("Revised.") and after.embedding != before.embedding
    finally:
        indexed.execute(
            "UPDATE paragraphs SET text = replace(text, ' Revised.', '') WHERE id = 'lease:p1:¶4'"
        )
        build_index(indexed)


def test_the_full_text_column_is_generated_by_postgres(indexed: psycopg.Connection) -> None:
    row = indexed.execute(
        "SELECT tsv @@ plainto_tsquery('english', 'long stop date') FROM chunks "
        "WHERE paragraph_id = 'ppa:p4:¶2'"
    ).fetchone()
    assert row == (True,)


# ---------- search ----------


def test_keyword_search_alone_misses_a07(indexed: psycopg.Connection) -> None:
    """The reason retrieval is hybrid: a paraphrase shares no content words with the text."""
    [a07] = [i for i in LOOKUPS if i["id"] == "a07"]
    top = [pid for pid, _ in keyword_search(indexed, a07["question"], TOP_K)]
    assert "lease:p1:¶5" not in top


def _recall_case(item: dict[str, Any]) -> Any:
    if item["id"] != "a07":
        return item
    return pytest.param(
        item,
        marks=pytest.mark.xfail(
            strict=True,
            reason="hybrid ranks lease:p1:¶5 8th: keyword noise ('long', 'land') outranks "
            "vector's rank 6. Vector alone is 8/8. Open decision, see the C13 PR.",
        ),
    )


@pytest.mark.parametrize("item", [_recall_case(i) for i in LOOKUPS], ids=lambda i: i["id"])
def test_hybrid_recall_at_6(indexed: psycopg.Connection, item: dict[str, Any]) -> None:
    hits = [h.paragraph_id for h in search(indexed, item["question"]).hits]
    assert len(hits) == TOP_K
    assert set(item["paragraphs"]) <= set(hits), hits


def test_vector_search_alone_recalls_every_lookup(indexed: psycopg.Connection) -> None:
    for item in LOOKUPS:
        ranks = measure(indexed, item).ranks
        assert all(r.vector is not None and r.vector <= TOP_K for r in ranks), item["id"]


def test_hits_carry_ranks_similarity_and_fused_score(indexed: psycopg.Connection) -> None:
    result = search(indexed, "What price does the PPA pay per MWh?")
    first = result.hits[0]
    assert first.paragraph_id == "ppa:p3:¶1"
    assert (first.vector_rank, first.keyword_rank) == (1, 1)
    k = retrieval_config().rrf_k
    assert first.rrf == pytest.approx(2 / (k + 1))
    assert all(-1 <= h.similarity <= 1 for h in result.hits)
    assert [h.rrf for h in result.hits] == sorted((h.rrf for h in result.hits), reverse=True)
    assert result.keyword_found and result.best_similarity >= first.similarity


def test_early_exit_signals(indexed: psycopg.Connection) -> None:
    """Below min_similarity with no keyword match: abstain without calling the model."""
    threshold = retrieval_config().min_similarity
    x02 = search(indexed, "What is the cap on the EPC contractor's delay liquidated damages?")
    assert not x02.keyword_found and x02.best_similarity < threshold
    for item in LOOKUPS:
        assert search(indexed, item["question"]).best_similarity >= threshold, item["id"]


def test_calibrate_prints_every_golden_question(indexed: psycopg.Connection) -> None:
    table = calibrate(indexed)
    for item in read_ask_golden():
        assert f"\n{item['id']} " in "\n" + table
    assert "a07  lookup" in table and "lease:p1:¶5" in table
