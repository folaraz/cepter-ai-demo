from app.checks.render import capitalise, format_number, join_prose, noun_list, number_word
from app.checks.runner import Outcome, check
from app.checks.view import GraphView, Input


@check("export_capacity_consistent")
def export_capacity_consistent(inputs: dict[str, Input], view: GraphView) -> Outcome:
    group = inputs["export_capacity"].groups.get("export_capacity_mw")
    if group is None:
        return Outcome("missing_evidence", {})

    def noun(document_id: str) -> str:
        return view.documents[document_id].noun

    majority, *others = group.values  # corroborated values come first
    context: dict[str, object] = {
        "majority_value": format_number(float(majority.value)),  # type: ignore[arg-type]
        "majority_count_word": number_word(len(majority.documents)),
        # "two documents", or the one document's noun: never "one documents".
        "majority_where": (
            f"{number_word(len(majority.documents))} documents"
            if len(majority.documents) > 1
            else noun(majority.documents[0])
        ),
        "majority_docs_text": noun_list([noun(d) for d in majority.documents]),
        "source_count_word": capitalise(number_word(sum(len(v.documents) for v in group.values))),
    }
    if others:
        minority = others[0]
        high, low = float(majority.value), float(minority.value)  # type: ignore[arg-type]
        context |= {
            "minority_value": format_number(low),
            "minority_doc": join_prose([noun(d) for d in minority.documents]),
            "overstatement_pct": round((high - low) / high * 100),
        }
    # Refuse to guess: several values is a conflict for a reviewer, never a pick.
    return Outcome("conflict" if others else "pass", context)
