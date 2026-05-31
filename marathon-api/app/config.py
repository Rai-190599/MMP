from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://marathon:marathon@localhost:5432/marathon_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-to-a-long-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_BUCKET_NAME: str = "marathon-files"
    MINIO_SECURE: bool = False

    # SMTP — optional. If SMTP_HOST is empty/unset, email falls back to stub logging.
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    # Legacy alias kept for backward compat
    SMTP_FROM: Optional[str] = None

    # Twilio — optional. If unset, WhatsApp falls back to stub logging.
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None

    # Public-facing MinIO endpoint for presigned URLs served to browsers.
    # Inside Docker the internal endpoint is e.g. "minio:9000" but browsers
    # need "localhost:9000". Set this to the externally reachable host:port.
    # Defaults to MINIO_ENDPOINT if not set.
    MINIO_PUBLIC_ENDPOINT: Optional[str] = None

    # Frontend base URL — used to build invite links in emails.
    FRONTEND_URL: str = "http://localhost:3000"


settings = Settings()
