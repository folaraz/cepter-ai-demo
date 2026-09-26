"""Thin data access, one module per table group. Plain SQL through psycopg 3; every
function takes a connection and returns Pydantic models from app.domain. Transactions
belong to the caller."""

from typing import Any

from psycopg.types.json import Jsonb
from pydantic import BaseModel


def params(model: BaseModel, *json_fields: str) -> dict[str, Any]:
    """A model as named query parameters, with its jsonb columns wrapped for psycopg."""
    values = model.model_dump()
    for name in json_fields:
        if values[name] is not None:
            values[name] = Jsonb(values[name])
    return values
