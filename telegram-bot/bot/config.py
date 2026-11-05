from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sentry_sdk.utils import BadDsn, Dsn


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str = Field(
        default="http://app:8000",
        validation_alias="API_BASE_URL",
    )
    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_service_token: str = Field(
        default="",
        validation_alias="TELEGRAM_BOT_SERVICE_TOKEN",
    )
    telegram_webhook_secret: str = Field(
        default="",
        validation_alias="TELEGRAM_WEBHOOK_SECRET",
    )
    telegram_webhook_path: str = Field(
        default="/telegram/webhook",
        validation_alias="TELEGRAM_WEBHOOK_PATH",
    )
    # Public HTTPS URL for setWebhook (empty = skip registration on startup)
    telegram_webhook_url: str = Field(default="", validation_alias="TELEGRAM_WEBHOOK_URL")
    telegram_mini_app_url: str = Field(default="", validation_alias="TELEGRAM_MINI_APP_URL")
    host: str = Field(default="0.0.0.0", validation_alias="BOT_HOST")
    port: int = Field(default=8081, validation_alias="BOT_PORT")

    # Sentry error + trace reporting. Empty DSN disables it (local dev, tests).
    sentry_dsn: str = Field(default="", validation_alias="SENTRY_DSN")
    sentry_environment: str = Field(
        default="development",
        validation_alias="SENTRY_ENVIRONMENT",
    )
    # Render sets RENDER_GIT_COMMIT on every deploy; it doubles as the release name.
    sentry_release: str = Field(
        default="",
        validation_alias=AliasChoices("SENTRY_RELEASE", "RENDER_GIT_COMMIT"),
    )
    sentry_traces_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        validation_alias="SENTRY_TRACES_SAMPLE_RATE",
    )

    @field_validator("sentry_dsn")
    @classmethod
    def _check_sentry_dsn(cls, value: str) -> str:
        # A malformed DSN fails startup loudly instead of silently dropping telemetry.
        value = value.strip()
        if value:
            try:
                Dsn(value)
            except BadDsn as exc:
                raise ValueError(f"SENTRY_DSN is not a valid Sentry DSN: {exc}") from exc
        return value


settings = Settings()
