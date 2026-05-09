"""Centralised timezone helpers.

Every datetime in the DB is stored as TIMESTAMPTZ (UTC).  The app never uses
naive datetimes — ``utc_now()`` replaces every ``datetime.now()`` and
``datetime.utcnow()`` call.  Wall-clock ↔ UTC conversions go through
``to_utc()`` / ``from_utc()`` using the trip's IANA timezone string.
"""
from __future__ import annotations

from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """Timezone-aware UTC now — the only 'now' the backend should use."""
    return datetime.now(timezone.utc)


def to_utc(dt_naive: datetime, tz_name: str) -> datetime:
    """Interpret a naive datetime as being in *tz_name* and convert to UTC.

    If *dt_naive* already carries tzinfo it is converted directly.
    """
    if dt_naive.tzinfo is not None:
        return dt_naive.astimezone(timezone.utc)
    tz = ZoneInfo(tz_name)
    return dt_naive.replace(tzinfo=tz).astimezone(timezone.utc)


def from_utc(dt_utc: datetime, tz_name: str) -> datetime:
    """Convert a UTC datetime to the wall-clock time in *tz_name*."""
    tz = ZoneInfo(tz_name)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(tz)


def today_in_tz(tz_name: str) -> date:
    """Return today's date in the given timezone."""
    return utc_now().astimezone(ZoneInfo(tz_name)).date()


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Guarantee a datetime is tz-aware UTC.  Treat naive as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
