"""The Ask retrieval index (`chunks`): one embedded chunk per paragraph."""

from pydantic import BaseModel, ConfigDict


class Chunk(BaseModel):
    """`tsv` is a generated column: never written, and not read back here."""

    model_config = ConfigDict(frozen=True)

    paragraph_id: str
    document_id: str
    content: str  # "{document title} — {heading}: {text}"
    embedding: list[float]
    embedding_model: str  # a different model forces re-embedding
