"""
Authentication router.

Endpoints:
- POST /auth/register  → Create new user account
- POST /auth/login     → Login and receive JWT access + refresh tokens
- POST /auth/refresh   → Get new tokens using refresh token (with rotation)
- POST /auth/logout    → Revoke refresh token (logout)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone

from schemas.auth import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    RefreshRequest, LogoutRequest
)
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    save_refresh_token,
    revoke_refresh_token,
    is_refresh_token_valid,
)
from config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from database import get_db
from models.user import User
from models.refresh_token import RefreshToken

# Standardized exceptions (Week 2 - Dan 3)
from core.exceptions import UnauthorizedException, ValidationException

# Rate Limiting (Week 2)
from core.rate_limiter import (
    conditional_limit,
    LOGIN_RATE_LIMIT,
    REGISTER_RATE_LIMIT,
    REFRESH_RATE_LIMIT,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account. Email must be unique. Password is hashed with bcrypt."
)
@conditional_limit(REGISTER_RATE_LIMIT)
def register_user(
    request: Request,
    response: Response,
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Register a new user.

    - Normalizes email to lowercase
    - Checks for duplicate email
    - Hashes password before storing
    - Returns the created user (without password)
    """
    # Normalize email
    email = user_in.email.lower().strip()

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    # Hash the password
    try:
        hashed_password = get_password_hash(user_in.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    # Create user
    new_user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=user_in.full_name.strip() if user_in.full_name else None,
        is_active=True,
        is_superuser=False,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="Authenticates user and returns JWT access + refresh tokens."
)
@conditional_limit(LOGIN_RATE_LIMIT)
def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    User login.

    - Validates email + password
    - Returns short-lived access token + long-lived refresh token
    """
    email = login_data.email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise UnauthorizedException(message="Incorrect email or password")

    if not verify_password(login_data.password, user.hashed_password):
        raise UnauthorizedException(message="Incorrect email or password")

    if not user.is_active:
        raise ValidationException(
            message="User account is inactive",
            details={"email": email}
        )

    # Generate tokens
    access_token = create_access_token(user_id=user.id, email=user.email)
    refresh_token, jti = create_refresh_token(user_id=user.id)

    # Save refresh token jti in DB (for revocation / rotation)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    save_refresh_token(db, user_id=user.id, jti=jti, expires_at=expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ==========================================
# Refresh & Logout (Dan 4)
# ==========================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a valid refresh token",
)
@conditional_limit(REFRESH_RATE_LIMIT)
def refresh_token(
    request: Request,
    response: Response,
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Takes a valid refresh token and returns a new access token.
    Implements refresh token rotation (old refresh token is revoked).
    """
    payload = decode_token(refresh_request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedException(message="Invalid refresh token")

    user_id = int(payload["sub"])
    jti = payload.get("jti")
    if not jti:
        raise UnauthorizedException(message="Invalid refresh token")

    # Check database blacklist + expiry
    if not is_refresh_token_valid(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired"
        )

    # Verify user still exists and is active
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Revoke the old refresh token (rotation)
    revoke_refresh_token(db, jti)

    # Issue new tokens
    access_token = create_access_token(user_id=user.id, email=user.email)
    new_refresh_token, new_jti = create_refresh_token(user_id=user.id)

    new_expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    save_refresh_token(db, user_id=user.id, jti=new_jti, expires_at=new_expires)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    summary="Logout - revokes the refresh token",
)
def logout(
    logout_request: LogoutRequest,
    db: Session = Depends(get_db)
):
    """Revokes the provided refresh token so it can no longer be used."""
    payload = decode_token(logout_request.refresh_token)
    if payload and payload.get("type") == "refresh":
        jti = payload.get("jti")
        if jti:
            revoke_refresh_token(db, jti)

    # Always return success (don't leak information)
    return {"message": "Successfully logged out"}
