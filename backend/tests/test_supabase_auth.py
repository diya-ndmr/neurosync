import json
from io import BytesIO
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

from app.config.settings import settings
from app.services import supabase_auth
from app.services.supabase_auth import InvalidSupabaseToken


def test_supabase_access_token_is_checked_with_auth_user_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://project-ref.supabase.co/")
    monkeypatch.setattr(settings, "supabase_anon_key", SecretStr("public-anon-key"))

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://project-ref.supabase.co/auth/v1/user"
        assert request.get_header("Apikey") == "public-anon-key"
        assert request.get_header("Authorization") == "Bearer user-access-token"
        assert timeout == 10
        return BytesIO(json.dumps({
            "id": "supabase-user-id",
            "email": "user@example.edu",
            "email_confirmed_at": "2026-01-01T00:00:00Z",
            "user_metadata": {"full_name": "Verified User"},
        }).encode())

    monkeypatch.setattr(supabase_auth, "urlopen", fake_urlopen)

    assert supabase_auth.verify_supabase_access_token("user-access-token") == {
        "uid": "supabase-user-id",
        "email": "user@example.edu",
        "email_verified": True,
        "name": "Verified User",
    }


def test_supabase_rejects_invalid_access_token(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://project-ref.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", SecretStr("public-anon-key"))

    def reject_request(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", None, None)

    monkeypatch.setattr(supabase_auth, "urlopen", reject_request)

    with pytest.raises(InvalidSupabaseToken):
        supabase_auth.verify_supabase_access_token("expired-access-token")
