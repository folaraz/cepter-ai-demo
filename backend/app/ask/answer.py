"""Lookup answers (SPEC C14 steps 5 and 6): retrieve, draft with the model, then verify
every sentence in code before anyone sees it.

Verification uses the verifier's own functions (app/verify/normalise.py):
- a citation whose paragraph wasn't retrieved, or whose quote isn't verbatim, is dropped;
- a sentence left with no verified citation is dropped;
- a sentence stating a number or date that none of its verified quotes contains is
  dropped ("the lease runs for 40 years" citing "35 years").
Dropped sentences are counted, never shown.
"""

from dataclasses import dataclass, field

from app.api.models import AskSentence, QuoteEvidence
from app.ask.prompts import answer_system, answer_user
from app.domain.ask import AnswerDraft, DraftSentence, ask_config
from app.domain.documents import Paragraph
from app.published import Published, evidence_of
from app.retrieval.search import Hit
from app.verify.normalise import dates_in, find_quote, numbers_in, same_number


@dataclass
class Verified:
    sentences: list[AskSentence] = field(default_factory=list)
    dropped: int = 0


def in_document_order(p: Published, hits: list[Hit]) -> list[Paragraph]:
    paragraphs = [p.view.paragraphs[h.paragraph_id] for h in hits]
    return sorted(paragraphs, key=lambda x: (p.view.doc_rank(x.document_id), x.page, x.ordinal))


def prompt(question: str, paragraphs: list[Paragraph]) -> tuple[str, str]:
    return answer_system(), answer_user(question, paragraphs)


def verify_draft(p: Published, draft: AnswerDraft, retrieved: set[str]) -> Verified:
    limit = ask_config().max_sentences
    result = Verified(dropped=max(0, len(draft.sentences) - limit))
    for sentence in draft.sentences[:limit]:
        kept = verify_sentence(p, sentence, retrieved)
        if kept is None:
            result.dropped += 1
        else:
            result.sentences.append(kept)
    return result


def verify_sentence(
    p: Published, sentence: DraftSentence, retrieved: set[str]
) -> AskSentence | None:
    cites: list[QuoteEvidence] = []
    for c in sentence.citations:
        paragraph = p.view.paragraphs.get(c.paragraph_id)
        if paragraph is None or c.paragraph_id not in retrieved:
            continue
        span = find_quote(c.quote, paragraph.text)
        if span is None:
            continue
        if any(
            x.citation.paragraph_id == c.paragraph_id and (x.quote_start, x.quote_end) == span
            for x in cites
        ):
            continue
        cites.append(_evidence(p, paragraph, span))
    if not cites:
        return None
    quotes = " ".join(c.citation.quote for c in cites)
    quoted_numbers, quoted_dates = numbers_in(quotes), set(dates_in(quotes))
    for n in numbers_in(sentence.text):
        if not any(same_number(n, q) for q in quoted_numbers):
            return None
    if not set(dates_in(sentence.text)) <= quoted_dates:
        return None
    return AskSentence(text=sentence.text.strip(), citations=cites, finding_id=None)


def _evidence(p: Published, paragraph: Paragraph, span: tuple[int, int]) -> QuoteEvidence:
    document = p.view.documents[paragraph.document_id]
    start, end = span
    return QuoteEvidence.model_validate(
        {
            "kind": "quote",
            "citation": {
                "document_id": document.id,
                "paragraph_id": paragraph.id,
                "page": paragraph.page,
                "quote": paragraph.text[start:end],
            },
            "document_title": document.title,
            "file_name": document.file_name,
            "role": "cited in answer",
            "heading": paragraph.heading or "",
            "paragraph_text": paragraph.text,
            "quote_start": start,
            "quote_end": end,
            "status": "verified",
        }
    )


def related(p: Published, cited: set[str]) -> tuple[str | None, str | None]:
    """The lowest-ID finding whose evidence includes every paragraph the answer cites,
    and its RFI."""
    if not cited:
        return None, None
    for finding in p.findings:  # in ID order
        evidence = {
            e["citation"]["paragraph_id"] for e in evidence_of(finding) if e["kind"] == "quote"
        }
        if cited <= evidence:
            return finding.id, finding.rfi_id
    return None, None
