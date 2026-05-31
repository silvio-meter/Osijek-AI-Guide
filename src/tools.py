"""
LangChain tools for Osijek AI Guide (Lega).

Provides tool definitions for restaurant search, event search, and hybrid
event retrieval. These tools are bound to the LLM via `.bind_tools()` and
can also be invoked directly in API endpoints.

Stub implementations return empty/placeholder data. Replace with real
scraping / DB logic as the project matures.
"""

import json
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input schemas (used by StructuredTool for proper bind_tools() support)
# ---------------------------------------------------------------------------

class RestaurantSearchInput(BaseModel):
    query: str = Field(default="restorani", description="Search query for restaurants or food")
    structured: bool = Field(default=True, description="Return structured JSON list if True")


class EventSearchInput(BaseModel):
    query: str = Field(default="događaji", description="Search query for events in Osijek")
    structured: bool = Field(default=True, description="Return structured JSON list if True")


class HybridEventsInput(BaseModel):
    query: str = Field(default="", description="Optional natural-language filter query")
    days_ahead: int = Field(default=14, description="How many days ahead to look for events")
    category: Optional[str] = Field(default=None, description="Filter by event category or tag")
    limit: int = Field(default=30, description="Maximum number of events to return")


# ---------------------------------------------------------------------------
# Core implementation functions (plain callables — easy to unit-test and
# call directly from API endpoints without going through the Tool wrapper)
# ---------------------------------------------------------------------------

def _search_restaurants_or_food_fn(query: str = "restorani", structured: bool = True) -> str:
    """
    Search for restaurants and food recommendations in Osijek.

    Stub implementation — returns an empty list.
    Replace with real scraping / vector-store retrieval logic.
    """
    results: List[Dict[str, Any]] = []
    if structured:
        return json.dumps(results, ensure_ascii=False)
    return "Trenutno nema dostupnih podataka o restoranima. Pokušaj kasnije."


def _search_osijek_events_fn(query: str = "događaji", structured: bool = True) -> str:
    """
    Search for upcoming events in Osijek.

    Stub implementation — returns an empty list.
    Replace with real scraping / DB retrieval logic.
    """
    results: List[Dict[str, Any]] = []
    if structured:
        return json.dumps(results, ensure_ascii=False)
    return "Trenutno nema dostupnih podataka o događajima. Pokušaj kasnije."


def get_hybrid_upcoming_events(
    days_ahead: int = 14,
    category: Optional[str] = None,
    limit: int = 30,
    query: str = "",
) -> List[Dict[str, Any]]:
    """
    Return upcoming events in Osijek using the hybrid curated + scraped model.

    This function is called directly from the /events endpoint as well as
    being wrapped as a LangChain tool in get_all_tools().

    Stub implementation — returns an empty list.
    Replace with real curated-DB + scraper logic.
    """
    return []


def _hybrid_events_tool_fn(
    query: str = "",
    days_ahead: int = 14,
    category: Optional[str] = None,
    limit: int = 30,
) -> str:
    """Tool-facing wrapper for get_hybrid_upcoming_events that returns JSON."""
    events = get_hybrid_upcoming_events(
        days_ahead=days_ahead,
        category=category,
        limit=limit,
        query=query,
    )
    return json.dumps(events, ensure_ascii=False)


# ---------------------------------------------------------------------------
# LangChain Tool objects
# ---------------------------------------------------------------------------

search_restaurants_or_food = StructuredTool.from_function(
    func=_search_restaurants_or_food_fn,
    name="search_restaurants_or_food",
    description=(
        "Search for restaurants and food recommendations in Osijek, Croatia. "
        "Use this tool when the user asks about where to eat, food options, "
        "restaurant recommendations, or cuisine types. "
        "Set structured=True to get a JSON list suitable for mobile cards/maps."
    ),
    args_schema=RestaurantSearchInput,
)

search_osijek_events = StructuredTool.from_function(
    func=_search_osijek_events_fn,
    name="search_osijek_events",
    description=(
        "Search for upcoming events in Osijek, Croatia. "
        "Use this tool when the user asks about concerts, festivals, exhibitions, "
        "sports events, or anything happening in the city. "
        "Set structured=True to get a JSON list suitable for mobile cards/maps."
    ),
    args_schema=EventSearchInput,
)

_hybrid_events_tool = StructuredTool.from_function(
    func=_hybrid_events_tool_fn,
    name="get_hybrid_upcoming_events",
    description=(
        "Retrieve upcoming events in Osijek using the hybrid curated + scraped model. "
        "Returns the highest-quality event data combining manually curated entries "
        "with scraped data from local portals. "
        "Supports filtering by category and a configurable look-ahead window."
    ),
    args_schema=HybridEventsInput,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_tools():
    """Return the full list of LangChain Tool objects available to the LLM."""
    return [
        search_restaurants_or_food,
        search_osijek_events,
        _hybrid_events_tool,
    ]
