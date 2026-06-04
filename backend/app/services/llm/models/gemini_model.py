"""Google Gemini provider wrapper."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from app.services.llm.models.base import BaseLLMModel, LLMResponse


def _clean_schema_for_gemini(schema: dict) -> dict:
    """Make a Pydantic JSON schema compatible with Gemini's structured output.

    Gemini rejects ``additionalProperties`` and ``$ref`` / ``$defs``.  This
    helper inlines all ``$defs`` references and then strips
    ``additionalProperties`` recursively.
    """
    defs = schema.pop("$defs", schema.pop("definitions", None))
    if defs:
        raw = json.dumps(schema)
        for name, definition in defs.items():
            ref = json.dumps({"$ref": f"#/$defs/{name}"})
            raw = raw.replace(ref, json.dumps(definition))
            ref_alt = json.dumps({"$ref": f"#/definitions/{name}"})
            raw = raw.replace(ref_alt, json.dumps(definition))
        schema = json.loads(raw)

    _strip_additional_properties(schema)
    return schema


def _strip_additional_properties(schema: dict) -> None:
    """Recursively remove 'additionalProperties' keys."""
    schema.pop("additionalProperties", None)
    for key in ("properties", "items"):
        val = schema.get(key)
        if isinstance(val, dict):
            for v in val.values():
                if isinstance(v, dict):
                    _strip_additional_properties(v)
    for key in ("allOf", "anyOf", "oneOf"):
        val = schema.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    _strip_additional_properties(item)


class GeminiModel(BaseLLMModel):

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None  # lazy google.genai client

    def _get_client(self):  # pragma: no cover — SDK init
        if self._client is None:
            from google import genai
            from app.services.llm.models._clients import get_shared_client
            self._client = get_shared_client(
                "gemini", self._api_key,
                lambda: genai.Client(api_key=self._api_key),
            )
        return self._client

    def provider_name(self) -> str:
        return "gemini"

    def model_name(self) -> str:
        return self._model

    async def complete(  # pragma: no cover — Google GenAI SDK call
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        from google.genai import types

        effective_max_tokens = (
            max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS
        )

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
            "max_output_tokens": effective_max_tokens,
        }
        if system_text:
            config_kwargs["system_instruction"] = system_text
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            clean_schema = _clean_schema_for_gemini(
                response_schema.model_json_schema()
            )
            config_kwargs["response_schema"] = clean_schema

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
