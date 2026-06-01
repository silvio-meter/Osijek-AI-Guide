"""
Rate Limiting configuration using slowapi (Dan 2 - Advanced).

Key improvements over Day 1:
- Smart key function: prefers authenticated user_id, falls back to IP
- Better rate limit definitions
- Improved 429 error responses
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from starlette.responses import JSONResponse

from core.security import decode_token
from schemas.error import ErrorResponse


import os

# ==========================================
# Environment Detection
# ==========================================

# We consider the app to be in "test mode" if either:
# - The TESTING environment variable is set to "1", or
# - Pytest is running (PYTEST_CURRENT_TEST is automatically set by pytest)
IS_TESTING = (
    os.getenv("TESTING") == "1" or
    "PYTEST_CURRENT_TEST" in os.environ
)


# ==========================================
# Rate Limit Definitions
# ==========================================

if IS_TESTING:
    # In test mode we completely disable rate limiting on all endpoints.
    # This is the correct long-term approach because:
    # - Normal tests should NEVER go through rate-limited auth endpoints for setup.
    # - We only want to test rate limiting behavior in dedicated, isolated tests.
    # - This makes the entire test suite deterministic and fast.
    DEFAULT_RATE_LIMIT = None          # None = no limit
    LOGIN_RATE_LIMIT = None
    REGISTER_RATE_LIMIT = None
    REFRESH_RATE_LIMIT = None
    CHAT_RATE_LIMIT = None
else:
    # Production / normal development limits (deliberately strict for security)
    DEFAULT_RATE_LIMIT = "120/minute"
    LOGIN_RATE_LIMIT = "8/minute"
    REGISTER_RATE_LIMIT = "4/minute"
    REFRESH_RATE_LIMIT = "15/minute"
    CHAT_RATE_LIMIT = "25/minute"


# ==========================================
# Smart Rate Limit Key Function
# ==========================================

def get_rate_limit_key(request: Request) -> str:
    """
    Returns the key used for rate limiting.

    Priority:
    1. Authenticated user → "user:{user_id}"
    2. Fallback → IP address

    This gives much fairer limiting for logged-in users across different IPs
    (mobile + wifi, VPN, etc.).
    """
    # Try to extract Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)

        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"

    # Fallback to IP address
    return get_remote_address(request)


# ==========================================
# Limiter instance (now using smart key)
# ==========================================

# In testing mode we don't want any global rate limits at all.
# Individual routes can still opt-in to rate limiting if needed for specific tests.
if IS_TESTING:
    limiter = Limiter(
        key_func=get_rate_limit_key,
        default_limits=[],           # No global limits in test mode
        headers_enabled=False,
    )
else:
    limiter = Limiter(
        key_func=get_rate_limit_key,
        default_limits=[DEFAULT_RATE_LIMIT],
        headers_enabled=True,
    )


# ==========================================
# Custom 429 Handler (improved for mobile apps)
# ==========================================

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Returns a clean, consistent 429 response using the standard ErrorResponse format.
    """
    retry_after = getattr(exc, "retry_after", 60)

    error_response = ErrorResponse(
        error="rate_limit_exceeded",
        message="Previše zahtjeva u kratkom vremenu. Molimo pričekajte prije sljedećeg pokušaja.",
        details={"retry_after_seconds": int(retry_after)},
    )

    return JSONResponse(
        status_code=429,
        content=error_response.model_dump(),
        headers={"Retry-After": str(int(retry_after))},
    )


# ==========================================
# Helper for applying rate limits safely in tests
# ==========================================

def conditional_limit(limit_string: str):
    """
    Returns a rate limit decorator, or a no-op decorator if we're in testing mode.

    Usage:
        @conditional_limit(LOGIN_RATE_LIMIT)
        def login(...):
            ...
    """
    if IS_TESTING:
        # Return a no-op decorator
        def noop_decorator(func):
            return func
        return noop_decorator
    else:
        return limiter.limit(limit_string)
