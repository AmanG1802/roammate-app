"""Admin-only endpoints for the Roammate dashboard.

All GET endpoints require a valid admin JWT (``Depends(get_admin)``).
The login endpoint is public.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin
from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models.all_models import GoogleMapsApiUsage, TokenUsage, User

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def admin_login(body: LoginRequest):
    if body.username != settings.ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    expire = datetime.utcnow() + timedelta(hours=settings.ADMIN_TOKEN_EXPIRE_HOURS)
    token = jwt.encode({"admin": True, "exp": expire}, settings.SECRET_KEY, algorithm=ALGORITHM)
    return LoginResponse(access_token=token)


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", dependencies=[Depends(get_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {
        "total": len(users),
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


# ── Token Usage Options (distinct providers & models from DB) ─────────────────

@router.get("/token-usage/options", dependencies=[Depends(get_admin)])
async def token_usage_options(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TokenUsage.provider, TokenUsage.model)
        .distinct()
        .order_by(TokenUsage.provider, TokenUsage.model)
    )
    rows = result.all()
    providers: dict[str, list[str]] = {}
    for r in rows:
        providers.setdefault(r.provider, []).append(r.model)
    return {"providers": providers}


# ── Token Usage Summary ───────────────────────────────────────────────────────

@router.get("/token-usage/summary", dependencies=[Depends(get_admin)])
async def token_usage_summary(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    month: Optional[str] = None,
    day: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    filters = _token_filters(model=model, provider=provider, month=month, day=day)
    base = select(TokenUsage).where(*filters) if filters else select(TokenUsage)
    result = await db.execute(base)
    rows = result.scalars().all()

    total_tokens = sum(r.tokens_total for r in rows)
    total_cost = float(sum(r.cost_usd or 0 for r in rows))
    request_count = len(rows)

    by_provider: dict[str, int] = {}
    by_model: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for r in rows:
        by_provider[r.provider] = by_provider.get(r.provider, 0) + r.tokens_total
        by_model[r.model] = by_model.get(r.model, 0) + r.tokens_total
        if r.source:
            by_source[r.source] = by_source.get(r.source, 0) + r.tokens_total

    return {
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "request_count": request_count,
        "avg_tokens_per_request": round(total_tokens / request_count, 1) if request_count else 0,
        "top_model": max(by_model, key=by_model.get) if by_model else None,
        "by_provider": by_provider,
        "by_model": by_model,
        "by_source": by_source,
    }


# ── Token Usage Per User ──────────────────────────────────────────────────────

@router.get("/token-usage/users", dependencies=[Depends(get_admin)])
async def token_usage_users(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    month: Optional[str] = None,
    day: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    filters = _token_filters(model=model, provider=provider, month=month, day=day)
    stmt = (
        select(
            TokenUsage.user_id,
            User.name,
            User.email,
            func.sum(TokenUsage.tokens_in).label("tokens_in"),
            func.sum(TokenUsage.tokens_out).label("tokens_out"),
            func.sum(TokenUsage.tokens_total).label("tokens_total"),
            func.sum(TokenUsage.cost_usd).label("cost_usd"),
        )
        .join(User, TokenUsage.user_id == User.id, isouter=True)
        .where(*filters)
        .group_by(TokenUsage.user_id, User.name, User.email)
        .order_by(func.sum(TokenUsage.tokens_total).desc())
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where((User.name.ilike(like)) | (User.email.ilike(like)))

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "user_id": r.user_id,
            "name": r.name or ("Unattributed" if r.user_id is None else None),
            "email": r.email or ("—" if r.user_id is None else None),
            "tokens_in": int(r.tokens_in or 0),
            "tokens_out": int(r.tokens_out or 0),
            "tokens_total": int(r.tokens_total or 0),
            "cost_usd": round(float(r.cost_usd or 0), 4),
        }
        for r in rows
    ]


# ── Maps Usage Summary ────────────────────────────────────────────────────────

@router.get("/maps-usage/summary", dependencies=[Depends(get_admin)])
async def maps_usage_summary(
    ops: Optional[list[str]] = Query(None),
    month: Optional[str] = None,
    day: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    filters = _maps_filters(ops=ops, month=month, day=day)
    base = select(GoogleMapsApiUsage).where(*filters) if filters else select(GoogleMapsApiUsage)
    result = await db.execute(base)
    rows = result.scalars().all()

    total_calls = len(rows)
    cache_hits = sum(1 for r in rows if r.cache_state == "hit")
    errors = sum(1 for r in rows if r.status == "error")
    total_cost = float(sum(r.cost_usd or 0 for r in rows))

    by_op: dict[str, int] = {}
    for r in rows:
        by_op[r.op] = by_op.get(r.op, 0) + 1

    return {
        "total_calls": total_calls,
        "cache_hits": cache_hits,
        "cache_hit_rate_pct": round(cache_hits / total_calls * 100, 1) if total_calls else 0,
        "error_count": errors,
        "error_rate_pct": round(errors / total_calls * 100, 1) if total_calls else 0,
        "total_cost_usd": round(total_cost, 4),
        "by_op": by_op,
    }


# ── Maps Usage Per User ───────────────────────────────────────────────────────

@router.get("/maps-usage/users", dependencies=[Depends(get_admin)])
async def maps_usage_users(
    ops: Optional[list[str]] = Query(None),
    month: Optional[str] = None,
    day: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    filters = _maps_filters(ops=ops, month=month, day=day)
    stmt = (
        select(
            GoogleMapsApiUsage.user_id,
            User.name,
            User.email,
            GoogleMapsApiUsage.op,
            func.count().label("call_count"),
            func.sum(GoogleMapsApiUsage.cost_usd).label("cost_usd"),
        )
        .join(User, GoogleMapsApiUsage.user_id == User.id, isouter=True)
        .where(*filters)
        .group_by(GoogleMapsApiUsage.user_id, User.name, User.email, GoogleMapsApiUsage.op)
        .order_by(GoogleMapsApiUsage.user_id)
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where((User.name.ilike(like)) | (User.email.ilike(like)))

    result = await db.execute(stmt)
    rows = result.all()

    # Pivot: group by user_id (None grouped as "Unattributed"), build calls_by_op dict
    user_map: dict = {}
    for r in rows:
        uid = r.user_id if r.user_id is not None else "unattributed"
        if uid not in user_map:
            user_map[uid] = {
                "user_id": r.user_id,
                "name": r.name or ("Unattributed" if r.user_id is None else None),
                "email": r.email or ("—" if r.user_id is None else None),
                "calls_by_op": {},
                "cost_usd": 0.0,
            }
        user_map[uid]["calls_by_op"][r.op] = int(r.call_count or 0)
        user_map[uid]["cost_usd"] += float(r.cost_usd or 0)

    out = sorted(user_map.values(), key=lambda u: sum(u["calls_by_op"].values()), reverse=True)
    for u in out:
        u["cost_usd"] = round(u["cost_usd"], 4)
    return out


# ── Helpers ───────────────────────────────────────────────────────────────────

def _token_filters(
    *,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    month: Optional[str] = None,
    day: Optional[str] = None,
) -> list:
    clauses = []
    if model:
        clauses.append(TokenUsage.model == model)
    if provider:
        clauses.append(TokenUsage.provider == provider)
    if day:
        try:
            d = datetime.strptime(day, "%Y-%m-%d")
            clauses.append(func.date(TokenUsage.created_at) == d.date())
        except ValueError:
            pass
    elif month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            clauses.append(TokenUsage.created_at >= start)
            clauses.append(TokenUsage.created_at < end)
        except ValueError:
            pass
    return clauses


def _maps_filters(
    *,
    ops: Optional[list[str]] = None,
    month: Optional[str] = None,
    day: Optional[str] = None,
) -> list:
    clauses = []
    if ops:
        clauses.append(GoogleMapsApiUsage.op.in_(ops))
    if day:
        try:
            d = datetime.strptime(day, "%Y-%m-%d")
            clauses.append(func.date(GoogleMapsApiUsage.created_at) == d.date())
        except ValueError:
            pass
    elif month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            clauses.append(GoogleMapsApiUsage.created_at >= start)
            clauses.append(GoogleMapsApiUsage.created_at < end)
        except ValueError:
            pass
    return clauses
