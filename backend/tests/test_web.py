"""C10: FastAPI serves the built UI at / with a fallback to index.html."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ClientFor

NO_DATABASE = "postgresql://nobody@127.0.0.1:1/none?connect_timeout=1"
INDEX = "<!doctype html><div id=root></div>"


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path.parent / "secret.txt").write_text("outside dist", encoding="utf-8")
    return tmp_path


@pytest.fixture
def site(
    dist: Path, client_for: ClientFor, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("FRONTEND_DIST", str(dist))
    with client_for(NO_DATABASE) as client:
        yield client


def test_the_root_serves_the_app(site: TestClient) -> None:
    response = site.get("/")
    assert response.status_code == 200
    assert response.text == INDEX
    assert response.headers["cache-control"] == "no-cache"


def test_ui_routes_fall_back_to_the_app(site: TestClient) -> None:
    for path in ("/findings/F-03", "/requests", "/ask"):
        response = site.get(path)
        assert (response.status_code, response.text) == (200, INDEX), path


def test_built_files_are_served_as_themselves(site: TestClient) -> None:
    script = site.get("/assets/index-abc123.js")
    assert script.text == "console.log(1)"
    assert "immutable" in script.headers["cache-control"]
    assert site.get("/favicon.svg").text == "<svg/>"


def test_api_paths_never_fall_back(site: TestClient) -> None:
    response = site.get("/api/no-such-endpoint")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}
    assert site.get("/api/health").json()["status"] == "degraded"  # the real API still answers


def test_nothing_outside_dist_is_served(site: TestClient) -> None:
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        response = site.get(path)
        assert "outside dist" not in response.text, path


def test_without_a_build_the_api_still_works(
    tmp_path: Path, client_for: ClientFor, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path / "missing"))
    with client_for(NO_DATABASE) as client:
        assert client.get("/").status_code == 404
        assert client.get("/api/health").status_code == 503  # degraded, but served
