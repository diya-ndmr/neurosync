import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.settings import settings


class InvalidSupabaseToken(Exception):
    pass


def verify_supabase_access_token(access_token: str) -> dict[str, Any]:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("Supabase Auth is not configured on the backend.")

    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={
            "apikey": settings.supabase_anon_key.get_secret_value(),
            "Authorization": f"Bearer {access_token}",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            user = json.load(response)
    except HTTPError as error:
        if error.code in {401, 403}:
            raise InvalidSupabaseToken("Supabase access token is invalid or expired") from error
        raise RuntimeError(f"Supabase Auth returned HTTP {error.code}.") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError("Could not reach Supabase Auth to validate the access token.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError("Supabase Auth returned an invalid response.") from error

    if not isinstance(user, dict):
        raise InvalidSupabaseToken("Supabase user response is invalid")

    user_metadata = user.get("user_metadata")
    if not isinstance(user_metadata, dict):
        user_metadata = {}

    return {
        "uid": user.get("id"),
        "email": user.get("email"),
        "email_verified": bool(user.get("email_confirmed_at")),
        "name": user_metadata.get("full_name") or user_metadata.get("name"),
    }
