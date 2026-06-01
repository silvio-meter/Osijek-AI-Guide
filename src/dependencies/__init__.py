"""
FastAPI dependencies for Osijek AI Guide.
"""
from dependencies.auth import get_current_user, get_current_active_user

__all__ = ["get_current_user", "get_current_active_user"]
