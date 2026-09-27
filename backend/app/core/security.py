import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


# ── Case-code utilities ──────────────────────────────────────────────────────

def generate_case_code() -> str:
    """Generates a cryptographically random, URL-safe case code."""
    return secrets.token_urlsafe(24)


def hash_case_code(case_code: str) -> str:
    """Computes the SHA-256 hash of a case code for secure storage."""
    return hashlib.sha256(case_code.strip().encode("utf-8")).hexdigest()


# ── Password utilities (bcrypt) ──────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Returns a bcrypt hash of the given password."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifies a plain password against a bcrypt hash. Returns False on any error."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


# ── JWT utilities ────────────────────────────────────────────────────────────

def create_access_token(subject: str) -> str:
    """Creates a signed JWT access token for the given subject (moderator username).
    
    Expiration is controlled by settings.ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
