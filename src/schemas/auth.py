"""
Authentication related Pydantic schemas.
Used for request validation and response models.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for user registration (POST /auth/register)."""
    email: EmailStr
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=72,
        description="Password must be between 8 and 72 characters (bcrypt limitation)"
    )
    full_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="Optional full name of the user"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "email": "ana@example.com",
                "password": "mojalozinka123",
                "full_name": "Ana Horvat"
            }
        }
    )


class UserResponse(BaseModel):
    """Safe response schema (never expose hashed_password)."""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,   # Important: allows creating from SQLAlchemy User object
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "ana@example.com",
                "full_name": "Ana Horvat",
                "is_active": True,
                "created_at": "2026-05-31T12:34:56.789Z"
            }
        }
    )


# ==========================================
# Login & Token schemas (Dan 3)
# ==========================================

class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "email": "ana@example.com",
                "password": "mojalozinka123"
            }
        }
    )


class TokenResponse(BaseModel):
    """Response containing JWT tokens after successful login or refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    )


class RefreshRequest(BaseModel):
    """Body for refreshing access token using a refresh token."""
    refresh_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


class LogoutRequest(BaseModel):
    """Body for logout (revokes the refresh token)."""
    refresh_token: str
