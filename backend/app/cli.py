"""The `lens` command."""

from collections import Counter

import typer

from app.config import get_settings
from app.db.migrate import migrate as apply_schema
from app.db.pool import connect
from app.db.repositories import runs
from app.domain.claims import Claim
from app.domain.runs import RunKind
from app.evals.harness import run_eval
from app.evals.report import format_report
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.client import MissingRecording
from app.llm.tracing import db_tracer
from app.pipeline import PipelineResult, run_pipeline
from app.reviews.golden import export_session_corrections
from app.reviews.seed import apply_seed

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
    by_doc: dict[str, list[Claim]] = {}
    for claim in result.claims:
        by_doc.setdefault(claim.document_id, []).append(claim)
    for document_id, doc_claims in by_doc.items():
        verified = sum(c.status == "verified" for c in doc_claims)
        typer.echo(
            f"{document_id:<10} {verified:>3} verified  {len(doc_claims) - verified:>3} rejected"
        )
    reasons = Counter(c.rejection_reason for c in result.claims if c.rejection_reason)
    for reason, count in sorted(reasons.items()):
        typer.echo(f"  rejected {reason}: {count}")
    typer.echo(f"graph: {result.nodes} nodes, {result.edges} edges")
    for f in result.findings:
        typer.echo(f"{f.id} {f.result:<16} {f.title}")
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


@app.command()
def seed() -> None:
    """Apply backend/seed/reviews.yaml to the published run (idempotent)."""
    with connect(get_settings().database_url) as conn:
        run = runs.get_published_run(conn)
        if run is None:
            typer.echo("no published run; run `lens run --publish` first", err=True)
            raise typer.Exit(1)
        typer.echo(f"{apply_seed(conn, run.id)} seed reviews added")


golden = typer.Typer(no_args_is_help=True, help="The golden set in evals/golden.jsonl.")
app.add_typer(golden, name="golden")


@golden.command("export")
def golden_export(
    session: str = typer.Option(..., help="The session whose corrections to promote."),
) -> None:
    """Append a session's corrections to evals/golden.jsonl, to commit as CI tests."""
    with connect(get_settings().database_url) as conn:
        written = export_session_corrections(conn, session)
    for item in written:
        typer.echo(f"{item['id']} {item['check_id']}: expect {item['expect']}")
    typer.echo(f"{len(written)} corrections appended to evals/golden.jsonl")


@app.command("eval")
def eval_command(
    session: str | None = typer.Option(None, help="Include this session's corrections."),
    gate: float | None = typer.Option(None, help="Passing score; defaults to EVAL_GATE."),
    as_json: bool = typer.Option(False, "--json", help="Print the eval row as JSON."),
    no_ask: bool = typer.Option(False, "--no-ask", help="Skip the Ask metrics (C14)."),
) -> None:
    """Re-run the pipeline in replay mode and score it against the golden set. Exits 1
    when failing: score under the gate, a citation that isn't verbatim, or a correction
    that no longer holds."""
    settings = get_settings()
    with connect(settings.database_url) as conn:
        llm = AnthropicLLMClient(trace=db_tracer(conn), default_mode="replay")
        result = run_eval(conn, llm, session_id=session, gate=gate or settings.eval_gate)
    if as_json:
        typer.echo(result.model_dump_json(indent=2))
    else:
        typer.echo(format_report(result))
    if result.state != "passing":
        raise typer.Exit(1)
