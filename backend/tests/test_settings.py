import pytest
from pydantic import ValidationError

from app.config.settings import Settings

VALID_SECRET = "0123456789abcdef" * 4
SECURE_PRODUCTION_SETTINGS = {
    "secret_key": VALID_SECRET,
    "allow_demo_tokens": False,
    "cors_origins": ["https://portal.example.edu"],
    "mock_sso_enabled": False,
    "resend_api_key": "re_test_key",
    "resend_from_email": "NeuroSync <no-reply@university.edu>",
    "frontend_url": "https://portal.example.edu",
    "database_url": "postgresql://app-db.example.edu/neurosync",
    "mock_lms_database_url": "postgresql://lms-db.example.edu/neurosync_lms",
}


def test_production_settings_accept_explicit_secure_configuration():
    settings = Settings.model_validate(
        {
            **SECURE_PRODUCTION_SETTINGS,
            "environment": "production",
        }
    )

    assert settings.cors_origins == ["https://portal.example.edu"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": "neuro-sync-secret-key-change-in-production"},
        {"allow_demo_tokens": True},
        {"cors_origins": ["*"]},
        {"cors_origins": []},
        {"secret_key": "s" * 64},
        {"mock_sso_enabled": True},
        {"resend_api_key": None},
        {"resend_from_email": "NeuroSync <onboarding@resend.dev>"},
        {"frontend_url": "http://portal.example.edu"},
        {"database_url": "sqlite:///./database/neurosync.db"},
        {"mock_lms_database_url": "sqlite:///./database/lms.db"},
    ],
)
def test_production_settings_reject_insecure_configuration(overrides):
    with pytest.raises(ValidationError):
        Settings.model_validate({"environment": "production", **SECURE_PRODUCTION_SETTINGS, **overrides})