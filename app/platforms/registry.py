from app.config import Settings
from app.platforms.base import Platform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.devto import DevToPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform

PLATFORM_CLASSES: tuple[type[Platform], ...] = (
    TelegramPlatform,
    DiscordPlatform,
    MastodonPlatform,
    BlueskyPlatform,
    DevToPlatform,
)


def build_platforms(settings: Settings, client) -> list[Platform]:
    return [platform_cls(settings, client) for platform_cls in PLATFORM_CLASSES]
