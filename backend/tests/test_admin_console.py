import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import admin_console
from app.database.connection import Base, get_db
from app.middleware.security import get_current_user
from app.models.audit_event import AuditEvent
from app.models.csv_import_history import CsvImportHistory
from app.models.user import User, UserRole


@pytest.fixture
def admin_client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    session_factory = sessionmaker(bind=test_engine)
    app = FastAPI()
    app.include_router(admin_console.router)

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: User(
        id="admin-id",
        email="admin@example.test",
        password_hash="unused",
        name="Admin",
        role=UserRole.admin,
    )
    with TestClient(app) as client:
        yield client, session_factory
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_model_performance_returns_only_recorded_metrics(admin_client, monkeypatch, tmp_path):
    client, _ = admin_client
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps({
            "best_model": "logistic_regression",
            "evaluated_at": "2025-01-01T00:00:00+00:00",
            "training_data_source": "Synthetic student risk dataset",
            "results": {
                "logistic_regression": {
                    "precision_weighted": 0.81,
                    "recall_weighted": 0.82,
                    "f1_weighted": 0.815,
                },
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(admin_console, "METRICS_PATH", metrics_path)

    response = client.get("/api/admin/model-performance")

    assert response.status_code == 200
    assert response.json() == {
        "model_name": "logistic_regression",
        "precision": 0.81,
        "recall": 0.82,
        "f1_score": 0.815,
        "evaluated_at": "2025-01-01T00:00:00+00:00",
        "training_data_source": "Synthetic student risk dataset",
        "validation_status": "prototype_not_validated_on_real_student_data",
    }


def test_model_performance_does_not_fill_missing_metrics_with_zero(admin_client, monkeypatch, tmp_path):
    client, _ = admin_client
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps({"best_model": "legacy", "results": {"legacy": {"f1_weighted": 0.7}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(admin_console, "METRICS_PATH", metrics_path)

    response = client.get("/api/admin/model-performance")

    assert response.status_code == 200
    assert response.json()["precision"] is None
    assert response.json()["recall"] is None
    assert response.json()["f1_score"] == 0.7
    assert response.json()["evaluated_at"] is None


def test_security_and_integration_status_are_explicitly_unconfigured(admin_client, monkeypatch):
    client, _ = admin_client
    monkeypatch.setattr(admin_console, "is_moodle_configured", lambda: False)
    monkeypatch.setattr(admin_console, "get_safe_moodle_base_url", lambda: None)
    monkeypatch.setattr(admin_console, "_database_status", lambda database_engine: "connected")

    security = client.get("/api/admin/security")
    integrations = client.get("/api/admin/integrations")

    assert security.status_code == 200
    assert security.json()["mfa"]["status"] == "not_integrated"
    assert security.json()["data_retention"]["status"] == "not_configured"
    assert security.json()["encryption"]["encryption_at_rest"] == "not_verifiable_from_application"
    assert integrations.status_code == 200
    assert integrations.json()["moodle"]["sync_available"] is False
    assert integrations.json()["moodle"]["last_successful_sync"] is None


def test_audit_log_is_admin_visible_and_csv_imports_are_listed(admin_client):
    client, session_factory = admin_client
    with session_factory() as db:
        db.add(AuditEvent(
            event_id="csv-event",
            actor_reference="admin@example.test",
            action="CSV_IMPORT_STUDENTS",
            outcome="REJECTED",
        ))
        db.add(AuditEvent(
            event_id="login-event",
            actor_reference="admin@example.test",
            action="LOGIN",
            outcome="SUCCESS",
        ))
        db.add(CsvImportHistory(
            import_id="csv-import",
            actor_id="admin-id",
            dataset="students",
            outcome="REJECTED",
            total_rows=1,
            valid_rows=0,
            invalid_rows=1,
            errors=[{
                "row": 2,
                "field": "email",
                "code": "invalid_email",
                "message": "Enter a valid email address.",
            }],
        ))
        db.commit()

    audit = client.get("/api/admin/audit-events?limit=10")
    imports = client.get("/api/admin/integrations")

    assert audit.status_code == 200
    assert audit.json()["total"] == 2
    assert imports.status_code == 200
    import_history = imports.json()["csv_import_history"][0]
    assert import_history["dataset"] == "students"
    assert import_history["validation_error"] is True
    assert import_history["errors"][0]["code"] == "invalid_email"


def test_admin_console_rejects_non_admin(admin_client):
    client, _ = admin_client
    client.app.dependency_overrides[get_current_user] = lambda: User(
        id="lecturer-id",
        email="lecturer@example.test",
        password_hash="unused",
        name="Lecturer",
        role=UserRole.lecturer,
    )

    response = client.get("/api/admin/security")

    assert response.status_code == 403
