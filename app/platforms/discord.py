from typing import Any

from app.platforms.base import Platform, PlatformError


class DiscordPlatform(Platform):
    name = "Discord"
    slug = "discord"

    def required_credentials(self) -> dict[str, str | None]:
        return {
            "DISCORD_BOT_TOKEN": self.settings.discord_bot_token,
            "DISCORD_CHANNEL_ID": self.settings.discord_channel_id,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bot {self.settings.discord_bot_token}",
            "Content-Type": "application/json",
        }

    async def publish(self, message: str, link: str) -> dict[str, Any]:
        channel_id = self.settings.discord_channel_id or ""
        api = "https://discord.com/api/v10"

        response = await self.send(
            "POST",
            f"{api}/channels/{channel_id}/messages",
            headers=self._headers(),
            json={"content": message, "allowed_mentions": {"parse": []}},
        )
        result = response.json()

        message_id = result.get("id")
        if not message_id:
            raise PlatformError("discord did not return a message id")

        guild_id = None
        try:
            channel = await self.client.get(
                f"{api}/channels/{channel_id}", headers=self._headers()
            )
            if channel.status_code < 400:
                guild_id = (channel.json() or {}).get("guild_id")
        except Exception:
            guild_id = None

        posted_url = (
            f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
            if guild_id
            else None
        )
        return {"posted_url": posted_url, "public_access": True}
