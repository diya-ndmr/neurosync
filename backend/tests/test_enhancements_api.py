from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import enhancements
from app.api import assessments as assessments_api
from app.api import wellbeing as wellbeing_api
from app.database.connection import Base, get_db
from app.middleware.security import get_current_user
from app.models.module import Module
from app.models.student import StudentProfile
from app.models.user import User, UserRole


@pytest.fixture
def enhancements_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'enhancements.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    db.add_all([
        User(id="student-user", name="Student One", email="student1@example.edu", password_hash="x", role=UserRole.student),
        User(id="other-user", name="Student Two", email="student2@example.edu", password_hash="x", role=UserRole.student),
        User(id="lecturer-user", name="Lecturer", email="lecturer@example.edu", password_hash="x", role=UserRole.lecturer),
        User(id="advisor-user", name="Advisor", email="advisor@example.edu", password_hash="x", role=UserRole.advisor),
        User(id="admin-user", name="Admin", email="admin@example.edu", password_hash="x", role=UserRole.admin),
        StudentProfile(id="student-one", user_id="student-user", student_number="S001", first_name="Student", surname="One", programme="Computing"),
        StudentProfile(id="student-two", user_id="other-user", student_number="S002", first_name="Student", surname="Two", programme="Computing"),
        Module(id="module-one", module_code="TEST101", module_name="Test Module", faculty="Computing"),
    ])
    db.commit()
    db.close()

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    identity = {"user": _load_user(factory, "lecturer-user")}
    app = FastAPI()
    app.include_router(enhancements.router)
    app.include_router(wellbeing_api.router)
    app.include_router(assessments_api.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: identity["user"]
    client = TestClient(app, raise_server_exceptions=False)
    client.act_as = lambda user_id: identity.update({"user": _load_user(factory, user_id)})  # type: ignore[attr-defined]
    yield client
    client.close()
    engine.dispose()


def _load_user(factory, user_id):
    db = factory()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        profile = user.student_profile
        if profile is not None:
            db.expunge(profile)
        db.expunge(user)
        return user
    finally:
        db.close()


def test_class_attendance_uses_recorded_status_and_excludes_approved_leave(enhancements_client):
    client = enhancements_client
    client.act_as("admin-user")
    for offset, attendance_status in ((10, "present"), (8, "late"), (5, "absent"), (2, "approved_leave")):
        response = client.post("/api/attendance/classes", json={
            "student_id": "student-one",
            "module_id": "module-one",
            "class_name": f"Class {offset}",
            "class_date": (date.today() - timedelta(days=offset)).isoformat(),
            "status": attendance_status,
        })
        assert response.status_code == 201, response.text

    client.act_as("student-user")
    summary = client.get("/api/students/student-one/attendance/summary")
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert data["attendance_rate"] == 67
    assert data["classes_attended"] == 2
    assert data["classes_counted"] == 3
    assert data["excused_absences"] == 1
    assert len(data["records"]) == 4

    forbidden = client.get("/api/students/student-two/attendance/summary")
    assert forbidden.status_code == 403

    client.act_as("admin-user")
    records = client.get("/api/attendance/classes?module_id=module-one")
    assert records.status_code == 200
    record = next(row for row in records.json() if row["status"] == "absent")
    corrected = client.patch(f"/api/attendance/classes/{record['id']}", json={
        "student_id": record["student_id"],
        "module_id": "module-one",
        "class_name": record["class_name"],
        "class_date": record["date"],
        "status": "excused",
    })
    assert corrected.status_code == 200, corrected.text


def test_preferences_are_saved_per_account(enhancements_client):
    client = enhancements_client
    client.act_as("student-user")
    saved = client.put("/api/preferences", json={
        "theme": "dark",
        "accent": "purple",
        "layout": "compact",
        "study_reminders": False,
        "weekly_summary": True,
        "reminder_frequency": "off",
        "text_size": "large",
        "dashboard_order": ["attendance", "recommendations"],
        "preferred_study_start": "20:00",
        "timezone": "Africa/Johannesburg",
    })
    assert saved.status_code == 200, saved.text
    saved_preferences = client.get("/api/preferences").json()
    assert saved_preferences["theme"] == "dark"
    assert saved_preferences["preferred_study_start"] == "20:00"
    assert saved_preferences["timezone"] == "Africa/Johannesburg"

    client.act_as("other-user")
    assert client.get("/api/preferences").json()["theme"] == "light"


def test_student_wellness_appointments_route_is_not_captured_as_a_student_id(enhancements_client):
    client = enhancements_client
    client.act_as("student-user")

    appointments = client.get("/api/wellbeing/appointments")
    assert appointments.status_code == 200, appointments.text
    assert appointments.json() == []

    history = client.get("/api/wellbeing/student-one")
    assert history.status_code == 200, history.text
    assert history.json() == []


def test_topic_recommendations_follow_lecturer_feedback_and_track_resource_activity(enhancements_client, monkeypatch):
    client = enhancements_client
    monkeypatch.setattr(enhancements, "_module_scope", lambda *args: None)
    client.act_as("admin-user")
    topic = client.post("/api/learning/topics", json={
        "module_id": "module-one",
        "name": "Linked lists",
        "description": "Nodes and pointers",
    })
    assert topic.status_code == 201, topic.text
    feedback = client.post("/api/learning/feedback", json={
        "student_id": "student-one",
        "topic_id": topic.json()["id"],
        "strengths": ["arrays"],
        "learning_gaps": ["linked list traversal"],
        "feedback": "Practise traversing a linked list and tracing pointer updates.",
        "learning_goal": "Complete the linked-list exercise",
        "goal_due_date": (date.today() + timedelta(days=7)).isoformat(),
    })
    assert feedback.status_code == 201, feedback.text
    assessment = client.post("/api/assessments", json={
        "student_id": "student-one",
        "module_id": "module-one",
        "assessment_type": "PRACTICE",
        "mark": 42,
        "assessment_date": date.today().isoformat(),
    })
    assert assessment.status_code == 200, assessment.text
    resource = client.post("/api/learning/resources/link", json={
        "topic_id": topic.json()["id"],
        "title": "Linked list practice",
        "description": "Exercises with worked examples",
        "url": "https://example.edu/linked-lists",
    })
    assert resource.status_code == 201, resource.text
    upload = client.post(
        f"/api/learning/resources/upload?topic_id={topic.json()['id']}&title=Lecture%20notes",
        files={"file": ("linked-lists.txt", b"Node and pointer notes", "text/plain")},
    )
    assert upload.status_code == 201, upload.text

    context = client.get("/api/students/student-one/support-context?module_id=module-one")
    assert context.status_code == 200, context.text
    assert context.json()["academic_average"] == 42
    assert "consider discussing academic support" in context.json()["support_suggestion"]

    client.act_as("student-user")
    support = client.get("/api/students/student-one/learning-support")
    assert support.status_code == 200, support.text
    item = support.json()[0]
    assert item["topic"] == "Linked lists"
    assert item["learning_gaps"] == ["linked list traversal"]
    assert item["performance_context"]["module_average"] == 42
    assert item["mastery_claimed"] is False
    assert len(item["resources"]) == 2
    assert "identified as a learning gap" in item["recommendation_explanation"]
    student_context = client.get("/api/students/student-one/support-context?module_id=module-one")
    assert student_context.status_code == 403
    progress = client.patch(f"/api/learning/resources/{resource.json()['id']}/progress", json={"status": "completed"})
    assert progress.status_code == 200, progress.text
    assert progress.json()["status"] == "completed"
    uploaded_resource = next(row for row in item["resources"] if row["resource_type"] == "file")
    downloaded = client.get(uploaded_resource["url"])
    assert downloaded.status_code == 200
    assert downloaded.content == b"Node and pointer notes"
    assert client.get("/api/students/student-two/learning-support").status_code == 403


def test_wellness_booking_requires_referral_and_keeps_student_bookings_private(enhancements_client):
    client = enhancements_client
    client.act_as("student-user")
    assert client.get("/api/wellbeing/slots").status_code == 403

    client.act_as("admin-user")
    referral = client.post("/api/wellbeing/referrals", json={
        "student_id": "student-one",
        "student_message": "Your university recommends speaking with Student Wellness.",
    })
    assert referral.status_code == 201, referral.text
    slot = client.post("/api/wellbeing/slots", json={
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "duration_minutes": 30,
        "location": "Wellness Centre",
    })
    assert slot.status_code == 201, slot.text

    client.act_as("student-user")
    available = client.get("/api/wellbeing/slots")
    assert available.status_code == 200
    booking = client.post("/api/wellbeing/appointments", json={
        "referral_id": referral.json()["id"],
        "slot_id": slot.json()["id"],
    })
    assert booking.status_code == 201, booking.text
    assert booking.json()["status"] == "confirmed"
    booking_id = booking.json()["id"]

    client.act_as("advisor-user")
    follow_up = client.patch(f"/api/wellbeing/appointments/{booking_id}", json={
        "status": "follow_up",
        "follow_up": "Support team to check in next week.",
    })
    assert follow_up.status_code == 200, follow_up.text

    client.act_as("student-user")
    student_booking = client.get("/api/wellbeing/appointments").json()[0]
    assert student_booking["follow_up"] is None
    client.act_as("advisor-user")
    cancelled = client.patch(f"/api/wellbeing/appointments/{booking_id}", json={"status": "cancelled"})
    assert cancelled.status_code == 200, cancelled.text
    client.act_as("student-user")
    assert any(row["id"] == slot.json()["id"] for row in client.get("/api/wellbeing/slots").json())
    rebooking = client.post("/api/wellbeing/appointments", json={
        "referral_id": referral.json()["id"],
        "slot_id": slot.json()["id"],
    })
    assert rebooking.status_code == 201, rebooking.text

    client.act_as("other-user")
    assert client.get("/api/wellbeing/appointments").json() == []
    assert client.get("/api/wellbeing/slots").status_code == 403

    client.act_as("lecturer-user")
    assert client.get("/api/wellbeing/appointments").status_code == 403

    client.act_as("advisor-user")
    referrals = client.get("/api/wellbeing/referrals")
    assert referrals.status_code == 200
    assert referrals.json()[0]["student_id"] == "student-one"
    assert client.get("/api/wellbeing/slots/manage").status_code == 200
    appointments = client.get("/api/wellbeing/appointments")
    assert appointments.status_code == 200
    assert {row["status"] for row in appointments.json()} == {"cancelled", "confirmed"}
