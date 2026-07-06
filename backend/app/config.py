from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Mood Tracker"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    database_url: str = Field(
        default="postgresql+psycopg://mood:mood@localhost:5432/mood_tracker",
        validation_alias="DATABASE_URL",
    )
    db_table_prefix: str = Field(default="mt_", validation_alias="DB_TABLE_PREFIX")
    minio_endpoint: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="mood", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="moodsecret", validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="mood-tracker", validation_alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")


settings = Settings()
