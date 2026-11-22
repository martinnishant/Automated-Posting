import asyncio
import logging

import httpx

from app.config import Settings
from app.platforms.base import Platform
from app.platforms.registry import build_platforms
from app.schemas import (
    TRAILING_PUNCTUATION,
    URL_PATTERN,
    PostingResponse,
    PostingSummary,
    PostResult,
    PostStatus,
)

logger = logging.getLogger("posting")


class PostingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def publish(self, message: str) -> PostingResponse:
        link = self.extract_link(message)

        async with httpx.AsyncClient(timeout=self.settings.request_timeout) as client:
            platforms = build_platforms(self.settings, client)
            logger.info("dispatching to %d platforms", len(platforms))
            results = await asyncio.gather(
                *(platform.run(message, link) for platform in platforms),
                return_exceptions=True,
            )

        normalised = [self._normalise(item) for item in results]
        succeeded = sum(1 for item in normalised if item.status is PostStatus.SUCCESS)
        logger.info("completed: %d succeeded, %d failed", succeeded, len(normalised) - succeeded)

        return PostingResponse(
            success=succeeded == len(normalised),
            summary=PostingSummary.from_results(normalised),
            results=normalised,
        )

    @staticmethod
    def extract_link(message: str) -> str:
        return URL_PATTERN.findall(message)[0].rstrip(TRAILING_PUNCTUATION)

    @staticmethod
    def _normalise(item: object) -> PostResult:
        if isinstance(item, PostResult):
            return item

        if isinstance(item, BaseException):
            return PostResult(
                platform="unknown",
                status=PostStatus.FAILED,
                error=f"Unhandled error: {item.__class__.__name__}",
            )

        return PostResult(platform="unknown", status=PostStatus.FAILED, error="no result returned")


def platform_status(settings: Settings) -> tuple[list[str], list[str]]:
    platforms: list[Platform] = build_platforms(settings, client=None)
    registered = [platform.slug for platform in platforms]
    configured = [platform.slug for platform in platforms if not platform.missing_credentials()]
    return registered, configured
