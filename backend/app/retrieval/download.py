"""Fetch the embedding model into EMBEDDING_CACHE_DIR. The Docker build runs this, so a
running container never downloads anything:

    python -m app.retrieval.download
"""

import yaml

from app.config import ASK_YAML, get_settings


def embedding_model_name() -> str:
    ask = yaml.safe_load(ASK_YAML.read_text(encoding="utf-8"))
    return str(ask["retrieval"]["embedding_model"])


def download() -> str:
    from fastembed import TextEmbedding  # heavy import, only when needed

    name = embedding_model_name()
    cache = get_settings().embedding_cache_dir
    cache.mkdir(parents=True, exist_ok=True)
    model = TextEmbedding(model_name=name, cache_dir=str(cache))
    [vector] = list(model.embed(["warm-up"]))  # proves the model loads, offline
    return f"{name}: {len(vector)} dimensions, cached in {cache}"


if __name__ == "__main__":
    print(download())
