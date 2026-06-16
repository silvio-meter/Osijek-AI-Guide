"""
Phase 3 — unified tool registry (server + client execution).

Server tools run on FastAPI; client tools are emitted as SSE tool_request_client
events and executed on the Flutter app.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool

from tools import (
    get_all_tools as get_server_langchain_tools,
    get_current_weather_osijek,
    search_osijek_events,
    search_restaurants_or_food,
)

ExecutionTarget = Literal["server", "client"]

# ---------------------------------------------------------------------------
# Client tool stubs — bound to the LLM but never executed on the server.
# ---------------------------------------------------------------------------


@tool
def get_place_details(place_id: str) -> str:
    """Get rich details for one place from the mobile catalog (name, description, tags, neighborhood).
    Use when the user asks about a specific venue or you need facts before recommending."""
    return "CLIENT_TOOL_PENDING"


@tool
def search_places(query: str, category: str = "") -> str:
    """Search the local Osijek places catalog (167 curated venues). Use for restaurants, cafés, sights, parks.
    category is optional: gastro, kultura, priroda, etc."""
    return "CLIENT_TOOL_PENDING"


@tool
def get_nearby_places(radius_meters: int = 1500, limit: int = 5) -> str:
    """Find places near the user's current GPS location from the mobile app. Requires client location."""
    return "CLIENT_TOOL_PENDING"


@tool
def get_recommended_places(limit: int = 5) -> str:
    """Personalized place recommendations based on the user's interests and visit history in the app."""
    return "CLIENT_TOOL_PENDING"


@tool
def get_user_active_plan() -> str:
    """Return the user's active itinerary plan (title, steps, last visited step) from the mobile app."""
    return "CLIENT_TOOL_PENDING"


_CLIENT_TOOLS = [
    get_place_details,
    search_places,
    get_nearby_places,
    get_recommended_places,
    get_user_active_plan,
]

_CLIENT_TOOL_NAMES = {t.name for t in _CLIENT_TOOLS}

_SERVER_TOOL_NAMES = {t.name for t in get_server_langchain_tools()}


def get_tool_execution(name: str) -> ExecutionTarget | None:
    if name in _SERVER_TOOL_NAMES:
        return "server"
    if name in _CLIENT_TOOL_NAMES:
        return "client"
    return None


def get_all_agent_tools():
    """All tools exposed to the Phase 3 agent LLM (server + client)."""
    return get_server_langchain_tools() + _CLIENT_TOOLS


def get_tool_registry_metadata() -> list[dict]:
    """OpenAI-style metadata for docs / debugging."""
    items: list[dict] = []
    for t in get_server_langchain_tools():
        items.append({"name": t.name, "execution": "server", "description": (t.description or "")[:200]})
    for t in _CLIENT_TOOLS:
        items.append({"name": t.name, "execution": "client", "description": (t.description or "")[:200]})
    return items


def is_client_tool(name: str) -> bool:
    return name in _CLIENT_TOOL_NAMES


def is_server_tool(name: str) -> bool:
    return name in _SERVER_TOOL_NAMES