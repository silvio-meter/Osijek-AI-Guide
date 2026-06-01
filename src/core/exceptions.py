"""
Custom exceptions for the Osijek AI Guide API.

These exceptions are caught by global handlers in api.py and converted
to consistent ErrorResponse objects.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found", details: Any = None):
        super().__init__(
            error_code="not_found",
            message=message,
            status_code=404,
            details=details,
        )


class UnauthorizedException(AppException):
    """Authentication required or failed."""

    def __init__(self, message: str = "Authentication required", details: Any = None):
        super().__init__(
            error_code="unauthorized",
            message=message,
            status_code=401,
            details=details,
        )


class ForbiddenException(AppException):
    """User does not have permission."""

    def __init__(self, message: str = "Permission denied", details: Any = None):
        super().__init__(
            error_code="forbidden",
            message=message,
            status_code=403,
            details=details,
        )


class ValidationException(AppException):
    """Input validation failed."""

    def __init__(self, message: str = "Validation error", details: Any = None):
        super().__init__(
            error_code="validation_error",
            message=message,
            status_code=422,
            details=details,
        )


class RateLimitException(AppException):
    """Too many requests."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Any = None,
    ):
        super().__init__(
            error_code="rate_limit_exceeded",
            message=message,
            status_code=429,
            details=details,
        )
        self.retry_after = retry_after
