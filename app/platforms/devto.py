import re
from typing import Any

from app.platforms.base import Platform, PlatformError

TITLE_LIMIT = 70


class DevToPlatform(Platform):
    name = "Dev.to"
    slug = "devto"

    def required_credentials(self) -> dict[str, str | None]:
        return {"DEVTO_API_KEY": self.settings.devto_api_key}

    async def publish(self, message: str, link: str) -> dict[str, Any]:
        response = await self.send(
            "POST",
            "https://dev.to/api/articles",
            headers={
                "api-key": self.settings.devto_api_key or "",
                "Content-Type": "application/json",
                "Accept": "application/vnd.forem.api-v1+json",
            },
            json={
                "article": {
                    "title": self._title(message, link),
                    "published": True,
                    "body_markdown": self._body(message, link),
                    "tags": self._tags(),
                }
            },
        )
        result = response.json()

        url = result.get("url") or result.get("canonical_url")
        if not url:
            raise PlatformError("dev.to did not return an article url")

        return {"posted_url": url, "public_access": bool(result.get("published", True))}

    @staticmethod
    def _title(message: str, link: str) -> str:
        headline = message.replace(link, "").strip(" -–—|:.")
        headline = re.sub(r"\s+", " ", headline)

        if len(headline) > TITLE_LIMIT:
            headline = headline[:TITLE_LIMIT].rsplit(" ", 1)[0].rstrip(" ,.;:")

        return headline or f"Update from {link.split('//')[-1].split('/')[0]}"

    @staticmethod
    def _body(message: str, link: str) -> str:
        text = message.replace(link, "").strip()
        return f"{text}\n\n[{link}]({link})\n"

    def _tags(self) -> list[str]:
        raw = [tag.strip().replace(" ", "") for tag in self.settings.devto_tags.split(",")]
        return [tag for tag in raw if tag][:4]
