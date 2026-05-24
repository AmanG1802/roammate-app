"""Tutorial onboarding endpoints — see docs/[33].

All state is per-platform (web vs ios) and keyed by the X-Client-Platform
header so the iOS and Web tours progress independently.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.all_models import Trip, User
from app.services.tutorial_seed import (
    delete_tutorial_trip,
    find_existing_tutorial_trip,
    seed_tutorial_trip,
)

log = logging.getLogger(__name__)

router = APIRouter()


TutorialStatus = Literal["not_started", "in_progress", "completed", "skipped"]


def _platform_from_header(x_client_platform: Optional[str]) -> str:
    p = (x_client_platform or "").strip().lower()
    return "ios" if p == "ios" else "web"


def _status_col(platform: str) -> str:
    return "tutorial_status_ios" if platform == "ios" else "tutorial_status_web"


def _step_col(platform: str) -> str:
    return "tutorial_step_ios" if platform == "ios" else "tutorial_step_web"


def _get_status(user: User, platform: str) -> str:
    return getattr(user, _status_col(platform))


def _get_step(user: User, platform: str) -> int:
    return int(getattr(user, _step_col(platform)) or 0)


def _set_status(user: User, platform: str, value: str) -> None:
    setattr(user, _status_col(platform), value)


def _set_step(user: User, platform: str, value: int) -> None:
    setattr(user, _step_col(platform), int(value))


class TutorialStatusOut(BaseModel):
    status: TutorialStatus
    step: int
    trip_id: Optional[int] = None
    platform: Literal["web", "ios"]


class StepIn(BaseModel):
    step: int = Field(ge=0, le=100)


@router.get("/status", response_model=TutorialStatusOut)
async def get_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    platform = _platform_from_header(x_client_platform)
    trip = await find_existing_tutorial_trip(db, current_user)
    return TutorialStatusOut(
        status=_get_status(current_user, platform),  # type: ignore[arg-type]
        step=_get_step(current_user, platform),
        trip_id=trip.id if trip else None,
        platform=platform,  # type: ignore[arg-type]
    )


@router.post("/start", response_model=TutorialStatusOut)
async def start(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    platform = _platform_from_header(x_client_platform)
    trip = await find_existing_tutorial_trip(db, current_user)
    if trip is None:
        trip = await seed_tutorial_trip(db, current_user)
    _set_status(current_user, platform, "in_progress")
    _set_step(current_user, platform, max(1, _get_step(current_user, platform)))
    await db.commit()
    await db.refresh(current_user)
    return TutorialStatusOut(
        status=_get_status(current_user, platform),  # type: ignore[arg-type]
        step=_get_step(current_user, platform),
        trip_id=trip.id,
        platform=platform,  # type: ignore[arg-type]
    )


@router.patch("/step", response_model=TutorialStatusOut)
async def patch_step(
    body: StepIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    platform = _platform_from_header(x_client_platform)
    _set_step(current_user, platform, body.step)
    if _get_status(current_user, platform) == "not_started":
        _set_status(current_user, platform, "in_progress")
    await db.commit()
    trip = await find_existing_tutorial_trip(db, current_user)
    return TutorialStatusOut(
        status=_get_status(current_user, platform),  # type: ignore[arg-type]
        step=body.step,
        trip_id=trip.id if trip else None,
        platform=platform,  # type: ignore[arg-type]
    )


@router.post("/skip", response_model=TutorialStatusOut)
async def skip(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    platform = _platform_from_header(x_client_platform)
    _set_status(current_user, platform, "skipped")
    await db.commit()
    trip = await find_existing_tutorial_trip(db, current_user)
    return TutorialStatusOut(
        status="skipped",
        step=_get_step(current_user, platform),
        trip_id=trip.id if trip else None,
        platform=platform,  # type: ignore[arg-type]
    )


@router.post("/complete", response_model=TutorialStatusOut)
async def complete(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    platform = _platform_from_header(x_client_platform)
    _set_status(current_user, platform, "completed")
    trip = await find_existing_tutorial_trip(db, current_user)
    if trip is not None:
        trip.is_tutorial_completed = True
    await db.commit()
    return TutorialStatusOut(
        status="completed",
        step=_get_step(current_user, platform),
        trip_id=trip.id if trip else None,
        platform=platform,  # type: ignore[arg-type]
    )


@router.post("/replay", response_model=TutorialStatusOut)
async def replay(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    platform = _platform_from_header(x_client_platform)
    trip = await seed_tutorial_trip(db, current_user)  # idempotent: deletes + reseeds
    _set_status(current_user, platform, "in_progress")
    _set_step(current_user, platform, 1)
    await db.commit()
    return TutorialStatusOut(
        status="in_progress",
        step=1,
        trip_id=trip.id,
        platform=platform,  # type: ignore[arg-type]
    )


@router.post("/reset", response_model=TutorialStatusOut)
async def reset(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    """Reset the tour to a pristine pre-Welcome state for this platform.

    Deletes the tutorial trip and clears progress so the Welcome banner shows
    again (Web replay-from-settings). A fresh trip is seeded on the next /start.
    """
    platform = _platform_from_header(x_client_platform)
    await delete_tutorial_trip(db, current_user)
    _set_status(current_user, platform, "not_started")
    _set_step(current_user, platform, 0)
    await db.commit()
    return TutorialStatusOut(
        status="not_started",
        step=0,
        trip_id=None,
        platform=platform,  # type: ignore[arg-type]
    )


@router.delete("/trip", response_model=TutorialStatusOut)
async def delete_trip(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_client_platform: Optional[str] = Header(None, alias="X-Client-Platform"),
):
    platform = _platform_from_header(x_client_platform)
    await delete_tutorial_trip(db, current_user)
    return TutorialStatusOut(
        status=_get_status(current_user, platform),  # type: ignore[arg-type]
        step=_get_step(current_user, platform),
        trip_id=None,
        platform=platform,  # type: ignore[arg-type]
    )
