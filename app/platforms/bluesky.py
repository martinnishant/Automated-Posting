from datetime import datetime, timezone
from typing import Any

from app.platforms.base import Platform, PlatformError


class BlueskyPlatform(Platform):
    name = "Bluesky"
    slug = "bluesky"

    def required_credentials(self) -> dict[str, str | None]:
        return {
            "BLUESKY_HANDLE": self.settings.bluesky_handle,
            "BLUESKY_APP_PASSWORD": self.settings.bluesky_app_password,
        }

    async def publish(self, message: str, link: str) -> dict[str, Any]:
        pds = "https://bsky.social"
        session = await self.send(
            "POST",
            f"{pds}/xrpc/com.atproto.server.createSession",
            json={
                "identifier": self.settings.bluesky_handle,
                "password": self.settings.bluesky_app_password,
            },
        )
        session_data = session.json()
        token = session_data.get("accessJwt")
        did = session_data.get("did")

        if not token or not did:
            raise PlatformError("bluesky session could not be created")

        created = await self.send(
            "POST",
            f"{pds}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": message,
                    "createdAt": self._timestamp(),
                    "facets": [self._link_facet(message, link)],
                },
            },
        )
        record = created.json()
        uri = record.get("uri", "")
        rkey = uri.rsplit("/", 1)[-1] if uri else None

        return {
            "posted_url": f"https://bsky.app/profile/{did}/post/{rkey}" if rkey else None,
            "public_access": True,
        }

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _link_facet(message: str, link: str) -> dict[str, Any]:
        start = message.find(link)
        byte_start = len(message[: max(start, 0)].encode("utf-8"))
        byte_end = byte_start + len(link.encode("utf-8"))

        return {
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
        }
