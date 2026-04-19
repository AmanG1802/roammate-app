"""Anthropic / Claude provider wrapper."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.services.llm.models.base import BaseLLMModel, LLMResponse


class ClaudeModel(BaseLLMModel):

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None  # lazy AsyncAnthropic

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    def provider_name(self) -> str:
        return "claude"

    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        system_text = ""
        chat_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        # Structured output via tool_use: define a single tool whose input
        # schema matches the Pydantic model, then force the model to call it.
        if response_schema is not None:
            tool_schema = response_schema.model_json_schema()
            kwargs["tools"] = [
                {
                    "name": "structured_response",
                    "description": "Return the structured response.",
                    "input_schema": tool_schema,
                }
            ]
            kwargs["tool_choice"] = {"type": "tool", "name": "structured_response"}

        async def _call():
            return await self._get_client().messages.create(**kwargs)

        resp = await self._retry(_call)

        content = ""
        if response_schema is not None:
            for block in resp.content:
                if getattr(block, "type", None) == "tool_use":
                    content = json.dumps(block.input)
                    break
        else:
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    content = block.text
                    break

        return LLMResponse(
            content=content,
            raw_response=resp.model_dump() if hasattr(resp, "model_dump") else {},
            input_tokens=getattr(resp.usage, "input_tokens", 0),
            output_tokens=getattr(resp.usage, "output_tokens", 0),
            model=self._model,
            provider="claude",
        )
