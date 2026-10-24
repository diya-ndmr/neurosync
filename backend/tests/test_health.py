import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.api import health


@pytest.fixture
def health_client():
    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app)


def test_liveness_does_not_depend_on_database_availability(health_client, monkeypatch):
    def database_probe_must_not_run(database_name, database_engine):
        raise AssertionError(f"liveness unexpectedly probed {database_name}: {database_engine!r}")

    monkeypatch.setattr(health, "_database_is_available", database_probe_must_not_run)

    response = health_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_checks_both_databases(health_client, monkeypatch):
    app_engine = create_engine("sqlite://")
    lms_database_engine = create_engine("sqlite://")
    monkeypatch.setattr(health, "engine", app_engine)
    monkeypatch.setattr(health, "lms_engine", lms_database_engine)

    response = health_client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"application_database": "ready", "lms_database": "ready"},
    }
    app_engine.dispose()
    lms_database_engine.dispose()


def test_readiness_returns_safe_503_when_database_is_unavailable(health_client, monkeypatch, caplog):
    class UnavailableEngine:
        def connect(self):
            raise OperationalError("SELECT 1", {}, RuntimeError("private connection detail"))

    app_engine = create_engine("sqlite://")
    monkeypatch.setattr(health, "engine", UnavailableEngine())
    monkeypatch.setattr(health, "lms_engine", app_engine)

    with caplog.at_level(logging.WARNING):
        response = health_client.get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "not_ready",
            "checks": {"application_database": "unavailable", "lms_database": "ready"},
        }
    }
    assert "private connection detail" not in response.text
    assert "application" in caplog.text
    app_engine.dispose()