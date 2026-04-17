from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func as sa_func, or_
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.all_models import (
    Group, GroupMember, User, Trip, TripMember,
    IdeaBinItem as IdeaBinItemModel, Notification, IdeaTag, IdeaVote,
)
from app.schemas.group import (
    GroupOut, GroupDetailOut, GroupCreate, GroupUpdate,
    GroupMemberOut, GroupInviteRequest, GroupRoleUpdateRequest,
    GroupInvitationOut, GroupSummary, GroupInviterSummary, GroupTripSummary,
    GROUP_ROLES,
)
from app.schemas.trip import IdeaBinItem
from app.schemas.library import LibraryIdeaOut, TripProvenance, TagSummary
from app.services import notification_service
from app.schemas.notification import NotificationType
from app.api.deps import get_current_user

router = APIRouter()


async def _require_group_member(db: AsyncSession, group_id: int, user_id: int) -> GroupMember:
    stmt = select(GroupMember).where(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id,
        GroupMember.status == "accepted",
    )
    m = (await db.execute(stmt)).scalars().first()
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return m


async def _group_member_ids(db: AsyncSession, group_id: int, *, exclude_user_id: int | None = None) -> list[int]:
    stmt = select(GroupMember.user_id).where(
        GroupMember.group_id == group_id, GroupMember.status == "accepted"
    )
    rows = (await db.execute(stmt)).scalars().all()
    if exclude_user_id is not None:
        return [uid for uid in rows if uid != exclude_user_id]
    return list(rows)


@router.get("/", response_model=List[GroupOut])
async def list_my_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Groups where the current user is an accepted member."""
    stmt = (
        select(Group, GroupMember.role)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == current_user.id, GroupMember.status == "accepted")
    )
    rows = (await db.execute(stmt)).all()

    results: list[GroupOut] = []
    for g, role in rows:
        member_count_stmt = select(sa_func.count(GroupMember.id)).where(
            GroupMember.group_id == g.id, GroupMember.status == "accepted"
        )
        member_count = (await db.execute(member_count_stmt)).scalar_one()
        trip_count_stmt = select(sa_func.count(Trip.id)).where(Trip.group_id == g.id)
        trip_count = (await db.execute(trip_count_stmt)).scalar_one()
        results.append(GroupOut(
            id=g.id, name=g.name, owner_id=g.owner_id, created_at=g.created_at,
            my_role=role, member_count=member_count, trip_count=trip_count,
        ))
    return results


@router.post("/", response_model=GroupDetailOut, status_code=201)
async def create_group(
    group_in: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not group_in.name.strip():
        raise HTTPException(status_code=422, detail="Group name is required")

    group = Group(name=group_in.name.strip(), owner_id=current_user.id)
    db.add(group)
    await db.flush()

    db.add(GroupMember(group_id=group.id, user_id=current_user.id, role="admin", status="accepted"))

    await notification_service.emit(
        db,
        recipient_ids=[current_user.id],
        type=NotificationType.GROUP_CREATED,
        payload={"group_name": group.name},
        actor_id=current_user.id,
        group_id=group.id,
    )

    await db.commit()
    await db.refresh(group)
    return GroupDetailOut(
        id=group.id, name=group.name, owner_id=group.owner_id,
        created_at=group.created_at, my_role="admin",
    )


@router.get("/invitations/pending", response_model=List[GroupInvitationOut])
async def list_my_group_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(GroupMember)
        .where(GroupMember.user_id == current_user.id, GroupMember.status == "invited")
        .options(selectinload(GroupMember.group))
    )
    members = (await db.execute(stmt)).scalars().all()

    results: list[GroupInvitationOut] = []
    for m in members:
        admin_stmt = (
            select(GroupMember)
            .where(GroupMember.group_id == m.group_id, GroupMember.role == "admin", GroupMember.status == "accepted")
            .options(selectinload(GroupMember.user))
        )
        admin = (await db.execute(admin_stmt)).scalars().first()
        inviter = GroupInviterSummary(name=admin.user.name or "", email=admin.user.email) if admin and admin.user else None
        results.append(GroupInvitationOut(
            id=m.id, group_id=m.group_id, role=m.role,
            group=GroupSummary(id=m.group.id, name=m.group.name),
            inviter=inviter,
        ))
    return results


@router.post("/invitations/{member_id}/accept", response_model=GroupMemberOut)
async def accept_group_invitation(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(GroupMember)
        .where(GroupMember.id == member_id, GroupMember.user_id == current_user.id, GroupMember.status == "invited")
        .options(selectinload(GroupMember.user), selectinload(GroupMember.group))
    )
    member = (await db.execute(stmt)).scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="Invitation not found")

    member.status = "accepted"
    await db.flush()

    group_name = member.group.name if member.group else ""
    await notification_service.emit(
        db,
        recipient_ids=[current_user.id],
        type=NotificationType.GROUP_INVITE_ACCEPTED,
        payload={"group_name": group_name, "self": True},
        actor_id=current_user.id,
        group_id=member.group_id,
    )
    others = await _group_member_ids(db, member.group_id, exclude_user_id=current_user.id)
    if others:
        await notification_service.emit(
            db,
            recipient_ids=others,
            type=NotificationType.GROUP_INVITE_ACCEPTED,
            payload={"group_name": group_name, "joined_user_name": current_user.name or ""},
            actor_id=current_user.id,
            group_id=member.group_id,
        )

    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/invitations/{member_id}/decline", status_code=204)
async def decline_group_invitation(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(GroupMember).where(
        GroupMember.id == member_id,
        GroupMember.user_id == current_user.id,
        GroupMember.status == "invited",
    )
    member = (await db.execute(stmt)).scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="Invitation not found")
    await db.delete(member)
    await db.commit()


@router.get("/{group_id}", response_model=GroupDetailOut)
async def get_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    caller = await _require_group_member(db, group_id, current_user.id)
    group = (await db.execute(select(Group).where(Group.id == group_id))).scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupDetailOut(
        id=group.id, name=group.name, owner_id=group.owner_id,
        created_at=group.created_at, my_role=caller.role,
    )


@router.patch("/{group_id}", response_model=GroupDetailOut)
async def update_group(
    group_id: int,
    body: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    caller = await _require_group_member(db, group_id, current_user.id)
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update the group")

    group = (await db.execute(select(Group).where(Group.id == group_id))).scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if body.name is not None and body.name.strip():
        group.name = body.name.strip()

    await db.commit()
    await db.refresh(group)
    return GroupDetailOut(
        id=group.id, name=group.name, owner_id=group.owner_id,
        created_at=group.created_at, my_role=caller.role,
    )


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    caller = await _require_group_member(db, group_id, current_user.id)
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete the group")

    group = (await db.execute(select(Group).where(Group.id == group_id))).scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Detach trips (preserve them) and drop members.
    await db.execute(update(Trip).where(Trip.group_id == group_id).values(group_id=None))
    for m in (await db.execute(select(GroupMember).where(GroupMember.group_id == group_id))).scalars().all():
        await db.delete(m)
    await db.execute(update(Notification).where(Notification.group_id == group_id).values(group_id=None))
    await db.delete(group)
    await db.commit()


@router.get("/{group_id}/members", response_model=List[GroupMemberOut])
async def list_group_members(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_group_member(db, group_id, current_user.id)
    stmt = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .options(selectinload(GroupMember.user))
    )
    return (await db.execute(stmt)).scalars().all()


@router.post("/{group_id}/invite", response_model=GroupMemberOut, status_code=201)
async def invite_to_group(
    group_id: int,
    body: GroupInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    caller = await _require_group_member(db, group_id, current_user.id)
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can invite members")

    if body.role not in GROUP_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {', '.join(GROUP_ROLES)}")

    invitee = (await db.execute(select(User).where(User.email == body.email))).scalars().first()
    if not invitee:
        raise HTTPException(status_code=404, detail="No account found with that email")

    existing = (await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == invitee.id)
    )).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="User is already part of this group")

    new_member = GroupMember(group_id=group_id, user_id=invitee.id, role=body.role, status="invited")
    db.add(new_member)

    group = (await db.execute(select(Group).where(Group.id == group_id))).scalars().first()
    await notification_service.emit(
        db,
        recipient_ids=[invitee.id],
        type=NotificationType.GROUP_INVITE_RECEIVED,
        payload={
            "group_name": group.name if group else "",
            "inviter_name": current_user.name or "",
            "role": body.role,
        },
        actor_id=current_user.id,
        group_id=group_id,
    )

    await db.commit()
    await db.refresh(new_member)

    stmt = (
        select(GroupMember)
        .where(GroupMember.id == new_member.id)
        .options(selectinload(GroupMember.user))
    )
    return (await db.execute(stmt)).scalars().first()


@router.patch("/{group_id}/members/{member_id}/role", response_model=GroupMemberOut)
async def update_group_member_role(
    group_id: int,
    member_id: int,
    body: GroupRoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    caller = await _require_group_member(db, group_id, current_user.id)
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change roles")

    if body.role not in GROUP_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {', '.join(GROUP_ROLES)}")

    stmt = (
        select(GroupMember)
        .where(GroupMember.id == member_id, GroupMember.group_id == group_id)
        .options(selectinload(GroupMember.user))
    )
    target = (await db.execute(stmt)).scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    target.role = body.role
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{group_id}/members/{member_id}", status_code=204)
async def remove_group_member(
    group_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    caller = await _require_group_member(db, group_id, current_user.id)
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove members")

    stmt = select(GroupMember).where(GroupMember.id == member_id, GroupMember.group_id == group_id)
    target = (await db.execute(stmt)).scalars().first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    if target.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the group")

    removed_user = (await db.execute(select(User).where(User.id == target.user_id))).scalars().first()
    group = (await db.execute(select(Group).where(Group.id == group_id))).scalars().first()
    group_name = group.name if group else ""

    remaining = await _group_member_ids(db, group_id, exclude_user_id=current_user.id)
    remaining = [uid for uid in remaining if uid != target.user_id]

    await notification_service.emit(
        db,
        recipient_ids=[target.user_id],
        type=NotificationType.GROUP_MEMBER_REMOVED,
        payload={"group_name": group_name, "actor_name": current_user.name or "", "self": True},
        actor_id=current_user.id,
        group_id=group_id,
    )
    if remaining:
        await notification_service.emit(
            db,
            recipient_ids=remaining,
            type=NotificationType.GROUP_MEMBER_REMOVED,
            payload={
                "group_name": group_name,
                "removed_user_name": (removed_user.name if removed_user else "") or "",
                "actor_name": current_user.name or "",
            },
            actor_id=current_user.id,
            group_id=group_id,
        )

    await db.delete(target)
    await db.commit()


@router.get("/{group_id}/trips", response_model=List[GroupTripSummary])
async def list_group_trips(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_group_member(db, group_id, current_user.id)
    stmt = select(Trip).where(Trip.group_id == group_id).order_by(Trip.start_date.nulls_last(), Trip.created_at.desc())
    return (await db.execute(stmt)).scalars().all()


@router.post("/{group_id}/trips/{trip_id}", response_model=GroupTripSummary)
async def attach_trip_to_group(
    group_id: int,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Attach an existing trip to a group. Caller must be group admin AND trip admin."""
    caller = await _require_group_member(db, group_id, current_user.id)
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only group admins can attach trips")

    trip_caller = (await db.execute(
        select(TripMember).where(TripMember.trip_id == trip_id, TripMember.user_id == current_user.id)
    )).scalars().first()
    if not trip_caller or trip_caller.role != "admin":
        raise HTTPException(status_code=403, detail="You must be a trip admin to attach it")

    trip = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.group_id == group_id:
        return trip  # idempotent

    trip.group_id = group_id

    group = (await db.execute(select(Group).where(Group.id == group_id))).scalars().first()
    others = await _group_member_ids(db, group_id, exclude_user_id=current_user.id)
    if others:
        await notification_service.emit(
            db,
            recipient_ids=others,
            type=NotificationType.GROUP_TRIP_ATTACHED,
            payload={
                "trip_name": trip.name,
                "group_name": group.name if group else "",
                "actor_name": current_user.name or "",
            },
            actor_id=current_user.id,
            trip_id=trip_id,
            group_id=group_id,
        )

    await db.commit()
    await db.refresh(trip)
    return trip


@router.delete("/{group_id}/trips/{trip_id}", status_code=204)
async def detach_trip_from_group(
    group_id: int,
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    caller = await _require_group_member(db, group_id, current_user.id)
    if caller.role != "admin":
        raise HTTPException(status_code=403, detail="Only group admins can detach trips")

    trip = (await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.group_id == group_id)
    )).scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not attached to this group")

    trip.group_id = None
    await db.commit()


@router.get("/{group_id}/ideas", response_model=List[LibraryIdeaOut])
async def get_group_idea_library(
    group_id: int,
    q: Optional[str] = Query(None, description="Free-text search on idea title"),
    tag: Optional[str] = Query(None, description="Filter by tag (lowercase)"),
    trip_id: Optional[int] = Query(None, description="Limit to a single source trip"),
    sort: str = Query("recent", description="recent | top | title"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregated idea library across a group's trips, with tags + vote counts + provenance."""
    await _require_group_member(db, group_id, current_user.id)

    stmt = (
        select(IdeaBinItemModel, Trip)
        .join(Trip, Trip.id == IdeaBinItemModel.trip_id)
        .where(Trip.group_id == group_id)
    )
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(sa_func.lower(IdeaBinItemModel.title).like(like))
    if trip_id is not None:
        stmt = stmt.where(IdeaBinItemModel.trip_id == trip_id)
    if tag:
        tag_norm = tag.strip().lower()
        stmt = stmt.join(IdeaTag, IdeaTag.idea_id == IdeaBinItemModel.id).where(IdeaTag.tag == tag_norm)

    rows = (await db.execute(stmt)).all()

    results: list[LibraryIdeaOut] = []
    for idea, trip in rows:
        tag_rows = (await db.execute(
            select(IdeaTag.tag).where(IdeaTag.idea_id == idea.id)
        )).scalars().all()
        up = (await db.execute(
            select(sa_func.count(IdeaVote.id)).where(IdeaVote.idea_id == idea.id, IdeaVote.value == 1)
        )).scalar_one()
        down = (await db.execute(
            select(sa_func.count(IdeaVote.id)).where(IdeaVote.idea_id == idea.id, IdeaVote.value == -1)
        )).scalar_one()
        mine = (await db.execute(
            select(IdeaVote.value).where(IdeaVote.idea_id == idea.id, IdeaVote.user_id == current_user.id)
        )).scalars().first() or 0
        results.append(LibraryIdeaOut(
            id=idea.id, trip_id=idea.trip_id, title=idea.title,
            place_id=idea.place_id, lat=idea.lat, lng=idea.lng,
            url_source=idea.url_source, time_hint=idea.time_hint,
            added_by=idea.added_by, origin_idea_id=idea.origin_idea_id,
            tags=list(tag_rows), up=up, down=down, my_vote=mine,
            trip=TripProvenance(id=trip.id, name=trip.name),
        ))

    if sort == "top":
        results.sort(key=lambda r: (r.up - r.down, r.up), reverse=True)
    elif sort == "title":
        results.sort(key=lambda r: r.title.lower())
    else:
        results.sort(key=lambda r: r.id, reverse=True)
    return results


@router.get("/{group_id}/tags", response_model=List[TagSummary])
async def list_group_tags(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tag cloud for the group: every tag used across any of its trips' ideas, with counts."""
    await _require_group_member(db, group_id, current_user.id)
    stmt = (
        select(IdeaTag.tag, sa_func.count(IdeaTag.id))
        .join(IdeaBinItemModel, IdeaBinItemModel.id == IdeaTag.idea_id)
        .join(Trip, Trip.id == IdeaBinItemModel.trip_id)
        .where(Trip.group_id == group_id)
        .group_by(IdeaTag.tag)
        .order_by(sa_func.count(IdeaTag.id).desc())
    )
    rows = (await db.execute(stmt)).all()
    return [TagSummary(tag=tag, count=cnt) for tag, cnt in rows]
