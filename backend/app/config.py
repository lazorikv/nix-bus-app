from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Bus Management API"
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+psycopg2://bus:bus@localhost:5432/bus"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # MinIO / S3-compatible object storage
    s3_endpoint_url: str = "http://localhost:9000"
    # Endpoint embedded in presigned URLs served to clients (browser-reachable).
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "bus-photos"
    s3_region: str = "us-east-1"
    presigned_url_expire_seconds: int = 3600

    # First admin bootstrap (optional)
    first_admin_email: str | None = None
    first_admin_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
