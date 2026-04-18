"""Pydantic validation for vote schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.votes import VoteRequest, VoteTally


@pytest.mark.parametrize("v", [-1, 0, 1])
def test_vote_request_accepts_valid_values(v):
    assert VoteRequest(value=v).value == v


@pytest.mark.parametrize("v", [2, -2, 10, 1.5])
def test_vote_request_rejects_out_of_range(v):
    with pytest.raises(ValidationError):
        VoteRequest(value=v)


def test_vote_request_missing_field():
    with pytest.raises(ValidationError):
        VoteRequest()  # type: ignore[call-arg]


def test_vote_tally_defaults_zero():
    t = VoteTally()
    assert t.up == 0 and t.down == 0 and t.my_vote == 0


# ── VoterInfo / VoterList ────────────────────────────────────────────────────

from app.schemas.votes import VoterInfo, VoterList


def test_voter_info_requires_name():
    with pytest.raises(ValidationError):
        VoterInfo()  # type: ignore[call-arg]


def test_voter_info_accepts_name():
    v = VoterInfo(name="Alice")
    assert v.name == "Alice"


def test_voter_list_defaults_empty():
    vl = VoterList()
    assert vl.up_voters == [] and vl.down_voters == []


# ── TodayEvent.is_ongoing ────────────────────────────────────────────────────

from app.schemas.dashboard import TodayEvent


def test_today_event_is_ongoing_defaults_false():
    e = TodayEvent(id=1, title="T")
    assert e.is_ongoing is False and e.is_next is False


def test_today_event_accepts_is_ongoing_true():
    e = TodayEvent(id=1, title="T", is_ongoing=True)
    assert e.is_ongoing is True
