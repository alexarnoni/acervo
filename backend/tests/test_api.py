"""Testes que nao precisam de banco: as queries sao substituidas por stubs."""
import pytest
from fastapi.testclient import TestClient

from app import main, queries


@pytest.fixture(autouse=True)
def stub_queries(monkeypatch):
    main._cache.clear()
    main._hits.clear()
    monkeypatch.setattr(queries, "by_year", lambda: [{"year": 2020, "hours": 1.0, "plays": 2}])
    monkeypatch.setattr(queries, "top_artists", lambda limit: [{"artist_name": "X", "hours": 1.0, "plays": limit}])


client = TestClient(main.app)


def test_get_endpoint_ok():
    r = client.get("/api/by-year")
    assert r.status_code == 200 and r.json()[0]["year"] == 2020


def test_limit_is_validated():
    assert client.get("/api/top-artists?limit=0").status_code == 422
    assert client.get("/api/top-artists?limit=9999").status_code == 422
    assert client.get("/api/top-artists?limit=5").json()[0]["plays"] == 5


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_no_write_endpoints(method):
    assert getattr(client, method)("/api/by-year").status_code == 405


def test_cors_only_allowed_origins():
    ok = client.get("/api/by-year", headers={"Origin": "https://alexarnoni.com"})
    assert ok.headers.get("access-control-allow-origin") == "https://alexarnoni.com"
    bad = client.get("/api/by-year", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 3)
    codes = [client.get("/api/by-year").status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]


def test_no_sensitive_columns_in_schema():
    sql = open("../database/setup_db.sql", encoding="utf-8").read().lower()
    assert "ip_addr" not in sql and "conn_country" not in sql
