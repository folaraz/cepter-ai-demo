from app.checks.impl._values import as_date
from app.checks.render import short_date
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input


@check("grid_before_cod")
def grid_before_cod(inputs: dict[str, Input], view: GraphView) -> Outcome:
    connection = as_date(inputs["connection_date"].value("connection_date"))
    target = as_date(inputs["target_cod"].value("target_cod"))
    long_stop = as_date(inputs["long_stop_date"].value("long_stop_date"))

    context: dict[str, object] = {}
    if connection:
        context["connection_date_short"] = short_date(connection)
    if target:
        context["target_cod_short"] = short_date(target)
    if connection and target:
        context["days"] = (connection - target).days
    if connection and long_stop:
        context["slack_days"] = (long_stop - connection).days

    late = connection is not None and target is not None and connection > target
    return Outcome("fail" if late else "pass", context)
