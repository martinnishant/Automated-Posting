import hashlib
import time
from typing import Any

from app.platforms.base import Platform, PlatformError


class MastodonPlatform(Platform):
    name = "Mastodon"
    slug = "mastodon"

    def required_credentials(self) -> dict[str, str | None]:
        return {"MASTODON_ACCESS_TOKEN": self.settings.mastodon_access_token}

    async def publish(self, message: str, link: str) -> dict[str, Any]:
        base = self.settings.mastodon_base_url.rstrip("/")

        response = await self.send(
            "POST",
            f"{base}/api/v1/statuses",
            headers={
                "Authorization": f"Bearer {self.settings.mastodon_access_token}",
                "Idempotency-Key": self._idempotency_key(message),
            },
            data={"status": message, "visibility": "public"},
        )
        result = response.json()

        url = result.get("url") or result.get("uri")
        if not url:
            raise PlatformError("mastodon did not return a status url")

        visibility = result.get("visibility", "public")
        return {"posted_url": url, "public_access": visibility == "public"}

    @staticmethod
    def _idempotency_key(message: str) -> str:
        digest = hashlib.sha256(f"{message}:{time.time() // 60}".encode()).hexdigest()
        return digest[:32]
