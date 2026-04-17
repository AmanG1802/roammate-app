"""Idea-scoped endpoints: tags + cross-trip copy (provenance)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.session import get_db
from app.models.all_models import IdeaBinItem, IdeaTag, User
from app.schemas.library import TagList, CopyIdeaRequest
from app.schemas.trip import IdeaBinItem as IdeaBinItemSchema
from app.services.roles import require_trip_member, require_vote_role
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/{idea_id}/tags", response_model=List[str])
async def list_idea_tags(
    idea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    idea = (await db.execute(select(IdeaBinItem).where(IdeaBinItem.id == idea_id))).scalars().first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    await require_trip_member(db, idea.trip_id, current_user.id)
    rows = (await db.execute(select(IdeaTag.tag).where(IdeaTag.idea_id == idea_id))).scalars().all()
    return list(rows)


@router.put("/{idea_id}/tags", response_model=List[str])
async def set_idea_tags(
    idea_id: int,
    body: TagList,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace the tag list for this idea. Requires admin or view_with_vote."""
    idea = (await db.execute(select(IdeaBinItem).where(IdeaBinItem.id == idea_id))).scalars().first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    await require_vote_role(db, idea.trip_id, current_user.id)

    await db.execute(delete(IdeaTag).where(IdeaTag.idea_id == idea_id))
    for t in body.tags:
        db.add(IdeaTag(idea_id=idea_id, tag=t))
    await db.commit()
    return body.tags


@router.post("/{idea_id}/copy", response_model=IdeaBinItemSchema)
async def copy_idea_to_trip(
    idea_id: int,
    body: CopyIdeaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Copy an idea into another trip, preserving provenance via origin_idea_id.
    Caller must be a member of both the source and target trips."""
    src = (await db.execute(select(IdeaBinItem).where(IdeaBinItem.id == idea_id))).scalars().first()
    if not src:
        raise HTTPException(status_code=404, detail="Idea not found")
    await require_trip_member(db, src.trip_id, current_user.id)
    await require_trip_member(db, body.target_trip_id, current_user.id)

    copy = IdeaBinItem(
        trip_id=body.target_trip_id,
        title=src.title,
        place_id=src.place_id,
        lat=src.lat,
        lng=src.lng,
        url_source=src.url_source,
        time_hint=src.time_hint,
        added_by=src.added_by,
        origin_idea_id=src.origin_idea_id or src.id,
    )
    db.add(copy)
    await db.flush()

    # Copy tags too — provenance is useless without them
    src_tags = (await db.execute(select(IdeaTag.tag).where(IdeaTag.idea_id == src.id))).scalars().all()
    for tag in src_tags:
        db.add(IdeaTag(idea_id=copy.id, tag=tag))

    await db.commit()
    await db.refresh(copy)
    return copy
