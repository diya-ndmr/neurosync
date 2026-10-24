from typing import Literal, Optional
from email.utils import parseaddr

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "sqlite:///./neurosync.db"
    mock_lms_database_url: str = "sqlite:///./database/neurosync_workbook.db"
    secret_key: str = "neuro-sync-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    firebase_credentials_path: Optional[str] = None
    firebase_project_id: Optional[str] = None
    resend_api_key: Optional[SecretStr] = None
    moodle_base_url: Optional[str] = None
    moodle_token: Optional[SecretStr] = None
    resend_from_email: str = "NeuroSync <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:5173"
    allow_demo_tokens: bool = True
    # Prototype-only simulated Microsoft SSO (no real Entra ID call is made).
    mock_sso_enabled: bool = True

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment == "production":
            if self.mock_sso_enabled:
                raise ValueError("Mock Microsoft SSO must be disabled in production")
            if not self.resend_api_key:
                raise ValueError("Production requires RESEND_API_KEY for account verification and password resets")
            sender_email = parseaddr(self.resend_from_email)[1]
            if not sender_email or sender_email.rsplit("@", 1)[-1].lower() == "resend.dev":
                raise ValueError("Production requires a sender address on a verified email domain")
            if not self.frontend_url.startswith("https://"):
                raise ValueError("Production requires an HTTPS FRONTEND_URL")
            if not self.sync_database_url.startswith(("postgresql://", "postgresql+")):
                raise ValueError("Production requires a persistent PostgreSQL DATABASE_URL")
            if not self.mock_lms_database_url.startswith(("postgresql://", "postgres://", "postgresql+")):
                raise ValueError("Production requires a persistent PostgreSQL MOCK_LMS_DATABASE_URL")
            secret_lower = self.secret_key.lower()
            placeholder_markers = ("change-me", "replace-me", "placeholder", "neuro-sync-secret")
            if (
                len(self.secret_key) < 32
                or len(set(self.secret_key)) < 16
                or any(marker in secret_lower for marker in placeholder_markers)
            ):
                raise ValueError("Production requires a strong, unique SECRET_KEY of at least 32 characters")
            if self.allow_demo_tokens:
                raise ValueError("Demo tokens must be disabled in production")
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError("Production requires explicit CORS_ORIGINS; wildcard origins are not allowed")
        return self

    @property
    def sync_database_url(self) -> str:
        """Handle 'postgres://' vs 'postgresql://' for Render/Heroku."""
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql://", 1)
        return self.database_url


settings = Settings()
