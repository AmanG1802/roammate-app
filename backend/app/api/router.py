from fastapi import APIRouter
from app.api.endpoints import trips, events, users, notifications, groups

router = APIRouter()
router.include_router(trips.router, prefix="/trips", tags=["trips"])
router.include_router(events.router, prefix="/events", tags=["events"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(groups.router, prefix="/groups", tags=["groups"])
