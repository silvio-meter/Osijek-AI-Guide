"""
Request logging middleware with Correlation ID (X-Request-ID).

This middleware:
- Generates or accepts X-Request-ID
- Logs basic request information (method, path, status, duration, user)
- Puts the request_id into request.state for use in other parts of the app
"""

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.security import decode_token

logger = logging.getLogger("lega.api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every HTTP request with a correlation ID.
    """

    async def dispatch(self, request: Request, call_next):
        # Get or generate X-Request-ID
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Store it in request.state so it can be used elsewhere (e.g. in error handlers, services)
        request.state.request_id = request_id

        # Try to extract user info for logging
        user_id = self._extract_user_id(request)

        start_time = time.time()

        # Process the request
        response: Response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Add the request ID to the response headers
        response.headers["X-Request-ID"] = request_id

        # Log the request
        self._log_request(request, response, duration_ms, user_id, request_id)

        return response

    def _extract_user_id(self, request: Request) -> str | None:
        """Try to extract user_id from Authorization header for logging purposes."""
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return None

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)

        if payload and payload.get("type") == "access":
            return payload.get("sub")
        return None

    def _log_request(
        self,
        request: Request,
        response: Response,
        duration_ms: int,
        user_id: str | None,
        request_id: str,
    ):
        """Log basic request information in a readable format."""
        client_host = request.client.host if request.client else "-"
        user_part = f"user={user_id}" if user_id else "user=anonymous"

        log_message = (
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={duration_ms}ms "
            f"ip={client_host} "
            f"{user_part} "
            f"request_id={request_id}"
        )

        # Choose log level based on status
        if response.status_code >= 500:
            logger.error(log_message)
        elif response.status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)
