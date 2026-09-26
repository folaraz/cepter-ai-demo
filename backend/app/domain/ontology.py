"""The ontology in backend/ontology.yaml: node types, their properties, edge types, and
how each value is verified. tests/test_ontology.py keeps the Literals below in step with
the YAML."""

from functools import cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.config import BACKEND_DIR

ONTOLOGY_YAML = BACKEND_DIR / "ontology.yaml"

# Types the extractor may emit. The Asset is created from the manifest, not extracted.
NodeType = Literal[
    "Party",
    "LandParcel",
    "Lease",
    "Easement",
    "Permit",
    "Condition",
    "GridConnection",
    "OfftakeAgreement",
]
EdgeType = Literal["PARTY_TO", "COVERS", "SITE_INCLUDES", "CABLE_CROSSES", "HAS_CONDITION"]
PropertyType = Literal["number", "date", "string", "enum"]
VerifyKind = Literal["number", "date", "text", "name", "keywords", "parcel"]
EdgeVerifyKind = Literal["name", "parcel", "quote_only"]

ASSET = "Asset"
ASSET_LOCAL_ID = "asset"


class PropertySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: PropertyType
    verify: VerifyKind
    values: list[str] | None = None  # enum values
    keywords: dict[str, list[str]] | None = None  # verify: keywords, per enum value
    many: bool = False  # several values allowed, never a conflict (technology)


class NodeSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    extracted: bool = True
    key: str | None = None  # merge by this property
    properties: dict[str, PropertySpec]


class EdgeSpec(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    sources: list[str] = Field(alias="from")
    targets: list[str] = Field(alias="to")
    properties: dict[str, PropertySpec] = {}
    verify_edge: EdgeVerifyKind


class Ontology(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: int
    nodes: dict[str, NodeSpec]
    edges: dict[str, EdgeSpec]
    merge: dict[str, str]


def read_ontology(path: Path) -> Ontology:
    return Ontology.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@cache
def load_ontology() -> Ontology:
    return read_ontology(ONTOLOGY_YAML)
