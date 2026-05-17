"""Authentication endpoints: signup/login/verify/refresh/logout/oauth/reset.

Token transport:
  - Web clients: cookies (`rm_access`, `rm_refresh`) set HttpOnly + Secure +
    SameSite=Lax. The refresh cookie is scoped to /api/auth so it isn't sent
    on every request.
  - iOS clients: same response body also returns the raw tokens so the iOS
    APIClient can store them in Keychain.
"""
from __future__ import annotations

from typing import Literal, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_unverified
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.all_models import User, UserIdentity
from app.services.auth import oauth_apple, oauth_google
from app.services.auth.email import (
    send_email_changed_notice,
    send_password_reset,
    send_verify_email,
)
from app.services.auth.linking import (
    OAuthLinkBlocked,
    OAuthClaims,
    find_or_create_user_for_oauth,
)
from app.services.auth.tokens import (
    create_access_token,
    issue_refresh_token,
    revoke_all_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.auth.verifications import (
    consume_reset,
    consume_verification,
    issue_reset,
    issue_verification,
)
from app.utils.tz import utc_now


router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    skip_verification: bool = False


class VerifyIn(BaseModel):
    token: str


class ResendIn(BaseModel):
    email: EmailStr


class OAuthIn(BaseModel):
    id_token: str
    platform: Literal["web", "ios"] = "web"
    nonce: Optional[str] = None    # Apple-only; ignored by Google


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangeEmailIn(BaseModel):
    new_email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int                # seconds for access token
    user: dict


class IdentityOut(BaseModel):
    provider: str
    email_at_link: Optional[str]
    created_at: str
    has_password: bool


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "avatar_url": u.avatar_url,
        "email_verified": bool(u.email_verified),
    }


def _set_cookies(response: Response, *, access: str, refresh: str) -> None:
    response.set_cookie(
        "rm_access",
        access,
        max_age=settings.ACCESS_TOKEN_TTL_MIN * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )
    response.set_cookie(
        "rm_refresh",
        refresh,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 86400,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
        path="/api/auth",
    )


def _clear_cookies(response: Response) -> None:
    for name, path in [("rm_access", "/"), ("rm_refresh", "/api/auth")]:
        response.delete_cookie(name, path=path, domain=settings.COOKIE_DOMAIN)


async def _issue_session(
    db: AsyncSession,
    response: Response,
    user: User,
    *,
    device_label: Optional[str] = None,
) -> TokenPair:
    access = create_access_token(user)
    raw_refresh, _ = await issue_refresh_token(db, user, device_label=device_label)
    _set_cookies(response, access=access, refresh=raw_refresh)
    return TokenPair(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_TTL_MIN * 60,
        user=_user_dict(user),
    )


def _build_verify_url(token: str) -> str:
    return f"{settings.PUBLIC_WEB_URL.rstrip('/')}/verify?{urlencode({'token': token})}"


def _build_reset_url(token: str) -> str:
    return f"{settings.PUBLIC_WEB_URL.rstrip('/')}/reset?{urlencode({'token': token})}"


def _device_label(request: Request) -> str:
    ua = request.headers.get("user-agent", "")[:120]
    return ua or "unknown"


# ── Email + password ─────────────────────────────────────────────────────────

@router.post("/signup", status_code=200)
async def signup(body: SignupIn, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        # Don't reveal whether the email is taken or just unverified — return 200 either way.
        if not existing.email_verified:
            raw = await issue_verification(db, existing, email=email, purpose="signup")
            await db.commit()
            send_verify_email(email, existing.name, _build_verify_url(raw))
        return {"detail": "If the email is available, a verification link was sent."}

    user = User(
        email=email,
        name=body.name,
        hashed_password=get_password_hash(body.password),
        email_verified=False,
    )
    db.add(user)
    await db.flush()
    raw = await issue_verification(db, user, email=email, purpose="signup")
    await db.commit()
    send_verify_email(email, user.name, _build_verify_url(raw))
    return {"detail": "Check your email to verify your account."}


@router.post("/verify", response_model=TokenPair)
async def verify(
    body: VerifyIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    row = await consume_verification(db, body.token)
    if row is None:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="User no longer exists")

    if row.purpose == "change_email":
        user.email = row.email
        send_email_changed_notice(row.email, user.name, row.email)
    user.email_verified = True
    user.email_verified_at = utc_now()
    await db.flush()
    pair = await _issue_session(db, response, user, device_label=_device_label(request))
    await db.commit()
    return pair


@router.post("/verify/resend", status_code=204)
async def verify_resend(
    body: ResendIn,
    db: AsyncSession = Depends(get_db),
):
    email = body.email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    # Always return 204 to avoid email enumeration.
    if user is not None and not user.email_verified:
        raw = await issue_verification(db, user, email=email, purpose="signup")
        await db.commit()
        send_verify_email(email, user.name, _build_verify_url(raw))
    return Response(status_code=204)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = body.email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.email_verified and not body.skip_verification:
        raw = await issue_verification(db, user, email=email, purpose="signup")
        await db.commit()
        send_verify_email(email, user.name, _build_verify_url(raw))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email not verified")

    pair = await _issue_session(db, response, user, device_label=_device_label(request))
    await db.commit()
    return pair


# ── OAuth ────────────────────────────────────────────────────────────────────

@router.post("/google", response_model=TokenPair)
async def login_with_google(
    body: OAuthIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        ident = oauth_google.verify(body.id_token, platform=body.platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        user = await find_or_create_user_for_oauth(db, OAuthClaims(
            provider="google",
            subject=ident.sub,
            email=ident.email,
            email_verified=ident.email_verified,
            name=ident.name,
            avatar_url=ident.picture,
        ))
    except OAuthLinkBlocked as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "verify_existing_email_first", "email": exc.email},
        )

    pair = await _issue_session(db, response, user, device_label=_device_label(request))
    await db.commit()
    return pair


@router.post("/apple", response_model=TokenPair)
async def login_with_apple(
    body: OAuthIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        ident = await oauth_apple.verify(body.id_token, platform=body.platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        user = await find_or_create_user_for_oauth(db, OAuthClaims(
            provider="apple",
            subject=ident.sub,
            email=ident.email,
            email_verified=ident.email_verified,
            name=None,           # Apple supplies name only on first login (client must POST it separately if desired)
            avatar_url=None,
        ))
    except OAuthLinkBlocked as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "verify_existing_email_first", "email": exc.email},
        )

    pair = await _issue_session(db, response, user, device_label=_device_label(request))
    await db.commit()
    return pair


# ── Refresh / logout ─────────────────────────────────────────────────────────

class RefreshIn(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw = body.refresh_token or request.cookies.get("rm_refresh")
    if not raw:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        user, new_raw, _ = await rotate_refresh_token(db, raw)
    except ValueError:
        _clear_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access = create_access_token(user)
    _set_cookies(response, access=access, refresh=new_raw)
    await db.commit()
    return TokenPair(
        access_token=access,
        refresh_token=new_raw,
        expires_in=settings.ACCESS_TOKEN_TTL_MIN * 60,
        user=_user_dict(user),
    )


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw = request.cookies.get("rm_refresh")
    body_token = None
    try:
        body = await request.json()
        body_token = (body or {}).get("refresh_token")
    except Exception:
        pass
    raw = raw or body_token
    if raw:
        await revoke_refresh_token(db, raw)
        await db.commit()
    _clear_cookies(response)
    return Response(status_code=204)


# ── Password reset ───────────────────────────────────────────────────────────

@router.post("/password/forgot", status_code=204)
async def password_forgot(body: ForgotIn, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is not None and user.hashed_password:
        raw = await issue_reset(db, user)
        await db.commit()
        send_password_reset(email, user.name, _build_reset_url(raw))
    return Response(status_code=204)


@router.post("/password/reset", status_code=200)
async def password_reset(
    body: ResetIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    row = await consume_reset(db, body.token)
    if row is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="User no longer exists")

    user.hashed_password = get_password_hash(body.new_password)
    user.auth_version = (user.auth_version or 1) + 1
    await revoke_all_for_user(db, user.id)
    pair = await _issue_session(db, response, user, device_label=_device_label(request))
    await db.commit()
    return pair


# ── Account management ──────────────────────────────────────────────────────

@router.get("/me", response_model=dict)
async def me(current_user: User = Depends(get_current_user)):
    return _user_dict(current_user)


@router.get("/me/identities")
async def list_identities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(UserIdentity).where(UserIdentity.user_id == current_user.id)
    )).scalars().all()
    return {
        "has_password": bool(current_user.hashed_password),
        "identities": [
            {
                "provider": r.provider,
                "email_at_link": r.email_at_link,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.delete("/me/identities/{provider}", status_code=204)
async def unlink_identity(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(UserIdentity).where(UserIdentity.user_id == current_user.id)
    )).scalars().all()
    target = next((r for r in rows if r.provider == provider), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Identity not linked")
    other_methods = (len(rows) - 1) + (1 if current_user.hashed_password else 0)
    if other_methods <= 0:
        raise HTTPException(status_code=400, detail="Cannot remove the only sign-in method")
    await db.delete(target)
    await db.commit()
    return Response(status_code=204)


@router.post("/me/email/change", status_code=204)
async def change_email(
    body: ChangeEmailIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.hashed_password or not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Password incorrect")
    new_email = body.new_email.lower()
    if new_email == current_user.email:
        raise HTTPException(status_code=400, detail="Same email")
    taken = (await db.execute(select(User).where(User.email == new_email))).scalar_one_or_none()
    if taken is not None:
        raise HTTPException(status_code=409, detail="Email already in use")
    raw = await issue_verification(db, current_user, email=new_email, purpose="change_email")
    await db.commit()
    send_verify_email(new_email, current_user.name, _build_verify_url(raw))
    return Response(status_code=204)
