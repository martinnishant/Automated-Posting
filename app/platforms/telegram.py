from typing import Any

from app.platforms.base import Platform, PlatformError


class TelegramPlatform(Platform):
    name = "Telegram"
    slug = "telegram"

    def required_credentials(self) -> dict[str, str | None]:
        return {
            "TELEGRAM_BOT_TOKEN": self.settings.telegram_bot_token,
            "TELEGRAM_CHAT_ID": self.settings.telegram_chat_id,
        }

    async def publish(self, message: str, link: str) -> dict[str, Any]:
        chat_id = self.settings.telegram_chat_id or ""
        token = self.settings.telegram_bot_token
        base = f"https://api.telegram.org/bot{token}"

        response = await self.send(
            "POST",
            f"{base}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": False,
            },
        )
        payload = response.json()

        if not payload.get("ok"):
            raise PlatformError(payload.get("description", "telegram rejected the request"))

        result = payload.get("result") or {}
        return {
            "posted_url": await self._resolve_url(base, chat_id, result),
            "public_access": True,
        }

    async def _resolve_url(self, base: str, chat_id: str, result: dict[str, Any]) -> str | None:
        username = (result.get("chat") or {}).get("username")

        if not username and chat_id.startswith("@"):
            username = chat_id.lstrip("@")

        if not username:
            try:
                info = await self.client.get(f"{base}/getChat", params={"chat_id": chat_id})
                username = (info.json().get("result") or {}).get("username")
            except Exception:
                username = None

        message_id = result.get("message_id")
        return f"https://t.me/{username}/{message_id}" if username and message_id else None
