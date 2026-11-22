from abc import ABC, abstractmethod
from asyncio import TimeoutError as AsyncTimeoutError
from asyncio import wait_for
from datetime import datetime
from typing import Any

import httpx

from app.config import Settings
from app.schemas import PostResult, PostStatus


class PlatformError(Exception):
    ...


class Platform(ABC):
    name: str
    slug: str
    public_by_default: bool = True

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    @abstractmethod
    def required_credentials(self) -> dict[str, str | None]:
        ...

    @abstractmethod
    async def publish(self, message: str, link: str) -> dict[str, Any]:
        ...

    def missing_credentials(self) -> list[str]:
        return [key for key, value in self.required_credentials().items() if not value]

    async def run(self, message: str, link: str) -> PostResult:
        missing = self.missing_credentials()

        if missing:
            return self._failed(f"Missing credentials: {', '.join(missing)}")

        try:
            outcome = await wait_for(self.publish(message, link), timeout=self.settings.request_timeout)
        except AsyncTimeoutError:
            return self._failed(f"Request timed out after {self.settings.request_timeout:g}s")
        except PlatformError as exc:
            return self._failed(str(exc))
        except httpx.HTTPError as exc:
            return self._failed(f"Network error: {exc.__class__.__name__}")
        except Exception as exc:
            return self._failed(f"Unexpected error: {exc.__class__.__name__}")

        return self._succeeded(
            posted_url=outcome.get("posted_url"),
            public_access=bool(outcome.get("public_access", self.public_by_default)),
        )

    async def send(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        response = await self.client.request(method, url, **kwargs)

        if response.status_code >= 400:
            raise PlatformError(self.describe_error(response))

        return response

    @staticmethod
    def describe_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            for key in ("error", "description", "message", "detail", "errors"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return f"{response.status_code}: {value.strip()}"
                if isinstance(value, list) and value:
                    return f"{response.status_code}: {value[0]}"

        text = response.text.strip().replace("\n", " ")
        return f"{response.status_code}: {text[:180] or response.reason_phrase}"

    def _succeeded(self, posted_url: str | None, public_access: bool) -> PostResult:
        stamp = datetime.now(self.settings.tz)
        return PostResult(
            platform=self.name,
            status=PostStatus.SUCCESS,
            posted_url=posted_url,
            public_access=public_access,
            date=stamp.date(),
            time=stamp.time().replace(microsecond=0),
        )

    def _failed(self, error: str) -> PostResult:
        return PostResult(platform=self.name, status=PostStatus.FAILED, error=error)
