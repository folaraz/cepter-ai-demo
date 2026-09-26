"""Where traced model calls go: an llm_calls row per call, replayed or not."""

from psycopg import Connection

from app.db.repositories import runs
from app.domain.runs import NewLLMCall
from app.llm.anthropic_client import Tracer


def db_tracer(conn: Connection) -> Tracer:
    def trace(call: NewLLMCall) -> None:
        runs.insert_llm_call(conn, call)

    return trace
