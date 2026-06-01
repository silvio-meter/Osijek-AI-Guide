"""
Standardized error response models for the Osijek AI Guide API.

All errors returned by the API should follow this structure for
consistent error handling on the mobile app side.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any


class ErrorResponse(BaseModel):
    """
    Standard error response format used across the entire API.
    """

    error: str = Field(
        ...,
        description="Machine-readable error code (e.g. 'rate_limit_exceeded', 'invalid_credentials')",
        examples=["rate_limit_exceeded", "invalid_credentials", "validation_error"]
    )

    message: str = Field(
        ...,
        description="Human-readable error message (preferably in Croatian for production)",
        examples=["Previše zahtjeva. Molimo pričekajte prije sljedećeg pokušaja."]
    )

    details: Optional[Any] = Field(
        None,
        description="Optional additional details about the error (e.g. validation errors list)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "rate_limit_exceeded",
                "message": "Previše zahtjeva. Molimo pričekajte prije sljedećeg pokušaja.",
                "details": None
            }
        }
    )
