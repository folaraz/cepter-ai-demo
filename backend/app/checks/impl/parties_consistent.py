from app.checks.render import join_prose
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input

ROLES = ("tenant", "customer", "generator")


@check("parties_consistent")
def parties_consistent(inputs: dict[str, Input], view: GraphView) -> Outcome:
    if not all(inputs[key].edges for key in ROLES):
        # A role without evidence: the runner reports missing evidence. No `names`, so the
        # title can't read as if the parties had been compared.
        return Outcome("missing_evidence", {})
    parties = {edge.source_id for key in ROLES for edge in inputs[key].edges}
    if len(parties) == 1:  # after name normalisation the tenant is one node
        return Outcome("pass", {"names": ""})
    names = sorted(view.node(p).name or view.node(p).key for p in parties)
    return Outcome("fail", {"names": join_prose(names)})
