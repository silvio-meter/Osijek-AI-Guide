"""
Security middleware for the Osijek AI Guide API (Week 2 - Dan 4).

Includes:
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- Basic request body size limit
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds common security headers to every response.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Basic XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (restrict powerful browser features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # HSTS - only enable in production over HTTPS
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejects requests that are too large.

    This is a simple implementation. For very high traffic, consider using
    a reverse proxy (nginx, traefik, cloudflare) for this instead.
    """

    def __init__(self, app, max_size: int = 1_000_000):  # 1 MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    logger.warning(
                        f"Request body too large: {size} bytes from {request.client.host}"
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "payload_too_large",
                            "message": f"Request body exceeds maximum allowed size of {self.max_size} bytes.",
                            "details": {"max_size_bytes": self.max_size},
                        },
                    )
            except ValueError:
                pass  # Invalid Content-Length header, let it pass to be handled elsewhere

        return await call_next(request)
