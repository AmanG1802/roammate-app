from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.all_models import User
from app.core.config import settings
from app.core.security import ALGORITHM


# kept for OpenAPI docs / Swagger "Authorize" button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


def _extract_token(request: Request, header_token: str | None) -> str | None:
    """Allow either Authorization: Bearer <jwt> (iOS) or rm_access cookie (web)."""
    if header_token:
        return header_token
    return request.cookies.get("rm_access")


async def _resolve_user(db: AsyncSession, token: str | None, *, require_verified: bool) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        token_ver = payload.get("ver")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    if user is None:
        raise credentials_exception

    # Tokens issued before auth_version was bumped are no longer valid.
    if token_ver is not None and int(token_ver) != int(user.auth_version or 1):
        raise credentials_exception

    if require_verified and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    return await _resolve_user(db, _extract_token(request, token), require_verified=True)


async def get_current_user_unverified(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Same as get_current_user but does NOT require email_verified.

    Used by /auth/verify/resend and similar routes the unverified user must hit.
    """
    return await _resolve_user(db, _extract_token(request, token), require_verified=False)


# ── Admin auth ────────────────────────────────────────────────────────────────

admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


def get_admin(token: str = Depends(admin_oauth2_scheme)) -> bool:
    """Validate admin JWT — rejects regular user tokens."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an admin token")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
