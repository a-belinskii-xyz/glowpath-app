from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Mood Tracker"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    app_public_url: str = Field(
        default="http://localhost:8000",
        validation_alias="APP_PUBLIC_URL",
    )
    frontend_url: str = Field(
        default="http://localhost:5173",
        validation_alias="FRONTEND_URL",
    )
    cors_origins: str = Field(
        default="http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )
    database_url: str = Field(
        default="postgresql+psycopg://mood:mood@localhost:5432/mood_tracker",
        validation_alias="DATABASE_URL",
    )
    test_database_url: str = Field(
        default="postgresql+psycopg://mood:mood@localhost:5432/mood_tracker_test",
        validation_alias="TEST_DATABASE_URL",
    )
    db_table_prefix: str = Field(default="mt_", validation_alias="DB_TABLE_PREFIX")
    minio_endpoint: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="mood", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="moodsecret", validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="mood-tracker", validation_alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")

    jwt_secret_key: str = Field(
        default="dev-only-change-me-in-production",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=30,
        validation_alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    )
    auth_token_expire_hours: int = Field(default=24, validation_alias="AUTH_TOKEN_EXPIRE_HOURS")

    google_client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/v1/auth/google/callback",
        validation_alias="GOOGLE_REDIRECT_URI",
    )

    smtp_host: str = Field(default="localhost", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    email_from: str = Field(default="noreply@mood-tracker.local", validation_alias="EMAIL_FROM")

    # Max tag groups a user can pin to the entry form (rest under "Other")
    entry_visible_tag_group_limit: int = Field(
        default=6,
        ge=1,
        validation_alias="ENTRY_VISIBLE_TAG_GROUP_LIMIT",
    )


settings = Settings()
