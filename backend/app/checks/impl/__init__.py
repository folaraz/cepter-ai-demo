"""One module per check in backend/checks/; importing this registers them all."""

from app.checks.impl import (
    cable_route_rights,
    export_capacity_consistent,
    grid_before_cod,
    lease_covers_operating_life,
    offtaker_identified,
    parties_consistent,
    permission_in_force,
    pre_commencement_conditions,
)

__all__ = [
    "cable_route_rights",
    "export_capacity_consistent",
    "grid_before_cod",
    "lease_covers_operating_life",
    "offtaker_identified",
    "parties_consistent",
    "permission_in_force",
    "pre_commencement_conditions",
]
