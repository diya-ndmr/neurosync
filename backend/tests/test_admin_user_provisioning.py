from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import admin_users, auth, forgot_password
from app import bootstrap_admin
from app.config.settings import settings
from app.database.connection import Base, get_db
from app.models.audit_event import AuditEvent
from app.models.user import PasswordResetToken, User, UserRole
from app.services.authentication_service import create_access_token, hash_password
from app.services.email_service import EmailDeliveryError


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'admin-users.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(admin_users.router)
    app.include_router(auth.router)
    app.include_router(forgot_password.router)
    app.dependency_overrides[get_db] = override_get_db
    setup_emails = []
    monkeypatch.setattr(settings, "resend_api_key", SecretStr("test-resend-key"))
    monkeypatch.setattr(settings, "frontend_url", "https://portal.example.edu")
    monkeypatch.setattr(admin_users, "send_password_reset_email", lambda email, url: setup_emails.append((email, url)))

    with factory() as db:
        admin = User(
            email="admin@example.edu",
            name="Admin",
            password_hash=hash_password("admin-password"),
            role=UserRole.admin,
        )
        student = User(
            email="student@example.edu",
            name="Student",
            password_hash=hash_password("student-password"),
            role=UserRole.student,
        )
        db.add_all([admin, student])
        db.commit()
        admin_headers = {"Authorization": f"Bearer {create_access_token(admin.id)}"}
        student_headers = {"Authorization": f"Bearer {create_access_token(student.id)}"}

    client = TestClient(app)
    client.admin_headers = admin_headers
    client.student_headers = student_headers
    client.setup_emails = setup_emails
    client.session_factory = factory
    yield client
    client.close()
    engine.dispose()


@pytest.mark.parametrize("role", ["lecturer", "advisor"])
def test_admin_provisions_staff_with_single_use_setup_link(admin_client, role):
    response = admin_client.post(
        "/api/admin/users/provision",
        headers=admin_client.admin_headers,
        json={"name": "New Staff", "email": f"{role}@example.edu", "role": role},
    )

    assert response.status_code == 201, response.text
    assert response.json()["role"] == role
    assert admin_client.setup_emails[0][0] == f"{role}@example.edu"
    setup_token = parse_qs(urlparse(admin_client.setup_emails[0][1]).query)["token"][0]
    changed = admin_client.post(
        "/api/auth/reset-password",
        json={"token": setup_token, "new_password": "new-secure-password"},
    )
    assert changed.status_code == 200, changed.text

    login = admin_client.post(
        "/api/auth/login",
        json={"email": f"{role}@example.edu", "password": "new-secure-password"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["role"] == role

    with admin_client.session_factory() as db:
        audit = db.query(AuditEvent).filter_by(action="ADMIN_PROVISION_STAFF_ACCOUNT").one()
        provisioned = db.query(User).filter_by(email=f"{role}@example.edu").one()
        assert audit.actor_reference == "admin@example.edu"
        assert provisioned.role.value == role
        assert db.query(PasswordResetToken).filter_by(user_id=provisioned.id).count() == 0


def test_staff_provisioning_requires_admin_and_rejects_duplicate_accounts(admin_client):
    payload = {"name": "Lecturer", "email": "lecturer@example.edu", "role": "lecturer"}
    assert admin_client.post("/api/admin/users/provision", json=payload).status_code == 401
    assert admin_client.post(
        "/api/admin/users/provision",
        headers=admin_client.student_headers,
        json=payload,
    ).status_code == 403
    assert admin_client.post(
        "/api/admin/users/provision",
        headers=admin_client.admin_headers,
        json={**payload, "email": "student@example.edu"},
    ).status_code == 409
    assert admin_client.post(
        "/api/admin/users/provision",
        headers=admin_client.admin_headers,
        json={**payload, "role": "admin"},
    ).status_code == 422


def test_setup_email_failure_rolls_back_staff_account(admin_client, monkeypatch):
    def fail_delivery(_email, _url):
        raise EmailDeliveryError("mail service unavailable")

    monkeypatch.setattr(admin_users, "send_password_reset_email", fail_delivery)
    response = admin_client.post(
        "/api/admin/users/provision",
        headers=admin_client.admin_headers,
        json={"name": "New Staff", "email": "staff@example.edu", "role": "advisor"},
    )
    assert response.status_code == 502

    with admin_client.session_factory() as db:
        assert db.query(User).filter_by(email="staff@example.edu").count() == 0
        assert db.query(PasswordResetToken).count() == 0


def test_initial_admin_bootstrap_is_production_only_and_one_time(admin_client, monkeypatch):
    with admin_client.session_factory() as db:
        db.query(User).delete()
        db.commit()
    monkeypatch.setattr(bootstrap_admin.settings, "environment", "production")
    monkeypatch.setattr(bootstrap_admin, "SessionLocal", admin_client.session_factory)

    user_id = bootstrap_admin.create_initial_admin(
        " FIRST.ADMIN@EXAMPLE.EDU ",
        "First Administrator",
        "very-long-initial-admin-password",
    )
    with admin_client.session_factory() as db:
        user = db.get(User, user_id)
        assert user.email == "first.admin@example.edu"
        assert user.role == UserRole.admin

    with pytest.raises(RuntimeError, match="one-time"):
        bootstrap_admin.create_initial_admin(
            "second.admin@example.edu",
            "Second Administrator",
            "very-long-initial-admin-password",
        )


def test_initial_admin_bootstrap_rejects_weak_password(admin_client, monkeypatch):
    monkeypatch.setattr(bootstrap_admin.settings, "environment", "production")
    monkeypatch.setattr(bootstrap_admin, "SessionLocal", admin_client.session_factory)
    with pytest.raises(ValueError, match="16 characters"):
        bootstrap_admin.create_initial_admin("new.admin@example.edu", "Admin", "short")
