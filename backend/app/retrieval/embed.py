"""The local embedding model (fastembed, named in backend/ask.yaml), loaded once per
process from EMBEDDING_CACHE_DIR. Vectors are unit length, so cosine similarity is a
dot product and pgvector's cosine distance is 1 - similarity."""

from collections.abc import Iterable
from functools import cache
from typing import Any

import numpy as np

from app.config import get_settings
from app.retrieval.download import embedding_model_name


@cache
def _model() -> Any:
    from fastembed import TextEmbedding  # heavy import (onnxruntime), only when needed

    cache_dir = get_settings().embedding_cache_dir
    return TextEmbedding(model_name=embedding_model_name(), cache_dir=str(cache_dir))


def _unit(vector: Any) -> list[float]:
    v = np.asarray(vector, dtype=np.float64)
    norm = np.linalg.norm(v)
    return [float(x) for x in (v / norm if norm else v)]


def embed_passages(texts: Iterable[str]) -> list[list[float]]:
    """Document side: the chunks that are searched."""
    return [_unit(v) for v in _model().passage_embed(list(texts))]


def embed_query(text: str) -> list[float]:
    """Question side. bge models embed queries and passages slightly differently."""
    [vector] = list(_model().query_embed(text))
    return _unit(vector)
