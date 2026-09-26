"""Shared fixtures.

Database tests get a throwaway database created on the server at DATABASE_URL. Locally
they skip when Postgres isn't running; in CI (LENS_REQUIRE_DB=1) they fail instead.
"""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.config import get_settings
from app.db.migrate import migrate
from app.db.pool import connect


def _admin_url() -> str:
    return get_settings().database_url


@pytest.fixture(scope="session")
def db_server() -> str:
    url = _admin_url()
    try:
        psycopg.connect(url, connect_timeout=2).close()
    except psycopg.OperationalError as exc:
        if os.environ.get("LENS_REQUIRE_DB") == "1":
            raise
        pytest.skip(f"no database at DATABASE_URL ({exc.__class__.__name__})")
    return url


@pytest.fixture
def empty_database(db_server: str) -> Iterator[str]:
    """URL of a new, empty database, dropped after the test."""
    name = f"lens_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(db_server, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    params = conninfo_to_dict(db_server)
    params["dbname"] = name
    try:
        yield make_conninfo("", **params)
    finally:
        with psycopg.connect(db_server, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def conn(empty_database: str) -> Iterator[psycopg.Connection]:
    """An autocommit connection to a new database with the schema applied."""
    migrate(empty_database)
    with connect(empty_database) as conn:
        yield conn
