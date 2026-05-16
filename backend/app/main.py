from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router
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
    yield


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


@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
