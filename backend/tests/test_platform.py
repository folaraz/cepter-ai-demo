"""C0: settings, migrations and /api/health."""

from collections.abc import Callable, Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import RECORDINGS_DIR, Settings, get_settings
from app.db.migrate import migrate
from app.main import app

TABLES = {
    "documents",
    "paragraphs",
    "chunks",
    "runs",
    "llm_calls",
    "claims",
    "nodes",
    "edges",
    "provenance",
    "findings",
    "reviews",
    "asks",
    "eval_runs",
}


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("LLM_MODE", "LLM_MODEL", "ASK_LIVE", "EVAL_GATE", "COOKIE_SECURE"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.llm_mode == "replay"
    assert s.llm_model == "claude-sonnet-5"
    assert s.ask_live is False
    assert s.eval_gate == 0.90
    assert str(s.embedding_cache_dir) == ".models"


def test_settings_reject_unknown_llm_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODE", "sometimes")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


ClientFor = Callable[[str], TestClient]


@pytest.fixture
def client_for(monkeypatch: pytest.MonkeyPatch) -> Iterator[ClientFor]:
    def make(database_url: str) -> TestClient:
        monkeypatch.setenv("DATABASE_URL", database_url)
        get_settings.cache_clear()
        return TestClient(app)

    yield make
    get_settings.cache_clear()


def test_health_degraded_without_database(client_for: ClientFor) -> None:
    with client_for("postgresql://nobody@127.0.0.1:1/none?connect_timeout=1") as client:
        r = client.get("/api/health")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["published_run"] is None
    assert body["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert body["ask_live"] is False


@pytest.mark.db
def test_migrate_creates_every_table_and_is_idempotent(empty_database: str) -> None:
    migrate(empty_database)
    migrate(empty_database)
    with psycopg.connect(empty_database) as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()
        }
        ext = conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'").fetchone()
    assert tables == TABLES
    assert ext is not None


@pytest.mark.db
def test_health_ok_after_migrate(empty_database: str, client_for: ClientFor) -> None:
    migrate(empty_database)
    with client_for(empty_database) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "published_run": None,
        "recordings": len(list(RECORDINGS_DIR.glob("*.json"))),
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "ask_live": False,
    }


@pytest.mark.db
def test_health_reports_the_published_run(empty_database: str, client_for: ClientFor) -> None:
    migrate(empty_database)
    with psycopg.connect(empty_database) as conn:
        conn.execute(
            "INSERT INTO runs (id, kind, as_of, status) "
            "VALUES ('r-old', 'published', '2026-09-21', 'superseded'), "
            "       ('r-0921-a', 'published', '2026-09-21', 'succeeded')"
        )
    with client_for(empty_database) as client:
        assert client.get("/api/health").json()["published_run"] == "r-0921-a"
