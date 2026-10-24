from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import analytics as analytics_api
from app.database.connection import Base, get_db
from app.middleware.security import get_current_user
from app.models.risk_prediction import RiskLevel, RiskPrediction
from app.models.student import StudentProfile
from app.models.user import UserRole


@pytest.fixture
def recovery_client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'recovery.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    recovering = StudentProfile(
        id="student-recovering", user_id="user-recovering", student_number="REC001",
        first_name="Avery", surname="Example", programme="Computing", year_level=2,
    )
    not_sustained = StudentProfile(
        id="student-not-sustained", user_id="user-not-sustained", student_number="REC002",
        first_name="Jordan", surname="Example", programme="Computing", year_level=1,
    )
    watch = StudentProfile(
        id="student-watch", user_id="user-watch", student_number="REC003",
        first_name="Taylor", surname="Example", programme="Data Science", year_level=3,
    )
    no_prediction = StudentProfile(
        id="student-no-prediction", user_id="user-no-prediction", student_number="REC004",
        first_name="Morgan", surname="Example", programme="Computing", year_level=1,
    )
    db.add_all([recovering, not_sustained, watch, no_prediction])
    db.flush()
    now = datetime.now(timezone.utc)
    for index, level in enumerate((RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW)):
        db.add(RiskPrediction(
            id=f"recover-{index}", student_id=recovering.id, risk_score=(85, 55, 20)[index],
            risk_level=level, explanation="Recorded assessment", model_version=f"model-{index}",
            created_at=now + timedelta(days=index),
        ))
    for index, level in enumerate((RiskLevel.HIGH, RiskLevel.LOW, RiskLevel.HIGH)):
        db.add(RiskPrediction(
            id=f"other-{index}", student_id=not_sustained.id, risk_score=70,
            risk_level=level, explanation="Recorded assessment", model_version="model-1",
            created_at=now + timedelta(days=index),
        ))
    db.add(RiskPrediction(
        id="watch-1", student_id=watch.id, risk_score=52,
        risk_level=RiskLevel.MEDIUM, explanation="Recorded assessment", model_version="model-watch",
        created_at=now,
    ))
    db.commit()
    db.close()

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    identity = {"user": SimpleNamespace(id="admin-user", role=UserRole.admin)}
    app = FastAPI()
    app.include_router(analytics_api.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: identity["user"]
    client = TestClient(app)
    client.act_as = lambda role: identity.update({"user": SimpleNamespace(id="test-user", role=role)})  # type: ignore[attr-defined]
    yield client
    client.close()
    engine.dispose()


def test_recovery_endpoint_returns_only_recorded_high_medium_low_sequences(recovery_client):
    response = recovery_client.get("/api/admin/recovering-students")

    assert response.status_code == 200
    payload = response.json()["items"]
    assert len(payload) == 1
    item = payload[0]
    assert item["student_id"] == "student-recovering"
    assert [entry["risk_level"] for entry in item["risk_history"]] == ["HIGH", "MEDIUM", "LOW"]
    assert [entry["risk_score"] for entry in item["risk_history"]] == [85.0, 55.0, 20.0]
    assert [entry["model_version"] for entry in item["risk_history"]] == ["model-0", "model-1", "model-2"]


def test_recovery_endpoint_requires_administrator_role(recovery_client):
    recovery_client.act_as(UserRole.lecturer)

    response = recovery_client.get("/api/admin/recovering-students")

    assert response.status_code == 403


def test_radar_returns_evidenced_categories_and_requires_admin(recovery_client):
    response = recovery_client.get("/api/admin/radar")

    assert response.status_code == 200
    items = response.json()["items"]
    categories = {item["category"] for item in items}
    assert {"IMPROVING", "EMERGING_RISK", "WATCH", "DATA_ISSUE"} <= categories
    assert all(item["evidence"] for item in items)
    improving = next(item for item in items if item["category"] == "IMPROVING")
    assert improving["record_ids"] == ["recover-0", "recover-1", "recover-2"]

    recovery_client.act_as(UserRole.lecturer)
    assert recovery_client.get("/api/admin/radar").status_code == 403


@pytest.mark.parametrize(
    ("question", "expected_category"),
    [
        ("Which students need attention?", "EMERGING_RISK"),
        ("Who is recovering?", "IMPROVING"),
        ("Show data issues", "DATA_ISSUE"),
    ],
)
def test_ask_neurosync_resolves_supported_queries_from_authorized_records(recovery_client, question, expected_category):
    response = recovery_client.post("/api/admin/ask", json={"question": question})

    assert response.status_code == 200
    result = response.json()
    assert result["supported"] is True
    assert result["items"]
    assert any(item["category"] == expected_category for item in result["items"])
    assert all(item["evidence"] for item in result["items"])


def test_ask_neurosync_declines_unsupported_questions(recovery_client):
    response = recovery_client.post("/api/admin/ask", json={"question": "What caused this student's grades to change?"})

    assert response.status_code == 200
    assert response.json()["supported"] is False
    assert response.json()["items"] == []


def test_ask_neurosync_requires_administrator_role(recovery_client):
    recovery_client.act_as(UserRole.lecturer)

    assert recovery_client.post("/api/admin/ask", json={"question": "Who needs attention?"}).status_code == 403