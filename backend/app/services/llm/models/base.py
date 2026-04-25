"""Base class for LLM provider wrappers.

Every provider (OpenAI, Anthropic, Google) implements ``BaseLLMModel``.
The return type is always ``LLMResponse`` so the upper layers never touch
provider-specific SDKs.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0  # seconds
RETRYABLE_STATUS_CODES = {429, 500, 503}


@dataclass
class LLMResponse:
    """Unified return value from any LLM provider."""

    content: str
    raw_response: dict[str, Any] = field(default_factory=dict, repr=False)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""


class BaseLLMModel(ABC):
    """Wrapper around a single LLM provider."""

    # Fallback output-token cap used when a caller does not pass max_tokens.
    # Per-operation overrides (extract, plan) live in app.core.config.
    DEFAULT_MAX_TOKENS: int = 2000

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Send messages and return a structured response.

        ``max_tokens=None`` means "use ``DEFAULT_MAX_TOKENS``" — concrete
        implementations are expected to resolve the fallback before calling
        the underlying SDK.
        """
        ...

    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def model_name(self) -> str:
        ...

    async def _retry(self, coro_factory, *, retries: int = MAX_RETRIES):
        """Call *coro_factory()* with exponential back-off on transient errors."""
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                return await coro_factory()
            except Exception as exc:
                last_exc = exc
                status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
                if status not in RETRYABLE_STATUS_CODES and attempt > 0:
                    raise
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                log.warning(
                    "LLM call attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, retries, exc, wait,
                )
                await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]
