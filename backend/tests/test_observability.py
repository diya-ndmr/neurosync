import json
import logging
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import observability
from app.observability import JsonLogFormatter, RequestObservabilityMiddleware


class CapturedLogger:
    def __init__(self):
        self.entries = []

    def info(self, message, *, extra):
        self.entries.append(("info", message, extra))

    def error(self, message, *, extra):
        self.entries.append(("error", message, extra))


def test_json_formatter_emits_only_allowlisted_structured_fields():
    record = logging.LogRecord("neurosync", logging.INFO, "", 0, "request_completed", (), None)
    record.event = "request_completed"
    record.request_id = "request-123"
    record.route = "/students/{student_id}"
    record.authorization = "Bearer sensitive-token"

    rendered = JsonLogFormatter().format(record)
    payload = json.loads(rendered)

    assert payload["event"] == "request_completed"
    assert payload["route"] == "/students/{student_id}"
    assert "authorization" not in payload
    assert "sensitive-token" not in rendered


def test_request_middleware_logs_route_template_and_returns_correlation_id(monkeypatch):
    captured = CapturedLogger()
    monkeypatch.setattr(observability, "logger", captured)
    app = FastAPI()
    app.add_middleware(RequestObservabilityMiddleware)

    @app.get("/students/{student_id}")
    def student_record(student_id: str, request: Request):
        return {"student_id": student_id, "request_id": request.state.request_id}

    client = TestClient(app)
    response = client.get(
        "/students/student-private-42?search=secret-query-value",
        headers={"Authorization": "Bearer sensitive-token"},
    )
    client.close()

    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["request_id"]
    assert captured.entries[0][2]["route"] == "/students/{student_id}"
    assert captured.entries[0][2]["status_code"] == 200
    assert "student-private-42" not in str(captured.entries)
    assert "secret-query-value" not in str(captured.entries)
    assert "sensitive-token" not in str(captured.entries)
