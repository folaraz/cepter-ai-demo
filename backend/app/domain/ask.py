"""What the model returns in Ask, and the Ask configuration in backend/ask.yaml.

The model does two things here (SPEC C14): route a question, and draft a lookup answer.
Both are checked by code before anyone sees them.
"""

from functools import cache
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.config import ASK_YAML

Route = Literal["lookup", "relationship", "out_of_scope"]


class RouteDecision(BaseModel):
    """ask.route.v2's answer. Code checks it against ask.yaml; anything not allowed there
    falls back to lookup."""

    route: Route
    graph_query: str | None = Field(description="A graph query ID, for route relationship")
    params: dict[str, str | None] = Field(description="The graph query's parameters")


class DraftCitation(BaseModel):
    paragraph_id: str
    quote: str  # copied exactly from that paragraph


class DraftSentence(BaseModel):
    text: str
    citations: list[DraftCitation]


class AnswerDraft(BaseModel):
    """ask.answer.v1's answer."""

    sentences: list[DraftSentence]  # at most answer.max_sentences
    abstain: bool
    abstain_reason: str | None


class Limits(BaseModel):
    question_chars: dict[str, int]
    live_questions_per_session_per_day: int
    live_daily_budget_gbp: float
    cache_hours: int


class Messages(BaseModel):
    abstain_not_found: str
    abstain_unverified: str
    out_of_scope: str
    unavailable_live_off: str
    unavailable_limit: str


class AskConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    route_prompt_version: str
    answer_prompt_version: str
    max_sentences: int
    limits: Limits
    messages: Messages
    graph_queries: dict[str, dict[str, Any]]


@cache
def ask_config() -> AskConfig:
    raw = yaml.safe_load(ASK_YAML.read_text(encoding="utf-8"))
    return AskConfig(
        route_prompt_version=raw["routing"]["prompt_version"],
        answer_prompt_version=raw["answer"]["prompt_version"],
        max_sentences=raw["answer"]["max_sentences"],
        limits=Limits.model_validate(raw["limits"]),
        messages=Messages.model_validate(raw["messages"]),
        graph_queries=raw["graph_queries"],
    )
