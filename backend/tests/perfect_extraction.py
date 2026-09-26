"""A hand-written, correct pass-1 answer for each document in the data room.

Tests use it to exercise the verifier and consolidation end to end without recordings:
every quote here is copied from the committed PDFs, and every fact and edge in
data/dataroom/planted_facts.yaml is stated. It is what a perfect extractor would return.
"""

from typing import Any

from app.domain.extraction import ExtractionResult


def _p(name: str, value: Any, paragraph: str, quote: str) -> dict[str, Any]:
    return {"name": name, "value": value, "paragraph_id": paragraph, "quote": quote}


def _e(local_id: str, type_: str, name: str | None, *props: dict[str, Any]) -> dict[str, Any]:
    return {"local_id": local_id, "type": type_, "name": name, "properties": list(props)}


def _r(
    type_: str, source: str, target: str, paragraph: str, quote: str, role: str | None = None
) -> dict[str, Any]:
    return {
        "type": type_,
        "source_local_id": source,
        "target_local_id": target,
        "role": role,
        "paragraph_id": paragraph,
        "quote": quote,
    }


def _parcels(paragraph: str, quote: str, *numbers: str) -> list[dict[str, Any]]:
    return [
        _e(f"p{n}", "LandParcel", f"Parcel {n}", _p("number", n, paragraph, quote)) for n in numbers
    ]


LEASE = {
    "asset_properties": [
        _p(
            "technology",
            ["solar_pv", "bess"],
            "lease:p1:¶2",
            "solar photovoltaic and battery storage",
        ),
    ],
    "entities": [
        _e(
            "hartley",
            "Party",
            "JOHN HARTLEY",
            _p("name", "JOHN HARTLEY", "lease:p1:¶1", "JOHN HARTLEY"),
        ),
        _e(
            "bsl",
            "Party",
            "Brackenfield Solar Limited",
            _p("name", "Brackenfield Solar Limited", "lease:p1:¶1", "Brackenfield Solar Limited"),
        ),
        _e(
            "lease",
            "Lease",
            None,
            _p("start_date", "2026-01-01", "lease:p1:¶5", "1 January 2026"),
            _p("term_years", 35, "lease:p1:¶5", "35 years"),
            _p("signed_date", "2025-12-15", "lease:p1:¶1", "made on 15 December 2025"),
        ),
        *_parcels("lease:p1:¶3", "Parcels 9, 10 and 11", "9", "10", "11"),
    ],
    "relations": [
        _r(
            "PARTY_TO",
            "hartley",
            "lease",
            "lease:p1:¶1",
            'JOHN HARTLEY of Bracken Farm, Wickham (the "Landlord")',
            "landlord",
        ),
        _r(
            "PARTY_TO",
            "bsl",
            "lease",
            "lease:p1:¶1",
            'Brackenfield Solar Limited, a company registered in England and Wales (the "Tenant")',
            "tenant",
        ),
        *[
            _r("COVERS", "lease", f"p{n}", "lease:p1:¶3", "Parcels 9, 10 and 11")
            for n in (9, 10, 11)
        ],
    ],
}

PLANNING = {
    "asset_properties": [
        _p("export_capacity_mw", 49.9, "planning:p1:¶4", "maximum export capacity of 49.9MW"),
        _p(
            "technology",
            ["solar_pv", "bess"],
            "planning:p1:¶4",
            "solar photovoltaic array and battery energy storage system",
        ),
    ],
    "entities": [
        _e(
            "permit",
            "Permit",
            None,
            _p("reference", "24/00318/FUL", "planning:p1:¶1", "24/00318/FUL"),
            _p("decision_date", "2024-06-12", "planning:p1:¶3", "12 June 2024"),
            _p(
                "authority",
                "Wickham District Council",
                "planning:p2:¶1",
                "Wickham District Council",
            ),
        ),
        _e(
            "bsl",
            "Party",
            "Brackenfield Solar Ltd",
            _p("name", "Brackenfield Solar Ltd", "planning:p1:¶2", "Brackenfield Solar Ltd"),
        ),
        _e(
            "hartley",
            "Party",
            "Mr J. Hartley",
            _p("name", "Mr J. Hartley", "planning:p1:¶2", "Mr J. Hartley"),
        ),
        _e(
            "c1",
            "Condition",
            None,
            _p(
                "condition_type",
                "time_limit",
                "planning:p2:¶2",
                "shall be begun before the expiration of three years",
            ),
            _p("years", 3, "planning:p2:¶2", "three years"),
        ),
        _e(
            "c2",
            "Condition",
            None,
            _p("condition_type", "approved_plans", "planning:p2:¶4", "the approved plans"),
        ),
        _e(
            "c3",
            "Condition",
            None,
            _p(
                "condition_type",
                "temporary_period",
                "planning:p3:¶2",
                "for a limited period of 40 years",
            ),
            _p("years", 40, "planning:p3:¶2", "40 years"),
        ),
        _e(
            "c4",
            "Condition",
            None,
            _p(
                "condition_type",
                "decommissioning",
                "planning:p3:¶4",
                "a scheme for the removal of the development",
            ),
        ),
        _e(
            "c5",
            "Condition",
            None,
            _p(
                "condition_type",
                "pre_commencement",
                "planning:p3:¶6",
                "No development shall commence until",
            ),
            _p(
                "requires",
                "Construction Traffic Management Plan",
                "planning:p3:¶6",
                "a Construction Traffic Management Plan",
            ),
        ),
    ],
    "relations": [
        _r(
            "PARTY_TO",
            "bsl",
            "permit",
            "planning:p1:¶2",
            "Applicant: Brackenfield Solar Ltd",
            "applicant",
        ),
        _r(
            "PARTY_TO",
            "hartley",
            "permit",
            "planning:p1:¶2",
            "Landowner: Mr J. Hartley",
            "landowner",
        ),
        _r(
            "HAS_CONDITION",
            "permit",
            "c1",
            "planning:p2:¶2",
            "The development hereby permitted shall be begun",
        ),
        _r(
            "HAS_CONDITION",
            "permit",
            "c2",
            "planning:p2:¶4",
            "The development shall be carried out in accordance with the approved plans",
        ),
        _r(
            "HAS_CONDITION",
            "permit",
            "c3",
            "planning:p3:¶2",
            "The permission hereby granted shall be for a limited period",
        ),
        _r(
            "HAS_CONDITION",
            "permit",
            "c4",
            "planning:p3:¶4",
            "a scheme for the removal of the development shall be submitted",
        ),
        _r(
            "HAS_CONDITION", "permit", "c5", "planning:p3:¶6", "No development shall commence until"
        ),
    ],
}

GRID = {
    "asset_properties": [
        _p(
            "export_capacity_mw",
            45,
            "grid_offer:p2:¶3",
            "The Maximum Export Capacity at the Point of Connection shall be 45 MW",
        ),
    ],
    "entities": [
        _e(
            "fdn",
            "Party",
            "Fenland Distribution Networks plc",
            _p(
                "name",
                "Fenland Distribution Networks plc",
                "grid_offer:p1:¶2",
                "Fenland Distribution Networks plc",
            ),
        ),
        _e(
            "bsl",
            "Party",
            "Brackenfield Solar Limited",
            _p(
                "name",
                "Brackenfield Solar Limited",
                "grid_offer:p1:¶2",
                "Brackenfield Solar Limited",
            ),
        ),
        _e(
            "gc",
            "GridConnection",
            None,
            _p("reference", "FDN/CO/2024/0917", "grid_offer:p1:¶1", "FDN/CO/2024/0917"),
            _p(
                "connection_date",
                "2029-10-01",
                "grid_offer:p2:¶3",
                "The Connection Date shall be 1 October 2029",
            ),
            _p(
                "substation",
                "Wickham Primary Substation",
                "grid_offer:p2:¶1",
                "Wickham Primary Substation",
            ),
            _p("voltage_kv", 33, "grid_offer:p2:¶1", "33 kV"),
            _p(
                "max_import_capacity_mw",
                20,
                "grid_offer:p2:¶4",
                "The Maximum Import Capacity at the Point of Connection shall be 20 MW",
            ),
        ),
    ],
    "relations": [
        _r(
            "PARTY_TO",
            "fdn",
            "gc",
            "grid_offer:p1:¶2",
            "made by Fenland Distribution Networks plc",
            "network_operator",
        ),
        _r(
            "PARTY_TO", "bsl", "gc", "grid_offer:p1:¶2", "to Brackenfield Solar Limited", "customer"
        ),
    ],
}

PPA = {
    "asset_properties": [
        _p("export_capacity_mw", 49.9, "ppa:p1:¶2", "Contracted Capacity: 49.9 MW"),
        _p(
            "technology",
            ["solar_pv", "bess"],
            "ppa:p1:¶3",
            "solar photovoltaic generating station and co-located battery storage",
        ),
    ],
    "entities": [
        _e(
            "bsl",
            "Party",
            "Brackenfield Solar Limited",
            _p("name", "Brackenfield Solar Limited", "ppa:p1:¶1", "Brackenfield Solar Limited"),
        ),
        _e(
            "nw",
            "Party",
            "Northwind Energy Supply Limited",
            _p(
                "name",
                "Northwind Energy Supply Limited",
                "ppa:p1:¶1",
                "Northwind Energy Supply Limited",
            ),
        ),
        _e(
            "ppa",
            "OfftakeAgreement",
            None,
            _p("target_cod", "2029-03-31", "ppa:p4:¶1", "on or before 31 March 2029"),
            _p(
                "long_stop_date",
                "2029-12-31",
                "ppa:p4:¶2",
                'by 31 December 2029 (the "Long-Stop Date")',
            ),
            _p("term_years", 10, "ppa:p2:¶3", "10 years"),
            _p("price_gbp_per_mwh", 61.5, "ppa:p3:¶1", "£61.50 per MWh"),
            _p(
                "signed_date",
                "2025-03-03",
                "ppa:p5:¶1",
                "Northwind Energy Supply Limited on 3 March 2025",
            ),
        ),
    ],
    "relations": [
        _r(
            "PARTY_TO",
            "bsl",
            "ppa",
            "ppa:p1:¶1",
            'Brackenfield Solar Limited (the "Generator")',
            "generator",
        ),
        _r(
            "PARTY_TO",
            "nw",
            "ppa",
            "ppa:p1:¶1",
            'Northwind Energy Supply Limited (the "Buyer")',
            "buyer",
        ),
    ],
}

SITE = {
    "asset_properties": [],
    "entities": [
        *_parcels("site_plan:p1:¶1", "Parcels 9, 10 and 11", "9", "10", "11"),
        *_parcels("site_plan:p1:¶2", "Parcels 14 and 15", "14", "15"),
    ],
    "relations": [
        *[
            _r("SITE_INCLUDES", "asset", f"p{n}", "site_plan:p1:¶1", "Parcels 9, 10 and 11")
            for n in (9, 10, 11)
        ],
        *[
            _r("CABLE_CROSSES", "asset", f"p{n}", "site_plan:p1:¶2", "Parcels 14 and 15")
            for n in (14, 15)
        ],
    ],
}

PERFECT: dict[str, ExtractionResult] = {
    doc: ExtractionResult.model_validate(answer)
    for doc, answer in {
        "lease": LEASE,
        "planning": PLANNING,
        "grid": GRID,
        "ppa": PPA,
        "site": SITE,
    }.items()
}
