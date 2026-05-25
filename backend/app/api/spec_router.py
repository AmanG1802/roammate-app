"""
Spec-first router: builds a FastAPI APIRouter entirely from docs/api/openapi.yaml.

A route only exists on the running server if:
  1. It has an `operationId` in the spec.
  2. That operationId has a handler registered in registry.py.

If any spec operationId is missing from the registry, build() raises RuntimeError
at startup — not at request time.  This means:
  - Adding a spec operation without a handler → server refuses to start.
  - Writing a handler without a spec entry → it is never reachable (not registered).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yaml
from fastapi import APIRouter

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})


def _primary_status_code(operation: dict[str, Any]) -> int:
    for code in operation.get("responses", {}):
        try:
            n = int(code)
            if 200 <= n < 300:
                return n
        except (ValueError, TypeError):
            pass
    return 200


def build(spec_path: Path, handlers: dict[str, Callable]) -> APIRouter:
    """
    Parse spec_path and return an APIRouter whose routes are defined entirely
    by the spec's paths and operationIds.

    Raises ValueError  if any operation is missing an operationId.
    Raises RuntimeError if any operationId has no handler in `handlers`.
    """
    spec = yaml.safe_load(spec_path.read_text())
    router = APIRouter()
    missing: list[str] = []

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in _HTTP_METHODS or not isinstance(operation, dict):
                continue

            op_id = operation.get("operationId")
            if not op_id:
                raise ValueError(
                    f"Missing operationId for {method.upper()} {path} — "
                    "every operation in docs/api/openapi.yaml must have an operationId."
                )

            handler = handlers.get(op_id)
            if handler is None:
                missing.append(f"  {method.upper():7} {path}  (operationId={op_id!r})")
                continue

            route_fn = getattr(router, method)
            route_fn(
                path,
                operation_id=op_id,
                tags=operation.get("tags", []),
                summary=operation.get("summary", ""),
                status_code=_primary_status_code(operation),
            )(handler)

    if missing:
        raise RuntimeError(
            "Spec-first: the following spec operations have no handler in app/api/registry.py.\n"
            "Implement the handler and register it before the server can start:\n"
            + "\n".join(missing)
        )

    return router
