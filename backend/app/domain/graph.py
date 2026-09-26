"""The consolidated graph: `nodes`, `edges`, and the `provenance` linking each fact in it
to the verified claim that supports it."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

ProvenanceStatus = Literal["verified", "corroborated", "conflict"]


class Node(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str  # "{run_id}:{type}:{key}"
    run_id: str
    type: str
    key: str  # merge key, e.g. a normalised name or a parcel number
    name: str | None  # display name
    props: dict[str, JsonValue]  # consolidated values; a conflict keeps every value


class NewEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    type: str
    source_id: str
    target_id: str
    props: dict[str, JsonValue]  # e.g. {"role": "landlord"} on PARTY_TO


class Edge(NewEdge):
    id: int


class NewProvenance(BaseModel):
    """Supports either a node (and one of its properties, or its identity when property is
    None) or an edge, never both."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    node_id: str | None
    edge_id: int | None
    property: str | None
    value: JsonValue
    claim_id: int
    document_id: str
    paragraph_id: str
    quote: str  # paragraph.text[quote_start:quote_end]
    quote_start: int
    quote_end: int
    status: ProvenanceStatus


class Provenance(NewProvenance):
    id: int
