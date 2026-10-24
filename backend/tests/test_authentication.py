"""Authentication regression tests.

Guards the bcrypt-based password service: passlib 1.7.4 could not initialise a
bcrypt >= 4.1 backend, which made every /api/auth/login call return HTTP 500 and
silently pushed the frontend into demo-token mode.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import parse_qs, urlparse

from app.api import auth as auth_api
from app.config.settings import settings
from app.database.connection import Base, get_db
from app.models.audit_event import AuditEvent
from app.models.user import EmailVerificationToken
from app.services.authentication_service import hash_password, verify_password
from app.services.email_service import EmailDeliveryError

# Hash produced by the previous passlib-based implementation for the password
# "demo1234" (the seeded demo accounts). It must keep verifying after the swap to
# the bcrypt library.
LEGACY_PASSLIB_HASH = "$2b$12$hFesLdUZtR82Bj1PaqkNveGw9vKW80pJlU.0CFQccLceMUPvsmqvG"


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
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
    verification_emails = []

    def capture_verification_email(email, url):
        verification_emails.append((email, url))

    monkeypatch.setattr(settings, "resend_api_key", SecretStr("test-resend-key"))
    monkeypatch.setattr(auth_api, "send_verification_email", capture_verification_email)
    client = TestClient(app)
    client.audit_session_factory = factory
    client.verification_emails = verification_emails
    yield client
    client.close()
    engine.dispose()


def verify_registration(client, email):
    matching_emails = [url for recipient, url in client.verification_emails if recipient == email]
    assert matching_emails, f"No verification email sent to {email}"
    token = parse_qs(urlparse(matching_emails[-1]).query)["token"][0]
    return client.post("/api/auth/verify-email", json={"token": token})


def test_hash_and_verify_round_trip():
    hashed = hash_password("demo1234")
    assert hashed.startswith("$2b$")
    assert verify_password("demo1234", hashed) is True
    assert verify_password("demo12345", hashed) is False


def test_verify_handles_legacy_and_malformed_hashes_without_raising():
    assert verify_password("demo1234", LEGACY_PASSLIB_HASH) is True
    assert verify_password("wrong-password", LEGACY_PASSLIB_HASH) is False
    assert verify_password("demo1234", "") is False
    assert verify_password("demo1234", "not-a-bcrypt-hash") is False


def test_long_passphrase_is_truncated_at_bcrypt_limit():
    long_password = "a" * 200
    hashed = hash_password(long_password)
    assert verify_password(long_password, hashed) is True
    assert verify_password("a" * 72, hashed) is True
    assert verify_password("a" * 71, hashed) is False


def test_malformed_demo_tokens_are_401_not_500(auth_client):
    """A malformed Authorization header used to raise IndexError/ValueError → 500."""
    for token in ["demo-token-bogus-1", "demo-token-", "demo-token-student", "demo-token-nope"]:
        response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401, f"{token!r} -> {response.status_code} {response.text}"


def test_demo_tokens_can_be_disabled(auth_client, monkeypatch):
    from app.config.settings import settings

    registered = auth_client.post("/api/auth/register", json={
        "name": "Demo Student",
        "email": "student@university.edu",
        "password": "demo1234",
        "role": "student",
    })
    assert registered.status_code == 200, registered.text
    assert verify_registration(auth_client, "student@university.edu").status_code == 200

    allowed = auth_client.get("/api/auth/me", headers={"Authorization": "Bearer demo-token-student-1"})
    assert allowed.status_code == 200, allowed.text

    monkeypatch.setattr(settings, "allow_demo_tokens", False)
    refused = auth_client.get("/api/auth/me", headers={"Authorization": "Bearer demo-token-student-1"})
    assert refused.status_code == 401, refused.text
    assert "disabled" in refused.json()["detail"]


def test_login_returns_usable_jwt_and_rejects_bad_credentials(auth_client):
    registered = auth_client.post("/api/auth/register", json={
        "name": "Dr. Demo Lecturer",
        "email": "lecturer@university.edu",
        "password": "demo1234",
        "role": "lecturer",
    })
    assert registered.status_code == 200, registered.text

    pending = auth_client.post("/api/auth/login", json={"email": "lecturer@university.edu", "password": "demo1234"})
    assert pending.status_code == 403
    assert "Confirm your email" in pending.json()["detail"]

    duplicate = auth_client.post("/api/auth/register", json={
        "name": "Duplicate",
        "email": "lecturer@university.edu",
        "password": "demo1234",
        "role": "lecturer",
    })
    assert duplicate.status_code == 400

    assert verify_registration(auth_client, "lecturer@university.edu").status_code == 200
    rejected = auth_client.post("/api/auth/login", json={"email": "lecturer@university.edu", "password": "wrong"})
    assert rejected.status_code == 401

    logged_in = auth_client.post("/api/auth/login", json={"email": "lecturer@university.edu", "password": "demo1234"})
    assert logged_in.status_code == 200, logged_in.text
    payload = logged_in.json()
    assert payload["role"] == "lecturer"
    assert payload["token"]

    # The issued JWT must authenticate protected routes (this is the token the
    # lecturer and advisor workflow screens send as a Bearer token).
    me = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {payload['token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "lecturer@university.edu"

    anonymous = auth_client.get("/api/auth/me")
    assert anonymous.status_code == 401
    assert anonymous.headers.get("www-authenticate") == "Bearer"


def test_login_success_and_failure_are_audited_without_credentials(auth_client):
    auth_client.post("/api/auth/register", json={
        "name": "Audit Student",
        "email": "audit@example.edu",
        "password": "safe-password-123",
        "role": "student",
    })
    assert verify_registration(auth_client, "audit@example.edu").status_code == 200
    auth_client.post("/api/auth/login", json={"email": "audit@example.edu", "password": "wrong-password"})
    success = auth_client.post("/api/auth/login", json={"email": "audit@example.edu", "password": "safe-password-123"})
    assert success.status_code == 200

    db = auth_client.audit_session_factory()
    try:
        events = db.query(AuditEvent).filter(AuditEvent.actor_reference == "audit@example.edu").order_by(AuditEvent.occurred_at).all()
        assert [event.outcome for event in events] == ["FAILURE", "SUCCESS"]
        assert all(event.action == "AUTH_LOGIN" for event in events)
        assert all(event.actor_id is None for event in events[:1])
        assert events[1].actor_id == success.json()["user_id"]
        assert all(event.request_id and event.source_ip for event in events)
        assert not hasattr(events[0], "password")
        assert not hasattr(events[0], "token")
    finally:
        db.close()


def test_mock_microsoft_sso_signs_in_existing_user_only(auth_client, monkeypatch):
    auth_client.post("/api/auth/register", json={
        "name": "Sarah", "email": "sarah@university.edu", "password": "demo1234", "role": "student",
    })
    unverified = auth_client.post("/api/auth/sso/microsoft/mock", json={"email": "Sarah@University.edu"})
    assert unverified.status_code == 403
    assert verify_registration(auth_client, "sarah@university.edu").status_code == 200
    ok = auth_client.post("/api/auth/sso/microsoft/mock", json={"email": "Sarah@University.edu"})
    assert ok.status_code == 200, ok.text
    me = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {ok.json()['token']}"})
    assert me.status_code == 200 and me.json()["email"] == "sarah@university.edu"

    unknown = auth_client.post("/api/auth/sso/microsoft/mock", json={"email": "nobody@university.edu"})
    assert unknown.status_code == 403

    monkeypatch.setattr(settings, "mock_sso_enabled", False)
    off = auth_client.post("/api/auth/sso/microsoft/mock", json={"email": "sarah@university.edu"})
    assert off.status_code == 404


def test_email_verification_tokens_are_hashed_one_time_and_resendable(auth_client):
    registered = auth_client.post("/api/auth/register", json={
        "name": "Casey Student",
        "email": "Casey@Example.edu",
        "password": "safe-password-123",
        "role": "student",
    })
    assert registered.status_code == 200
    assert auth_client.verification_emails[0][0] == "casey@example.edu"
    initial_token = parse_qs(urlparse(auth_client.verification_emails[0][1]).query)["token"][0]

    db = auth_client.audit_session_factory()
    try:
        stored = db.query(EmailVerificationToken).one()
        assert stored.token_hash != initial_token
        assert len(stored.token_hash) == 64
    finally:
        db.close()

    response = auth_client.post("/api/auth/verify-email/resend", json={"email": "casey@example.edu"})
    assert response.status_code == 200
    new_token = parse_qs(urlparse(auth_client.verification_emails[-1][1]).query)["token"][0]
    assert new_token != initial_token
    assert auth_client.post("/api/auth/verify-email", json={"token": initial_token}).status_code == 400
    assert auth_client.post("/api/auth/verify-email", json={"token": new_token}).status_code == 200
    assert auth_client.post("/api/auth/verify-email", json={"token": new_token}).status_code == 400
    assert auth_client.post(
        "/api/auth/verify-email/resend",
        json={"email": "nobody@example.edu"},
    ).json() == auth_api.VERIFICATION_EMAIL_RESPONSE


def test_public_registration_cannot_assign_admin(auth_client):
    response = auth_client.post("/api/auth/register", json={
        "name": "Admin Request",
        "email": "admin@example.edu",
        "password": "safe-password-123",
        "role": "admin",
    })
    assert response.status_code == 422


@pytest.mark.parametrize("role", ["lecturer", "advisor"])
@pytest.mark.parametrize("environment", ["production", "staging"])
def test_non_development_registration_restricts_staff_roles(auth_client, monkeypatch, role, environment):
    monkeypatch.setattr(settings, "environment", environment)
    options = auth_client.get("/api/auth/registration-options")
    assert options.status_code == 200
    assert options.json()["roles"] == ["student"]
    response = auth_client.post("/api/auth/register", json={
        "name": "Unprovisioned Staff",
        "email": f"{role}@example.edu",
        "password": "safe-password-123",
        "role": role,
    })
    assert response.status_code == 403


def test_production_still_allows_student_registration(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    response = auth_client.post("/api/auth/register", json={
        "name": "Production Student",
        "email": "production-student@example.edu",
        "password": "safe-password-123",
        "role": "student",
    })
    assert response.status_code == 200, response.text
    assert verify_registration(auth_client, "production-student@example.edu").status_code == 200


def test_registration_requires_resend_configuration(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", None)
    response = auth_client.post("/api/auth/register", json={
        "name": "No Email",
        "email": "no-email@example.edu",
        "password": "safe-password-123",
        "role": "student",
    })
    assert response.status_code == 503
    db = auth_client.audit_session_factory()
    try:
        from app.models.user import User

        assert db.query(User).filter_by(email="no-email@example.edu").count() == 0
    finally:
        db.close()


def test_failed_registration_email_can_be_resent(auth_client, monkeypatch):
    def fail_delivery(*_):
        raise EmailDeliveryError("provider unavailable")

    monkeypatch.setattr(auth_api, "send_verification_email", fail_delivery)
    response = auth_client.post("/api/auth/register", json={
        "name": "Email Retry",
        "email": "retry@example.edu",
        "password": "safe-password-123",
        "role": "student",
    })
    assert response.status_code == 502
    assert "Account created" in response.json()["detail"]
    blocked = auth_client.post("/api/auth/login", json={
        "email": "retry@example.edu",
        "password": "safe-password-123",
    })
    assert blocked.status_code == 403

    monkeypatch.setattr(
        auth_api,
        "send_verification_email",
        lambda email, url: auth_client.verification_emails.append((email, url)),
    )
    resent = auth_client.post("/api/auth/verify-email/resend", json={"email": "retry@example.edu"})
    assert resent.status_code == 200
    assert verify_registration(auth_client, "retry@example.edu").status_code == 200
    assert auth_client.post("/api/auth/login", json={
        "email": "retry@example.edu",
        "password": "safe-password-123",
    }).status_code == 200
