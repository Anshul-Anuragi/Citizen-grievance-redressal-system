from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator

# The hardcoded default value that must NEVER be used in production.
# This constant is public so it can be referenced in the startup guard.
_INSECURE_DEFAULT_SECRET = "SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION_MPONLINE_2026_REDRESSAL_SYSTEM"


class Settings(BaseSettings):
    PROJECT_NAME: str = "JanSeva AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    # Default to SQLite file for local dev, PostgreSQL for production
    DATABASE_URL: str = "sqlite+aiosqlite:///./grievance_system.db"

    # JWT Security
    # CRITICAL: Override SECRET_KEY in production via environment variable.
    # The default value is intentionally weak; startup will refuse to run in
    # production if it detects the insecure default.
    SECRET_KEY: str = _INSECURE_DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ANONYMOUS_SESSION_EXPIRE_DAYS: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Storage Configuration (Supabase or Local Proxy)
    STORAGE_TYPE: str = "local"  # 'local' or 'supabase'
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "complaint-attachments"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 25

    # Email Configuration
    EMAIL_PROVIDER: str = "mock"  # 'mock', 'smtp', or 'resend'
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@mp.gov.in"
    RESEND_API_KEY: Optional[str] = None

    # Gemini AI Optional Layer
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Demo Seed Passwords (provisioned securely if set, otherwise auto-generated)
    SEED_CITIZEN_PASSWORD: Optional[str] = None
    SEED_ADMIN_PASSWORD: Optional[str] = None
    SEED_OFFICER_PASSWORD: Optional[str] = None

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        """
        Reject the insecure default SECRET_KEY at parse time only if ENVIRONMENT
        can be determined.  Full production guard runs at application startup in
        main.py so it can read ENVIRONMENT.  Here we just ensure the value is
        non-empty.
        """
        if not v or not v.strip():
            raise ValueError(
                "SECRET_KEY must not be empty. "
                "Set a strong random value via the SECRET_KEY environment variable."
            )
        return v

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
