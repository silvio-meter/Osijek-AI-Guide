"""
Security utilities for authentication.

- Password hashing (bcrypt)
- JWT token creation & verification (python-jose)
"""

import bcrypt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from sqlalchemy.orm import Session

from config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from models.refresh_token import RefreshToken


# ==========================================
# Password hashing
# ==========================================

def get_password_hash(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    bcrypt has a hard limit of 72 bytes. We safely truncate (UTF-8 aware).
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


# ==========================================
# JWT Token handling
# ==========================================

def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Internal helper to create a signed JWT."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_access_token(user_id: int, email: str) -> str:
    """Create a short-lived access token."""
    return _create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"email": email}
    )


def create_refresh_token(user_id: int) -> tuple[str, str]:
    """
    Create a long-lived refresh token + unique jti.
    Returns (token, jti)
    """
    jti = str(uuid.uuid4())

    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: Dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": expire,
        "jti": jti,
    }

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt, jti


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    Returns the payload if valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_type(token: str) -> Optional[str]:
    """Helper to quickly get the token type (access / refresh)."""
    payload = decode_token(token)
    if payload:
        return payload.get("type")
    return None


# ==========================================
# Refresh token database helpers (blacklist + rotation)
# ==========================================

def save_refresh_token(db: Session, user_id: int, jti: str, expires_at: datetime) -> RefreshToken:
    """Persist a refresh token jti in the database."""
    token_record = RefreshToken(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(token_record)
    db.commit()
    db.refresh(token_record)
    return token_record


def revoke_refresh_token(db: Session, jti: str) -> bool:
    """Revoke (blacklist) a refresh token by its jti.
    Returns True if the token was successfully revoked (or was already revoked).
    """
    token_record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not token_record:
        return False
    if token_record.revoked:
        return True  # Already revoked - idempotent

    token_record.revoked = True
    db.commit()
    return True


def is_refresh_token_valid(db: Session, jti: str) -> bool:
    """Check if a refresh token jti exists, is not revoked, and not expired."""
    token_record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not token_record:
        return False
    if token_record.revoked:
        return False

    # Make comparison safe (handle both naive and aware datetimes)
    expires = token_record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires < datetime.now(timezone.utc):
        return False
    return True
