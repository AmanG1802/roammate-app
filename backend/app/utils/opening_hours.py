"""Opening-hours feasibility checks.

Operates on Google Places ``regularOpeningHours`` JSON as stored on
place-bearing rows (``opening_hours`` column). Supports both the new Places API
shape (``periods[].open/close = {day, hour, minute}``) and the legacy shape
(``periods[].open/close = {day, time: "HHMM"}``).

Day numbering follows Google: 0 = Sunday … 6 = Saturday.
"""
from __future__ import annotations

from datetime import date, time
from typing import Optional


def _to_minutes(point: dict) -> Optional[int]:
    """Minutes-since-midnight for a Places open/close point, or None."""
    if not isinstance(point, dict):
        return None
    if "hour" in point:  # new Places API shape
        try:
            return int(point.get("hour", 0)) * 60 + int(point.get("minute", 0))
        except (TypeError, ValueError):
            return None
    raw = point.get("time")  # legacy shape: "HHMM"
    if isinstance(raw, str) and raw.isdigit() and len(raw) == 4:
        return int(raw[:2]) * 60 + int(raw[2:])
    return None


def _google_weekday(day_date: date) -> int:
    """Python weekday (Mon=0) → Google weekday (Sun=0)."""
    return (day_date.weekday() + 1) % 7


def is_open_during(
    opening_hours: Optional[dict],
    day_date: Optional[date],
    start: Optional[time],
    end: Optional[time],
) -> Optional[bool]:
    """Is the venue open for the whole [start, end] window on ``day_date``?

    Returns True/False, or None when hours are unknown/unparseable (callers
    treat None as "don't warn"). Conservative: a window is only "open" when it
    fits entirely inside a single opening period for that weekday. Periods that
    close on a later day (overnight venues) are treated as open through the rest
    of the day. An open period with no close is treated as 24h.
    """
    if not opening_hours or day_date is None or start is None:
        return None

    periods = opening_hours.get("periods") if isinstance(opening_hours, dict) else None
    if not periods:
        # Some payloads only carry weekdayDescriptions / openNow — not enough to
        # reason precisely, so abstain.
        return None

    gday = _google_weekday(day_date)
    start_m = start.hour * 60 + start.minute
    end_m = (end.hour * 60 + end.minute) if end is not None else start_m

    found_day = False
    for period in periods:
        if not isinstance(period, dict):
            continue
        open_pt = period.get("open")
        if not isinstance(open_pt, dict) or open_pt.get("day") != gday:
            continue
        found_day = True
        open_m = _to_minutes(open_pt)
        if open_m is None:
            continue

        close_pt = period.get("close")
        if not isinstance(close_pt, dict):
            # No close → treated as open 24h from the open time.
            if start_m >= open_m:
                return True
            continue

        close_day = close_pt.get("day")
        if close_day != gday:
            # Closes on a later day (overnight) — open through end of this day.
            if start_m >= open_m:
                return True
            continue

        close_m = _to_minutes(close_pt)
        if close_m is None:
            continue
        if open_m <= start_m and end_m <= close_m:
            return True

    # We had hours for this weekday but the window didn't fit → closed.
    # If the venue simply has no period for this weekday, it's closed that day.
    return False if (found_day or periods) else None
