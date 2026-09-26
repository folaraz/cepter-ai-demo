"""The Python ontology types stay in step with backend/ontology.yaml."""

from typing import get_args

import yaml

from app.domain.ontology import (
    ASSET,
    ONTOLOGY_YAML,
    EdgeType,
    NodeType,
    PropertyType,
    VerifyKind,
    load_ontology,
)

RAW = yaml.safe_load(ONTOLOGY_YAML.read_text(encoding="utf-8"))


def test_node_types_are_the_extracted_nodes() -> None:
    extracted = [n for n, spec in RAW["nodes"].items() if spec.get("extracted", True)]
    assert list(get_args(NodeType)) == extracted
    assert ASSET in RAW["nodes"] and ASSET not in get_args(NodeType)


def test_edge_types_match() -> None:
    assert list(get_args(EdgeType)) == list(RAW["edges"])


def test_every_property_loads_with_its_type_and_verify_kind() -> None:
    ontology = load_ontology()
    for node_type, raw in RAW["nodes"].items():
        props = ontology.nodes[node_type].properties
        assert list(props) == list(raw["properties"])
        for name, spec in props.items():
            assert spec.type in get_args(PropertyType), f"{node_type}.{name}"
            assert spec.verify in get_args(VerifyKind), f"{node_type}.{name}"
            if spec.type == "enum":
                assert spec.values, f"{node_type}.{name} has no values"
            if spec.verify == "keywords":
                assert set(spec.keywords or {}) == set(spec.values or [])


def test_edges_load_with_endpoints() -> None:
    ontology = load_ontology()
    for edge_type, raw in RAW["edges"].items():
        edge = ontology.edges[edge_type]
        assert edge.sources == raw["from"] and edge.targets == raw["to"]
        assert set(edge.sources + edge.targets) <= set(RAW["nodes"])
    assert "role" in ontology.edges["PARTY_TO"].properties


def test_merge_rules_name_real_nodes() -> None:
    assert set(load_ontology().merge) <= set(get_args(NodeType))
