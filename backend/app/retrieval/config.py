"""The `retrieval` block of backend/ask.yaml."""

from functools import cache

import yaml
from pydantic import BaseModel

from app.config import ASK_YAML


class RetrievalConfig(BaseModel):
    embedding_model: str
    dimensions: int
    chunk_text: str  # "{document_title} — {heading}: {text}"
    candidates_per_method: int  # top N from vector search and from keyword search
    rrf_k: int  # reciprocal rank fusion: score = sum(1 / (rrf_k + rank))
    top_k: int  # paragraphs given to the answer model
    min_similarity: float  # early-exit threshold (with no keyword hit)
    prompt_order: str


@cache
def retrieval_config() -> RetrievalConfig:
    ask = yaml.safe_load(ASK_YAML.read_text(encoding="utf-8"))
    return RetrievalConfig.model_validate(ask["retrieval"])
