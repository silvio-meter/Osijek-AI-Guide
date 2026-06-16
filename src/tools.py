"""
Tools for Osijek AI Guide - Lega
Real tool calling for live/dynamic information (weather, events, restaurants).
"""

from langchain_core.tools import tool
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re
import json
from typing import List, Dict, Optional, Any
from datetime import datetime as dt
from pathlib import Path
from functools import lru_cache

# Tavily is optional - only imported if the package is installed
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TavilyClient = None
    TAVILY_AVAILABLE = False
    print("[tools] Warning: tavily-python not installed. Tavily fallback will be disabled.")

# Local scrapers
from scrapers import fetch_local_osijek_events, fetch_local_osijek_restaurants, _format_restaurant_results

# Database for curated events (hybrid model)
from database import SessionLocal
from models.event import Event

load_dotenv()

# Tavily client (optional)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client = None
if TAVILY_AVAILABLE and TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    except Exception as e:
        print(f"[tools] Failed to initialize Tavily client: {e}")


@lru_cache(maxsize=1)
def _get_place_web_map() -> dict:
    """Load places from the mobile map data (source of truth for rich places + web URLs).
    Returns lowercased name -> web URL for all places that have a website.
    This allows the AI to target specific venue websites for current programs, menus, opening hours etc.
    Falls back gracefully if the file is not present (e.g. Railway backend deploy without mobile assets sibling).
    """
    FALLBACK_WEB = {
        "djecje_kazaliste_branka_mihaljevica": "https://www.djecje-kazaliste.hr/tjedni-raspored/",
        "dječje kazalište branka mihaljevića": "https://www.djecje-kazaliste.hr/tjedni-raspored/",
        "kino_urania": "https://kinematografi-osijek.hr/",
        "kino urania": "https://kinematografi-osijek.hr/",
        "kino_europa": "https://kinematografi-osijek.hr/tjedni-pregled/",
        "kino europa": "https://kinematografi-osijek.hr/tjedni-pregled/",
        "cinestar_osijek": "https://cinestarcinemas.hr/osijek-portanova-centar",
        "cinestar": "https://cinestarcinemas.hr/osijek-portanova-centar",
    }
    try:
        # Try sibling path (local dev)
        base = Path(__file__).resolve().parents[1]
        places_path = base.parent / "lega_mobile" / "assets" / "osijek_places.json"
        if not places_path.exists():
            # Try common Railway /app paths or current dir
            alt_paths = [
                Path("/app/lega_mobile/assets/osijek_places.json"),
                Path.cwd() / "lega_mobile" / "assets" / "osijek_places.json",
                Path("/lega_mobile/assets/osijek_places.json"),
            ]
            for ap in alt_paths:
                if ap.exists():
                    places_path = ap
                    break
        if not places_path.exists():
            print("[tools] osijek_places.json not found at expected paths, using fallback web map for critical venues")
            return FALLBACK_WEB

        with open(places_path, encoding="utf-8") as f:
            places = json.load(f)

        web_map = FALLBACK_WEB.copy()  # start with fallback
        for p in places:
            web = p.get("web")
            if web and str(web).strip():
                web = str(web).strip()
                name = p.get("name", "").lower().strip()
                if name:
                    web_map[name] = web
                    for word in name.split():
                        if len(word) > 3:
                            web_map[word] = web
                pid = p.get("id", "").lower()
                if pid:
                    web_map[pid] = web
                    for word in pid.split("_"):
                        if len(word) > 3:
                            web_map[word] = web
                for tag in p.get("tags", []) or []:
                    if tag and len(tag) > 3:
                        web_map[tag.lower()] = web
        return web_map
    except Exception as e:
        print(f"[tools] Could not load osijek_places.json for web map: {e} - using fallback")
        return FALLBACK_WEB


def _get_site_restriction(query: str) -> str:
    """If the query mentions a known place with a website, return a 'site:domain' restriction for Tavily."""
    web_map = _get_place_web_map()
    q_lower = query.lower()
    for key, web in web_map.items():
        if key in q_lower:
            try:
                from urllib.parse import urlparse
                domain = urlparse(web).netloc
                if domain:
                    return f" site:{domain}"
            except:
                pass
    return ""


# ============================================================
# TOOL 1: Weather (Open-Meteo - free, no key required)
# ============================================================

@tool
def get_current_weather_osijek() -> str:
    """
    MANDATORY tool for any weather-related question about Osijek.
    Use this for questions containing: weather, temperature, rain, forecast, jacket, warm, cold, outside, tonight, today, tomorrow.
    Always returns up-to-date current conditions + 3-day forecast for Osijek.
    """
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=45.5511&longitude=18.6939"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,weather_code"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&timezone=Europe/Zagreb"
            "&forecast_days=3"
        )
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data.get("current", {})
        daily = data.get("daily", {})
        
        # Simple weather code mapping (WMO)
        weather_codes = {
            0: "vedro / sunčano",
            1: "pretežno vedro",
            2: "djelomično oblačno",
            3: "oblačno",
            45: "magla",
            48: "magla s inijem",
            51: "slaba kiša",
            53: "kiša",
            55: "jaka kiša",
            61: "slaba kiša",
            63: "kiša",
            65: "jaka kiša",
            71: "slabi snijeg",
            73: "snijeg",
            80: "slaba pljuskova",
            81: "pljuskovi",
            82: "jaki pljuskovi",
            95: "oluja",
        }
        
        current_code = current.get("weather_code", 0)
        current_desc = weather_codes.get(current_code, "nepoznato")
        
        temp = current.get("temperature_2m", "?")
        humidity = current.get("relative_humidity_2m", "?")
        wind = current.get("wind_speed_10m", "?")
        
        # Daily forecast
        dates = daily.get("time", [])[:3]
        max_t = daily.get("temperature_2m_max", [])[:3]
        min_t = daily.get("temperature_2m_min", [])[:3]
        precip = daily.get("precipitation_probability_max", [])[:3]
        
        forecast_lines = []
        for i in range(min(3, len(dates))):
            code = daily.get("weather_code", [0]*3)[i]
            desc = weather_codes.get(code, "promjenjivo")
            forecast_lines.append(
                f"{dates[i]}: {min_t[i]:.0f}–{max_t[i]:.0f}°C, {desc}, kiša {precip[i]}%"
            )
        
        forecast_text = "\n".join(forecast_lines)
        
        result = (
            f"Trenutno u Osijeku: {temp}°C, {current_desc}, "
            f"vlažnost {humidity}%, vjetar {wind} km/h.\n\n"
            f"Prognoza za sljedeća 3 dana:\n{forecast_text}"
        )
        return result
        
    except Exception as e:
        return f"Ne mogu dohvatiti vrijeme trenutno (greška: {str(e)}). Pokušaj kasnije."


# ============================================================
# TOOL 2: Events in Osijek (Tavily) - Improved
# ============================================================

def _build_smart_event_query(original_query: str) -> str:
    """Creates a much smarter, time-aware query for Tavily."""
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    
    # Croatian month names for better local results
    months_hr = {
        1: "siječanj", 2: "veljača", 3: "ožujak", 4: "travanj",
        5: "svibanj", 6: "lipanj", 7: "srpanj", 8: "kolovoz",
        9: "rujan", 10: "listopad", 11: "studeni", 12: "prosinac"
    }
    month_name = months_hr.get(current_month, "lipanj")

    # Detect intent for time sensitivity
    q_lower = original_query.lower()
    
    time_boosters = []
    
    if any(w in q_lower for w in ["večeras", "danas", "današnji", "tonight"]):
        time_boosters = ["večeras", "danas", "u Osijeku večeras"]
    elif any(w in q_lower for w in ["ovaj tjedan", "ovaj vikend", "sljedećih 7 dana", "this week"]):
        time_boosters = ["ovaj tjedan", "u narednih 7 dana", "ovaj vikend"]
    elif any(w in q_lower for w in ["sutra", "preksutra"]):
        time_boosters = ["sutra", "u naredna 2-3 dana"]
    else:
        # Default: focus on near future
        time_boosters = ["u narednih 14 dana", "lipanj 2026", "srpanj 2026"]

    # Build strong query
    base = f"{original_query} Osijek"
    
    # Add time context strongly
    time_part = " ".join(time_boosters)
    
    # Final enhanced query
    enhanced = f"{base} {time_part} koncert žurka festival utakmica izložba događaj 2026 raspored predstave kazalište kino"
    
    return enhanced


def fetch_curated_events(days_ahead: int = 14) -> List[Dict]:
    """
    Fetch manually curated (high-quality) events from the database.
    These take priority over scraped events.
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        future = now + timedelta(days=days_ahead)

        query = db.query(Event).filter(
            Event.is_active == True,
            Event.is_curated == True,
        )

        # Filter events that are in the future or ongoing
        query = query.filter(
            (Event.start_date >= now) | (Event.end_date >= now) | (Event.start_date.is_(None))
        )

        events = query.order_by(Event.start_date.asc().nulls_last()).limit(30).all()

        result = []
        for ev in events:
            result.append({
                "title": ev.title,
                "description": ev.description or ev.short_description,
                "start_date": ev.start_date.isoformat() if ev.start_date else None,
                "end_date": ev.end_date.isoformat() if ev.end_date else None,
                "date_text": ev.date_text,
                "location": ev.location,
                "url": ev.url,
                "source": "curated",
                "category": ev.category,
                "tags": ev.tags or [],
                "has_reliable_date": ev.has_reliable_date,
            })
        return result
    finally:
        db.close()


def _normalize_event_date_key(e: Dict) -> Any:
    """Return a sortable key for an event (prefer reliable dates, then parse ISO if possible)."""
    has_reliable = bool(e.get("has_reliable_date"))
    raw = e.get("start_date") or e.get("date") or e.get("date_text") or "9999-12-31"

    sort_date = "9999-12-31T23:59:59"  # safe fallback string

    if isinstance(raw, dt):
        sort_date = raw.isoformat()
    elif isinstance(raw, str) and raw != "9999-12-31":
        try:
            if "T" in raw:
                p = dt.fromisoformat(raw.replace("Z", "+00:00"))
            else:
                p = dt.fromisoformat(raw + "T00:00:00")
            sort_date = p.isoformat()
        except Exception:
            sort_date = raw  # keep original string as last resort (still comparable within strings)

    return (0 if has_reliable else 1, sort_date)


def _merge_events(curated: List[Dict], scraped: List[Dict], max_total: int = 20) -> List[Dict]:
    """
    Merge curated and scraped events.
    Curated events have absolute priority. Deduplication by normalized title.
    Sorted so events with reliable dates come first.
    """
    merged = []
    seen_titles = set()

    # Curated first (highest trust)
    for ev in curated:
        title_key = (ev.get("title") or "").lower().strip()[:80]
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            merged.append(ev)

    # Then scraped (only if not duplicate)
    for ev in scraped:
        title_key = (ev.get("title") or "").lower().strip()[:80]
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            merged.append(ev)

    # Stable sort: reliable dates first, then chronological
    merged.sort(key=_normalize_event_date_key)
    return merged[:max_total]


def get_hybrid_upcoming_events(
    days_ahead: int = 14,
    category: Optional[str] = None,
    limit: int = 30
) -> List[Dict]:
    """
    Direct (non-LLM) hybrid events fetch for public API and mobile use.
    Returns merged list: curated (priority) + scraped, no Tavily fallback.
    This is the recommended function for direct structured event lists.
    """
    try:
        curated = fetch_curated_events(days_ahead=days_ahead)
    except Exception as e:
        print(f"[hybrid events] curated fetch error: {e}")
        curated = []

    try:
        scraped = fetch_local_osijek_events(days_ahead=days_ahead, use_cache=True)
    except Exception as e:
        print(f"[hybrid events] scraper error: {e}")
        scraped = []

    merged = _merge_events(curated, scraped, max_total=limit * 2)

    if category:
        cl = category.lower().strip()
        merged = [
            e for e in merged
            if cl in (e.get("category") or "").lower()
            or cl in [t.lower() for t in (e.get("tags") or [])]
            or cl in (e.get("title") or "").lower()
        ]

    return merged[:limit]


@tool
def search_osijek_events(query: str = "događaji", structured: bool = False) -> str:
    """
    MANDATORY tool for ANY question about current or upcoming events, raspored, predstave, kazalište, kino, tjedni program in Osijek.
    Especially for Dječje kazalište Branka Mihaljevića, Kino Urania, Kino Europa, CineStar, etc.

    ALWAYS call this for queries containing raspored, predstave, kazalište, dječje, kino, program, što se događa, etc.

    Hybrid strategy (Opcija B):
    1. First tries curated (manually maintained) events from the database.
    2. Then adds scraped events from local sources (osijek031 + sib + osijeknews + djecje kazalište).
    3. Merges them intelligently (curated events have priority).
    4. If schedule query or specific venue with web, ALWAYS supplements with Tavily site-restricted search for fresh data from the venue's own page.

    This gives the best quality + coverage. Never answer "nemam podataka" for these without calling this tool first.
    """
    # Fast path for venue-specific schedule queries (Dječje kazalište, kina etc.): return URL immediately.
    # Avoids slow scraper timeouts (osijeknews, djecje verification) that cause chat/stream timeouts in the app.
    q_lower = query.lower()
    is_venue_schedule_query = any(venue in q_lower for venue in ["dječje kazalište", "djecje kazalište", "kazalištu", "urania", "europa", "cinestar", "kino"]) and any(word in q_lower for word in ["raspored", "predstave", "filmovi", "program", "kino", "kazalište"])
    if is_venue_schedule_query:
        web_map = _get_place_web_map()
        matched_url = None
        matched_name = None
        for key, web in web_map.items():
            if key in q_lower and web:
                matched_url = web
                matched_name = key
                break
        if not matched_url:
            if "dječje kazalište" in q_lower or "djecje kazalište" in q_lower or "kazalištu" in q_lower:
                matched_url = "https://www.djecje-kazaliste.hr/tjedni-raspored/"
                matched_name = "Dječje kazalište Branka Mihaljevića"
            elif "urania" in q_lower:
                matched_url = "https://kinematografi-osijek.hr/"
                matched_name = "Kino Urania"
            elif "europa" in q_lower:
                matched_url = "https://kinematografi-osijek.hr/tjedni-pregled/"
                matched_name = "Kino Europa"
            elif "cinestar" in q_lower:
                matched_url = "https://cinestarcinemas.hr/osijek-portanova-centar"
                matched_name = "CineStar Osijek"
        if matched_url:
            return f"Trenutno nemam detaljan raspored za iduća 3 dana iz mojih izvora za {matched_name or 'ovo mjesto'}, ali službena stranica za program/raspored je {matched_url}. Preporučujem da provjeriš tamo (često ima tjedni ili mjesečni raspored). Ako želiš plan za nešto drugo (npr. uz Dravu ili Baranju), reci!"

    # Use the shared hybrid logic (curated + scraped, no Tavily here)
    merged = []
    curated_count = 0
    scraped_count = 0
    try:
        # We call the two sources again only for source_note classification (cheap with cache)
        curated_raw = fetch_curated_events(days_ahead=14)
        scraped_raw = fetch_local_osijek_events(days_ahead=14, use_cache=True)
        curated_count = len(curated_raw)
        scraped_count = len(scraped_raw)
        merged = get_hybrid_upcoming_events(days_ahead=14, limit=20)
        print(f"[events tool] Hybrid returned {len(merged)} events ({curated_count} curated + {scraped_count} scraped)")
    except Exception as e:
        print(f"[events tool] Hybrid fetch error: {e}")

    if merged:
        site_restriction = _get_site_restriction(query)
        q_lower = query.lower()
        is_schedule_query = any(kw in q_lower for kw in ["raspored", "predstave", "program", "kazalište", "kino", "dječje", "djecje", "predstava", "show", "performance", "tjedni"])
        # If the query targets a specific place that has a web page (from map data),
        # OR it's a schedule/program query for theater/cinema/venue (e.g. dječje kazalište),
        # always supplement with site-restricted Tavily for current program/schedule.
        # This ensures we get fresh data even if local scrapers hit anti-bot protection.
        if site_restriction or is_schedule_query or not merged:
            # fall through to (site-aware) Tavily
            pass
        else:
            if structured:
                return json.dumps(merged, ensure_ascii=False)

            # Text formatting
            reliable = []
            uncertain = []

            for ev in merged:
                title = ev.get("title", "Događaj")
                url = ev.get("url", "")
                date_str = ev.get("start_date") or ev.get("date") or ev.get("date_text")
                source = ev.get("source", "unknown")

                if date_str:
                    line = f"• **{title}** ({date_str})\n  Izvor: {source} → {url}"
                    reliable.append(line)
                else:
                    line = f"• **{title}**\n  Izvor: {source} → {url}"
                    uncertain.append(line)

            formatted = []
            if reliable:
                formatted.append("**S jasnim datumom:**\n" + "\n\n".join(reliable))
            if uncertain:
                formatted.append("**U narednim danima (točan datum nije pouzdano određen):**\n" + "\n\n".join(uncertain))

            if formatted:
                source_note = "kurirani + scraperi"
                if curated_count > 0 and scraped_count == 0:
                    source_note = "kurirani događaji"
                elif scraped_count > 0 and curated_count == 0:
                    source_note = "lokalni scraperi"

                return f"Pronađeni događaji ({source_note}):\n\n" + "\n\n".join(formatted)

    # === Special case for venue-specific schedule queries (Dječje kazalište, Kino Urania, Europa, CineStar etc.) ===
    # Always provide the official web link from osijek_places.json (the source of truth for venue websites).
    # This solves the "ne radi" / "nemam podataka" issue when direct scraping is blocked by site protection
    # or when no exact matches for "next 3 days" are in search results.
    q_lower = query.lower()
    is_venue_schedule_query = any(venue in q_lower for venue in ["dječje kazalište", "djecje kazalište", "kazalištu", "urania", "europa", "cinestar", "kino"]) and any(word in q_lower for word in ["raspored", "predstave", "filmovi", "program", "kino", "kazalište"])
    if is_venue_schedule_query:
        web_map = _get_place_web_map()
        matched_url = None
        matched_name = None
        for key, web in web_map.items():
            if key in q_lower and web:
                matched_url = web
                matched_name = key
                break
        # Hardcoded fallbacks for critical venues (web_map load often fails in Railway because lega_mobile/assets not present in backend container)
        if not matched_url:
            if "dječje kazalište" in q_lower or "djecje kazalište" in q_lower or "kazalištu" in q_lower:
                matched_url = "https://www.djecje-kazaliste.hr/tjedni-raspored/"
                matched_name = "Dječje kazalište Branka Mihaljevića"
            elif "urania" in q_lower:
                matched_url = "https://kinematografi-osijek.hr/"
                matched_name = "Kino Urania"
            elif "europa" in q_lower:
                matched_url = "https://kinematografi-osijek.hr/tjedni-pregled/"
                matched_name = "Kino Europa"
            elif "cinestar" in q_lower:
                matched_url = "https://cinestarcinemas.hr/osijek-portanova-centar"
                matched_name = "CineStar Osijek"
        if matched_url:
            return f"Trenutno nemam detaljan raspored za iduća 3 dana iz mojih izvora za {matched_name or 'ovo mjesto'}, ali službena stranica za program/raspored je {matched_url}. Preporučujem da provjeriš tamo (često ima tjedni ili mjesečni raspored). Ako želiš plan za nešto drugo (npr. uz Dravu ili Baranju), reci!"

    # === 4. Fallback / Supplement: Tavily (with site restriction for places that have web) ===
    if not tavily_client:
        return "Trenutno nemam dovoljno svježih podataka o događajima u Osijeku."

    try:
        enhanced_query = _build_smart_event_query(query)
        site_restriction = _get_site_restriction(query)
        if site_restriction:
            enhanced_query = enhanced_query + site_restriction
        response = tavily_client.search(
            query=enhanced_query,
            max_results=8,
            search_depth="advanced"
        )
        results = response.get("results", [])

        if not results:
            return "Trenutno nema relevantnih rezultata za događaje u Osijeku."

        formatted = []
        for r in results[:6]:
            title = r.get("title", "Događaj")
            content = r.get("content", "")[:300]
            url = r.get("url", "")
            formatted.append(f"• **{title}**\n  {content}\n  Izvor: {url}")

        return "Pronađeni događaji (web pretraga - fallback):\n\n" + "\n\n".join(formatted)

    except Exception as e:
        return f"Greška pri pretrazi događaja: {str(e)}"


# ============================================================
# TOOL 3: Restaurants, bars, food (Tavily) - Improved
# ============================================================

def _build_smart_food_query(original_query: str) -> str:
    """Creates smarter queries for food/restaurants in Osijek."""
    q_lower = original_query.lower()
    
    boosters = ["Osijek"]
    
    # Location boosters
    if "tvrđa" in q_lower or "tvrdja" in q_lower:
        boosters.append("Tvrđa")
    if "centar" in q_lower:
        boosters.append("centar")
    if "obala" in q_lower or "drava" in q_lower:
        boosters.append("obala Drave")
    
    # Food type boosters
    if any(w in q_lower for w in ["riba", "riblja", "šaran", "smuđ"]):
        boosters.append("riba slavonska")
    if any(w in q_lower for w in ["pizza", "pizzeria"]):
        boosters.append("pizza")
    if any(w in q_lower for w in ["tradicionalna", "slavonska", "čobanac", "kulen"]):
        boosters.append("tradicionalna slavonska hrana")
    
    # General
    boosters.append("restoran bar preporuka 2026")
    
    return f"{original_query} {' '.join(boosters)}"


@tool
def search_restaurants_or_food(query: str = "restorani", structured: bool = False) -> str:
    """
    MANDATORY and PRIMARY tool for ANY question about restaurants, where to eat, fish, pizza, 
    "dobra riba", "gdje večerati", traditional food, etc. in Osijek.

    When `structured=True` (for mobile apps), returns clean JSON-like data instead of text.
    Use this for map integration and cards in the mobile app.

    ALWAYS call this tool first for food-related questions.
    """
    # === Primary: High-quality local curated data ===
    try:
        local_restaurants = fetch_local_osijek_restaurants(use_cache=True, structured=structured)
        if local_restaurants:
            if structured:
                # Return compact structured version for mobile (with geo data when available)
                clean = []
                for r in local_restaurants[:15]:
                    item = {
                        "name": r.get("name"),
                        "address": r.get("address"),
                        "phone": r.get("phone"),
                        "rating": r.get("rating"),
                        "tags": r.get("tags", []),
                        "specialties": r.get("specialties", []),
                        "distance_note": r.get("distance_note"),
                        "source": r.get("source")
                    }
                    if r.get("lat") and r.get("lng"):
                        item["lat"] = r["lat"]
                        item["lng"] = r["lng"]
                    clean.append(item)
                return json.dumps(clean, ensure_ascii=False)

            formatted = _format_restaurant_results(local_restaurants, query)
            return formatted
    except Exception as e:
        print(f"[restaurant tool] Local curated error: {e}")

    # === Fallback: Tavily (existing smart logic) ===
    if not tavily_client:
        return "Trenutno nemam dovoljno svježih podataka o restoranima (nema Tavily ključa)."

    try:
        enhanced_query = _build_smart_food_query(query)
        site_restriction = _get_site_restriction(query)
        if site_restriction:
            enhanced_query = enhanced_query + site_restriction

        response = tavily_client.search(
            query=enhanced_query,
            max_results=7,
            search_depth="advanced"
        )

        results = response.get("results", [])

        if not results:
            return "Nema rezultata za pretragu hrane i restorana."

        formatted = []
        for r in results[:6]:
            title = r.get("title", "Mjesto")
            content = r.get("content", "")[:320]
            url = r.get("url", "")
            formatted.append(f"• **{title}**\n  {content}\n  Izvor: {url}")

        return "Pronađeni restorani i barovi (web pretraga):\n\n" + "\n\n".join(formatted)

    except Exception as e:
        return f"Greška pri pretrazi restorana: {str(e)}"


# ============================================================
# Helper: Get all tools
# ============================================================

def get_all_tools():
    """Returns all tools available to Lega for live information."""
    from chat_data_tools import get_events_today, get_wine_recommendations

    return [
        get_current_weather_osijek,
        search_osijek_events,
        get_events_today,
        get_wine_recommendations,
        search_restaurants_or_food,
    ]