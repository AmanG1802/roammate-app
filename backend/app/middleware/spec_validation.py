"""
Runtime request validation middleware: checks incoming requests against
docs/api/openapi.yaml.  Enabled only when VALIDATE_SPEC=true (dev/staging).
Never enable in production — adds latency.
"""
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_SPEC_PATH = Path(__file__).resolve().parent.parent.parent / "openapi.yaml"


# ── Runtime request validation middleware ────────────────────────────────────

_openapi = None


def _get_openapi():
    global _openapi
    if _openapi is None:
        from openapi_core import OpenAPI
        _openapi = OpenAPI.from_file_path(str(_SPEC_PATH))
    return _openapi


class SpecValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/openapi.json", "/docs", "/redoc", "/health"):
            return await call_next(request)

        try:
            from openapi_core.contrib.starlette import StarletteOpenAPIRequest
            openapi_request = StarletteOpenAPIRequest(request)
            _get_openapi().validate_request(openapi_request)
        except Exception as exc:
            return JSONResponse(
                status_code=422,
                content={"detail": f"[SpecValidation] {exc}"},
            )

        return await call_next(request)
