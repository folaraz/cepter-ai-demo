"""Source documents and their paragraphs, as stored in `documents` and `paragraphs`."""

from pydantic import BaseModel, ConfigDict


class ManifestDocument(BaseModel):
    """One entry under `documents:` in data/dataroom/manifest.yaml."""

    model_config = ConfigDict(frozen=True)

    id: str  # short key used in the API: lease, planning, grid, ppa, site
    file: str  # PDF file name under data/dataroom/pdf/
    title: str
    paragraph_prefix: str  # paragraph IDs are "{paragraph_prefix}:p{page}:¶{n}"
    noun: str  # how templates refer to the document in running text
    kind: str  # ontology type of the document's main agreement or instrument


class Document(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    file_name: str
    title: str
    noun: str
    paragraph_prefix: str
    pages: int
    sha256: str  # of the PDF bytes; a change forces re-ingest


class Paragraph(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str  # "grid_offer:p2:¶3"
    document_id: str
    page: int
    ordinal: int  # 1-based, counted per page
    heading: str | None  # the nearest bold heading above, carried across pages
    text: str  # display text: NFKC, whitespace collapsed
