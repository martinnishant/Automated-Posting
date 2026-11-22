import re
from datetime import date as Date
from datetime import time as Time
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

URL_PATTERN = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?)]}'\""
MESSAGE_MAX_LENGTH = 200


class PostStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class PostRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MESSAGE_MAX_LENGTH)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        message = value.strip()

        if not message:
            raise ValueError("message must not be empty")

        if len(message) > MESSAGE_MAX_LENGTH:
            raise ValueError(f"message must not exceed {MESSAGE_MAX_LENGTH} characters")

        links = [link.rstrip(TRAILING_PUNCTUATION) for link in URL_PATTERN.findall(message)]

        if not links:
            raise ValueError("message must contain exactly one CTA link, none were found")

        if len(links) > 1:
            raise ValueError("message must contain exactly one CTA link, multiple links were found")

        if not cls._is_valid_url(links[0]):
            raise ValueError("the CTA link is not a valid URL")

        return message

    @staticmethod
    def _is_valid_url(link: str) -> bool:
        parsed = urlparse(link)
        host = parsed.hostname or ""

        return (
            parsed.scheme in {"http", "https"}
            and "." in host
            and not host.endswith(".")
            and all(part for part in host.split("."))
        )


class PostResult(BaseModel):
    platform: str
    status: PostStatus
    posted_url: str | None = None
    public_access: bool = False
    date: Date | None = None
    time: Time | None = None
    error: str | None = None


class PostingSummary(BaseModel):
    total: int
    succeeded: int
    failed: int

    @classmethod
    def from_results(cls, results: list[PostResult]) -> "PostingSummary":
        succeeded = sum(1 for result in results if result.status is PostStatus.SUCCESS)
        return cls(total=len(results), succeeded=succeeded, failed=len(results) - succeeded)


class PostingResponse(BaseModel):
    success: bool
    summary: PostingSummary
    results: list[PostResult]


class ValidationFailure(BaseModel):
    success: bool = False
    detail: str = "request validation failed"
    errors: list[dict[str, Any]]
