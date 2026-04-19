"""Per-user-per-trip brainstorm endpoints.

Every query in this module filters by ``trip_id`` AND ``user_id == current_user.id``.
Two members on the same trip each see only their own bin + chat history.
The ``promote`` endpoint is the one exception that fan-outs notifications to
the trip's other members — but even there, the *source* rows being promoted
must belong to the caller. Promoted rows land in the shared ``IdeaBinItem``
table, which then becomes visible to all trip members.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.all_models import (
    User,
    Trip,
    BrainstormBinItem,
    BrainstormMessage,
    IdeaBinItem,
)
from app.schemas.brainstorm import (
    BrainstormItemOut,
    BrainstormMessageOut,
    BrainstormChatRequest,
    BrainstormChatResponse,
    BrainstormExtractResponse,
    BrainstormBulkRequest,
    BrainstormPromoteRequest,
)
from app.schemas.trip import IdeaBinItem as IdeaBinItemSchema
from app.services.roles import require_trip_member
from app.services import notification_service
from app.services.llm.registry import get_brainstorm_client
from app.services.llm.place_enricher import enrich_items
from app.services.llm.dedup import deduplicate
from app.schemas.notification import NotificationType
from app.core.time_categories import TIME_CATEGORY_DEFAULTS

router = APIRouter()


# ── Google-Maps-parity fields copied verbatim on promotion ────────────────
_COPY_FIELDS = (
    "title",
    "description",
    "category",
    "place_id",
    "lat",
    "lng",
    "address",
    "photo_url",
    "rating",
    "price_level",
    "types",
    "opening_hours",
    "phone",
    "website",
    "time_hint",
    "time_category",
    "url_source",
)


def _first_name(user: User) -> str:
    if not user.name:
        return ""
    return user.name.split()[0]


@router.get("/{trip_id}/brainstorm/items", response_model=List[BrainstormItemOut])
async def list_items(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)
    stmt = (
        select(BrainstormBinItem)
        .where(
            BrainstormBinItem.trip_id == trip_id,
            BrainstormBinItem.user_id == current_user.id,
        )
        .order_by(BrainstormBinItem.created_at)
    )
    return (await db.execute(stmt)).scalars().all()


@router.get("/{trip_id}/brainstorm/messages", response_model=List[BrainstormMessageOut])
async def list_messages(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)
    stmt = (
        select(BrainstormMessage)
        .where(
            BrainstormMessage.trip_id == trip_id,
            BrainstormMessage.user_id == current_user.id,
        )
        .order_by(BrainstormMessage.created_at)
    )
    return (await db.execute(stmt)).scalars().all()


@router.post("/{trip_id}/brainstorm/chat", response_model=BrainstormChatResponse)
async def chat(
    trip_id: int,
    body: BrainstormChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)

    stmt = (
        select(BrainstormMessage)
        .where(
            BrainstormMessage.trip_id == trip_id,
            BrainstormMessage.user_id == current_user.id,
        )
        .order_by(BrainstormMessage.created_at)
    )
    history_rows = (await db.execute(stmt)).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    user_msg = BrainstormMessage(
        trip_id=trip_id,
        user_id=current_user.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)

    client = get_brainstorm_client()
    assistant_content = await client.chat(history, body.message, trip_id=trip_id)
    assistant_msg = BrainstormMessage(
        trip_id=trip_id,
        user_id=current_user.id,
        role="assistant",
        content=assistant_content,
    )
    db.add(assistant_msg)

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    full_history = history_rows + [user_msg, assistant_msg]
    return BrainstormChatResponse(
        assistant_message=BrainstormMessageOut.model_validate(assistant_msg),
        history=[BrainstormMessageOut.model_validate(m) for m in full_history],
    )


@router.post("/{trip_id}/brainstorm/extract", response_model=BrainstormExtractResponse)
async def extract(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)

    stmt = (
        select(BrainstormMessage)
        .where(
            BrainstormMessage.trip_id == trip_id,
            BrainstormMessage.user_id == current_user.id,
        )
        .order_by(BrainstormMessage.created_at)
    )
    history_rows = (await db.execute(stmt)).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    client = get_brainstorm_client()
    raw_items = await client.extract_items(history, trip_id=trip_id)
    raw_items = await enrich_items(raw_items)

    existing_stmt = select(BrainstormBinItem).where(
        BrainstormBinItem.trip_id == trip_id,
        BrainstormBinItem.user_id == current_user.id,
    )
    existing_rows = (await db.execute(existing_stmt)).scalars().all()
    raw_items = deduplicate(raw_items, existing_rows)

    created: list[BrainstormBinItem] = []
    for item in raw_items:
        row = BrainstormBinItem(
            trip_id=trip_id,
            user_id=current_user.id,
            added_by="AI",
            **{k: item.get(k) for k in _COPY_FIELDS},
        )
        db.add(row)
        created.append(row)

    await db.commit()
    for row in created:
        await db.refresh(row)

    return BrainstormExtractResponse(items=created)


@router.post("/{trip_id}/brainstorm/bulk", response_model=List[BrainstormItemOut])
async def bulk_insert(
    trip_id: int,
    body: BrainstormBulkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed the caller's Brainstorm Bin with a batch of items.

    Used by the dashboard Create-Trip flow after ``/api/llm/plan-trip`` returns
    a preview — the client posts the preview's items here.
    """
    await require_trip_member(db, trip_id, current_user.id)

    created: list[BrainstormBinItem] = []
    for item in body.items:
        row = BrainstormBinItem(
            trip_id=trip_id,
            user_id=current_user.id,
            added_by="AI",
            **item.model_dump(),
        )
        db.add(row)
        created.append(row)

    await db.commit()
    for row in created:
        await db.refresh(row)
    return created


@router.post("/{trip_id}/brainstorm/promote", response_model=List[IdeaBinItemSchema])
async def promote(
    trip_id: int,
    body: BrainstormPromoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move caller's brainstorm items into the shared Idea Bin (copy + delete).

    Open to any trip member. The ``added_by`` field on the new IdeaBinItem
    rows is set to the promoter's first name (never "AI"), regardless of the
    source item's origin.
    """
    await require_trip_member(db, trip_id, current_user.id)

    stmt = select(BrainstormBinItem).where(
        BrainstormBinItem.trip_id == trip_id,
        BrainstormBinItem.user_id == current_user.id,
    )
    if body.item_ids is not None:
        if not body.item_ids:
            return []
        stmt = stmt.where(BrainstormBinItem.id.in_(body.item_ids))
    sources = (await db.execute(stmt)).scalars().all()

    if body.item_ids is not None and len(sources) != len(set(body.item_ids)):
        # Some requested ids don't exist in the caller's scope.
        raise HTTPException(status_code=404, detail="One or more items not found")

    if not sources:
        return []

    # Enrich any items missing a place_id before promoting
    unenriched = [
        {k: getattr(src, k) for k in _COPY_FIELDS}
        for src in sources
        if not getattr(src, "place_id", None)
    ]
    if unenriched:
        enriched_dicts = await enrich_items(unenriched)
        _enriched_by_title = {d["title"]: d for d in enriched_dicts}
        for src in sources:
            if not getattr(src, "place_id", None) and src.title in _enriched_by_title:
                enriched = _enriched_by_title[src.title]
                for fld in ("place_id", "lat", "lng", "address", "photo_url",
                            "rating", "opening_hours", "phone", "website"):
                    val = enriched.get(fld)
                    if val is not None:
                        setattr(src, fld, val)

    promoter = _first_name(current_user) or None
    created: list[IdeaBinItem] = []
    for src in sources:
        fields = {k: getattr(src, k) for k in _COPY_FIELDS}
        if not fields.get("time_hint") and fields.get("time_category"):
            fields["time_hint"] = TIME_CATEGORY_DEFAULTS.get(fields["time_category"])
        idea = IdeaBinItem(
            trip_id=trip_id,
            added_by=promoter,
            **fields,
        )
        db.add(idea)
        created.append(idea)

    await db.flush()
    for src in sources:
        await db.delete(src)

    trip_row = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalars().first()
    trip_name = trip_row.name if trip_row else ""
    recipients = await notification_service.trip_member_ids(
        db, trip_id, exclude_user_id=current_user.id
    )
    if recipients:
        await notification_service.emit(
            db,
            recipient_ids=recipients,
            type=NotificationType.BRAINSTORM_PROMOTED,
            payload={
                "trip_name": trip_name,
                "count": len(created),
                "titles": [c.title for c in created],
                "actor_name": current_user.name or "",
            },
            actor_id=current_user.id,
            trip_id=trip_id,
        )

    await db.commit()
    for idea in created:
        await db.refresh(idea)

    return [
        IdeaBinItemSchema(
            id=i.id, trip_id=i.trip_id, title=i.title,
            description=i.description, category=i.category,
            place_id=i.place_id, lat=i.lat, lng=i.lng,
            address=i.address, photo_url=i.photo_url, rating=i.rating,
            price_level=i.price_level, types=i.types, opening_hours=i.opening_hours,
            phone=i.phone, website=i.website,
            url_source=i.url_source, time_hint=i.time_hint, time_category=i.time_category,
            added_by=i.added_by, up=0, down=0, my_vote=0,
        )
        for i in created
    ]


@router.delete("/{trip_id}/brainstorm/items", status_code=204)
async def clear_items(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all brainstorm bin items for the current user on this trip."""
    await require_trip_member(db, trip_id, current_user.id)
    stmt = select(BrainstormBinItem).where(
        BrainstormBinItem.trip_id == trip_id,
        BrainstormBinItem.user_id == current_user.id,
    )
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        await db.delete(row)
    await db.commit()


@router.delete("/{trip_id}/brainstorm/items/{item_id}", status_code=204)
async def delete_item(
    trip_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_trip_member(db, trip_id, current_user.id)

    stmt = select(BrainstormBinItem).where(
        BrainstormBinItem.id == item_id,
        BrainstormBinItem.trip_id == trip_id,
        BrainstormBinItem.user_id == current_user.id,
    )
    row = (await db.execute(stmt)).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(row)
    await db.commit()
