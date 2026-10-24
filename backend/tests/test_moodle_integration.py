import json
import socket
from io import BytesIO
from urllib.error import HTTPError

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import moodle
from app.middleware.security import get_current_user
from app.models.user import User, UserRole
from app.services import moodle_service


@pytest.fixture
def moodle_client():
    app = FastAPI()
    app.include_router(moodle.router)
    app.dependency_overrides[get_current_user] = lambda: User(
        id="admin-id",
        email="admin@example.test",
        password_hash="unused",
        name="Admin",
        role=UserRole.admin,
    )
    return TestClient(app)


def _configure_moodle(monkeypatch, base_url="http://localhost", token="test-secret-token"):
    monkeypatch.setattr(moodle_service.settings, "moodle_base_url", base_url)
    monkeypatch.setattr(
        moodle_service.settings,
        "moodle_token",
        SecretStr(token) if token is not None else None,
    )


def test_status_reports_missing_configuration_without_exposing_secrets(moodle_client, monkeypatch):
    _configure_moodle(monkeypatch, base_url=None, token=None)

    response = moodle_client.get("/api/moodle/status")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "base_url": None,
        "connection_status": "not_configured",
    }
    assert "token" not in response.text.lower()


def test_configured_status_never_returns_the_token(moodle_client, monkeypatch):
    _configure_moodle(monkeypatch, "http://localhost/moodle", "local-only-token")

    response = moodle_client.get("/api/moodle/status")

    assert response.status_code == 200
    assert response.json() == {
        "configured": True,
        "base_url": "http://localhost/moodle",
        "connection_status": "ready_to_test",
    }
    assert "local-only-token" not in response.text


def test_connection_test_posts_token_to_moodle_rest_endpoint(moodle_client, monkeypatch):
    _configure_moodle(monkeypatch, "http://localhost/moodle", "local-only-token")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            return json.dumps(
                {"sitename": "NeuroSync Moodle", "release": "5.3+", "userid": 1, "username": "admin"}
            ).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode()
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(moodle_service, "_open_moodle_request", fake_urlopen)

    response = moodle_client.post("/api/moodle/test")

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "connection_status": "connected",
        "site_name": "NeuroSync Moodle",
        "release": "5.3+",
    }
    assert captured["url"] == "http://localhost/moodle/webservice/rest/server.php"
    assert "wstoken=local-only-token" in captured["body"]
    assert captured["timeout"] == moodle_service.MOODLE_REQUEST_TIMEOUT_SECONDS
    assert "local-only-token" not in response.text
    assert "admin" not in response.text


@pytest.mark.parametrize(
    ("base_url", "token"),
    [(None, "present-token"), ("http://localhost", None)],
)
def test_connection_test_requires_both_settings(moodle_client, monkeypatch, base_url, token):
    _configure_moodle(monkeypatch, base_url, token)

    response = moodle_client.post("/api/moodle/test")

    assert response.status_code == 503
    assert "MOODLE_BASE_URL and MOODLE_TOKEN" in response.json()["detail"]
    assert "present-token" not in response.text


@pytest.mark.parametrize(
    "base_url",
    [
        "file:///tmp/moodle",
        "http://user:password@localhost",
        "http://localhost?token=leak",
        "http://localhost#fragment",
    ],
)
def test_connection_test_rejects_unsafe_base_urls(moodle_client, monkeypatch, base_url):
    _configure_moodle(monkeypatch, base_url, "local-only-token")

    response = moodle_client.post("/api/moodle/test")

    assert response.status_code == 503
    assert "MOODLE_BASE_URL must be an HTTP(S) URL" in response.json()["detail"]
    assert "password" not in response.text
    assert "local-only-token" not in response.text


def test_moodle_api_authentication_errors_are_safe(moodle_client, monkeypatch):
    _configure_moodle(monkeypatch)

    def reject_request(request, timeout):
        raise HTTPError(request.full_url, 403, "forbidden", {}, BytesIO(b"private token details"))

    monkeypatch.setattr(moodle_service, "_open_moodle_request", reject_request)

    response = moodle_client.post("/api/moodle/test")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Moodle rejected the token or the token lacks permission to read site information."
    )
    assert "private token details" not in response.text
    assert "test-secret-token" not in response.text


def test_moodle_api_error_payload_does_not_leak_remote_error(moodle_client, monkeypatch):
    _configure_moodle(monkeypatch)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            return json.dumps(
                {"exception": "moodle_exception", "message": "private service detail", "errorcode": "invalidtoken"}
            ).encode()

    monkeypatch.setattr(moodle_service, "_open_moodle_request", lambda request, timeout: FakeResponse())

    response = moodle_client.post("/api/moodle/test")

    assert response.status_code == 503
    assert "private service detail" not in response.text
    assert "test-secret-token" not in response.text


def test_moodle_timeout_returns_a_safe_error(moodle_client, monkeypatch):
    _configure_moodle(monkeypatch)

    def time_out(request, timeout):
        raise socket.timeout()

    monkeypatch.setattr(moodle_service, "_open_moodle_request", time_out)

    response = moodle_client.post("/api/moodle/test")

    assert response.status_code == 503
    assert response.json()["detail"] == "Moodle could not be reached. Check its URL and that it is running."
    assert "test-secret-token" not in response.text


@pytest.mark.parametrize(
    "response_body",
    [b"not json", b'{"userid":1}', b"[]"],
)
def test_malformed_moodle_responses_are_rejected(moodle_client, monkeypatch, response_body):
    _configure_moodle(monkeypatch)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            return response_body

    monkeypatch.setattr(moodle_service, "_open_moodle_request", lambda request, timeout: FakeResponse())

    response = moodle_client.post("/api/moodle/test")

    assert response.status_code == 503
    assert response.json()["detail"].startswith("Moodle returned an invalid")
    assert "test-secret-token" not in response.text


def test_moodle_endpoints_require_administrator(moodle_client, monkeypatch):
    _configure_moodle(monkeypatch)
    moodle_client.app.dependency_overrides[get_current_user] = lambda: User(
        id="student-id",
        email="student@example.test",
        password_hash="unused",
        name="Student",
        role=UserRole.student,
    )

    assert moodle_client.get("/api/moodle/status").status_code == 403
    assert moodle_client.post("/api/moodle/test").status_code == 403
