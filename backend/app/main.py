from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import engine
from app.db.auto_migrate import sync_schema
from app.models.all_models import (  # noqa: F401 – ensure all models register on Base.metadata
    User, Trip, TripMember, TimelineItem, IdeaBinItem, TripDay, Notification,
    Group, GroupMember, IdeaVote, EventVote, IdeaTag,
    BrainstormBinItem, BrainstormMessage, ConciergeMessage,
    TokenUsage, GoogleMapsApiUsage, DayRoute,
    SubscriptionEvent, UsageCounter,
    UserIdentity, EmailVerification, PasswordReset, RefreshToken,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await sync_schema(conn, Base.metadata)

    # A5: one app-scoped httpx client for Google Maps single-hit calls.
    from app.services.google_maps import http as gmap_http
    gmap_http.set_shared_client(gmap_http.build_client())

    # A6: warm the shared LLM SDK client once at startup so the first request
    # doesn't pay construction latency and concurrent first requests can't race
    # into double-init. Best-effort — a missing key / SDK never blocks boot.
    if settings.LLM_ENABLED:
        try:
            from app.services.llm.registry import build_model
            build_model()._get_client()
        except Exception:
            logger.warning("LLM client warm-up skipped", exc_info=True)


    try:
        yield
    finally:
        client = gmap_http.get_shared_client()
        if client is not None:
            await client.aclose()
            gmap_http.set_shared_client(None)
        from app.services.cache import redis_cache
        await redis_cache.backend.aclose()


app = FastAPI(title="Roammate API", version="1.0.0", lifespan=lifespan)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.VALIDATE_SPEC:
    from app.middleware.spec_validation import SpecValidationMiddleware
    app.add_middleware(SpecValidationMiddleware)
    logger.info("SpecValidationMiddleware enabled — requests validated against docs/api/openapi.yaml")


_SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"

from app.api import registry, spec_router as _spec_router_module
app.include_router(_spec_router_module.build(_SPEC_PATH, registry.HANDLERS))
