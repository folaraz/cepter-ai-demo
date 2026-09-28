"""What a perfect model would answer to Ask's two calls, from evals/ask_golden.jsonl.

- RouteDecision: the golden route, graph query and params; unknown questions are lookups.
- AnswerDraft: for an answerable lookup, one sentence stating every `answer_contains`
  string, each quoted from its expected paragraph; otherwise abstain.
"""

from typing import Any

from app.retrieval.calibrate import read_ask_golden

GOLDEN = {i["question"]: i for i in read_ask_golden()}


def route(question: str) -> dict[str, Any]:
    item = GOLDEN.get(question)
    if item is None or item["route"] == "lookup":
        return {"route": "lookup", "graph_query": None, "params": {}}
    if item["route"] == "out_of_scope":
        return {"route": "out_of_scope", "graph_query": None, "params": {}}
    return {"route": "relationship", "graph_query": item["graph_query"], "params": item["params"]}


def draft(user: str) -> dict[str, Any]:
    question = user.splitlines()[0].removeprefix("Question: ")
    item = GOLDEN.get(question)
    if item is None or item["expect"] != "answer" or item["route"] != "lookup":
        return {"sentences": [], "abstain": True, "abstain_reason": "not stated"}
    [paragraph] = item["paragraphs"]
    facts = item["answer_contains"]
    return {
        "sentences": [
            {
                "text": f"The documents state {' and '.join(facts)}.",
                "citations": [{"paragraph_id": paragraph, "quote": f} for f in facts],
            }
        ],
        "abstain": False,
        "abstain_reason": None,
    }
