from datetime import datetime, time, timedelta
from typing import Any


def _parse_time(v: Any) -> time | None:
    """Coerce a wire value to ``datetime.time`` or None.

    Accepts ``None``, an already-parsed ``time``, or an ``"HH:MM:SS"`` /
    ``"HH:MM"`` string. Raises 422 on anything else so concierge / loose
    callers can't smuggle garbage into TIME columns.
    """
    if v is None:
        return None
    if isinstance(v, time):
        return v
    if isinstance(v, str):
        try:
            return time.fromisoformat(v)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid time format: {v!r}") from exc
    raise HTTPException(status_code=422, detail=f"Invalid time value type: {type(v).__name__}")

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api import pagination
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func as sa_func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.db.session import get_db
from app.models.all_models import Trip, TripMember, User, IdeaBinItem as IdeaBinItemModel, TripDay, TimelineItem as EventModel, Notification, IdeaVote, EventVote, PLACE_FIELDS
from app.schemas.trip import (
    Trip as TripSchema, TripCreate, TripUpdate, IngestRequest, IdeaBinItem,
    TripMemberOut, InviteRequest, TripDayCreate, TripDayOut,
    InvitationOut, TripSummary, InviterSummary,
    RoleUpdateRequest, VALID_ROLES, TripWithRole,
)
from app.services.idea_bin import idea_bin_service
from app.services import notification_service
from app.services import entitlements
from app.services.vote_tally import tally_votes
from app.schemas.notification import NotificationType
from app.api.deps import get_current_user


async def _sync_trip_end_date(db: AsyncSession, trip_id: int) -> None:
    """Recompute Trip.end_date = start_date + (TripDay count - 1)."""
    trip = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalars().first()
    if not trip or not trip.start_date:
        return
    day_count = (await db.execute(
        select(sa_func.count(TripDay.id)).where(TripDay.trip_id == trip_id)
    )).scalar_one()
    if day_count > 0:
        sd = trip.start_date.date() if hasattr(trip.start_date, 'date') else trip.start_date
        trip.end_date = datetime.combine(sd + timedelta(days=day_count - 1), datetime.min.time())

router = APIRouter()

@router.get("/", response_model=List[TripWithRole])
async def get_my_trips(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int | None = None,
    cursor: str | None = None,
):
    """
    Get all trips where the current user is an accepted member,
    including the user's role in each trip.
    """
    stmt = (
        select(Trip, TripMember.role)
        .join(TripMember)
        .where(TripMember.user_id == current_user.id, TripMember.status == "accepted")
    )
    # Opt-in cursor pagination (D3). Default (no params) returns the full list,
    # unchanged for current clients; the body stays a bare array either way and
    # the next cursor is advertised via response headers.
    if pagination.is_paginated(limit, cursor):
        eff_limit = pagination.clamp_limit(limit)
        stmt = pagination.apply_keyset(stmt, Trip.id, cursor=cursor, limit=eff_limit, descending=True)
        rows = (await db.execute(stmt)).all()
        page, has_more = pagination.page_slice(rows, eff_limit)
        response.headers["X-Has-More"] = "true" if has_more else "false"
        if page and has_more:
            response.headers["X-Next-Cursor"] = pagination.encode_cursor(page[-1][0].id)
        rows = page
    else:
        rows = (await db.execute(stmt)).all()
    return [
        TripWithRole(
            id=trip.id,
            name=trip.name,
            start_date=trip.start_date,
            end_date=trip.end_date,
            timezone=trip.timezone or "UTC",
            created_at=trip.created_at,
            created_by_id=trip.created_by_id,
            my_role=role,
            is_tutorial=bool(trip.is_tutorial),
            is_tutorial_completed=bool(trip.is_tutorial_completed),
        )
        for trip, role in rows
    ]

@router.post("/", response_model=TripSchema)
async def create_trip(
    trip_in: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new trip and add the current user as the owner.
    Auto-creates Day 1 from the start_date if provided.
    """
    await entitlements.enforce_active_trip(db, current_user)
    trip = Trip(
        name=trip_in.name,
        start_date=trip_in.start_date,
        end_date=trip_in.end_date,
        timezone=trip_in.timezone,
        destination_city=trip_in.destination_city,
        country_code=trip_in.country_code,
        destination_lat=trip_in.destination_lat,
        destination_lng=trip_in.destination_lng,
        created_by_id=current_user.id
    )
    db.add(trip)
    await db.flush()

    member = TripMember(
        trip_id=trip.id,
        user_id=current_user.id,
        role="admin"
    )
    db.add(member)

    if trip_in.start_date:
        day1 = TripDay(
            trip_id=trip.id,
            date=trip_in.start_date.date() if hasattr(trip_in.start_date, 'date') else trip_in.start_date,
            day_number=1,
        )
        db.add(day1)
        await db.flush()
        await _sync_trip_end_date(db, trip.id)

    await notification_service.emit(
        db,
        recipient_ids=[current_user.id],
        type=NotificationType.TRIP_CREATED,
        payload={"trip_name": trip.name},
        actor_id=current_user.id,
        trip_id=trip.id,
    )

    await db.commit()
    await db.refresh(trip)
    return trip


@router.get("/invitations/pending", response_model=List[InvitationOut])
async def get_my_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all pending trip invitations for the current user."""
    stmt = (
        select(TripMember)
        .where(TripMember.user_id == current_user.id, TripMember.status == "invited")
        .options(selectinload(TripMember.trip))
    )
    members = (await db.execute(stmt)).scalars().all()

    # Load every relevant trip's admin (with user) in one query rather than one
    # per invitation (D5); first admin per trip wins, matching prior behaviour.
    trip_ids = [m.trip_id for m in members]
    admins_by_trip: dict[int, TripMember] = {}
    if trip_ids:
        admin_rows = (await db.execute(
            select(TripMember)
            .where(TripMember.trip_id.in_(trip_ids), TripMember.role == "admin")
            .options(selectinload(TripMember.user))
        )).scalars().all()
        for a in admin_rows:
            admins_by_trip.setdefault(a.trip_id, a)

    results: list[dict] = []
    for m in members:
        owner_member = admins_by_trip.get(m.trip_id)
        inviter = None
        if owner_member and owner_member.user:
            inviter = InviterSummary(name=owner_member.user.name or "", email=owner_member.user.email)
        results.append(InvitationOut(
            id=m.id,
            trip_id=m.trip_id,
            role=m.role,
            trip=TripSummary(id=m.trip.id, name=m.trip.name, start_date=m.trip.start_date),
            inviter=inviter,
        ))
    return results


@router.post("/invitations/{member_id}/accept", response_model=TripMemberOut)
async def accept_invitation(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a pending trip invitation."""
    stmt = (
        select(TripMember)
        .where(TripMember.id == member_id, TripMember.user_id == current_user.id, TripMember.status == "invited")
        .options(selectinload(TripMember.user))
    )
    member = (await db.execute(stmt)).scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="Invitation not found")

    member.status = "accepted"
    await db.flush()

    trip_stmt = select(Trip).where(Trip.id == member.trip_id)
    trip = (await db.execute(trip_stmt)).scalars().first()
    trip_name = trip.name if trip else ""

    await notification_service.emit(
        db,
        recipient_ids=[current_user.id],
        type=NotificationType.INVITE_ACCEPTED,
        payload={"trip_name": trip_name, "self": True},
        actor_id=current_user.id,
        trip_id=member.trip_id,
    )
    others = await notification_service.trip_member_ids(
        db, member.trip_id, exclude_user_id=current_user.id
    )
    if others:
        await notification_service.emit(
            db,
            recipient_ids=others,
            type=NotificationType.INVITE_ACCEPTED,
            payload={"trip_name": trip_name, "joined_user_name": current_user.name or ""},
            actor_id=current_user.id,
            trip_id=member.trip_id,
        )

    await db.commit()
    await db.refresh(member)

    stmt = (
        select(TripMember)
        .where(TripMember.id == member.id)
        .options(selectinload(TripMember.user))
    )
    return (await db.execute(stmt)).scalars().first()


@router.delete("/invitations/{member_id}/decline", status_code=204)
async def decline_invitation(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decline (remove) a pending trip invitation."""
    stmt = select(TripMember).where(
        TripMember.id == member_id,
        TripMember.user_id == current_user.id,
        TripMember.status == "invited",
    )
    member = (await db.execute(stmt)).scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="Invitation not found")

    trip_id = member.trip_id
    trip_stmt = select(Trip).where(Trip.id == trip_id)
    trip = (await db.execute(trip_stmt)).scalars().first()
    trip_name = trip.name if trip else ""

    admin_stmt = select(TripMember.user_id).where(
        TripMember.trip_id == trip_id, TripMember.role == "admin"
    )
    admin_ids = [uid for uid in (await db.execute(admin_stmt)).scalars().all() if uid != current_user.id]

    await db.delete(member)

    if admin_ids:
        await notification_service.emit(
            db,
            recipient_ids=admin_ids,
            type=NotificationType.INVITE_DECLINED,
            payload={"trip_name": trip_name, "declined_user_name": current_user.name or ""},
            actor_id=current_user.id,
            trip_id=trip_id,
        )
    await db.commit()


@router.patch("/{trip_id}", response_model=TripSchema)
async def update_trip(
    trip_id: int,
    update: TripUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update trip metadata (name, start_date, end_date).

    When start_date changes, all TripDay dates are shifted by the same delta
    so the itinerary moves with the new start date.
    """
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this trip")

    stmt = select(Trip).where(Trip.id == trip_id)
    trip = (await db.execute(stmt)).scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    renamed_from: Optional[str] = None
    date_changed: bool = False

    if update.name is not None and update.name != trip.name:
        renamed_from = trip.name
        trip.name = update.name

    if update.start_date is not None:
        new_start = update.start_date.date() if hasattr(update.start_date, 'date') else update.start_date
        old_start = trip.start_date.date() if trip.start_date and hasattr(trip.start_date, 'date') else trip.start_date

        # Preload every event for the trip once and bucket by day_date, instead
        # of issuing one SELECT per day inside the shift loop (D9 — removes the
        # N per-day event subqueries). The careful per-day ordering + flush is
        # kept so the (trip_id, date) unique constraint never collides mid-shift.
        events_by_day: dict = {}
        if old_start is None or new_start != old_start:
            all_events = (await db.execute(
                select(EventModel).where(EventModel.trip_id == trip_id)
            )).scalars().all()
            for evt in all_events:
                events_by_day.setdefault(evt.day_date, []).append(evt)

        if old_start and new_start != old_start:
            date_changed = True
            delta = new_start - old_start
            # Shift all TripDay dates AND their events' day_date by the same delta.
            # Process in reverse order (latest first) when shifting forward, or
            # in forward order (earliest first) when shifting backward, to avoid
            # unique-constraint collisions on (trip_id, date).
            day_stmt = (
                select(TripDay)
                .where(TripDay.trip_id == trip_id)
                .order_by(TripDay.date.desc() if delta.days > 0 else TripDay.date.asc())
            )
            days = (await db.execute(day_stmt)).scalars().all()
            for d in days:
                old_day_date = d.date
                new_day_date = old_day_date + delta
                for evt in events_by_day.get(old_day_date, []):
                    evt.day_date = new_day_date
                d.date = new_day_date
                await db.flush()
        elif not old_start:
            # Trip had no start_date before (legacy / Plan-Trip path that omitted
            # one). Rebase every existing TripDay from new_start by day_number so
            # Day 1 → new_start, Day N → new_start + (N-1)d. TimelineItems are
            # linked by day_date string, so rewrite those too.
            date_changed = True
            day_stmt = (
                select(TripDay)
                .where(TripDay.trip_id == trip_id)
                .order_by(TripDay.day_number.desc())
            )
            days = (await db.execute(day_stmt)).scalars().all()
            for d in days:
                old_day_date = d.date
                new_day_date = new_start + timedelta(days=max(d.day_number, 1) - 1)
                if old_day_date == new_day_date:
                    continue
                for evt in events_by_day.get(old_day_date, []):
                    evt.day_date = new_day_date
                d.date = new_day_date
                await db.flush()

        trip.start_date = update.start_date
        await db.flush()
        await _sync_trip_end_date(db, trip_id)

    if update.end_date is not None:
        trip.end_date = update.end_date
    if update.timezone is not None:
        trip.timezone = update.timezone

    all_members = await notification_service.all_trip_member_ids(db, trip_id)
    others = [uid for uid in all_members if uid != current_user.id]
    if renamed_from is not None:
        await notification_service.emit(
            db,
            recipient_ids=[current_user.id],
            type=NotificationType.TRIP_RENAMED,
            payload={"from": renamed_from, "to": trip.name, "actor_name": current_user.name or "", "self": True},
            actor_id=current_user.id,
            trip_id=trip_id,
        )
        if others:
            await notification_service.emit(
                db,
                recipient_ids=others,
                type=NotificationType.TRIP_RENAMED,
                payload={"from": renamed_from, "to": trip.name, "actor_name": current_user.name or ""},
                actor_id=current_user.id,
                trip_id=trip_id,
            )
    if date_changed:
        await notification_service.emit(
            db,
            recipient_ids=[current_user.id],
            type=NotificationType.TRIP_DATE_CHANGED,
            payload={
                "trip_name": trip.name,
                "new_start_date": trip.start_date.isoformat() if trip.start_date else None,
                "actor_name": current_user.name or "",
                "self": True,
            },
            actor_id=current_user.id,
            trip_id=trip_id,
        )
        if others:
            await notification_service.emit(
                db,
                recipient_ids=others,
                type=NotificationType.TRIP_DATE_CHANGED,
                payload={
                    "trip_name": trip.name,
                    "new_start_date": trip.start_date.isoformat() if trip.start_date else None,
                    "actor_name": current_user.name or "",
                },
                actor_id=current_user.id,
                trip_id=trip_id,
            )

    await db.commit()
    await db.refresh(trip)
    return trip

@router.get("/{trip_id}", response_model=TripSchema)
async def get_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check membership
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@router.delete("/{trip_id}", status_code=204)
async def delete_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a trip and all its related data. Caller must be admin."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete a trip")

    stmt = select(Trip).where(Trip.id == trip_id)
    trip = (await db.execute(stmt)).scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    all_members = await notification_service.all_trip_member_ids(db, trip_id)
    others = [uid for uid in all_members if uid != current_user.id]
    await notification_service.emit(
        db,
        recipient_ids=[current_user.id],
        type=NotificationType.TRIP_DELETED,
        payload={"trip_name": trip.name, "actor_name": current_user.name or "", "self": True},
        actor_id=current_user.id,
    )
    if others:
        await notification_service.emit(
            db,
            recipient_ids=others,
            type=NotificationType.TRIP_DELETED,
            payload={"trip_name": trip.name, "actor_name": current_user.name or ""},
            actor_id=current_user.id,
        )
    await db.flush()
    await db.execute(
        update(Notification).where(Notification.trip_id == trip_id).values(trip_id=None)
    )

    # Bulk-delete children in one statement each rather than looping per row
    # (D7). Children before parent so FK constraints hold; vote rows cascade
    # from their event/idea FK (ON DELETE CASCADE) as before.
    await db.execute(delete(EventModel).where(EventModel.trip_id == trip_id))
    await db.execute(delete(IdeaBinItemModel).where(IdeaBinItemModel.trip_id == trip_id))
    await db.execute(delete(TripDay).where(TripDay.trip_id == trip_id))
    await db.execute(delete(TripMember).where(TripMember.trip_id == trip_id))

    await db.delete(trip)
    await db.commit()


@router.get("/{trip_id}/ideas", response_model=List[IdeaBinItem])
async def get_idea_bin(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(IdeaBinItemModel).where(IdeaBinItemModel.trip_id == trip_id)
    ideas = (await db.execute(stmt)).scalars().all()

    idea_ids = [i.id for i in ideas]
    if not idea_ids:
        return []

    tallies = await tally_votes(db, IdeaVote, IdeaVote.idea_id, idea_ids, current_user.id)

    results = []
    for i in ideas:
        up, down, mine = tallies.get(i.id, (0, 0, 0))
        data = IdeaBinItem.model_validate(i, from_attributes=True).model_dump()
        data.update(up=up, down=down, my_vote=mine)
        results.append(IdeaBinItem.model_validate(data))
    return results


@router.get("/{trip_id}/members", response_model=List[TripMemberOut])
async def get_trip_members(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all members of a trip (with user details). Caller must be a member."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = (
        select(TripMember)
        .where(TripMember.trip_id == trip_id)
        .options(selectinload(TripMember.user))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{trip_id}/members/{member_id}/role", response_model=TripMemberOut)
async def update_member_role(
    trip_id: int,
    member_id: int,
    body: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a member's role. Caller must be admin."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change roles")

    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    stmt = (
        select(TripMember)
        .where(TripMember.id == member_id, TripMember.trip_id == trip_id)
        .options(selectinload(TripMember.user))
    )
    target = (await db.execute(stmt)).scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    old_role = target.role
    target.role = body.role

    if target.user_id != current_user.id and old_role != body.role:
        trip_stmt = select(Trip).where(Trip.id == trip_id)
        trip_row = (await db.execute(trip_stmt)).scalars().first()
        await notification_service.emit(
            db,
            recipient_ids=[target.user_id],
            type=NotificationType.MEMBER_ROLE_CHANGED,
            payload={
                "trip_name": trip_row.name if trip_row else "",
                "new_role": body.role,
                "actor_name": current_user.name or "",
            },
            actor_id=current_user.id,
            trip_id=trip_id,
        )

    await db.commit()
    await db.refresh(target)

    stmt = (
        select(TripMember)
        .where(TripMember.id == target.id)
        .options(selectinload(TripMember.user))
    )
    return (await db.execute(stmt)).scalars().first()


@router.delete("/{trip_id}/members/{member_id}", status_code=204)
async def remove_trip_member(
    trip_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from the trip. Caller must be admin and cannot remove themselves."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove members")

    stmt = select(TripMember).where(TripMember.id == member_id, TripMember.trip_id == trip_id)
    target = (await db.execute(stmt)).scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    if target.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the trip")

    removed_user_stmt = select(User).where(User.id == target.user_id)
    removed_user = (await db.execute(removed_user_stmt)).scalars().first()
    trip_stmt = select(Trip).where(Trip.id == trip_id)
    trip_row = (await db.execute(trip_stmt)).scalars().first()
    trip_name = trip_row.name if trip_row else ""

    remaining = await notification_service.trip_member_ids(
        db, trip_id, exclude_user_id=current_user.id
    )
    remaining = [uid for uid in remaining if uid != target.user_id]

    await notification_service.emit(
        db,
        recipient_ids=[target.user_id],
        type=NotificationType.MEMBER_REMOVED,
        payload={"trip_name": trip_name, "actor_name": current_user.name or "", "self": True},
        actor_id=current_user.id,
        trip_id=trip_id,
    )
    if remaining:
        await notification_service.emit(
            db,
            recipient_ids=remaining,
            type=NotificationType.MEMBER_REMOVED,
            payload={
                "trip_name": trip_name,
                "removed_user_name": (removed_user.name if removed_user else "") or "",
                "actor_name": current_user.name or "",
            },
            actor_id=current_user.id,
            trip_id=trip_id,
        )

    await db.delete(target)
    await db.commit()


@router.post("/{trip_id}/invite", response_model=TripMemberOut, status_code=201)
async def invite_to_trip(
    trip_id: int,
    invite: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a registered user to the trip by email. Caller must be admin."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to invite members")

    if invite.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    # Find the invitee by email
    stmt = select(User).where(User.email == invite.email)
    invitee = (await db.execute(stmt)).scalars().first()
    if not invitee:
        raise HTTPException(status_code=404, detail="No account found with that email")

    # Check for duplicate membership
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == invitee.id,
    )
    if (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=409, detail="User is already a member of this trip")

    new_member = TripMember(trip_id=trip_id, user_id=invitee.id, role=invite.role, status="invited")
    db.add(new_member)

    trip_stmt = select(Trip).where(Trip.id == trip_id)
    trip_row = (await db.execute(trip_stmt)).scalars().first()
    await notification_service.emit(
        db,
        recipient_ids=[invitee.id],
        type=NotificationType.INVITE_RECEIVED,
        payload={
            "trip_name": trip_row.name if trip_row else "",
            "inviter_name": current_user.name or "",
            "role": invite.role,
        },
        actor_id=current_user.id,
        trip_id=trip_id,
    )

    await db.commit()
    await db.refresh(new_member)

    # Re-fetch with user relationship loaded
    stmt = (
        select(TripMember)
        .where(TripMember.id == new_member.id)
        .options(selectinload(TripMember.user))
    )
    return (await db.execute(stmt)).scalars().first()


@router.delete("/{trip_id}/ideas/{idea_id}", status_code=204)
async def delete_idea(
    trip_id: int,
    idea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an idea from the bin (called when idea is moved to the itinerary)."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(IdeaBinItemModel).where(
        IdeaBinItemModel.id == idea_id,
        IdeaBinItemModel.trip_id == trip_id,
    )
    item = (await db.execute(stmt)).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Idea not found")

    await db.delete(item)
    await db.commit()


@router.patch("/{trip_id}/ideas/{idea_id}", response_model=IdeaBinItem)
async def update_idea(
    trip_id: int,
    idea_id: int,
    update: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an idea's fields (e.g. start_time)."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(IdeaBinItemModel).where(
        IdeaBinItemModel.id == idea_id,
        IdeaBinItemModel.trip_id == trip_id,
    )
    item = (await db.execute(stmt)).scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Idea not found")

    if "start_time" in update:
        item.start_time = _parse_time(update["start_time"])
    if "end_time" in update:
        item.end_time = _parse_time(update["end_time"])
    if (
        item.start_time is not None
        and item.end_time is not None
        and item.end_time < item.start_time
    ):
        raise HTTPException(
            status_code=422,
            detail="Overnight idea times (end < start) are not supported in v1.",
        )
    if "time_category" in update:
        item.time_category = update["time_category"]
    if "title" in update:
        item.title = update["title"]

    await db.commit()
    await db.refresh(item)
    return item


@router.post("/{trip_id}/ingest", response_model=List[IdeaBinItem])
async def ingest_to_idea_bin(
    trip_id: int,
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check membership
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to edit this trip")

    first_name = (current_user.name or "").split()[0] if current_user.name else None
    try:
        items = await idea_bin_service.ingest_from_text(
            db=db,
            trip_id=trip_id,
            text=request.text,
            source_url=request.source_url,
            added_by=first_name,
        )

        trip_stmt = select(Trip).where(Trip.id == trip_id)
        trip_row = (await db.execute(trip_stmt)).scalars().first()
        trip_name = trip_row.name if trip_row else ""
        titles = [it.title for it in items]
        recipients = await notification_service.trip_member_ids(
            db, trip_id, exclude_user_id=current_user.id
        )
        if recipients:
            await notification_service.emit(
                db,
                recipient_ids=recipients,
                type=NotificationType.IDEA_BIN_ITEM_ADDED,
                payload={
                    "trip_name": trip_name,
                    "titles": titles,
                    "count": len(titles),
                    "actor_name": current_user.name or "",
                },
                actor_id=current_user.id,
                trip_id=trip_id,
            )
            await db.commit()

        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Trip Days ─────────────────────────────────────────────────────────────────

@router.get("/{trip_id}/days", response_model=List[TripDayOut])
async def get_trip_days(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all days planned for a trip, ordered by date."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=403, detail="Not a member of this trip")

    stmt = select(TripDay).where(TripDay.trip_id == trip_id).order_by(TripDay.date)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{trip_id}/days", response_model=TripDayOut, status_code=201)
async def add_trip_day(
    trip_id: int,
    day_in: TripDayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new day to the trip's itinerary."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check duplicate
    stmt = select(TripDay).where(TripDay.trip_id == trip_id, TripDay.date == day_in.date)
    if (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=409, detail="Day already exists for this trip")

    # Compute next day_number
    stmt = select(sa_func.coalesce(sa_func.max(TripDay.day_number), 0)).where(
        TripDay.trip_id == trip_id
    )
    max_num = (await db.execute(stmt)).scalar()

    day = TripDay(trip_id=trip_id, date=day_in.date, day_number=max_num + 1)
    db.add(day)
    await db.flush()
    await _sync_trip_end_date(db, trip_id)
    await db.commit()
    await db.refresh(day)
    return day


@router.delete("/{trip_id}/days/{day_id}", status_code=204)
async def delete_trip_day(
    trip_id: int,
    day_id: int,
    items_action: str = Query("bin", description="What to do with day's events: 'bin' (restore to idea bin) or 'delete' (permanent)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a day from the trip, handle its events, and left-shift subsequent day numbers + dates."""
    stmt = select(TripMember).where(
        TripMember.trip_id == trip_id,
        TripMember.user_id == current_user.id,
    )
    caller = (await db.execute(stmt)).scalars().first()
    if not caller or caller.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    stmt = select(TripDay).where(TripDay.id == day_id, TripDay.trip_id == trip_id)
    day = (await db.execute(stmt)).scalars().first()
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    deleted_number = day.day_number
    deleted_date = day.date

    # Handle events on this day
    evt_stmt = select(EventModel).where(
        EventModel.trip_id == trip_id,
        EventModel.day_date == deleted_date,
    )
    day_events = (await db.execute(evt_stmt)).scalars().all()

    if items_action == "bin":
        for evt in day_events:
            fields = {f: getattr(evt, f) for f in PLACE_FIELDS}
            idea = IdeaBinItemModel(
                trip_id=trip_id,
                **fields,
                start_time=evt.start_time,
                end_time=evt.end_time,
            )
            db.add(idea)
            await db.flush()
            src_votes = (await db.execute(
                select(EventVote).where(EventVote.event_id == evt.id)
            )).scalars().all()
            for v in src_votes:
                db.add(IdeaVote(idea_id=idea.id, user_id=v.user_id, value=v.value))
            await db.delete(evt)
    else:
        # Permanent delete: one bulk statement instead of per-event deletes (D7).
        await db.execute(delete(EventModel).where(
            EventModel.trip_id == trip_id,
            EventModel.day_date == deleted_date,
        ))

    await db.delete(day)
    # Flush the delete first so the unique constraint on (trip_id, date)
    # won't collide when we shift subsequent dates down by one.
    await db.flush()

    # Left-shift: renumber AND re-date all days after the deleted one.
    # Also update day_date on events belonging to the shifted days so they
    # stay associated with their day after the date shift.
    stmt = (
        select(TripDay)
        .where(TripDay.trip_id == trip_id, TripDay.day_number > deleted_number)
        .order_by(TripDay.day_number)
    )
    later_days = (await db.execute(stmt)).scalars().all()
    for d in later_days:
        old_date = d.date
        new_date = old_date - timedelta(days=1)
        # Shift events on this day to the new date
        evt_shift = select(EventModel).where(
            EventModel.trip_id == trip_id,
            EventModel.day_date == old_date,
        )
        events_to_shift = (await db.execute(evt_shift)).scalars().all()
        for evt in events_to_shift:
            evt.day_date = new_date
        d.day_number -= 1
        d.date = new_date
        await db.flush()

    await _sync_trip_end_date(db, trip_id)
    await db.commit()
