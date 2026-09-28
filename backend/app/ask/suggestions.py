"""The suggested questions: golden Ask questions marked `suggested`, in file order. Their
answers are recorded, so they work with no API key."""

from app.api.models import AskSuggestion
from app.retrieval.calibrate import read_ask_golden


def suggestions() -> list[AskSuggestion]:
    return [
        AskSuggestion(id=i["id"], question=i["question"], route=i["route"])
        for i in read_ask_golden()
        if i.get("suggested")
    ]
