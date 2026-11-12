"""Tests for the database-aware health endpoint."""

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.v1.endpoints import health
from app.main import app

client = TestClient(app, backend_options={"use_uvloop": True})


def test_health_returns_ok_when_database_is_available(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database_connection", lambda: None)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_service_unavailable_when_database_fails(monkeypatch) -> None:
    def fail_connection() -> None:
        raise OperationalError("SELECT 1", {}, RuntimeError("connection failed"))

    monkeypatch.setattr(health, "check_database_connection", fail_connection)

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}
