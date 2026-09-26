"""Pass 1: one model call per document, returning claim drafts for the verifier (pass 2)."""

from psycopg import Connection

from app.db.repositories import documents
from app.domain.documents import Document, Paragraph
from app.domain.extraction import ClaimDraft, Entity, ExtractionResult
from app.domain.ontology import ASSET, ASSET_LOCAL_ID, load_ontology
from app.extract.prompt import PROMPT_VERSION, system_prompt, user_message
from app.llm.client import LLMClient, Mode


def extract_document(
    llm: LLMClient,
    document: Document,
    paragraphs: list[Paragraph],
    run_id: str,
    mode: Mode | None = None,
) -> ExtractionResult:
    return llm.structured(
        schema=ExtractionResult,
        system=system_prompt(load_ontology()),
        user=user_message(document, paragraphs),
        purpose=f"extract:{document.id}",
        prompt_version=PROMPT_VERSION,
        run_id=run_id,
        mode=mode,
    )


def to_drafts(document_id: str, result: ExtractionResult) -> list[ClaimDraft]:
    """Flatten a result into claims: one per property, one per relation. Each claim keeps
    a reference to the entity it is about, so pass 3 can resolve it to a graph node."""
    refs = {ASSET_LOCAL_ID: {"local_id": ASSET_LOCAL_ID, "type": ASSET, "name": None}}
    refs |= {e.local_id: _ref(e) for e in result.entities}

    owners = [(ASSET_LOCAL_ID, result.asset_properties)]
    owners += [(e.local_id, e.properties) for e in result.entities]
    drafts = [
        ClaimDraft(
            document_id=document_id,
            kind="property",
            local_ref=refs[local_id],
            property=claim.name,
            edge_type=None,
            target_ref=None,
            value=claim.value,
            paragraph_id=claim.paragraph_id,
            quote=claim.quote,
        )
        for local_id, claims in owners
        for claim in claims
    ]
    drafts += [
        ClaimDraft(
            document_id=document_id,
            kind="edge",
            local_ref=refs[rel.source_local_id],
            property=None,
            edge_type=rel.type,
            target_ref=refs[rel.target_local_id],
            value=rel.role,
            paragraph_id=rel.paragraph_id,
            quote=rel.quote,
        )
        for rel in result.relations
    ]
    return drafts


def _ref(entity: Entity) -> dict[str, str | None]:
    return {"local_id": entity.local_id, "type": entity.type, "name": entity.name}


def run_pass1(
    conn: Connection, llm: LLMClient, run_id: str, mode: Mode | None = None
) -> dict[str, list[ClaimDraft]]:
    """Extract every ingested document, in document order."""
    docs = documents.list_documents(conn)
    if not docs:
        raise RuntimeError("no documents; run `lens ingest` first")
    return {
        doc.id: to_drafts(
            doc.id,
            extract_document(llm, doc, documents.list_paragraphs(conn, doc.id), run_id, mode),
        )
        for doc in docs
    }
