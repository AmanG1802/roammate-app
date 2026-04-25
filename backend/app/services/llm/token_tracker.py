"""Token usage tracking for LLM calls.

Phase 1: structured logging to stdout (queryable via any log aggregator).
Phase 2: add Redis counters (``user:{id}:tokens:{date}``) for rate limiting.
Phase 3: add Postgres ``token_usage`` table for dashboards and quotas.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.llm.models.base import LLMResponse

log = logging.getLogger("roammate.tokens")


def track(
    response: LLMResponse,
    *,
    operation: str,
    user_id: Optional[int] = None,
    trip_id: Optional[int] = None,
    source: Optional[str] = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured log line for a single LLM call.

    Fields are intentionally flat so they can be parsed by structured-log
    tooling (Datadog, Loki, CloudWatch Insights) without nested JSON.
    """
    fields: dict[str, Any] = {
        "op": operation,
        "provider": response.provider,
        "model": response.model,
        "tokens_in": response.input_tokens,
        "tokens_out": response.output_tokens,
        "tokens_total": response.input_tokens + response.output_tokens,
    }
    if user_id is not None:
        fields["user_id"] = user_id
    if trip_id is not None:
        fields["trip_id"] = trip_id
    if source:
        fields["source"] = source
    if extra:
        fields.update(extra)

    log.info("token_usage %s", " ".join(f"{k}={v}" for k, v in fields.items()))
