from __future__ import annotations

from typing import Any


class UpbitError(Exception):
    """Base exception for Upbit wrapper errors."""


class UpbitAuthError(UpbitError):
    """Raised when authentication setup is missing or invalid."""


class UpbitAPIError(UpbitError):
    """Raised when Upbit API returns an error response."""

    def __init__(
        self,
        status_code: int,
        name: str | int | None,
        message: str,
        payload: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.name = name
        self.message = message
        self.payload = payload
        super().__init__(f"[{status_code}] {name}: {message}")


class UpbitRateLimitError(UpbitAPIError):
    """Raised for rate-limit related responses such as 429 and 418."""

    def __init__(
        self,
        status_code: int,
        name: str | int | None,
        message: str,
        retry_after: int | None = None,
        payload: Any | None = None,
    ) -> None:
        self.retry_after = retry_after
        suffix = f" (retry_after={retry_after}s)" if retry_after is not None else ""
        super().__init__(status_code, name, f"{message}{suffix}", payload=payload)


class UpbitParseError(UpbitError):
    """Raised when API response payload cannot be parsed into typed models."""

    def __init__(self, model: str, field: str, message: str) -> None:
        self.model = model
        self.field = field
        self.message = message
        super().__init__(f"{model}.{field}: {message}")
