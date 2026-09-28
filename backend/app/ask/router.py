"""Routing a question (SPEC C14 step 3). The model proposes; this module decides.

A relationship route is kept only if its graph query exists in backend/ask.yaml and every
param is one of that query's allowed values. Anything else becomes a lookup.
"""

from dataclasses import dataclass
from typing import Any

from app.domain.ask import RouteDecision, ask_config


@dataclass(frozen=True)
class Route:
    route: str  # lookup | relationship | out_of_scope
    graph_query: str | None
    params: dict[str, Any]


LOOKUP = Route("lookup", None, {})


def validate(decision: RouteDecision) -> Route:
    if decision.route == "out_of_scope":
        return Route("out_of_scope", None, {})
    if decision.route != "relationship":
        return LOOKUP
    query = ask_config().graph_queries.get(decision.graph_query or "")
    if query is None:
        return LOOKUP
    specs = query.get("params") or {}
    params: dict[str, Any] = {}
    for name, value in decision.params.items():
        spec = specs.get(name)
        if spec is None or value not in _allowed_values(spec):
            return LOOKUP
        params[name] = value
    for name, spec in specs.items():  # a param the model left out
        if name not in params:
            if None not in _allowed_values(spec):
                return LOOKUP
            params[name] = None
    return Route("relationship", decision.graph_query, params)


def _allowed_values(spec: dict[str, Any]) -> list[Any]:
    """A list of values, or the keys of a mapping (property_sources' properties)."""
    return list(spec["allowed"])
