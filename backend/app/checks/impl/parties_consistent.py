from app.checks.render import join_prose
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input


@check("parties_consistent")
def parties_consistent(inputs: dict[str, Input], view: GraphView) -> Outcome:
    parties = {
        edge.source_id for key in ("tenant", "customer", "generator") for edge in inputs[key].edges
    }
    if len(parties) <= 1:  # after name normalisation the tenant is one node
        return Outcome("pass", {"names": ""})
    names = sorted(view.node(p).name or view.node(p).key for p in parties)
    return Outcome("fail", {"names": join_prose(names)})
