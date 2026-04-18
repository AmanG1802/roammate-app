from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func as sa_func

from app.db.session import get_db
from app.models.all_models import Notification, User
from app.schemas.notification import NotificationOut, UnreadCountOut, ActorSummary
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=List[NotificationOut])
async def list_notifications(
    limit: int = Query(30, ge=1, le=100),
    before_id: Optional[int] = Query(None, description="Return notifications with id < before_id for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Most recent notifications for the current user."""
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if before_id is not None:
        stmt = stmt.where(Notification.id < before_id)
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    actor_ids = {n.actor_id for n in rows if n.actor_id is not None}
    actors: dict[int, User] = {}
    if actor_ids:
        u_stmt = select(User).where(User.id.in_(actor_ids))
        for u in (await db.execute(u_stmt)).scalars().all():
            actors[u.id] = u

    return [
        NotificationOut(
            id=n.id,
            type=n.type,
            payload=n.payload or {},
            trip_id=n.trip_id,
            group_id=n.group_id,
            actor=ActorSummary.model_validate(actors[n.actor_id]) if n.actor_id in actors else None,
            read_at=n.read_at,
            created_at=n.created_at,
        )
        for n in rows
    ]


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(sa_func.count(Notification.id))
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
    )
    n = (await db.execute(stmt)).scalar_one()
    return UnreadCountOut(unread=n)


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    n = (await db.execute(stmt)).scalars().first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        await db.commit()


@router.post("/mark-all-read", status_code=204)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.commit()
