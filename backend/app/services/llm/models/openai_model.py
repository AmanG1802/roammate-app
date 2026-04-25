"""OpenAI provider wrapper (GPT-4o, GPT-4o-mini, etc.)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.services.llm.models.base import BaseLLMModel, LLMResponse


class OpenAIModel(BaseLLMModel):

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None  # lazy AsyncOpenAI

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    def provider_name(self) -> str:
        return "openai"

    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        effective_max_tokens = (
            max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS
        )

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
        }
        if response_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": response_schema.model_json_schema(),
                },
            }

        async def _call():
            return await self._get_client().chat.completions.create(**kwargs)

        resp = await self._retry(_call)
        usage = resp.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            raw_response=resp.model_dump() if hasattr(resp, "model_dump") else {},
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model=self._model,
            provider="openai",
        )
