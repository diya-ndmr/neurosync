import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.config.settings import settings

MOODLE_REQUEST_TIMEOUT_SECONDS = 10


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


_MOODLE_OPENER = build_opener(_RejectRedirects())


class MoodleConfigurationError(Exception):
    pass


class MoodleConnectionError(Exception):
    pass


def is_moodle_configured() -> bool:
    return bool(settings.moodle_base_url and settings.moodle_token)


def get_safe_moodle_base_url() -> str | None:
    if not settings.moodle_base_url:
        return None
    try:
        return _validated_base_url(settings.moodle_base_url)
    except MoodleConfigurationError:
        return None


def _validated_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    try:
        parsed = urlsplit(base_url)
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
    except ValueError:
        valid_port = False
        parsed = urlsplit("")
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not valid_port
    ):
        raise MoodleConfigurationError(
            "MOODLE_BASE_URL must be an HTTP(S) URL without credentials, query parameters, or a fragment."
        )
    return base_url


def _open_moodle_request(request: Request, timeout: int):
    return _MOODLE_OPENER.open(request, timeout=timeout)


def test_moodle_connection() -> dict[str, str | None]:
    if not settings.moodle_base_url or not settings.moodle_token:
        raise MoodleConfigurationError(
            "Set MOODLE_BASE_URL and MOODLE_TOKEN in the backend environment before testing the connection."
        )

    base_url = _validated_base_url(settings.moodle_base_url)
    endpoint = f"{base_url}/webservice/rest/server.php"
    body = urlencode(
        {
            "wstoken": settings.moodle_token.get_secret_value(),
            "wsfunction": "core_webservice_get_site_info",
            "moodlewsrestformat": "json",
        }
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with _open_moodle_request(request, timeout=MOODLE_REQUEST_TIMEOUT_SECONDS) as response:
            response_body = response.read(1_048_577)
            if len(response_body) > 1_048_576:
                raise MoodleConnectionError("Moodle returned an invalid response.")
            payload: Any = json.loads(response_body)
    except HTTPError as error:
        if error.code in {401, 403}:
            raise MoodleConnectionError(
                "Moodle rejected the token or the token lacks permission to read site information."
            ) from None
        raise MoodleConnectionError("Moodle returned an HTTP error while testing the connection.") from None
    except (URLError, TimeoutError, socket.timeout, OSError):
        raise MoodleConnectionError("Moodle could not be reached. Check its URL and that it is running.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise MoodleConnectionError("Moodle returned an invalid response.") from None

    if not isinstance(payload, dict):
        raise MoodleConnectionError("Moodle returned an invalid response.")
    if "exception" in payload or "errorcode" in payload:
        raise MoodleConnectionError(
            "Moodle rejected the token or the token lacks permission to read site information."
        )

    site_name = payload.get("sitename")
    if not isinstance(site_name, str) or not site_name.strip():
        raise MoodleConnectionError("Moodle returned an invalid site-information response.")
    release = payload.get("release")
    return {
        "site_name": site_name.strip(),
        "release": release.strip() if isinstance(release, str) and release.strip() else None,
    }
