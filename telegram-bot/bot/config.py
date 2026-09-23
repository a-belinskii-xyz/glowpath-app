from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
