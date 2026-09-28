"""The extraction prompt. Any change to the text here changes the recording key, so bump
PROMPT_VERSION and re-record rather than editing a recorded prompt in place.

extract.v2: a PARTY_TO quote must name the party (v1 quotes like 'the "Landlord"' failed
the verifier's name rule); conditions get no number (it is only in headings); a
condition's `requires` is the plan's name, not the surrounding clause."""

from app.domain.documents import Document, Paragraph
from app.domain.ontology import ASSET, ASSET_LOCAL_ID, Ontology, PropertySpec

PROMPT_VERSION = "extract.v2"

RULES = f"""\
You extract facts from one document in the data room for a renewable-energy asset.
The facts feed a legal due-diligence review, and every fact is checked by code against
the document's own words.

Rules:
1. Use only the node types, properties and edge types listed below. Nothing else.
2. Every property and every relation cites exactly one paragraph ID from the list you are
   given, and a quote copied character for character from that paragraph: the shortest
   span that states the value. Never paraphrase, reorder, abbreviate or fix a quote.
3. Export capacity and technology are properties of the Asset, whichever document states
   them: put them in asset_properties. The asset's local_id is "{ASSET_LOCAL_ID}"; use it
   as the source of SITE_INCLUDES and CABLE_CROSSES. Never give an entity that local_id.
4. An import capacity is not an export capacity. The grid offer's Maximum Import Capacity
   is GridConnection.max_import_capacity_mw, never export_capacity_mw.
5. Each land parcel is its own LandParcel entity with its number as the number property.
   A sentence naming several parcels gives one relation per parcel, all citing it.
6. Each party is a Party entity with a name property quoted as written. Link it to the
   agreement or instrument with PARTY_TO and the role the text gives it. A PARTY_TO quote
   must contain both the party's name and the words that give its role, for example
   'ACME SOLAR LIMITED (the "Buyer")', never the role alone.
7. Each planning condition is its own Condition entity, linked from its Permit with
   HAS_CONDITION citing the condition's paragraph. Condition numbers appear only in
   headings, which cannot be quoted, so give a condition no number property.
   A condition's `requires` is only the name of the plan, scheme or document it requires
   (for example "Drainage Strategy"), not the clause around it.
8. Dates as ISO YYYY-MM-DD. Numbers as numbers (3, not "three"). Enum values exactly as
   listed.
9. Extract only what the text states. Never infer a value, and never record that
   something is absent or missing.
"""


def _describe(spec: PropertySpec) -> str:
    if spec.type == "enum":
        values = " | ".join(spec.values or [])
        return f"list of {values}" if spec.many else f"one of {values}"
    return {"number": "number", "date": "ISO date", "string": "text"}[spec.type]


def system_prompt(ontology: Ontology) -> str:
    lines = [RULES, "Node types and their properties:"]
    for node_type, node in ontology.nodes.items():
        label = f"{node_type} (asset_properties only)" if node_type == ASSET else node_type
        lines.append(f"- {label}")
        lines += [f"    {name}: {_describe(spec)}" for name, spec in node.properties.items()]
    lines.append("")
    lines.append("Edge types (source -> target):")
    for edge_type, edge in ontology.edges.items():
        line = f"- {edge_type}: {' | '.join(edge.sources)} -> {' | '.join(edge.targets)}"
        if "role" in edge.properties:
            line += f"; role: {_describe(edge.properties['role'])}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def paragraph_line(p: Paragraph) -> str:
    heading = f"({p.heading}) " if p.heading else ""
    return f"[{p.id}] {heading}{p.text}"


def user_message(document: Document, paragraphs: list[Paragraph]) -> str:
    return "\n".join([f"Document: {document.title}", "", *map(paragraph_line, paragraphs)])
