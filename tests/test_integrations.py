import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.services.posting_service import PostingService

MESSAGE = "Check out our latest business platform and grow your online visibility. https://example.com"

SETTINGS = Settings(
    telegram_bot_token="t",
    telegram_chat_id="@demo",
    discord_bot_token="d",
    discord_channel_id="123",
    mastodon_access_token="m",
    bluesky_handle="demo.bsky.social",
    bluesky_app_password="pw",
    devto_api_key="k",
)


def build_transport(failing: set[str] | None = None) -> httpx.MockTransport:
    failing = failing or set()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if "telegram" in str(request.url):
            if "telegram" in failing:
                return httpx.Response(401, json={"ok": False, "description": "Unauthorized"})
            return httpx.Response(
                200, json={"ok": True, "result": {"message_id": 1, "chat": {"username": "demo"}}}
            )
        if path.endswith("/messages"):
            if "discord" in failing:
                return httpx.Response(403, json={"message": "Missing Access"})
            return httpx.Response(200, json={"id": "2"})
        if path.endswith("/channels/123"):
            return httpx.Response(200, json={"guild_id": "9"})
        if path.endswith("/api/v1/statuses"):
            if "mastodon" in failing:
                return httpx.Response(422, json={"error": "Validation failed"})
            return httpx.Response(200, json={"url": "https://mastodon.social/@demo/3", "visibility": "public"})
        if path.endswith("createSession"):
            return httpx.Response(200, json={"accessJwt": "jwt", "did": "did:plc:demo"})
        if path.endswith("createRecord"):
            if "bluesky" in failing:
                return httpx.Response(400, json={"message": "InvalidRequest"})
            return httpx.Response(200, json={"uri": "at://did:plc:demo/app.bsky.feed.post/4"})
        if path.endswith("/api/articles"):
            if "devto" in failing:
                return httpx.Response(401, json={"error": "unauthorized"})
            return httpx.Response(201, json={"url": "https://dev.to/demo/post-5", "published": True})

        return httpx.Response(404, json={"error": "unmocked"})

    return httpx.MockTransport(handler)


def run_service(monkeypatch, failing: set[str] | None = None):
    transport = build_transport(failing)
    real_client = httpx.AsyncClient

    class PatchedClient(real_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", PatchedClient)
    return asyncio.run(PostingService(SETTINGS).publish(MESSAGE))


def test_all_platforms_succeed(monkeypatch):
    response = run_service(monkeypatch)

    assert response.success is True
    assert response.summary.succeeded == 5
    assert all(result.posted_url for result in response.results)


def test_single_failure_does_not_block_others(monkeypatch):
    response = run_service(monkeypatch, failing={"mastodon"})

    assert response.success is False
    assert response.summary.succeeded == 4
    mastodon = next(r for r in response.results if r.platform == "Mastodon")
    assert mastodon.status == "failed"
    assert mastodon.posted_url is None
    assert mastodon.date is None
    assert "422" in mastodon.error


def test_multiple_failures_are_isolated(monkeypatch):
    response = run_service(monkeypatch, failing={"discord", "devto"})

    failed = [r.platform for r in response.results if r.status == "failed"]
    assert sorted(failed) == ["Dev.to", "Discord"]
    assert response.summary.succeeded == 3


def test_results_are_json_serialisable(monkeypatch):
    response = run_service(monkeypatch)
    payload = json.loads(json.dumps(response.model_dump(mode="json")))

    assert payload["results"][0]["date"] == payload["results"][1]["date"]
    assert isinstance(payload["results"][0]["time"], str)


def test_link_is_extracted_without_trailing_punctuation():
    link = PostingService.extract_link("Read this now https://example.com/page).")

    assert link == "https://example.com/page"
