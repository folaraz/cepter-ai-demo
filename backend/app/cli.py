"""The `lens` command."""

import psycopg
import typer

from app.config import get_settings
from app.db.migrate import migrate as apply_schema
from app.ingest.service import ingest_dataroom

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
    with psycopg.connect(get_settings().database_url, autocommit=True) as conn:
        results = ingest_dataroom(conn)
    for r in results:
        state = "ingested" if r.changed else "unchanged"
        typer.echo(f"{r.document_id:<10} {r.paragraphs:>3} paragraphs  {state}")
    typer.echo(f"{sum(r.paragraphs for r in results)} paragraphs in {len(results)} documents")
