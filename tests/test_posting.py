import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

VALID_MESSAGE = "Check out our latest business platform and grow your online visibility. https://example.com"


@pytest.fixture
def client(monkeypatch):
    for key in (
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "DISCORD_BOT_TOKEN",
        "DISCORD_CHANNEL_ID",
        "MASTODON_ACCESS_TOKEN",
        "BLUESKY_HANDLE",
        "BLUESKY_APP_PASSWORD",
        "DEVTO_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_health_reports_every_platform(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["platforms"]) == 5


def test_success_returns_results_for_all_platforms(client):
    response = client.post("/posting", json={"message": VALID_MESSAGE})

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 5
    assert body["summary"]["total"] == 5


def test_unconfigured_platforms_fail_gracefully(client):
    body = client.post("/posting", json={"message": VALID_MESSAGE}).json()

    assert body["success"] is False
    assert all(result["status"] == "failed" for result in body["results"])
    assert all("Missing credentials" in result["error"] for result in body["results"])


def test_missing_message_is_rejected(client):
    response = client.post("/posting", json={})

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_message_over_limit_is_rejected(client):
    response = client.post("/posting", json={"message": "a" * 201})

    assert response.status_code == 422


def test_message_without_link_is_rejected(client):
    response = client.post("/posting", json={"message": "This message has no call to action"})

    assert response.status_code == 422
    assert "CTA link" in response.json()["errors"][0]["message"]


def test_multiple_links_are_rejected(client):
    message = "Two links here https://example.com and https://openai.com"
    response = client.post("/posting", json={"message": message})

    assert response.status_code == 422
    assert "multiple links" in response.json()["errors"][0]["message"]


def test_malformed_link_is_rejected(client):
    response = client.post("/posting", json={"message": "Bad link http://localhost"})

    assert response.status_code == 422
    assert "not a valid URL" in response.json()["errors"][0]["message"]


def test_boundary_length_is_accepted(client):
    message = "Grow faster today https://example.com" + "!" * 60
    assert len(message) <= 200

    response = client.post("/posting", json={"message": message})

    assert response.status_code == 200
