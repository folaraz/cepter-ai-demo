"""API response models. Each mirrors a type in design/api/types.ts, field for field."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.findings import Result, Severity

ReviewState = Literal["ai_extracted", "needs_review", "lawyer_verified", "corrected", "rejected"]
QuoteStatus = Literal["verified", "corroborated", "conflict"]
EvalState = Literal["passing", "stale", "running", "failing"]


class Health(BaseModel):
    """Operational status; not part of the UI contract."""

    status: Literal["ok", "degraded"]  # degraded: the database is unreachable
    published_run: str | None  # id of the live published run, if any
    recordings: int  # committed model recordings in backend/fixtures/llm/
    embedding_model: str
    ask_live: bool


# ---------- Evidence ----------


class Citation(BaseModel):
    document_id: str
    paragraph_id: str
    page: int
    quote: str


class QuoteEvidence(BaseModel):
    kind: Literal["quote"]
    citation: Citation
    document_title: str
    file_name: str
    role: str
    heading: str
    paragraph_text: str
    quote_start: int
    quote_end: int
    status: QuoteStatus


class MissingEvidence(BaseModel):
    kind: Literal["missing"]
    label: str
    note: str
    expected_by: str
    rfi_id: str | None


Evidence = QuoteEvidence | MissingEvidence


# ---------- Findings ----------


class FindingRow(BaseModel):
    id: str
    check_id: str
    title: str
    severity: Severity
    result: Result
    review: ReviewState
    quote_count: int
    gap_count: int
    source_titles: list[str]


class Finding(FindingRow):
    why: str
    how: str
    evidence: list[Evidence]


# ---------- Summary ----------


class Fact(BaseModel):
    key: str
    label: str
    value: str
    status: QuoteStatus
    finding_id: str | None  # None: no check tests this fact, so it opens nothing


class DateMark(BaseModel):
    key: str
    label: str
    date: str
    tone: Literal["neutral", "clash", "warning"]
    finding_id: str


class DateClash(BaseModel):
    from_key: str
    to_key: str
    days: int
    label: str
    finding_id: str


class LongHorizonNote(BaseModel):
    text: str
    flag: str
    finding_id: str


class DocumentSummary(BaseModel):
    id: str
    title: str
    file_name: str
    pages: int


class DocumentParty(BaseModel):
    name: str  # display name, "John Hartley"
    role: str  # as the document gives it, "landlord"


class DocumentDate(BaseModel):
    label: str  # "Signed"
    value: str  # "3 Mar 2025"


class DocumentListItem(BaseModel):
    id: str
    title: str
    file_name: str
    pages: int
    parties: list[DocumentParty]  # named in this document, in reading order
    date: DocumentDate | None  # the document's key date, as it states it
    finding_ids: list[str]  # findings (flagged or passed) that quote it, in finding order
    note_count: int  # statements taken from it


class DocumentParagraph(BaseModel):
    id: str
    heading: str  # "" when the paragraph has none
    text: str


class DocumentPage(BaseModel):
    number: int
    paragraphs: list[DocumentParagraph]


class DocumentNote(BaseModel):
    id: str  # "n1", in reading order
    paragraph_id: str
    quote_start: int  # paragraph.text[quote_start:quote_end] is the quote
    quote_end: int
    label: str  # "Export capacity", "Landlord"
    value: str  # "49.9 MW", "John Hartley"
    status: QuoteStatus
    finding_ids: list[str]  # findings whose evidence quotes this span


class DocumentDetail(BaseModel):
    document: DocumentListItem
    pages: list[DocumentPage]  # pages with text, in order
    notes: list[DocumentNote]


class ExpectedDocument(BaseModel):
    label: str
    expected_by: str
    rfi_id: str
    finding_id: str


class EvalStatus(BaseModel):
    state: EvalState
    score: float
    gate: float
    golden_count: int
    corrections_held: int
    corrections_total: int
    citation_validity: float
    cost_gbp: float
    last_run_at: str


class Asset(BaseModel):
    name: str
    subtitle: str
    synthetic: bool


class RunInfo(BaseModel):
    id: str
    at: str
    checks_total: int


class DateWindow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")  # "from" is a Python keyword
    to: str


class PassedCheck(BaseModel):
    check_id: str
    title: str


class Summary(BaseModel):
    asset: Asset
    run: RunInfo
    headline: str
    facts: list[Fact]
    dates: list[DateMark]
    date_window: DateWindow
    clash: DateClash | None  # only when the grid connection clashes with the PPA
    long_horizon: LongHorizonNote | None  # only when the lease falls short
    findings: list[FindingRow]
    passed: list[PassedCheck]
    documents: list[DocumentSummary]
    missing_documents: list[ExpectedDocument]
    eval: EvalStatus


# ---------- RFI ----------


class Rfi(BaseModel):
    id: str
    finding_id: str
    check_id: str
    title: str
    severity: Severity
    request: str
    why: str
    documents_expected: list[str]


# ---------- Review loop ----------


class ReviewRequest(BaseModel):
    action: Literal["accept", "reject", "correct"]
    corrected_result: Result | None = None  # required when action = "correct"
    reason: str | None = None  # required for reject and correct


class ReviewResponse(BaseModel):
    finding: FindingRow
    golden_item_id: str | None  # "corr-002" for reject and correct
    eval: EvalStatus  # "stale" after a new golden item
    undo_token: str


class UndoRequest(BaseModel):
    undo_token: str


# ---------- Ask (design/api/ask.types.ts) ----------

AskRoute = Literal["lookup", "relationship", "out_of_scope"]
AskStatus = Literal["answered", "abstained", "unavailable"]


class AskRequest(BaseModel):
    question: str  # 3–500 characters


class AskSentence(BaseModel):
    text: str
    citations: list[QuoteEvidence]  # verified quotes
    finding_id: str | None  # only on template sentences that state an absence


class AskResponse(BaseModel):
    id: str
    question: str
    route: AskRoute | None  # null when unavailable
    status: AskStatus
    sentences: list[AskSentence]  # empty unless answered
    message: str | None  # shown instead of sentences when abstained or unavailable
    related_finding_id: str | None
    related_rfi_id: str | None
    dropped_sentences: int
    mode: Literal["replay", "live", "cache"]
    latency_ms: int
    cost_gbp: float


class AskSuggestion(BaseModel):
    id: str  # golden item ID, e.g. "a01"
    question: str
    route: AskRoute
