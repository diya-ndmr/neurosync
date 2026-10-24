from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.support_requests import router
from app.database.connection import Base, get_db
from app.middleware.security import get_current_user
from app.models.student import StudentProfile
from app.models.support_request import SupportRequest
from app.models.user import User, UserRole


def make_client(tmp_path, linked=True, role=UserRole.student):
    engine = create_engine(f"sqlite:///{tmp_path / 'support.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = factory()
    user = User(id="student-user", email="student@example.test", password_hash="unused", name="Test Student", role=role)
    db.add(user)
    if linked:
        profile = StudentProfile(id="student-profile", user_id=user.id, student_number="NS-TEST-0001", first_name="Test", surname="Student", programme="Test Programme", year_level=1)
        db.add(profile)
        user.student_profile = profile
    else:
        user.student_profile = None
    db.commit()
    db.close()

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), engine


def test_student_can_submit_support_request(tmp_path):
    client, engine = make_client(tmp_path)
    response = client.post("/api/support-requests", json={"request_type": "Academic support", "message": "I need help planning my assessments."})
    assert response.status_code == 201
    assert response.json()["status"] == "OPEN"
    db = sessionmaker(bind=engine)()
    assert db.query(SupportRequest).count() == 1
    db.close()
    client.close()
    engine.dispose()


def test_support_request_without_profile_returns_not_found(tmp_path):
    client, engine = make_client(tmp_path, linked=False)
    response = client.post("/api/support-requests", json={"request_type": "Academic support", "message": "I need help planning my assessments."})
    assert response.status_code == 404
    assert response.json()["detail"] == "No student profile is linked to this account"
    client.close()
    engine.dispose()


def test_student_cannot_read_staff_support_queue(tmp_path):
    client, engine = make_client(tmp_path)
    response = client.get("/api/support-requests")
    assert response.status_code == 403
    client.close()
    engine.dispose()


def test_advisor_can_list_and_update_support_requests(tmp_path):
    client, engine = make_client(tmp_path, role=UserRole.advisor)
    db = sessionmaker(bind=engine)()
    db.add(SupportRequest(student_id="student-profile", request_type="Academic support", message="I need help with my study plan."))
    db.commit()
    db.close()

    listed = client.get("/api/support-requests?status=OPEN")
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["student_name"] == "Test Student"
    assert item["status"] == "OPEN"

    updated = client.patch(f"/api/support-requests/{item['id']}", json={"status": "IN_PROGRESS"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "IN_PROGRESS"
    client.close()
    engine.dispose()
