"""
Curated chat tools backed by local JSON (get_events_today, get_wine_recommendations).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from langchain_core.tools import tool

_DATA_DIR = Path(__file__).resolve().parent / "data"


def _load_events_catalog() -> list[dict]:
    path = _DATA_DIR / "osijek_events_today.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("events", [])


def _load_wine_catalog() -> list[dict]:
    path = _DATA_DIR / "baranja_wine.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("recommendations", [])


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def filter_events_today(
    events: list[dict],
    *,
    anchor: date | None = None,
    date_str: str = "",
    category: str = "",
    days_ahead: int = 3,
) -> list[dict]:
    today = anchor or date.today()
    if date_str:
        target = _parse_date(date_str)
        if target:
            return [
                e for e in events
                if _parse_date(e.get("date")) == target
                and (not category or (e.get("category") or "").lower() == category.lower())
            ]

    end = today + timedelta(days=days_ahead)
    out = []
    for e in events:
        ev_date = _parse_date(e.get("date"))
        if ev_date is None or ev_date < today or ev_date > end:
            continue
        if category and (e.get("category") or "").lower() != category.lower():
            continue
        out.append(e)
    out.sort(key=lambda x: x.get("date", ""))
    return out


def filter_wine_recommendations(
    wines: list[dict],
    *,
    wine_type: str = "",
    price_range: str = "",
    food_pairing: str = "",
) -> list[dict]:
    wt = wine_type.lower().strip()
    pr = price_range.lower().strip()
    fp = food_pairing.lower().strip()

    out = []
    for w in wines:
        if wt and (w.get("type") or "").lower() != wt:
            continue
        if pr and (w.get("price_range") or "").lower() != pr:
            continue
        if fp:
            pairings = [p.lower() for p in (w.get("food_pairing") or [])]
            if fp not in pairings and not any(fp in p for p in pairings):
                continue
        out.append(w)
    return out


@tool
def get_events_today(date: str = "", category: str = "") -> str:
    """
    Fetch events in Osijek for a specific date or the next few days.
    Use for: što se događa danas, događaji ovaj tjedan, koncerti, izložbe, sport, festivali.

    Args:
        date: Optional YYYY-MM-DD. If omitted, returns today + next 3 days.
        category: Optional filter — concert, exhibition, sport, festival, other.
    """
    try:
        events = filter_events_today(
            _load_events_catalog(),
            date_str=date,
            category=category,
        )
        payload = {"events": events, "count": len(events)}
        if not events:
            payload["note"] = (
                "Nema događaja u kuriranom katalogu za traženi period. "
                "Možeš probati search_osijek_events za širu pretragu."
            )
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"events": [], "error": str(e)}, ensure_ascii=False)


@tool
def get_wine_recommendations(
    wine_type: str = "",
    price_range: str = "",
    food_pairing: str = "",
) -> str:
    """
    Recommend wines and wineries from Baranja (Slavonia wine region).
    Use for: vino, vinarija, Baranja, crveno/bijelo vino, uz meso/ribu.

    Args:
        wine_type: Optional — crveno, bijelo, rose, slatko.
        price_range: Optional — low, medium, high.
        food_pairing: Optional — meso, riba, sir, desert.
    """
    try:
        recs = filter_wine_recommendations(
            _load_wine_catalog(),
            wine_type=wine_type,
            price_range=price_range,
            food_pairing=food_pairing,
        )
        payload = {"recommendations": recs, "count": len(recs)}
        if not recs:
            payload["note"] = (
                "Nema točnog poklapanja u katalogu — vrati najbliže alternative iz Baranje."
            )
            payload["recommendations"] = _load_wine_catalog()[:4]
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"recommendations": [], "error": str(e)}, ensure_ascii=False)