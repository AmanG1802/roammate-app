"""Tutorial trip seeder.

Idempotently builds (or rebuilds) a fully-canned NYC tutorial trip for a user:
  - 3 TripDay rows (today..+2 in trip TZ).
  - 5 TimelineItem rows from fixtures.
  - 4 IdeaBinItem rows.
  - 6 BrainstormBinItem rows.
  - 8 BrainstormMessage rows (initial chat history).
  - 3 DayRoute rows (pre-computed polylines).
  - 2 ConciergeMessage rows.

Calls no LLM and no Maps service. All data comes from tutorial_fixtures.
"""
from __future__ import annotations

import logging
from datetime import datetime, time as dt_time, timedelta, timezone as dt_tz
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import (
    BrainstormBinItem,
    BrainstormMessage,
    ConciergeMessage,
    DayRoute,
    IdeaBinItem,
    Notification,
    PLACE_FIELDS,
    TimelineItem,
    Trip,
    TripDay,
    TripMember,
    User,
)
from app.services.tutorial_fixtures import (
    BRAINSTORM_BIN_ITEMS,
    COUNTRY_CODE,
    DAY_ROUTES,
    DESTINATION_CITY,
    DESTINATION_LAT,
    DESTINATION_LNG,
    IDEA_BIN_ITEMS,
    INITIAL_BRAINSTORM_HISTORY,
    INITIAL_CONCIERGE_HISTORY,
    TIMELINE_EVENTS,
    TRIP_NAME,
    TRIP_TIMEZONE,
)

log = logging.getLogger(__name__)


def _today_in_tz(tz_name: str):
    tz = ZoneInfo(tz_name)
    return datetime.now(tz).date()


def _parse_time(s: str) -> dt_time:
    h, m, sec = s.split(":")
    return dt_time(int(h), int(m), int(sec))


def _place_kwargs(fixture: dict) -> dict:
    return {k: fixture.get(k) for k in PLACE_FIELDS}


async def find_existing_tutorial_trip(db: AsyncSession, user: User) -> Optional[Trip]:
    stmt = select(Trip).where(
        Trip.created_by_id == user.id,
        Trip.is_tutorial.is_(True),
    )
    return (await db.execute(stmt)).scalars().first()


async def delete_tutorial_trip(db: AsyncSession, user: User) -> bool:
    """Hard-delete the user's tutorial trip and all owned children.

    Children are cascaded via FK ondelete=CASCADE where present; rows without
    cascade (TripDay, TimelineItem, IdeaBinItem, DayRoute, TripMember) are
    cleared explicitly.
    """
    trip = await find_existing_tutorial_trip(db, user)
    if trip is None:
        return False

    trip_id = trip.id
    # Notifications keep a non-cascading FK to the trip; null it out first so the
    # trip delete never trips a FK violation.
    await db.execute(
        update(Notification).where(Notification.trip_id == trip_id).values(trip_id=None)
    )
    # Children without ondelete=CASCADE on the FK.
    for model in (TimelineItem, IdeaBinItem, TripDay, DayRoute, TripMember):
        rows = (
            await db.execute(select(model).where(model.trip_id == trip_id))
        ).scalars().all()
        for r in rows:
            await db.delete(r)
    await db.flush()
    await db.delete(trip)
    await db.commit()
    return True


async def seed_tutorial_trip(db: AsyncSession, user: User) -> Trip:
    """Create a fresh tutorial trip for *user*. Idempotent: existing tutorial
    trips are deleted and rebuilt so replay always produces a clean state."""
    await delete_tutorial_trip(db, user)

    start_date = _today_in_tz(TRIP_TIMEZONE)
    end_date = start_date + timedelta(days=2)
    start_dt = datetime.combine(start_date, dt_time(0, 0), tzinfo=ZoneInfo(TRIP_TIMEZONE))
    end_dt = datetime.combine(end_date, dt_time(23, 59), tzinfo=ZoneInfo(TRIP_TIMEZONE))

    trip = Trip(
        name=TRIP_NAME,
        start_date=start_dt,
        end_date=end_dt,
        timezone=TRIP_TIMEZONE,
        destination_city=DESTINATION_CITY,
        country_code=COUNTRY_CODE,
        destination_lat=DESTINATION_LAT,
        destination_lng=DESTINATION_LNG,
        created_by_id=user.id,
        is_tutorial=True,
        is_tutorial_completed=False,
    )
    db.add(trip)
    await db.flush()

    db.add(TripMember(trip_id=trip.id, user_id=user.id, role="admin", status="accepted"))

    days: list[TripDay] = []
    for i in range(3):
        d = TripDay(trip_id=trip.id, date=start_date + timedelta(days=i), day_number=i + 1)
        db.add(d)
        days.append(d)
    await db.flush()

    # Timeline events.
    for ev in TIMELINE_EVENTS:
        day = days[ev["day_index"]]
        item = TimelineItem(
            trip_id=trip.id,
            day_date=day.date,
            start_time=_parse_time(ev["start"]),
            end_time=_parse_time(ev["end"]),
            location_name=ev["title"],
            event_type=ev.get("category"),
            **_place_kwargs(ev),
        )
        db.add(item)

    # Idea Bin items (shared).
    for idea in IDEA_BIN_ITEMS:
        db.add(IdeaBinItem(trip_id=trip.id, **_place_kwargs(idea)))

    # Brainstorm bin (per-user).
    for bs in BRAINSTORM_BIN_ITEMS:
        db.add(BrainstormBinItem(trip_id=trip.id, user_id=user.id, **_place_kwargs(bs)))

    # Brainstorm chat history.
    for msg in INITIAL_BRAINSTORM_HISTORY:
        db.add(BrainstormMessage(
            trip_id=trip.id,
            user_id=user.id,
            role=msg["role"],
            content=msg["content"],
        ))

    # Concierge intro chat.
    for msg in INITIAL_CONCIERGE_HISTORY:
        db.add(ConciergeMessage(
            trip_id=trip.id,
            user_id=user.id,
            role=msg["role"],
            content=msg["content"],
        ))

    # Day routes.
    for r in DAY_ROUTES:
        day = days[r["day_index"]]
        db.add(DayRoute(
            trip_id=trip.id,
            day_date=str(day.date),
            encoded_polyline=r["encoded_polyline"],
            legs=r["legs"],
            total_distance_m=r["total_distance_m"],
            total_duration_s=r["total_duration_s"],
            ordered_event_ids=[],
            unroutable=[],
            waypoint_fingerprint=f"tutorial-{trip.id}-{r['day_index']}",
        ))

    await db.commit()
    await db.refresh(trip)
    log.info("Seeded tutorial trip %s for user %s", trip.id, user.id)
    return trip
