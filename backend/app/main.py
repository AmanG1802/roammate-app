from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router

app = FastAPI(title="Roammate API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.db.base_class import Base
from app.db.session import engine
from app.models.all_models import User, Trip, TripMember, Event, IdeaBinItem

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Dangerous, but useful for dev
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api")
