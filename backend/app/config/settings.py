import os
from typing import Literal, Optional

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "sqlite:///./neurosync.db"
    mock_lms_database_url: Optional[str] = None
    secret_key: str = "neuro-sync-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[SecretStr] = None
    moodle_base_url: Optional[str] = None
    moodle_token: Optional[SecretStr] = None
    frontend_url: str = "http://localhost:5173"
    allow_demo_tokens: bool = True
    # Prototype-only simulated Microsoft SSO (no real Entra ID call is made).
    mock_sso_enabled: bool = True

    @model_validator(mode="after")
    def validate_production_security(self):
        is_render_deployment = (
            os.getenv("RENDER", "").lower() == "true" or bool(os.getenv("RENDER_SERVICE_ID"))
        )
        if is_render_deployment and self.environment != "production":
            raise ValueError(
                "Render deployments require ENVIRONMENT=production; configure PostgreSQL database URLs "
                "instead of falling back to local SQLite files"
            )

        if self.environment == "production":
            if self.mock_sso_enabled:
                raise ValueError("Mock Microsoft SSO must be disabled in production")
            if not self.supabase_url or not self.supabase_url.startswith("https://"):
                raise ValueError("Production requires an HTTPS SUPABASE_URL")
            if not self.supabase_anon_key or not self.supabase_anon_key.get_secret_value():
                raise ValueError("Production requires SUPABASE_ANON_KEY")
            if not self.frontend_url.startswith("https://"):
                raise ValueError("Production requires an HTTPS FRONTEND_URL")
            if not self.sync_database_url.startswith(("postgresql://", "postgresql+")):
                raise ValueError("Production requires a persistent PostgreSQL DATABASE_URL")
            if not self.lms_sync_database_url.startswith(("postgresql://", "postgresql+")):
                raise ValueError("Production requires persistent PostgreSQL for LMS data")
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

    @property
    def lms_sync_database_url(self) -> str:
        """Use a separate LMS schema on Supabase when no second database is configured."""
        configured_url = self.mock_lms_database_url
        if configured_url:
            if configured_url.startswith("postgres://"):
                return configured_url.replace("postgres://", "postgresql://", 1)
            return configured_url
        if self.environment == "production":
            return self.sync_database_url
        return "sqlite:///./database/neurosync_workbook.db"


settings = Settings()
