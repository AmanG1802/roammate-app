"""OpenAI provider wrapper (GPT-4o, GPT-4o-mini, etc.)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.services.llm.models.base import BaseLLMModel, LLMResponse


def _ensure_additional_properties_false(schema: dict) -> dict:
    """Recursively set additionalProperties: false on all object schemas.

    OpenAI structured outputs require this on every object-type node.
    """
    if schema.get("type") == "object" or "properties" in schema:
        schema.setdefault("additionalProperties", False)
    for key in ("properties", "$defs", "definitions"):
        val = schema.get(key)
        if isinstance(val, dict):
            for v in val.values():
                if isinstance(v, dict):
                    _ensure_additional_properties_false(v)
    for key in ("items",):
        val = schema.get(key)
        if isinstance(val, dict):
            _ensure_additional_properties_false(val)
    for key in ("allOf", "anyOf", "oneOf"):
        val = schema.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    _ensure_additional_properties_false(item)
    return schema


class OpenAIModel(BaseLLMModel):

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None  # lazy AsyncOpenAI

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            from app.services.llm.models._clients import get_shared_client
            self._client = get_shared_client(
                "openai", self._api_key,
                lambda: AsyncOpenAI(api_key=self._api_key),
            )
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
            clean_schema = _ensure_additional_properties_false(
                response_schema.model_json_schema()
            )
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": clean_schema,
                    "strict": True,
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
