from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db.postgres_url import normalize_postgres_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GlowPath"
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
    # Direct Neon connection. Alembic uses this when set; the app keeps DATABASE_URL
    # (pooled is fine at runtime, migrations are not).
    database_url_unpooled: str = Field(
        default="",
        validation_alias="DATABASE_URL_UNPOOLED",
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

    # Reminder worker (daily mood + goal notifications).
    # Product kill switch: false hides delivery and locks the settings UI.
    feature_notifications_enabled: bool = Field(
        default=False,
        validation_alias="FEATURE_NOTIFICATIONS_ENABLED",
    )
    notifications_worker_enabled: bool = Field(
        default=True,
        validation_alias="NOTIFICATIONS_WORKER_ENABLED",
    )
    notifications_poll_interval_seconds: int = Field(
        default=60,
        ge=10,
        validation_alias="NOTIFICATIONS_POLL_INTERVAL_SECONDS",
    )
    # How long after the user's reminder time a missed tick may still send it
    # (catch-up). Each schedule is sent at most once per day regardless.
    notifications_match_window_minutes: int = Field(
        default=30,
        ge=1,
        le=30,
        validation_alias="NOTIFICATIONS_MATCH_WINDOW_MINUTES",
    )
    # Bearer secret for POST /v1/internal/reminders/tick (external scheduler).
    # Empty disables the endpoint (404).
    reminders_cron_secret: str = Field(
        default="",
        validation_alias="REMINDERS_CRON_SECRET",
    )

    # Max tag groups a user can pin to the entry form (rest under "Other")
    entry_visible_tag_group_limit: int = Field(
        default=6,
        ge=1,
        validation_alias="ENTRY_VISIBLE_TAG_GROUP_LIMIT",
    )
    # Max goals a user can pin to the entry form (rest under "Other")
    entry_visible_goal_limit: int = Field(
        default=3,
        ge=1,
        validation_alias="ENTRY_VISIBLE_GOAL_LIMIT",
    )
    # Max goals shown in calendar + period stats
    stats_visible_goal_limit: int = Field(
        default=5,
        ge=1,
        validation_alias="STATS_VISIBLE_GOAL_LIMIT",
    )

    # Weekly frequent-tag shortcuts on the entry form (bias-sensitive; default off).
    # TODO: replace these env knobs with a DB-backed flags table (no server restart).
    # Master kill switch. false = nobody sees the section, including allowlists.
    feature_weekly_frequent_tags: bool = Field(
        default=False,
        validation_alias="FEATURE_WEEKLY_FREQUENT_TAGS",
    )
    # Percent of users (stable hash of user id). 0 = only allowlists, 100 = everyone.
    feature_weekly_frequent_tags_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        validation_alias="FEATURE_WEEKLY_FREQUENT_TAGS_PERCENT",
    )
    # Comma-separated emails always in when the master switch is on.
    feature_weekly_frequent_tags_emails: str = Field(
        default="",
        validation_alias="FEATURE_WEEKLY_FREQUENT_TAGS_EMAILS",
    )
    # Comma-separated user UUIDs always in when the master switch is on.
    feature_weekly_frequent_tags_user_ids: str = Field(
        default="",
        validation_alias="FEATURE_WEEKLY_FREQUENT_TAGS_USER_IDS",
    )
    feature_weekly_frequent_tags_limit: int = Field(
        default=8,
        ge=1,
        le=24,
        validation_alias="FEATURE_WEEKLY_FREQUENT_TAGS_LIMIT",
    )
    feature_weekly_frequent_tags_days: int = Field(
        default=7,
        ge=1,
        le=31,
        validation_alias="FEATURE_WEEKLY_FREQUENT_TAGS_DAYS",
    )

    # Icon marketplace (catalog packs + internal token wallet).
    feature_icon_marketplace: bool = Field(
        default=True,
        validation_alias="FEATURE_ICON_MARKETPLACE",
    )
    # Monetization is hidden by default: only allowlisted testers see it (GP-15).
    feature_icon_marketplace_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        validation_alias="FEATURE_ICON_MARKETPLACE_PERCENT",
    )
    feature_icon_marketplace_emails: str = Field(
        default="",
        validation_alias="FEATURE_ICON_MARKETPLACE_EMAILS",
    )
    feature_icon_marketplace_user_ids: str = Field(
        default="",
        validation_alias="FEATURE_ICON_MARKETPLACE_USER_IDS",
    )

    # Plans page and billing API (Free / Plus / Pro). Testers only by default.
    feature_billing: bool = Field(
        default=True,
        validation_alias="FEATURE_BILLING",
    )
    feature_billing_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        validation_alias="FEATURE_BILLING_PERCENT",
    )
    feature_billing_emails: str = Field(
        default="",
        validation_alias="FEATURE_BILLING_EMAILS",
    )
    feature_billing_user_ids: str = Field(
        default="",
        validation_alias="FEATURE_BILLING_USER_IDS",
    )

    # Achievements (catalog unlocks + token / pack / icon rewards).
    feature_achievements: bool = Field(
        default=True,
        validation_alias="FEATURE_ACHIEVEMENTS",
    )
    feature_achievements_percent: int = Field(
        default=100,
        ge=0,
        le=100,
        validation_alias="FEATURE_ACHIEVEMENTS_PERCENT",
    )
    feature_achievements_emails: str = Field(
        default="",
        validation_alias="FEATURE_ACHIEVEMENTS_EMAILS",
    )
    feature_achievements_user_ids: str = Field(
        default="",
        validation_alias="FEATURE_ACHIEVEMENTS_USER_IDS",
    )

    # Guest local diary experiment (default off — login wall unchanged).
    feature_guest_local_diary: bool = Field(
        default=False,
        validation_alias="FEATURE_GUEST_LOCAL_DIARY",
    )
    feature_guest_local_diary_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        validation_alias="FEATURE_GUEST_LOCAL_DIARY_PERCENT",
    )
    feature_guest_local_diary_visitor_ids: str = Field(
        default="",
        validation_alias="FEATURE_GUEST_LOCAL_DIARY_VISITOR_IDS",
    )
    guest_experiment_secret: str = Field(
        default="dev-only-guest-experiment-secret-change-me",
        validation_alias="GUEST_EXPERIMENT_SECRET",
    )
    guest_visitor_cookie_name: str = Field(
        default="mt_vid",
        validation_alias="GUEST_VISITOR_COOKIE_NAME",
    )
    guest_visitor_cookie_max_age_days: int = Field(
        default=400,
        ge=1,
        le=730,
        validation_alias="GUEST_VISITOR_COOKIE_MAX_AGE_DAYS",
    )

    # Telegram bot integration (notifier + bot service auth)
    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field(default="", validation_alias="TELEGRAM_BOT_USERNAME")
    telegram_bot_service_token: str = Field(
        default="",
        validation_alias="TELEGRAM_BOT_SERVICE_TOKEN",
    )
    telegram_link_code_expire_minutes: int = Field(
        default=15,
        ge=1,
        le=120,
        validation_alias="TELEGRAM_LINK_CODE_EXPIRE_MINUTES",
    )
    telegram_init_data_max_age_seconds: int = Field(
        default=86400,
        ge=60,
        le=7 * 24 * 3600,
        validation_alias="TELEGRAM_INIT_DATA_MAX_AGE_SECONDS",
    )
    telegram_mini_app_url: str = Field(default="", validation_alias="TELEGRAM_MINI_APP_URL")
    # Browser login (OpenID Connect). Client id/secret come from BotFather → Login Widget.
    telegram_oidc_client_id: str = Field(default="", validation_alias="TELEGRAM_OIDC_CLIENT_ID")
    telegram_oidc_client_secret: str = Field(
        default="",
        validation_alias="TELEGRAM_OIDC_CLIENT_SECRET",
    )
    telegram_oidc_redirect_uri: str = Field(
        default="http://localhost:8000/v1/auth/telegram/callback",
        validation_alias="TELEGRAM_OIDC_REDIRECT_URI",
    )

    # Billing / subscriptions (fake provider is the local default).
    billing_currency: str = Field(default="RUB", validation_alias="BILLING_CURRENCY")
    billing_default_provider: str = Field(
        default="fake",
        validation_alias="BILLING_DEFAULT_PROVIDER",
    )
    billing_enabled_providers: str = Field(
        default="fake",
        validation_alias="BILLING_ENABLED_PROVIDERS",
    )
    stripe_secret_key: str = Field(default="", validation_alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", validation_alias="STRIPE_WEBHOOK_SECRET")
    sber_username: str = Field(default="", validation_alias="SBER_USERNAME")
    sber_password: str = Field(default="", validation_alias="SBER_PASSWORD")

    # Local semantic search (fastembed + pgvector).
    # The ONNX model is downloaded on first embed. Leave false on Render:
    # free instances have no persistent disk and 512 MB RAM.
    embedding_enabled: bool = Field(default=True, validation_alias="EMBEDDING_ENABLED")
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dims: int = Field(default=384, ge=1, validation_alias="EMBEDDING_DIMS")
    # pgvector cosine distance is 1 - cosine similarity (0 identical, 2 opposite).
    embedding_search_max_distance: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        validation_alias="EMBEDDING_SEARCH_MAX_DISTANCE",
    )

    @field_validator("database_url", "database_url_unpooled", "test_database_url", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return normalize_postgres_url(value)

    @property
    def migration_database_url(self) -> str:
        return self.database_url_unpooled or self.database_url


settings = Settings()
