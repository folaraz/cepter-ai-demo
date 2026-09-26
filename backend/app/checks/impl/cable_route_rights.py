from app.checks.impl._values import parcel_numbers
from app.checks.render import parcel_prose, range_dash, range_short
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input
from app.domain.findings import Result


@check("cable_route_rights")
def cable_route_rights(inputs: dict[str, Input], view: GraphView) -> Outcome:
    crossed = parcel_numbers(inputs["cable_route"], view)
    covered = parcel_numbers(inputs["land_rights"], view)
    uncovered = [n for n in crossed if n not in covered]

    context: dict[str, object] = {}
    if crossed:
        context["crossed_parcels"] = parcel_prose(crossed)
        context["uncovered_range"] = range_dash(uncovered)
    if covered:
        context["covered_parcels_short"] = range_short(covered)
    substation = inputs["substation"].value("substation")
    if substation is not None:
        context["substation"] = substation

    # Absence of an easement is not proof there is none: never "fail".
    result: Result = "missing_evidence" if not crossed or uncovered else "pass"
    return Outcome(result, context)
