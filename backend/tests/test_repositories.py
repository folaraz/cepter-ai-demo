"""C2: every table survives a write and a read through its repository."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest

from app.db.repositories import (
    asks,
    chunks,
    claims,
    documents,
    evals,
    findings,
    graph,
    reviews,
    runs,
)
from app.domain.asks import NewAsk
from app.domain.chunks import Chunk
from app.domain.claims import NewClaim
from app.domain.documents import Document, Paragraph
from app.domain.evals import EvalOutcome, NewEvalRun
from app.domain.findings import FindingRecord
from app.domain.graph import NewEdge, NewProvenance, Node
from app.domain.reviews import NewReview
from app.domain.runs import NewLLMCall

pytestmark = pytest.mark.db

RUN = "r-0921-a"
PARA = "ppa:p4:¶2"
QUOTE = "31 March 2028"
TEXT = f'If Commercial Operation has not occurred by {QUOTE} (the "Long-Stop Date"), ...'

# Tables with a round-trip test below. test_every_table_is_covered keeps this honest.
COVERED = {
    "documents",
    "paragraphs",
    "chunks",
    "runs",
    "llm_calls",
    "claims",
    "nodes",
    "edges",
    "provenance",
    "findings",
    "reviews",
    "asks",
    "eval_runs",
}


@pytest.fixture
def db(conn: psycopg.Connection) -> psycopg.Connection:
    """A run, a document and one paragraph, which most other rows reference."""
    documents.upsert_document(
        conn,
        Document(
            id="ppa",
            file_name="ppa.pdf",
            title="Power purchase agreement",
            noun="the PPA",
            paragraph_prefix="ppa",
            pages=5,
            sha256="a" * 64,
        ),
    )
    documents.replace_paragraphs(
        conn,
        "ppa",
        [Paragraph(id=PARA, document_id="ppa", page=4, ordinal=2, heading="3. Term", text=TEXT)],
    )
    runs.create_run(conn, RUN, "published", date(2026, 9, 21), prompt_versions={"x": "x.v1"})
    return conn


def new_claim(**overrides: object) -> NewClaim:
    fields: dict[str, object] = {
        "run_id": RUN,
        "document_id": "ppa",
        "kind": "property",
        "local_ref": {"local_id": "ppa1", "type": "OfftakeAgreement", "name": None},
        "property": "long_stop_date",
        "edge_type": None,
        "target_ref": None,
        "value": "2028-03-31",
        "paragraph_id": PARA,
        "quote": QUOTE,
        "status": "verified",
        "rejection_reason": None,
        "quote_start": TEXT.index(QUOTE),
        "quote_end": TEXT.index(QUOTE) + len(QUOTE),
    }
    return NewClaim.model_validate({**fields, **overrides})


def test_every_table_is_covered(conn: psycopg.Connection) -> None:
    rows = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    assert {r[0] for r in rows.fetchall()} == COVERED


def test_documents_and_paragraphs(db: psycopg.Connection) -> None:
    doc = documents.get_document(db, "ppa")
    assert doc is not None and doc.pages == 5 and doc.title == "Power purchase agreement"
    assert documents.list_documents(db) == [doc]
    [para] = documents.list_paragraphs(db, "ppa")
    assert para.id == PARA and para.heading == "3. Term" and para.text == TEXT


def test_chunks(db: psycopg.Connection) -> None:
    embedding = [0.0] * 383 + [1.0]
    chunk = Chunk(
        paragraph_id=PARA,
        document_id="ppa",
        content=f"Power purchase agreement — 3. Term: {TEXT}",
        embedding=embedding,
        embedding_model="BAAI/bge-small-en-v1.5",
    )
    chunks.upsert_chunks(db, [chunk])
    chunks.upsert_chunks(db, [chunk])  # an upsert, not a duplicate
    assert chunks.list_chunks(db) == [chunk]
    # The generated full-text column is filled in by Postgres.
    hit = db.execute(
        "SELECT paragraph_id FROM chunks WHERE tsv @@ plainto_tsquery('english', 'long stop')"
    ).fetchone()
    assert hit == (PARA,)


def test_runs_and_publishing(db: psycopg.Connection) -> None:
    run = runs.get_run(db, RUN)
    assert run is not None
    assert (run.kind, run.status, run.as_of) == ("published", "running", date(2026, 9, 21))
    assert run.prompt_versions == {"x": "x.v1"}
    assert runs.get_published_run(db) is None

    runs.publish_run(db, RUN)
    runs.create_run(db, "r-0922-a", "published", date(2026, 9, 22))
    runs.publish_run(db, "r-0922-a")

    live = runs.get_published_run(db)
    old = runs.get_run(db, RUN)
    assert live is not None and live.id == "r-0922-a" and live.finished_at is not None
    assert old is not None and old.status == "superseded"


def test_finish_run_records_the_error(db: psycopg.Connection) -> None:
    runs.finish_run(db, RUN, "failed", "extraction failed")
    run = runs.get_run(db, RUN)
    assert run is not None
    assert (run.status, run.error) == ("failed", "extraction failed")
    assert run.finished_at is not None


def test_llm_calls(db: psycopg.Connection) -> None:
    new = NewLLMCall(
        run_id=RUN,
        purpose="extract:ppa",
        model="claude-sonnet-5",
        prompt_version="extract.v1",
        request_hash="b" * 64,
        input_tokens=1200,
        output_tokens=300,
        latency_ms=4100,
        cost_gbp=Decimal("0.01234"),
        replayed=True,
    )
    call = runs.insert_llm_call(db, new)
    assert call.id > 0
    assert runs.list_llm_calls(db, RUN) == [call]
    assert call.model_dump(exclude={"id", "created_at"}) == new.model_dump()


def test_claims(db: psycopg.Connection) -> None:
    verified = new_claim()
    rejected = new_claim(
        quote="30 March 2028",
        status="rejected",
        rejection_reason="quote_not_verbatim",
        quote_start=None,
        quote_end=None,
    )
    edge = new_claim(
        kind="edge",
        property=None,
        edge_type="PARTY_TO",
        target_ref={"local_id": "buyer", "type": "Party", "name": "Northwind Energy Supply"},
        value=None,
    )
    stored = claims.insert_claims(db, [verified, rejected, edge])

    assert [c.model_dump(exclude={"id"}) for c in stored] == [
        c.model_dump() for c in (verified, rejected, edge)
    ]
    assert claims.list_claims(db, RUN) == stored
    assert claims.list_claims(db, RUN, "rejected") == [stored[1]]


def test_nodes_edges_and_provenance(db: psycopg.Connection) -> None:
    [claim] = claims.insert_claims(db, [new_claim()])
    asset = Node(
        id=f"{RUN}:Asset:asset",
        run_id=RUN,
        type="Asset",
        key="asset",
        name="Brackenfield Solar & Storage",
        props={"export_capacity_mw": [49.9, 45]},
    )
    ppa = Node(
        id=f"{RUN}:OfftakeAgreement:ppa",
        run_id=RUN,
        type="OfftakeAgreement",
        key="ppa",
        name=None,
        props={"long_stop_date": "2028-03-31"},
    )
    graph.insert_nodes(db, [asset, ppa])
    assert graph.list_nodes(db, RUN) == [asset, ppa]

    edge = graph.insert_edge(
        db,
        NewEdge(run_id=RUN, type="COVERS", source_id=ppa.id, target_id=asset.id, props={}),
    )
    assert graph.list_edges(db, RUN) == [edge]

    on_node = NewProvenance(
        run_id=RUN,
        node_id=ppa.id,
        edge_id=None,
        property="long_stop_date",
        value="2028-03-31",
        claim_id=claim.id,
        document_id="ppa",
        paragraph_id=PARA,
        quote=QUOTE,
        quote_start=claim.quote_start or 0,
        quote_end=claim.quote_end or 0,
        status="verified",
    )
    on_edge = on_node.model_copy(update={"node_id": None, "edge_id": edge.id, "property": None})
    graph.insert_provenance(db, [on_node, on_edge])
    assert [p.model_dump(exclude={"id"}) for p in graph.list_provenance(db, RUN)] == [
        on_node.model_dump(),
        on_edge.model_dump(),
    ]


def test_findings(db: psycopg.Connection) -> None:
    finding = FindingRecord(
        run_id=RUN,
        id="F-03",
        check_id="export_capacity_consistent",
        severity="high",
        result="conflict",
        title="Export capacity differs between documents",
        why="The grid offer caps export below the permitted capacity.",
        how="Three documents give different figures for the same thing.",
        context={"values": [49.9, 45], "rfi_id": "RFI-03"},
        evidence=[{"kind": "quote", "role": "grid limit", "quote_start": 10, "quote_end": 20}],
        rfi_id="RFI-03",
    )
    findings.insert_findings(db, [finding])
    assert findings.get_finding(db, RUN, "F-03") == finding
    assert findings.list_findings(db, RUN) == [finding]
    assert findings.get_finding(db, RUN, "F-99") is None


def test_reviews_and_undo(db: psycopg.Connection) -> None:
    seed = NewReview(
        session_id=None,
        finding_id="F-07",
        check_id="parties_consistent",
        action="reject",
        corrected_result=None,
        reason="Same person, written two ways.",
        evidence_fingerprint="c" * 64,
        golden_item_id="corr-001",
        undo_token="seed-1",
    )
    mine = NewReview(
        session_id="s-1",
        finding_id="F-03",
        check_id="export_capacity_consistent",
        action="correct",
        corrected_result="fail",
        reason="Grid import and export limits are different things.",
        evidence_fingerprint="d" * 64,
        golden_item_id="corr-002",
        undo_token="tok-1",
    )
    theirs = mine.model_copy(update={"session_id": "s-2", "undo_token": "tok-2"})
    stored = [reviews.insert_review(db, r) for r in (seed, mine, theirs)]
    assert [r.model_dump(exclude={"id", "reverted_at", "created_at"}) for r in stored] == [
        r.model_dump() for r in (seed, mine, theirs)
    ]

    assert [r.undo_token for r in reviews.list_visible_reviews(db, "s-1")] == ["seed-1", "tok-1"]
    assert [r.undo_token for r in reviews.list_visible_reviews(db, None)] == ["seed-1"]

    assert reviews.revert_review(db, "tok-1", "s-2") is None  # not s-2's review
    undone = reviews.revert_review(db, "tok-1", "s-1")
    assert undone is not None and undone.reverted_at is not None
    assert reviews.revert_review(db, "tok-1", "s-1") is None  # already reverted
    assert [r.undo_token for r in reviews.list_visible_reviews(db, "s-1")] == ["seed-1"]


def test_asks(db: psycopg.Connection) -> None:
    new = NewAsk(
        id="ask-1",
        session_id="s-1",
        run_id=RUN,
        question="When is the long-stop date?",
        question_norm="when is the long stop date",
        route="lookup",
        status="answered",
        mode="replay",
        retrieved=[{"paragraph_id": PARA, "vector_rank": 1, "keyword_rank": 1, "rrf": 0.0328}],
        response={"status": "answered", "sentences": [{"text": "31 March 2028."}]},
        dropped=0,
        cost_gbp=Decimal("0.00410"),
        latency_ms=1800,
    )
    stored = asks.insert_ask(db, new)
    assert stored.model_dump(exclude={"created_at"}) == new.model_dump()
    assert asks.get_ask(db, "ask-1") == stored


def test_eval_runs(db: psycopg.Connection) -> None:
    started = evals.start_eval_run(
        db,
        NewEvalRun(
            session_id="s-1",
            run_id=RUN,
            gate=Decimal("0.9000"),
            golden_hash="e" * 64,
            golden_count=21,
        ),
    )
    assert started.state == "running" and started.finished_at is None
    assert started.metrics == {}

    outcome = EvalOutcome(
        state="passing",
        score=Decimal("0.9750"),
        metrics={"extraction": {"passed": 15, "total": 15}},
        corrections_held=2,
        corrections_total=2,
        citation_validity=Decimal("1.0000"),
        cost_gbp=Decimal("0.21000"),
        error=None,
    )
    finished = evals.finish_eval_run(db, started.id, outcome)
    assert finished.model_dump(include=set(EvalOutcome.model_fields)) == outcome.model_dump()
    assert finished.finished_at is not None
    assert evals.get_eval_run(db, started.id) == finished
