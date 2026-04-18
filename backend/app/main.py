from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router
from app.db.base_class import Base
from app.db.session import engine
from app.db.auto_migrate import sync_schema
from app.models.all_models import (
    User, Trip, TripMember, Event, IdeaBinItem, TripDay, Notification,
    Group, GroupMember, IdeaVote, EventVote, IdeaTag,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await sync_schema(conn, Base.metadata)
    yield


app = FastAPI(title="Roammate API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
