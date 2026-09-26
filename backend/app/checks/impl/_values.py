"""Small readers shared by the check implementations."""

from datetime import date
from typing import Any

from app.checks.view import GraphView, Input
from app.domain.graph import Node


def as_date(value: Any) -> date | None:
    return date.fromisoformat(value) if isinstance(value, str) else None


def as_number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 February
        return d.replace(year=d.year + years, day=28)


def parcel_numbers(i: Input, view: GraphView) -> list[int]:
    """Numbers of the parcels an edge input reaches."""
    keys = {view.node(e.target_id).key for e in i.edges}
    return sorted(int(k) for k in keys if k.isdigit())


def condition_number(node: Node) -> str | None:
    """ "3" for the node named "Condition 3"."""
    if node.name and node.name.startswith("Condition "):
        return node.name.removeprefix("Condition ")
    return None
