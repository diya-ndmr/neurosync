"""Regression tests for the record-endpoint, access-control and validation errors.

Each test covers a defect that produced a wrong status code or an unhandled 500:
the untyped ``dict`` bodies, the unique ``module_code`` insert, missing role
checks and cross-student access to academic records.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import assessments as assessments_api
from app.api import attendance as attendance_api
from app.api import modules as modules_api
from app.api import predictions as predictions_api
from app.api import study_sessions as study_sessions_api
from app.api import wellbeing as wellbeing_api
from app.database.connection import Base, get_db
from app.middleware.security import get_current_user
from app.models.module import Module
from app.models.student import StudentProfile
from app.models.user import User, UserRole


@pytest.fixture
def api_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'records.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    db.add_all([
        User(id="u-student", name="Sarah Johnson", email="sarah@university.edu", password_hash="x", role=UserRole.student),
        User(id="u-other", name="Other Student", email="other@university.edu", password_hash="x", role=UserRole.student),
        User(id="u-lecturer", name="Dr. Mark Thompson", email="lecturer@university.edu", password_hash="x", role=UserRole.lecturer),
        User(id="u-admin", name="Prof. James Carter", email="admin@university.edu", password_hash="x", role=UserRole.admin),
        StudentProfile(id="s-1001", user_id="u-student", student_number="NS2024001", first_name="Sarah", surname="Johnson", programme="BSc Computing", year_level=2),
        StudentProfile(id="s-2002", user_id="u-other", student_number="NS2024022", first_name="Liam", surname="Patel", programme="BSc Computing", year_level=2),
        Module(id="m-1", module_code="TST101", module_name="Test Module", faculty="Computing"),
    ])
    db.commit()
    db.close()

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    identity = {"user": _load_user(factory, "u-lecturer")}
    app = FastAPI()
    for module in (attendance_api, assessments_api, study_sessions_api, wellbeing_api, modules_api, predictions_api):
        app.include_router(module.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: identity["user"]

    client = TestClient(app, raise_server_exceptions=False)
    client.act_as = lambda user_id: identity.update({"user": _load_user(factory, user_id)})  # type: ignore[attr-defined]
    yield client
    client.close()
    engine.dispose()


def _load_user(factory, user_id: str) -> User:
    db = factory()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        db.expunge(user)
        return user
    finally:
        db.close()


def test_unknown_and_missing_fields_are_rejected_as_422(api_client):
    """An unknown field used to reach ``Model(**data)`` and raise TypeError (500)."""
    api_client.act_as("u-lecturer")
    cases = [
        ("/api/attendance", {"student_id": "s-1001", "bogus_field": 1}),
        ("/api/assessments", {"bogus": "x"}),
        ("/api/study-sessions", {"bogus": "x"}),
    ]
    for path, payload in cases:
        response = api_client.post(path, json=payload)
        assert response.status_code == 422, f"{path} -> {response.status_code} {response.text}"


def test_out_of_range_values_are_rejected(api_client):
    api_client.act_as("u-lecturer")
    attendance = api_client.post("/api/attendance", json={
        "student_id": "s-1001", "module_id": "m-1", "attendance_percentage": 150, "date": "2026-09-01",
    })
    assert attendance.status_code == 422, attendance.text

    assessment = api_client.post("/api/assessments", json={
        "student_id": "s-1001", "module_id": "m-1", "assessment_type": "EXAM", "mark": -5, "assessment_date": "2026-09-01",
    })
    assert assessment.status_code == 422, assessment.text

    study = api_client.post("/api/study-sessions", json={
        "student_id": "s-1001", "subject": "Revision", "duration_minutes": 0, "activity_type": "READING",
    })
    assert study.status_code == 422, study.text


def test_unknown_student_or_module_is_a_clean_404(api_client):
    api_client.act_as("u-lecturer")
    unknown_student = api_client.post("/api/attendance", json={
        "student_id": "s-9999", "module_id": "m-1", "attendance_percentage": 80, "date": "2026-09-01",
    })
    assert unknown_student.status_code == 404, unknown_student.text
    assert unknown_student.json()["detail"] == "Student not found"

    unknown_module = api_client.post("/api/assessments", json={
        "student_id": "s-1001", "module_id": "m-999", "assessment_type": "EXAM", "mark": 70, "assessment_date": "2026-09-01",
    })
    assert unknown_module.status_code == 404, unknown_module.text
    assert unknown_module.json()["detail"] == "Module not found"


def test_valid_records_for_own_profile_are_created(api_client):
    api_client.act_as("u-lecturer")
    attendance = api_client.post("/api/attendance", json={
        "student_id": "s-1001", "module_id": "m-1", "attendance_percentage": 76.5, "date": "2026-09-01",
    })
    assert attendance.status_code == 200, attendance.text
    assessment = api_client.post("/api/assessments", json={
        "student_id": "s-1001", "module_id": "m-1", "assessment_type": "COURSEWORK", "mark": 68, "assessment_date": "2026-09-02",
    })
    assert assessment.status_code == 200, assessment.text

    api_client.act_as("u-student")
    study = api_client.post("/api/study-sessions", json={
        "student_id": "s-1001", "subject": "Algorithms", "duration_minutes": 45, "activity_type": "PRACTICE",
    })
    assert study.status_code == 200, study.text
    checkin = api_client.post("/api/wellbeing/checkin", json={"student_id": "s-1001", "mood_score": 7, "stress_level": 4})
    assert checkin.status_code == 200, checkin.text
    assert api_client.get("/api/students/s-1001/study-sessions").status_code == 200
    assert api_client.get("/api/wellbeing/s-1001").status_code == 200


def test_students_cannot_read_or_write_another_students_records(api_client):
    api_client.act_as("u-student")
    assert api_client.get("/api/students/s-2002/study-sessions").status_code == 403
    assert api_client.get("/api/students/s-2002/attendance").status_code == 403
    assert api_client.get("/api/students/s-2002/assessments").status_code == 403
    assert api_client.get("/api/wellbeing/s-2002").status_code == 403

    other_study = api_client.post("/api/study-sessions", json={
        "student_id": "s-2002", "subject": "Algorithms", "duration_minutes": 45, "activity_type": "PRACTICE",
    })
    assert other_study.status_code == 403, other_study.text
    other_checkin = api_client.post("/api/wellbeing/checkin", json={"student_id": "s-2002", "mood_score": 5, "stress_level": 5})
    assert other_checkin.status_code == 403, other_checkin.text
    other_prediction = api_client.post("/api/predictions/generate", json={"student_id": "s-2002"})
    assert other_prediction.status_code == 403, other_prediction.text


def test_module_creation_is_admin_only_and_duplicates_are_a_conflict(api_client):
    api_client.act_as("u-student")
    forbidden = api_client.post("/api/modules/", json={"module_code": "NEW101", "module_name": "New Module"})
    assert forbidden.status_code == 403, forbidden.text

    api_client.act_as("u-admin")
    created = api_client.post("/api/modules/", json={"module_code": "new101", "module_name": "New Module"})
    assert created.status_code == 200, created.text

    duplicate = api_client.post("/api/modules/", json={"module_code": "NEW101", "module_name": "New Module"})
    assert duplicate.status_code == 409, duplicate.text
    assert "already exists" in duplicate.json()["detail"]


def test_prediction_request_requires_a_student_id(api_client):
    """A missing student_id answered 404 ("Student not found") before validation."""
    api_client.act_as("u-lecturer")
    assert api_client.post("/api/predictions/generate", json={}).status_code == 422
    generated = api_client.post("/api/predictions/generate", json={"student_id": "s-1001"})
    assert generated.status_code == 200, generated.text
    assert generated.json()["risk_level"] in {"LOW", "MEDIUM", "HIGH"}

