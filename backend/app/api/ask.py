from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from psycopg import Connection

from app.api.deps import connection
from app.api.models import AskRequest, AskResponse, AskSuggestion
from app.api.session import session_id
from app.ask.service import InvalidQuestion, LLMFactory, ask
from app.ask.suggestions import suggestions
from app.llm.anthropic_client import AnthropicLLMClient
from app.published import NoPublishedRun

router = APIRouter()


def default_llm(trace: object) -> AnthropicLLMClient:
    return AnthropicLLMClient(trace=trace)  # type: ignore[arg-type]


@router.post("/ask", response_model=AskResponse)
def post_ask(
    body: AskRequest, request: Request, conn: Annotated[Connection, Depends(connection)]
) -> AskResponse:
    """Not streamed: every sentence is verified before it is sent."""
    factory: LLMFactory = getattr(request.app.state, "ask_llm", default_llm)
    try:
        return ask(conn, body.question, session_id=session_id(request), llm_factory=factory)
    except InvalidQuestion as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from None
    except NoPublishedRun:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No published run yet") from None


@router.get("/ask/suggestions", response_model=list[AskSuggestion])
def get_suggestions() -> list[AskSuggestion]:
    return suggestions()
