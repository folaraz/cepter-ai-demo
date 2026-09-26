from app.checks.impl._values import add_years, as_date, as_number, condition_number
from app.checks.render import short_date
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input


@check("permission_in_force")
def permission_in_force(inputs: dict[str, Input], view: GraphView) -> Outcome:
    decided = as_date(inputs["decision_date"].value("decision_date"))
    limit = inputs["time_limit"]
    years = as_number(limit.value("years"))

    context: dict[str, object] = {}
    if limit.nodes and (number := condition_number(limit.nodes[0])):
        context["condition_number"] = number
    if decided is None or years is None:
        return Outcome("pass", context)  # the runner reports what is missing

    deadline = add_years(decided, int(years))
    context["deadline_short"] = short_date(deadline)
    # No evidence of commencement exists in this data room, so a passed deadline fails.
    return Outcome("pass" if view.as_of < deadline else "fail", context)
