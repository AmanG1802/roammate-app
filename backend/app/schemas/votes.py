from typing import Optional, Literal
from pydantic import BaseModel, field_validator


VoteValue = Literal[-1, 0, 1]


class VoteRequest(BaseModel):
    value: int

    @field_validator("value")
    @classmethod
    def _bounded(cls, v: int) -> int:
        if v not in (-1, 0, 1):
            raise ValueError("value must be -1, 0, or 1")
        return v


class VoteTally(BaseModel):
    up: int = 0
    down: int = 0
    my_vote: int = 0  # -1, 0, 1
