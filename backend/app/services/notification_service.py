from typing import Iterable, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.all_models import Notification, TripMember
from app.schemas.notification import NotificationType


async def emit(
    db: AsyncSession,
    *,
    recipient_ids: Iterable[int],
    type: str,
    payload: dict[str, Any],
    actor_id: Optional[int] = None,
    trip_id: Optional[int] = None,
    group_id: Optional[int] = None,
) -> None:
    """Create one Notification row per recipient.

    Respects ``NotificationType.ENABLED`` — if the type is disabled the
    call is a silent no-op so callers don't need any conditional logic.
    """
    if not NotificationType.is_enabled(type):
        return

    seen: set[int] = set()
    for uid in recipient_ids:
        if uid is None or uid in seen:
            continue
        seen.add(uid)
        db.add(Notification(
            user_id=uid,
            type=type,
            payload=payload,
            trip_id=trip_id,
            group_id=group_id,
            actor_id=actor_id,
        ))


async def trip_member_ids(
    db: AsyncSession,
    trip_id: int,
    *,
    exclude_user_id: Optional[int] = None,
    accepted_only: bool = True,
) -> list[int]:
    """Return user_ids of trip members — handy for broadcasting trip-scoped notifications."""
    stmt = select(TripMember.user_id).where(TripMember.trip_id == trip_id)
    if accepted_only:
        stmt = stmt.where(TripMember.status == "accepted")
    rows = (await db.execute(stmt)).scalars().all()
    if exclude_user_id is not None:
        return [uid for uid in rows if uid != exclude_user_id]
    return list(rows)


async def all_trip_member_ids(
    db: AsyncSession,
    trip_id: int,
) -> list[int]:
    """Return ALL accepted member user_ids, including the caller."""
    stmt = select(TripMember.user_id).where(
        TripMember.trip_id == trip_id,
        TripMember.status == "accepted",
    )
    return list((await db.execute(stmt)).scalars().all())
