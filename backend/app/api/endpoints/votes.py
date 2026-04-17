"""Vote endpoints for IdeaBinItem (bin) and Event (timeline).

Role policy: only `admin` and `view_with_vote` trip members can cast votes.
`view_only` members can read tallies.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func

from app.db.session import get_db
from app.models.all_models import (
    IdeaBinItem, Event, IdeaVote, EventVote, User,
)
from app.schemas.votes import VoteRequest, VoteTally
from app.services.roles import require_trip_member, require_vote_role
from app.api.deps import get_current_user

router = APIRouter()


async def _tally_idea(db: AsyncSession, idea_id: int, user_id: int) -> VoteTally:
    up = (await db.execute(
        select(sa_func.count(IdeaVote.id)).where(IdeaVote.idea_id == idea_id, IdeaVote.value == 1)
    )).scalar_one()
    down = (await db.execute(
        select(sa_func.count(IdeaVote.id)).where(IdeaVote.idea_id == idea_id, IdeaVote.value == -1)
    )).scalar_one()
    mine = (await db.execute(
        select(IdeaVote.value).where(IdeaVote.idea_id == idea_id, IdeaVote.user_id == user_id)
    )).scalars().first() or 0
    return VoteTally(up=up, down=down, my_vote=mine)


async def _tally_event(db: AsyncSession, event_id: int, user_id: int) -> VoteTally:
    up = (await db.execute(
        select(sa_func.count(EventVote.id)).where(EventVote.event_id == event_id, EventVote.value == 1)
    )).scalar_one()
    down = (await db.execute(
        select(sa_func.count(EventVote.id)).where(EventVote.event_id == event_id, EventVote.value == -1)
    )).scalar_one()
    mine = (await db.execute(
        select(EventVote.value).where(EventVote.event_id == event_id, EventVote.user_id == user_id)
    )).scalars().first() or 0
    return VoteTally(up=up, down=down, my_vote=mine)


# ── Idea votes ────────────────────────────────────────────────────────────────

@router.post("/ideas/{idea_id}/vote", response_model=VoteTally)
async def vote_on_idea(
    idea_id: int,
    body: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    idea = (await db.execute(select(IdeaBinItem).where(IdeaBinItem.id == idea_id))).scalars().first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    await require_vote_role(db, idea.trip_id, current_user.id)

    existing = (await db.execute(
        select(IdeaVote).where(IdeaVote.idea_id == idea_id, IdeaVote.user_id == current_user.id)
    )).scalars().first()

    if body.value == 0:
        if existing:
            await db.delete(existing)
    else:
        if existing:
            existing.value = body.value
        else:
            db.add(IdeaVote(idea_id=idea_id, user_id=current_user.id, value=body.value))

    await db.commit()
    return await _tally_idea(db, idea_id, current_user.id)


@router.get("/ideas/{idea_id}/votes", response_model=VoteTally)
async def get_idea_votes(
    idea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    idea = (await db.execute(select(IdeaBinItem).where(IdeaBinItem.id == idea_id))).scalars().first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    await require_trip_member(db, idea.trip_id, current_user.id)
    return await _tally_idea(db, idea_id, current_user.id)


# ── Event votes ───────────────────────────────────────────────────────────────

@router.post("/events/{event_id}/vote", response_model=VoteTally)
async def vote_on_event(
    event_id: int,
    body: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    await require_vote_role(db, ev.trip_id, current_user.id)

    existing = (await db.execute(
        select(EventVote).where(EventVote.event_id == event_id, EventVote.user_id == current_user.id)
    )).scalars().first()

    if body.value == 0:
        if existing:
            await db.delete(existing)
    else:
        if existing:
            existing.value = body.value
        else:
            db.add(EventVote(event_id=event_id, user_id=current_user.id, value=body.value))

    await db.commit()
    return await _tally_event(db, event_id, current_user.id)


@router.get("/events/{event_id}/votes", response_model=VoteTally)
async def get_event_votes(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = (await db.execute(select(Event).where(Event.id == event_id))).scalars().first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    await require_trip_member(db, ev.trip_id, current_user.id)
    return await _tally_event(db, event_id, current_user.id)
