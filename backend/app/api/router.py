from fastapi import APIRouter
from app.api.endpoints import trips, events, users

router = APIRouter()
router.include_router(trips.router, prefix="/trips", tags=["trips"])
router.include_router(events.router, prefix="/events", tags=["events"])
router.include_router(users.router, prefix="/users", tags=["users"])
