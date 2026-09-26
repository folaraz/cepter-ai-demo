"""Claims (`claims`): every fact the model proposed in extraction, verified or not."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

ClaimKind = Literal["property", "edge"]
ClaimStatus = Literal["verified", "rejected"]
RejectionReason = Literal["no_such_paragraph", "quote_not_verbatim", "value_not_in_quote"]


class NewClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    document_id: str
    kind: ClaimKind
    local_ref: dict[str, JsonValue]  # the entity as the model named it: local_id, type, name
    property: str | None  # for a property claim
    edge_type: str | None  # for an edge claim
    target_ref: dict[str, JsonValue] | None  # for an edge claim
    value: JsonValue
    paragraph_id: str  # as cited by the model; may not exist
    quote: str
    status: ClaimStatus
    rejection_reason: RejectionReason | None  # set exactly when rejected
    quote_start: int | None  # offsets into the paragraph text, when verified
    quote_end: int | None


class Claim(NewClaim):
    id: int
