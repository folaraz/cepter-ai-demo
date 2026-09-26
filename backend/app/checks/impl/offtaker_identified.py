from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input


@check("offtaker_identified")
def offtaker_identified(inputs: dict[str, Input], view: GraphView) -> Outcome:
    buyers = [view.node(e.source_id) for e in inputs["buyer"].edges]
    context: dict[str, object] = {}
    if buyers:
        context["buyer_name"] = buyers[0].name or buyers[0].key
    signed = inputs["signed"].value("signed_date") is not None
    return Outcome("pass" if buyers and signed else "missing_evidence", context)
