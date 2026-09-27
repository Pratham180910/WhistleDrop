from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import jwt

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.moderator import Moderator
from app.schemas.moderator import ModeratorLogin, TokenResponse

_GENERIC_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

_bearer = HTTPBearer()


def authenticate_moderator(db: Session, login: ModeratorLogin) -> Optional[Moderator]:
    """Returns the Moderator if credentials are valid and account is active, else None."""
    moderator = db.query(Moderator).filter(Moderator.username == login.username).first()
    if not moderator:
        # Constant-time comparison avoidance: still hash to prevent timing attacks
        verify_password(login.password, "$2b$12$placeholder_hash_to_prevent_timing_attack_leak")
        return None
    if not verify_password(login.password, moderator.password_hash):
        return None
    if not moderator.is_active:
        return None
    return moderator


def login_moderator(db: Session, login: ModeratorLogin) -> TokenResponse:
    """Authenticates a moderator and returns a JWT. Raises 401 on failure."""
    moderator = authenticate_moderator(db, login)
    if not moderator:
        raise _GENERIC_401
    token = create_access_token(subject=moderator.username)
    return TokenResponse(access_token=token)


# ── Reusable auth dependency for future protected moderator routes ────────────

def require_moderator(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Moderator:
    """FastAPI dependency that validates the JWT and returns the active Moderator.

    Use as: `moderator: Moderator = Depends(require_moderator)` on protected routes.
    """
    try:
        payload = decode_access_token(credentials.credentials)
        username: str = payload.get("sub", "")
        if not username:
            raise _GENERIC_401
    except jwt.PyJWTError:
        raise _GENERIC_401

    moderator = db.query(Moderator).filter(Moderator.username == username).first()
    if not moderator or not moderator.is_active:
        raise _GENERIC_401
    return moderator
