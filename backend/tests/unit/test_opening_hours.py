"""Unit tests for app.utils.opening_hours.is_open_during."""
from datetime import date, time

from app.utils.opening_hours import is_open_during

# 2025-06-16 is a Monday → Google weekday 1.
MON = date(2025, 6, 16)
SUN = date(2025, 6, 15)  # Google weekday 0


def _hours_new(open_h, close_h, days=range(7)):
    return {"periods": [
        {"open": {"day": d, "hour": open_h, "minute": 0},
         "close": {"day": d, "hour": close_h, "minute": 0}}
        for d in days
    ]}


def test_window_inside_hours_is_open():
    h = _hours_new(9, 18)
    assert is_open_during(h, MON, time(10, 0), time(11, 0)) is True


def test_window_ending_after_close_is_closed():
    h = _hours_new(9, 18)
    assert is_open_during(h, MON, time(17, 30), time(18, 30)) is False


def test_window_before_open_is_closed():
    h = _hours_new(9, 18)
    assert is_open_during(h, MON, time(8, 0), time(8, 45)) is False


def test_no_period_for_that_weekday_is_closed():
    # Open only Sunday (day 0); Monday has no period.
    h = _hours_new(9, 18, days=[0])
    assert is_open_during(h, MON, time(10, 0), time(11, 0)) is False
    assert is_open_during(h, SUN, time(10, 0), time(11, 0)) is True


def test_legacy_hhmm_shape():
    h = {"periods": [
        {"open": {"day": 1, "time": "0900"}, "close": {"day": 1, "time": "1800"}},
    ]}
    assert is_open_during(h, MON, time(10, 0), time(11, 0)) is True
    assert is_open_during(h, MON, time(19, 0), time(20, 0)) is False


def test_overnight_period_open_through_end_of_day():
    # Opens Mon 18:00, closes Tue 02:00 → any Mon window after 18:00 is open.
    h = {"periods": [
        {"open": {"day": 1, "hour": 18, "minute": 0},
         "close": {"day": 2, "hour": 2, "minute": 0}},
    ]}
    assert is_open_during(h, MON, time(20, 0), time(21, 0)) is True


def test_open_24h_no_close():
    h = {"periods": [{"open": {"day": 1, "hour": 0, "minute": 0}}]}
    assert is_open_during(h, MON, time(3, 0), time(4, 0)) is True


def test_unknown_hours_returns_none():
    assert is_open_during(None, MON, time(10, 0), time(11, 0)) is None
    assert is_open_during({}, MON, time(10, 0), time(11, 0)) is None
    # openNow-only payload (no periods) → abstain.
    assert is_open_during({"openNow": True}, MON, time(10, 0), time(11, 0)) is None


def test_missing_inputs_return_none():
    h = _hours_new(9, 18)
    assert is_open_during(h, None, time(10, 0), time(11, 0)) is None
    assert is_open_during(h, MON, None, time(11, 0)) is None


def test_no_end_time_uses_start_instant():
    h = _hours_new(9, 18)
    assert is_open_during(h, MON, time(10, 0), None) is True
    assert is_open_during(h, MON, time(20, 0), None) is False
