"""What the model returns in pass 1 (`ExtractionResult`), and the claim drafts it becomes.

The schema enforces the ontology: node and edge types are enums, and a model validator
rejects unknown properties, values of the wrong type, enum values outside the list,
dangling local IDs and edges between the wrong types. A rejected answer goes back to the
model once with the errors (app/llm), so these rules double as feedback.

Whether each quote is verbatim and states its value is pass 2's job (app/verify).
"""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from app.domain.claims import ClaimKind
from app.domain.ontology import (
    ASSET,
    ASSET_LOCAL_ID,
    EdgeType,
    NodeType,
    PropertySpec,
    load_ontology,
)

PropertyValue = float | int | str | list[str]


class Cited(BaseModel):
    paragraph_id: str  # one of the IDs given in the prompt
    quote: str  # copied character for character: the shortest span that states the value


class PropertyClaim(Cited):
    name: str  # a property of the entity's type in ontology.yaml
    value: PropertyValue


class Entity(BaseModel):
    local_id: str  # unique within this document; "asset" is reserved for the Asset
    type: NodeType
    name: str | None
    properties: list[PropertyClaim]


class Relation(Cited):
    type: EdgeType
    source_local_id: str  # an entity's local_id, or "asset"
    target_local_id: str
    role: str | None  # PARTY_TO only


class ExtractionResult(BaseModel):
    # Export capacity and technology belong to the Asset, whichever document states them.
    asset_properties: list[PropertyClaim]
    entities: list[Entity]
    relations: list[Relation]

    @model_validator(mode="after")
    def _follows_the_ontology(self) -> Self:
        ontology = load_ontology()
        errors: list[str] = []

        types: dict[str, str] = {ASSET_LOCAL_ID: ASSET}
        for entity in self.entities:
            if entity.local_id == ASSET_LOCAL_ID:
                errors.append('local_id "asset" is reserved for the Asset')
            elif entity.local_id in types:
                errors.append(f"local_id {entity.local_id!r} is used twice")
            types[entity.local_id] = entity.type

        owners = [(ASSET, ASSET_LOCAL_ID, self.asset_properties)] + [
            (e.type, e.local_id, e.properties) for e in self.entities
        ]
        for node_type, local_id, claims in owners:
            specs = ontology.nodes[node_type].properties
            for claim in claims:
                spec = specs.get(claim.name)
                if spec is None:
                    errors.append(
                        f"{local_id}: {node_type} has no property {claim.name!r}; "
                        f"allowed: {', '.join(specs)}"
                    )
                elif problem := _value_problem(spec, claim.value):
                    errors.append(f"{local_id}.{claim.name}: {problem}")

        for rel in self.relations:
            where = f"{rel.type} {rel.source_local_id} -> {rel.target_local_id}"
            edge = ontology.edges[rel.type]
            source, target = types.get(rel.source_local_id), types.get(rel.target_local_id)
            if source is None or target is None:
                errors.append(f"{where}: unknown local_id")
                continue
            if source not in edge.sources:
                errors.append(f"{where}: source must be {' or '.join(edge.sources)}")
            if target not in edge.targets:
                errors.append(f"{where}: target must be {' or '.join(edge.targets)}")
            role_spec = edge.properties.get("role")
            if role_spec is None and rel.role is not None:
                errors.append(f"{where}: only PARTY_TO has a role")
            if role_spec is not None and (
                rel.role is None or rel.role not in (role_spec.values or [])
            ):
                errors.append(f"{where}: role must be one of {', '.join(role_spec.values or [])}")

        if errors:
            raise ValueError("does not follow the ontology:\n- " + "\n- ".join(errors))
        return self


def _value_problem(spec: PropertySpec, value: PropertyValue) -> str | None:
    values = value if isinstance(value, list) else [value]
    if isinstance(value, list) and not spec.many:
        return "takes one value, not a list"
    if spec.many and not isinstance(value, list):
        return "takes a list of values"
    for v in values:
        match spec.type:
            case "number":
                if isinstance(v, bool) or not isinstance(v, int | float):
                    return f"{v!r} is not a number"
            case "date":
                if not isinstance(v, str) or not _is_iso_date(v):
                    return f"{v!r} is not an ISO date (YYYY-MM-DD)"
            case "string":
                if not isinstance(v, str) or not v.strip():
                    return f"{v!r} is not text"
            case "enum":
                if v not in (spec.values or []):
                    return f"{v!r} is not one of {', '.join(spec.values or [])}"
    return None


def _is_iso_date(text: str) -> bool:
    try:
        return date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


class ClaimDraft(BaseModel):
    """One property or edge claim from pass 1, flattened and waiting for the verifier."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    kind: ClaimKind
    local_ref: dict[str, JsonValue]  # {"local_id", "type", "name"}
    property: str | None
    edge_type: str | None
    target_ref: dict[str, JsonValue] | None
    value: JsonValue  # the property value, or the PARTY_TO role
    paragraph_id: str
    quote: str
