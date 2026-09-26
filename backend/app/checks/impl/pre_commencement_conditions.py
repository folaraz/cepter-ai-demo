from app.checks.impl._values import condition_number
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input


@check("pre_commencement_conditions")
def pre_commencement_conditions(inputs: dict[str, Input], view: GraphView) -> Outcome:
    conditions = sorted(inputs["conditions"].nodes, key=lambda n: int(condition_number(n) or 0))
    undischarged = [c for c in conditions if view.group(c, "discharged_on") is None]
    if not undischarged:
        return Outcome("pass", {})

    first = undischarged[0]  # one finding; the first undischarged condition drives the wording
    context: dict[str, object] = {}
    if number := condition_number(first):
        context["condition_number"] = number
    requires = view.group(first, "requires")
    if requires is not None and requires.value is not None:
        context["condition_subject"] = requires.value
    return Outcome("missing_evidence", context)
