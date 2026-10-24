import hashlib
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import forgot_password as password_reset_api
from app.config.settings import settings
from app.database.connection import Base, get_db
from app.models.user import PasswordResetToken, User, UserRole
from app.services.authentication_service import hash_password, verify_password
from app.services.email_service import EmailDeliveryError
from app.services import email_service


@pytest.fixture
def password_reset_client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'password-reset.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    user = User(
        id="reset-user",
        email="person@example.edu",
        password_hash=hash_password("original-password"),
        name="Person",
        role=UserRole.student,
    )
    with factory() as db:
        db.add(user)
        db.commit()

    def override_get_db():
        with factory() as db:
            yield db

    app = FastAPI()
    app.include_router(password_reset_api.router)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    monkeypatch.setattr(settings, "resend_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "frontend_url", "https://portal.example.edu")
    client.session_factory = factory  # type: ignore[attr-defined]
    yield client
    client.close()
    engine.dispose()


def test_forgot_password_sends_a_reset_link_without_storing_raw_token(password_reset_client, monkeypatch):
    sent = {}

    def capture_email(recipient, reset_url):
        sent.update(recipient=recipient, reset_url=reset_url)

    monkeypatch.setattr(password_reset_api, "send_password_reset_email", capture_email)
    response = password_reset_client.post("/api/auth/forgot-password", json={"email": "PERSON@example.edu"})

    assert response.status_code == 200
    assert response.json() == password_reset_api.GENERIC_RESPONSE
    assert sent["recipient"] == "person@example.edu"
    parsed_url = urlparse(sent["reset_url"])
    assert parsed_url.scheme == "https"
    assert parsed_url.netloc == "portal.example.edu"
    token = parse_qs(parsed_url.query)["token"][0]
    with password_reset_client.session_factory() as db:
        stored_token = db.query(PasswordResetToken).one()
        assert stored_token.token_hash != token
        assert stored_token.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)


def test_reset_password_changes_password_and_consumes_token(password_reset_client, monkeypatch):
    monkeypatch.setattr(password_reset_api, "send_password_reset_email", lambda *_: None)
    password_reset_client.post("/api/auth/forgot-password", json={"email": "person@example.edu"})
    with password_reset_client.session_factory() as db:
        reset_token = db.query(PasswordResetToken).one()
        raw_token = "known-reset-token"
        reset_token.token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        db.commit()

    response = password_reset_client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "a-new-password"},
    )
    assert response.status_code == 200
    with password_reset_client.session_factory() as db:
        user = db.get(User, "reset-user")
        assert verify_password("a-new-password", user.password_hash)
        assert db.query(PasswordResetToken).count() == 0

    reused = password_reset_client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "another-password"},
    )
    assert reused.status_code == 400


def test_expired_password_reset_token_is_rejected(password_reset_client):
    raw_token = "expired-reset-token"
    with password_reset_client.session_factory() as db:
        db.add(PasswordResetToken(
            user_id="reset-user",
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        ))
        db.commit()

    response = password_reset_client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "a-new-password"},
    )
    assert response.status_code == 400


def test_unknown_email_returns_same_generic_response(password_reset_client, monkeypatch):
    monkeypatch.setattr(password_reset_api, "send_password_reset_email", lambda *_: pytest.fail("email must not send"))
    response = password_reset_client.post("/api/auth/forgot-password", json={"email": "unknown@example.edu"})

    assert response.status_code == 200
    assert response.json() == password_reset_api.GENERIC_RESPONSE


def test_email_failure_is_reported_and_reset_token_removed(password_reset_client, monkeypatch):
    def fail_email(*_):
        raise EmailDeliveryError("provider unavailable")

    monkeypatch.setattr(password_reset_api, "send_password_reset_email", fail_email)
    response = password_reset_client.post("/api/auth/forgot-password", json={"email": "person@example.edu"})

    assert response.status_code == 502
    with password_reset_client.session_factory() as db:
        assert db.query(PasswordResetToken).count() == 0


def test_missing_resend_configuration_fails_explicitly(password_reset_client, monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", None)
    response = password_reset_client.post("/api/auth/forgot-password", json={"email": "person@example.edu"})

    assert response.status_code == 503


def test_resend_service_posts_email_to_resend_api(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "resend_from_email", "NeuroSync <mail@example.edu>")
    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def capture_request(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(email_service, "urlopen", capture_request)
    email_service.send_password_reset_email("person@example.edu", "https://portal.example.edu/reset-password?token=x")

    request = captured["request"]
    payload = json.loads(request.data)
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_header("Authorization") == "Bearer test-key"
    assert captured["timeout"] == 10
    assert payload["from"] == "NeuroSync <mail@example.edu>"
    assert payload["to"] == ["person@example.edu"]
    assert "https://portal.example.edu/reset-password?token=x" in payload["html"]
