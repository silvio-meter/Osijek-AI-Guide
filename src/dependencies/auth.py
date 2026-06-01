"""
JWT Authentication dependencies for FastAPI.

Provides:
- get_current_user: Extracts and validates JWT, returns User from DB
- get_current_active_user: Same as above + ensures user is active
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.user import User
from core.security import decode_token

# Standardized exceptions for consistent ErrorResponse format
from core.exceptions import UnauthorizedException, ForbiddenException

# Use HTTPBearer for clean "Authorization: Bearer <token>" handling
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency that extracts the current authenticated user from JWT.
    
    Raises 401 if:
    - No token provided
    - Token is invalid/expired
    - Token is not an access token
    - User does not exist or is inactive
    """
    if not credentials:
        raise UnauthorizedException(
            message="Niste autentificirani. Potreban je valjani access token.",
            details={"reason": "no_token"}
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise UnauthorizedException(
            message="Token je nevažeći ili istekao.",
            details={"reason": "invalid_or_expired"}
        )

    # Only allow access tokens for protected routes (not refresh tokens)
    if payload.get("type") != "access":
        raise UnauthorizedException(
            message="Nevažeći tip tokena (očekivan access token).",
            details={"reason": "wrong_token_type"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(
            message="Nevažeći sadržaj tokena.",
            details={"reason": "invalid_payload"}
        )

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise UnauthorizedException(
            message="Nevažeći identifikator korisnika u tokenu.",
            details={"reason": "invalid_user_id"}
        )

    user = db.query(User).filter(User.id == user_id_int).first()
    if not user:
        raise UnauthorizedException(
            message="Korisnik nije pronađen.",
            details={"reason": "user_not_found"}
        )

    if not user.is_active:
        raise ForbiddenException(
            message="Korisnički račun je neaktivan.",
            details={"reason": "account_inactive"}
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Same as get_current_user but explicitly requires active user."""
    return current_user
