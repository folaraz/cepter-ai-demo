"""Pass 2: decide, in code, which of the model's claims the documents support.

For each claim draft:
1. the cited paragraph exists in the claim's own document, or the claim is rejected
   `no_such_paragraph` (the model only saw that document's paragraphs);
2. the quote is in that paragraph (see normalise.find_quote), or `quote_not_verbatim`;
3. the quote states the claimed value, by the property's `verify` kind in ontology.yaml
   (for an edge, its `verify_edge` rule), or `value_not_in_quote`.

A verified claim's quote becomes paragraph.text[start:end], so what the UI highlights is
always the document's own characters. Rejected claims are kept, with their reason.
"""

import re
from collections.abc import Iterable, Mapping

from pydantic import JsonValue

from app.consolidate.names import is_company, person_name, without_suffix
from app.domain.claims import NewClaim, RejectionReason
from app.domain.documents import Paragraph
from app.domain.extraction import ClaimDraft
from app.domain.ontology import Ontology, PropertySpec
from app.verify.normalise import contains_text, dates_in, find_quote, numbers_in, same_number


def verify_claims(
    drafts: Iterable[ClaimDraft],
    paragraphs: Mapping[str, Paragraph],
    ontology: Ontology,
    run_id: str,
) -> list[NewClaim]:
    drafts = list(drafts)
    known = _entity_facts(drafts)
    return [_verify(d, paragraphs, ontology, known, run_id) for d in drafts]


def _verify(
    draft: ClaimDraft,
    paragraphs: Mapping[str, Paragraph],
    ontology: Ontology,
    known: dict[tuple[str, str, str], str],
    run_id: str,
) -> NewClaim:
    paragraph = paragraphs.get(draft.paragraph_id)
    if paragraph is not None and paragraph.document_id != draft.document_id:
        paragraph = None
    span = find_quote(draft.quote, paragraph.text) if paragraph else None
    reason: RejectionReason | None
    if paragraph is None:
        reason = "no_such_paragraph"
    elif span is None:
        reason = "quote_not_verbatim"
    elif not _value_supported(draft, paragraph.text[span[0] : span[1]], ontology, known):
        reason = "value_not_in_quote"
    else:
        reason = None

    if reason is not None or paragraph is None or span is None:
        return _claim(draft, run_id, draft.quote, reason or "no_such_paragraph", None)
    return _claim(draft, run_id, paragraph.text[span[0] : span[1]], None, span)


def _claim(
    draft: ClaimDraft,
    run_id: str,
    quote: str,
    reason: RejectionReason | None,
    span: tuple[int, int] | None,
) -> NewClaim:
    return NewClaim(
        run_id=run_id,
        document_id=draft.document_id,
        kind=draft.kind,
        local_ref=draft.local_ref,
        property=draft.property,
        edge_type=draft.edge_type,
        target_ref=draft.target_ref,
        value=draft.value,
        paragraph_id=draft.paragraph_id,
        quote=quote,
        status="rejected" if reason else "verified",
        rejection_reason=reason,
        quote_start=span[0] if span else None,
        quote_end=span[1] if span else None,
    )


def _value_supported(
    draft: ClaimDraft, quote: str, ontology: Ontology, known: dict[tuple[str, str, str], str]
) -> bool:
    if draft.kind == "property":
        node_type = str(draft.local_ref["type"])
        spec = ontology.nodes[node_type].properties[str(draft.property)]
        return value_in_quote(spec, draft.value, quote)

    edge = ontology.edges[str(draft.edge_type)]
    role = edge.properties.get("role")
    if role is not None and not value_in_quote(role, draft.value, quote):
        return False
    match edge.verify_edge:
        case "name":
            name = _entity_fact(draft.document_id, draft.local_ref, "name", known)
            return name is not None and name_in_quote(name, quote)
        case "parcel":
            ref = draft.target_ref or {}
            number = _entity_fact(draft.document_id, ref, "number", known)
            return number is not None and parcel_in_quote(number, quote)
        case "quote_only":
            return True


def value_in_quote(spec: PropertySpec, value: JsonValue, quote: str) -> bool:
    """Whether the quote states `value`, by the property's verify kind."""
    values = value if isinstance(value, list) else [value]
    if not values:
        return False
    return all(_one_value_in_quote(spec, v, quote) for v in values)


def _one_value_in_quote(spec: PropertySpec, value: JsonValue, quote: str) -> bool:
    match spec.verify:
        case "number":
            return isinstance(value, int | float) and any(
                same_number(n, float(value)) for n in numbers_in(quote)
            )
        case "date":
            return isinstance(value, str) and value in dates_in(quote)
        case "text":
            return isinstance(value, str) and contains_text(quote, value)
        case "name":
            return isinstance(value, str) and name_in_quote(value, quote)
        case "parcel":
            return isinstance(value, str | int) and parcel_in_quote(str(value), quote)
        case "keywords":
            if not isinstance(value, str):
                return False
            keywords = (spec.keywords or {}).get(value, [])
            return not keywords or any(contains_text(quote, k) for k in keywords)


def name_in_quote(name: str, quote: str) -> bool:
    """Companies: the name without its legal suffix appears. People: the surname appears,
    and so does the first name or its initial."""
    if is_company(name):
        return contains_text(quote, without_suffix(name))
    person = person_name(name)
    if person is None:
        return contains_text(quote, name)
    return _word_in(person.surname, quote) and (
        _word_in(person.first, quote) or _word_in(person.initial, quote)
    )


def parcel_in_quote(number: str, quote: str) -> bool:
    """The parcel number as a whole number: "14" is in "Parcels 14 and 15", not in "140"."""
    digits = re.sub(r"\D", "", number)
    return bool(digits) and re.search(rf"(?<!\d){digits}(?!\d)", quote) is not None


def _word_in(word: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is not None


# ---------- facts about entities, for edge rules ----------


def _entity_facts(drafts: list[ClaimDraft]) -> dict[tuple[str, str, str], str]:
    """(document, local_id, property) -> value for the properties edge rules need: a
    party's name and a parcel's number, as the same document states them."""
    facts: dict[tuple[str, str, str], str] = {}
    for d in drafts:
        if d.kind == "property" and d.property in ("name", "number") and d.value is not None:
            key = (d.document_id, str(d.local_ref["local_id"]), d.property)
            facts.setdefault(key, str(d.value))
    return facts


def _entity_fact(
    document_id: str,
    ref: Mapping[str, JsonValue],
    prop: str,
    known: dict[tuple[str, str, str], str],
) -> str | None:
    """The entity's own property claim if it made one, else the name it was given."""
    stated = known.get((document_id, str(ref.get("local_id")), prop))
    if stated is not None:
        return stated
    name = ref.get("name")
    return name if isinstance(name, str) else None
