from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from psycopg import Connection

from app.api.deps import connection
from app.api.models import EvalStatus
from app.api.session import session_id
from app.config import get_settings
from app.db.repositories import evals as evals_repo
from app.domain.evals import EvalRun
from app.evals.harness import complete_eval, start_eval
from app.evals.status import eval_status
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.client import LLMClient
from app.llm.tracing import db_tracer

router = APIRouter()


def replay_llm(conn: Connection) -> LLMClient:
    """Evals always replay: no model is called, so a run takes seconds and costs nothing."""
    return AnthropicLLMClient(trace=db_tracer(conn), default_mode="replay")


def _finish(request: Request, started: EvalRun) -> None:
    factory = getattr(request.app.state, "eval_llm", replay_llm)
    with request.app.state.pool.connection() as conn:
        complete_eval(conn, factory(conn), started)


@router.post("/evals/run", response_model=EvalStatus)
def post_eval_run(
    request: Request,
    background: BackgroundTasks,
    conn: Annotated[Connection, Depends(connection)],
) -> EvalStatus:
    """Start re-checking the examples; one run per session at a time. Poll
    GET /api/evals/latest while the state is "running"."""
    session = session_id(request)
    if evals_repo.running_eval(conn, session) is None:
        started = start_eval(conn, session_id=session, gate=get_settings().eval_gate)
        background.add_task(_finish, request, started)
    return eval_status(conn, session)


@router.get("/evals/latest", response_model=EvalStatus)
def get_eval_latest(
    request: Request, conn: Annotated[Connection, Depends(connection)]
) -> EvalStatus:
    return eval_status(conn, session_id(request))
