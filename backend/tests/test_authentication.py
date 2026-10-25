"""Authentication tests for local development login and Supabase sessions."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import auth as auth_api
from app.config.settings import settings
from app.database.connection import Base, get_db
from app.models.audit_event import AuditEvent
from app.models.user import User, UserRole
from app.services.authentication_service import hash_password, verify_password
from app.services.supabase_auth import InvalidSupabaseToken

LEGACY_PASSLIB_HASH = "$2b$12$hFesLdUZtR82Bj1PaqkNveGw9vKW80pJlU.0CFQccLceMUPvsmqvG"


@pytest.fixture
def auth_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth_api.router)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.audit_session_factory = factory
    yield client
    client.close()
    engine.dispose()


def test_hash_and_verify_passwords():
    hashed = hash_password("demo1234")
    assert hashed.startswith("$2b$")
    assert verify_password("demo1234", hashed)
    assert not verify_password("wrong-password", hashed)
    assert verify_password("demo1234", LEGACY_PASSLIB_HASH)
    assert not verify_password("demo1234", "")
    assert not verify_password("demo1234", "not-a-bcrypt-hash")


def test_long_password_compatibility():
    long_passphrase = "a" * 200
    hashed = hash_password(long_passphrase)
    assert verify_password(long_passphrase, hashed)
    assert verify_password("a" * 72, hashed)
    assert not verify_password("a" * 71, hashed)


def test_development_registration_and_login(auth_client):
    registered = auth_client.post("/api/auth/register", json={
        "name": "Demo Student",
        "email": "Student@Example.edu",
        "password": "safe-password-123",
        "role": "student",
    })
    assert registered.status_code == 200, registered.text

    logged_in = auth_client.post("/api/auth/login", json={
        "email": "student@example.edu",
        "password": "safe-password-123",
    })
    assert logged_in.status_code == 200, logged_in.text
    token = logged_in.json()["token"]
    me = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "student@example.edu"

    assert auth_client.post(
        "/api/auth/login",
        json={"email": "student@example.edu", "password": "wrong-password"},
    ).status_code == 401


def test_supabase_session_creates_verified_student(auth_client, monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "verify_supabase_access_token",
        lambda token: {
            "uid": "supabase-student-1",
            "email": "STUDENT@example.edu",
            "email_verified": True,
            "name": "Supabase Student",
        },
    )
    response = auth_client.post("/api/auth/supabase-session", json={"access_token": "verified-token"})
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "student"
    assert response.json()["name"] == "Supabase Student"

    with auth_client.audit_session_factory() as db:
        user = db.query(User).filter_by(email="student@example.edu").one()
        assert user.role == UserRole.student


def test_supabase_session_preserves_preprovisioned_role(auth_client, monkeypatch):
    with auth_client.audit_session_factory() as db:
        db.add(User(
            id="preprovisioned-lecturer",
            email="lecturer@example.edu",
            name="Preprovisioned Lecturer",
            password_hash=hash_password("unused"),
            role=UserRole.lecturer,
        ))
        db.commit()

    monkeypatch.setattr(
        auth_api,
        "verify_supabase_access_token",
        lambda _token: {
            "uid": "supabase-lecturer-1",
            "email": "LECTURER@example.edu",
            "email_verified": True,
            "name": "Supabase Name",
        },
    )
    response = auth_client.post("/api/auth/supabase-session", json={"access_token": "verified-token"})
    assert response.status_code == 200
    assert response.json()["role"] == "lecturer"
    assert response.json()["name"] == "Preprovisioned Lecturer"


def test_supabase_session_rejects_unverified_or_invalid_tokens(auth_client, monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "verify_supabase_access_token",
        lambda _token: {"uid": "supabase-user", "email": "user@example.edu", "email_verified": False},
    )
    unverified = auth_client.post("/api/auth/supabase-session", json={"access_token": "unverified-token"})
    assert unverified.status_code == 401

    def reject_token(_token):
        raise InvalidSupabaseToken("invalid")

    monkeypatch.setattr(auth_api, "verify_supabase_access_token", reject_token)
    invalid = auth_client.post("/api/auth/supabase-session", json={"access_token": "invalid-token"})
    assert invalid.status_code == 401


def test_production_disables_legacy_password_login_and_registration(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    payload = {
        "name": "Production Student",
        "email": "production@example.edu",
        "password": "safe-password-123",
        "role": "student",
    }
    assert auth_client.post("/api/auth/register", json=payload).status_code == 404
    assert auth_client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    ).status_code == 404


def test_demo_tokens_can_be_disabled(auth_client, monkeypatch):
    with auth_client.audit_session_factory() as db:
        db.add(User(
            id="demo-user",
            email="demo@example.edu",
            name="Demo User",
            password_hash=hash_password("unused"),
            role=UserRole.student,
        ))
        db.commit()

    allowed = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer demo-token-student-123"},
    )
    assert allowed.status_code == 200

    monkeypatch.setattr(settings, "allow_demo_tokens", False)
    refused = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer demo-token-student-123"},
    )
    assert refused.status_code == 401
    assert "disabled" in refused.json()["detail"]


def test_malformed_demo_tokens_are_401_not_500(auth_client):
    for token in ["demo-token-bogus-1", "demo-token-", "demo-token-student", "demo-token-nope"]:
        response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


def test_supabase_login_is_audited_without_token_contents(auth_client, monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "verify_supabase_access_token",
        lambda _token: {
            "uid": "supabase-audit-user",
            "email": "audit@example.edu",
            "email_verified": True,
            "name": "Audit Student",
        },
    )
    response = auth_client.post("/api/auth/supabase-session", json={"access_token": "sensitive-token"})
    assert response.status_code == 200

    with auth_client.audit_session_factory() as db:
        event = db.query(AuditEvent).filter_by(action="AUTH_LOGIN_SUPABASE").one()
        assert event.outcome == "SUCCESS"
        assert event.actor_reference == "audit@example.edu"
        assert event.actor_id == response.json()["user_id"]
        assert event.request_id
        assert event.source_ip
        assert "sensitive-token" not in str(event.__dict__)
