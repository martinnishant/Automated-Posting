from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    request_timeout: float = Field(default=20.0, gt=0, le=60)
    posting_timezone: str = "Asia/Kolkata"

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    discord_bot_token: str | None = None
    discord_channel_id: str | None = None

    mastodon_base_url: str = "https://mastodon.social"
    mastodon_access_token: str | None = None

    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None

    devto_api_key: str | None = None
    devto_tags: str = "general"

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.posting_timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
