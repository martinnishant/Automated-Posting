import asyncio
import json
import sys

import httpx

from app.config import Settings
from app.services.posting_service import PostingService

MESSAGE = "Check out our latest business platform and grow your online visibility. https://example.com"
LINK = "https://example.com"


def mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith("/sendMessage"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {"message_id": 42, "chat": {"username": "demo_channel"}},
                },
            )
        if path.endswith("/channels/123/messages"):
            return httpx.Response(200, json={"id": "999888777"})
        if path.endswith("/channels/123"):
            return httpx.Response(200, json={"guild_id": "555444333"})
        if path.endswith("/api/v1/statuses"):
            return httpx.Response(
                200,
                json={
                    "url": "https://mastodon.social/@demo/1122334455",
                    "visibility": "public",
                },
            )
        if path.endswith("/com.atproto.server.createSession"):
            return httpx.Response(200, json={"accessJwt": "jwt", "did": "did:plc:demo"})
        if path.endswith("/com.atproto.repo.createRecord"):
            return httpx.Response(
                200,
                json={"uri": "at://did:plc:demo/app.bsky.feed.post/3kz7demo"},
            )
        if path.endswith("/api/articles"):
            return httpx.Response(
                201,
                json={"url": "https://dev.to/demo/grow-your-online-visibility-1abc", "published": True},
            )

        return httpx.Response(404, json={"error": "unmocked endpoint"})

    return httpx.MockTransport(handler)


async def main() -> None:
    settings = Settings(
        telegram_bot_token="demo",
        telegram_chat_id="@demo_channel",
        discord_bot_token="demo",
        discord_channel_id="123",
        mastodon_access_token="demo",
        bluesky_handle="demo.bsky.social",
        bluesky_app_password="demo-pass",
        devto_api_key="demo-key",
    )

    transport = mock_transport()
    original = httpx.AsyncClient

    class PatchedClient(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    httpx.AsyncClient = PatchedClient
    try:
        service = PostingService(settings)
        response = await service.publish(MESSAGE)
    finally:
        httpx.AsyncClient = original

    print(json.dumps(response.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
