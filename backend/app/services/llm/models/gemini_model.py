"""Google Gemini provider wrapper."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.services.llm.models.base import BaseLLMModel, LLMResponse


class GeminiModel(BaseLLMModel):

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None  # lazy google.genai client

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def provider_name(self) -> str:
        return "gemini"

    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        from google.genai import types

        system_text = ""
        contents: list[types.Content] = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=msg["content"])])
                )

        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_text:
            config_kwargs["system_instruction"] = system_text
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        config = types.GenerateContentConfig(**config_kwargs)

        async def _call():
            return await self._get_client().aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

        resp = await self._retry(_call)

        content = resp.text or ""
        usage_meta = getattr(resp, "usage_metadata", None)
        input_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
        output_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0

        return LLMResponse(
            content=content,
            raw_response={},
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self._model,
            provider="gemini",
        )
