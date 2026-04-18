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
