"""Unit tests for app.services.llm.models.base — LLMResponse and retry logic.

Tests the _retry method's exponential backoff, timeout, and retryable status codes.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.llm.models.base import (
    LLMResponse,
    BaseLLMModel,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    RETRYABLE_STATUS_CODES,
)


class ConcreteModel(BaseLLMModel):
    """Minimal concrete model for testing inherited _retry."""

    def provider_name(self) -> str:
        return "test"

    def model_name(self) -> str:
        return "test-model"

    async def complete(self, messages, **kwargs) -> LLMResponse:
        return LLMResponse(content="ok")


class TestLLMResponse:
    def test_llm_response_defaults(self):
        # Test 1a - Default field values
        resp = LLMResponse(content="hello")
        assert resp.content == "hello"
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0
        assert resp.model == ""
        assert resp.provider == ""
        assert resp.raw_response == {}

    def test_llm_response_custom_fields(self):
        # Test 1b - Custom values set correctly
        resp = LLMResponse(
            content="test",
            input_tokens=100,
            output_tokens=50,
            model="gpt-4o-mini",
            provider="openai",
            raw_response={"id": "123"},
        )
        assert resp.input_tokens == 100
        assert resp.output_tokens == 50
        assert resp.model == "gpt-4o-mini"
        assert resp.provider == "openai"
        assert resp.raw_response == {"id": "123"}


class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        # Test 1a - Successful call returns immediately
        model = ConcreteModel()
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            return "result"

        result = await model._retry(factory, timeout_s=5)
        assert result == "result"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_retryable_status_code(self):
        # Test 1b - Retries on 429/500/503 status codes
        model = ConcreteModel()
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                exc = Exception("rate limited")
                exc.status_code = 429
                raise exc
            return "success"

        with patch("app.services.llm.models.base.asyncio.sleep", new_callable=AsyncMock):
            result = await model._retry(factory, timeout_s=5)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_non_retryable_raises_after_first_retry(self):
        # Test 1c - Non-retryable status code raises after first retry attempt
        model = ConcreteModel()
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            exc = Exception("bad request")
            exc.status_code = 400
            raise exc

        with patch("app.services.llm.models.base.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="bad request"):
                await model._retry(factory, timeout_s=5)
        # First attempt always retries, second sees non-retryable and raises
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_timeout_raises_immediately(self):
        # Test 1d - asyncio.TimeoutError is NOT retried
        model = ConcreteModel()
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(100)

        with pytest.raises(asyncio.TimeoutError):
            await model._retry(factory, timeout_s=0.01)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausts_all_retries(self):
        # Test 1e - After MAX_RETRIES attempts, last exception is raised
        model = ConcreteModel()
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            exc = Exception("server error")
            exc.status_code = 500
            raise exc

        with patch("app.services.llm.models.base.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="server error"):
                await model._retry(factory, retries=3, timeout_s=5)
        assert call_count == 3


class TestRetryableStatusCodes:
    def test_retryable_status_codes(self):
        # Test 1a - Contains expected transient error codes
        assert 429 in RETRYABLE_STATUS_CODES
        assert 500 in RETRYABLE_STATUS_CODES
        assert 503 in RETRYABLE_STATUS_CODES

        # Test 1b - Client errors are not retryable
        assert 400 not in RETRYABLE_STATUS_CODES
        assert 401 not in RETRYABLE_STATUS_CODES
        assert 404 not in RETRYABLE_STATUS_CODES
