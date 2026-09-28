"""C12: JSON logs with request and run IDs, and the release command."""

import json
import logging
from pathlib import Path

import psycopg
import pytest
from typer.testing import CliRunner

from app.cli import app as cli
from app.config import get_settings
from app.logs import JsonFormatter, run_context
from tests.conftest import ClientFor

NO_DATABASE = "postgresql://nobody@127.0.0.1:1/none?connect_timeout=1"


def line(record: logging.LogRecord) -> dict[str, object]:
    return dict(json.loads(JsonFormatter().format(record)))


def test_log_lines_are_json_with_run_id_and_extras() -> None:
    record = logging.makeLogRecord(
        {"name": "lens.pipeline", "levelname": "INFO", "msg": "pipeline started", "kind": "eval"}
    )
    assert line(record)["run_id"] is None
    with run_context("r-20260927-1"):
        tagged = line(record)
    assert tagged["run_id"] == "r-20260927-1"
    assert (tagged["level"], tagged["logger"], tagged["msg"], tagged["kind"]) == (
        "info",
        "lens.pipeline",
        "pipeline started",
        "eval",
    )
    assert str(tagged["ts"]).endswith("+00:00")


def test_every_request_is_logged_with_its_id(
    client_for: ClientFor, capsys: pytest.CaptureFixture[str]
) -> None:
    with client_for(NO_DATABASE) as client:
        given = client.get("/api/nope", headers={"X-Request-ID": "req-123"})
        fresh = client.get("/api/nope")
    assert given.headers["X-Request-ID"] == "req-123"
    assert len(fresh.headers["X-Request-ID"]) == 32

    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.startswith("{")]
    requests = [x for x in lines if x["logger"] == "lens.http"]
    assert [(x["request_id"], x["path"], x["status"]) for x in requests] == [
        ("req-123", "/api/nope", 404),
        (fresh.headers["X-Request-ID"], "/api/nope", 404),
    ]
    assert all("duration_ms" in x and x["method"] == "GET" for x in requests)


@pytest.mark.db
def test_release_stops_before_serving_without_recordings(
    empty_database: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", empty_database)
    monkeypatch.setattr("app.llm.replay.RECORDINGS_DIR", tmp_path)
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(cli, ["release"])
    finally:
        get_settings.cache_clear()
    assert result.exit_code == 1
    assert "migrate: schema applied" in result.output
    assert "ingest: lease, planning, grid, ppa, site" in result.output
    assert "no recording for extract:" in result.output
    with psycopg.connect(empty_database) as conn:
        published = conn.execute(
            "SELECT count(*) FROM runs WHERE kind = 'published' AND status = 'succeeded'"
        ).fetchone()
    assert published == (0,)  # nothing half-released is served


def test_a_read_without_a_database_is_a_quick_503(client_for: ClientFor) -> None:
    with client_for(NO_DATABASE) as client:
        response = client.get("/api/summary")
    assert response.status_code == 503
    assert response.json() == {"detail": "The database is unavailable"}
