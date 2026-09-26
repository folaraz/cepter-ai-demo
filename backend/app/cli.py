"""The `lens` command."""

import typer

from app.config import get_settings
from app.db.migrate import migrate as apply_schema
from app.db.pool import connect
from app.domain.runs import RunKind
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.client import MissingRecording
from app.llm.tracing import db_tracer
from app.pipeline import PipelineResult, run_pipeline

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """DataRoom Lens backend commands."""


@app.command()
def migrate() -> None:
    """Apply backend/schema.sql to DATABASE_URL (idempotent)."""
    apply_schema(get_settings().database_url)
    typer.echo("schema applied")


@app.command()
def ingest() -> None:
    """Load the data room's PDFs into documents and paragraphs (skips unchanged files)."""
    with connect(get_settings().database_url) as conn:
        results = ingest_dataroom(conn)
    for r in results:
        state = "ingested" if r.changed else "unchanged"
        typer.echo(f"{r.document_id:<10} {r.paragraphs:>3} paragraphs  {state}")
    typer.echo(f"{sum(r.paragraphs for r in results)} paragraphs in {len(results)} documents")


def _report(result: PipelineResult) -> None:
    for document_id, drafts in result.drafts.items():
        properties = sum(d.kind == "property" for d in drafts)
        typer.echo(
            f"{document_id:<10} {properties:>3} properties  {len(drafts) - properties:>3} relations"
        )
    typer.echo(f"run {result.run_id}")


@app.command()
def record() -> None:
    """Call the model for every document and save the responses to backend/fixtures/llm/.
    Needs ANTHROPIC_API_KEY. Commit the recordings afterwards."""
    with connect(get_settings().database_url) as conn:
        ingest_dataroom(conn)
        llm = AnthropicLLMClient(trace=db_tracer(conn))
        _report(run_pipeline(conn, llm, mode="record"))


@app.command()
def run(
    publish: bool = typer.Option(False, help="Make this the run the app serves."),
) -> None:
    """Run the pipeline. Replays recorded model responses unless LLM_MODE says otherwise."""
    with connect(get_settings().database_url) as conn:
        llm = AnthropicLLMClient(trace=db_tracer(conn))
        kind: RunKind = "published" if publish else "eval"
        try:
            result = run_pipeline(conn, llm, kind=kind, publish=publish)
        except MissingRecording as err:
            typer.echo(str(err), err=True)
            raise typer.Exit(1) from None
        _report(result)
