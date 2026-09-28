"""The `lens` command."""

from collections import Counter

import typer

from app.ask.service import ask
from app.config import get_settings
from app.db.migrate import migrate as apply_schema
from app.db.pool import connect
from app.db.repositories import runs
from app.domain.claims import Claim
from app.domain.runs import RunKind
from app.evals.ask_eval import replay_runner
from app.evals.harness import run_eval
from app.evals.report import format_report
from app.ingest.service import ingest_dataroom
from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.client import MissingRecording
from app.llm.tracing import db_tracer
from app.pipeline import PipelineResult, run_pipeline
from app.retrieval.calibrate import calibrate, read_ask_golden
from app.retrieval.index import build_index
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
def record(
    ask_questions: bool = typer.Option(
        False, "--ask", help="Record Ask's golden questions instead of extraction."
    ),
) -> None:
    """Call the model and save its responses to backend/fixtures/llm/. Needs
    ANTHROPIC_API_KEY. Commit the recordings afterwards.

    Without --ask: one extraction call per document. With --ask: the routing and answer
    calls for every question in evals/ask_golden.jsonl, against the published run (run
    `lens run --publish` and `lens index` first)."""
    with connect(get_settings().database_url) as conn:
        if not ask_questions:
            ingest_dataroom(conn)
            llm = AnthropicLLMClient(trace=db_tracer(conn))
            _report(run_pipeline(conn, llm, mode="record"))
            return
        for item in read_ask_golden():
            answer = ask(
                conn,
                item["question"],
                session_id=None,
                policy="record",
                store=False,
                llm_factory=lambda trace: AnthropicLLMClient(trace=trace),
            )
            typer.echo(f"{item['id']:<4} {answer.route or '-':<13} {answer.status}")


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
    no_ask: bool = typer.Option(False, "--no-ask", help="Skip Ask's golden questions."),
) -> None:
    """Re-run the pipeline in replay mode and score it against the golden set. Exits 1
    when failing: score under the gate, a citation that isn't verbatim, or a correction
    that no longer holds."""
    settings = get_settings()
    with connect(settings.database_url) as conn:
        llm = AnthropicLLMClient(trace=db_tracer(conn), default_mode="replay")
        runner = None if no_ask else replay_runner
        result = run_eval(
            conn, llm, session_id=session, gate=gate or settings.eval_gate, ask_runner=runner
        )
    if as_json:
        typer.echo(result.model_dump_json(indent=2))
    else:
        typer.echo(format_report(result))
    if result.state != "passing":
        raise typer.Exit(1)


@app.command()
def release() -> None:
    """Everything a deploy runs before serving: migrate, ingest, run and publish the
    pipeline, index the paragraphs for Ask, seed the demo's reviews, then the accuracy
    check. Stops at the first
    failure, so a deploy never serves a run that failed its checks."""
    settings = get_settings()
    apply_schema(settings.database_url)
    typer.echo("migrate: schema applied")
    with connect(settings.database_url) as conn:
        changed = [r.document_id for r in ingest_dataroom(conn) if r.changed]
        typer.echo(f"ingest: {', '.join(changed) or 'no changes'}")

        llm = AnthropicLLMClient(trace=db_tracer(conn), default_mode="replay")
        try:
            published = run_pipeline(conn, llm, kind="published", publish=True)
        except MissingRecording as err:
            typer.echo(f"run: {err}", err=True)
            raise typer.Exit(1) from None
        typer.echo(f"run: published {published.run_id}")

        indexed = build_index(conn)
        typer.echo(f"index: {indexed.written} chunks embedded, {indexed.unchanged} unchanged")

        typer.echo(f"seed: {apply_seed(conn, published.run_id)} reviews added")

        result = run_eval(
            conn, llm, session_id=None, gate=settings.eval_gate, ask_runner=replay_runner
        )
        typer.echo(format_report(result))
    if result.state != "passing":
        raise typer.Exit(1)


@app.command()
def index() -> None:
    """Embed every paragraph into the Ask retrieval index (skips unchanged chunks)."""
    with connect(get_settings().database_url) as conn:
        result = build_index(conn)
    typer.echo(f"{result.written} chunks embedded, {result.unchanged} unchanged")


ask_cli = typer.Typer(no_args_is_help=True, help="Ask: questions about the data room.")
app.add_typer(ask_cli, name="ask")


@ask_cli.command("calibrate")
def ask_calibrate() -> None:
    """For every golden Ask question: the best similarity, and where each expected
    paragraph ranks under vector, keyword and hybrid search. Use it to set
    min_similarity in backend/ask.yaml and to check recall before recording."""
    with connect(get_settings().database_url) as conn:
        typer.echo(calibrate(conn))
