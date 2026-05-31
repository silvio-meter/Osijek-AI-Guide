# Restaurant Tool Design for Osijek AI Guide - Lega
**Option 1: Improved restaurant/food tool structure (modeled on events)**

Date: 2026
Status: Proposal for implementation

## 1. Current State (Problems)

The current `search_restaurants_or_food` in [src/tools.py](/Users/silviometer/Desktop/AI_PROJECTS/Osijek-AI-Guide/src/tools.py) is **pure Tavily**:

- Relies entirely on web search (even for well-known local classics).
- No persistent local knowledge of Osijek's strong gastro scene (Crna Svinja, Čingi Lingi Čarda, Corner, Projekt 9, Meandar, Pepe/Ventidue pizzas, etc.).
- Weak source attribution and structure in responses.
- No categorization (traditional Slavonian, fish/čarde, pizza, Drava view, Baranja day trip, modern fusion, casual...).
- Risk of hallucination or outdated info on "best" places.
- Inconsistent with the high-quality hybrid approach we built for events (`fetch_local_osijek_events` + Tavily fallback).

This is the exact situation we fixed for events earlier.

## 2. Goals (Same philosophy as events)

- **Primary**: High-quality, locally grounded data from the best Osijek sources.
- **Reliability**: Structured data + clear source attribution.
- **User experience**: Categorized, actionable answers ("dobra riba u Tvrđi", "tradicionalna slavonska večera", "pizza centar", "Baranja izlet").
- **Anti-hallucination**: Never invent restaurants. Always cite sources.
- **Hybrid**: Local curated/scraped first → Tavily for freshness/reviews/specific queries.
- **Maintainable**: 30-min caching, graceful degradation, debug mode.
- **Extensible**: Easy to add new sources (Gault&Millau updates, new chef lists).

## 3. Proposed Architecture

### 3.1 Data Model (Dict)

```python
{
    "name": str,
    "address": str,
    "phone": Optional[str],
    "url": str,
    "rating": Optional[float],           # from jelo.hr or curated
    "review_count": Optional[int],
    "price_level": Optional[str],        # "€", "€€", "€€€"
    "tags": List[str],                   # e.g. ["traditional", "fish", "čarda", "pizza", "drava_view", "fusion", "baranja", "grill", "vegan"]
    "specialties": List[str],            # key dishes mentioned in sources
    "distance_note": Optional[str],      # "10 min from center (Čepin)", "Bilje (15 min drive)"
    "source": str,                       # "jelo.hr", "curated:telegram-2024", "gaultmillau-2026", ...
    "last_updated": str,                 # ISO date or "curated-2026-05"
    "has_reliable_info": bool
}
```

### 3.2 Source Hierarchy (Priority)

1. **jelo.hr** (primary scraper target)
   - Best structured data on the market for Osijek (ratings + thousands of reviews, price levels, photos, profiles).
   - Top 10 for 2026 + full /restorani/osijek list.

2. **High-quality curated lists** (static or lightly parsed)
   - Gault&Millau Croatia Slavonija/Baranja/Srijem 2026 (highest authority)
   - Telegram Super1 top list
   - Putnikofer detailed recommendations
   - Chef Goran Kočiš / Jutarnji Dobra Hrana articles
   - Official TZ Osijek (when useful)

3. **Tavily fallback** (for freshness, specific reviews, "open now", new openings)

### 3.3 New Functions (in src/scrapers.py or dedicated restaurant_scrapers.py)

Recommended: Keep in `src/scrapers.py` for consistency (or split later if it grows).

Core public API:

```python
def fetch_jelo_osijek_restaurants(use_cache: bool = True, debug: bool = False) -> List[Dict]:
    """Scrape or parse jelo.hr/restorani/osijek + Top 10 guide."""

def fetch_gaultmillau_2026_highlights() -> List[Dict]:
    """Curated high-signal data from the May 2026 special edition."""

def fetch_curated_restaurant_recommendations() -> List[Dict]:
    """Merged high-quality curated sources (Telegram, Putnikofer, chef lists, G&M)."""

def fetch_local_osijek_restaurants(use_cache: bool = True) -> List[Dict]:
    """
    Main aggregator (analogous to fetch_local_osijek_events).
    Combines jelo.hr + curated + (future) other sources.
    Applies dedup, normalization, categorization, smart ranking.
    """
```

Helper functions (private):

- `_normalize_restaurant_name()`
- `_is_noise_restaurant()` (e.g. chains like McDonalds if we want to deprioritize, or generic entries)
- `_categorize_restaurant()` → returns list of tags
- `_enrich_from_detail_page()` (optional, limited calls like we did for events on 031)
- Caching helpers (already exist: `_get_cached`, `_set_cache`)

### 3.4 Integration in src/tools.py

Update `search_restaurants_or_food`:

```python
@tool
def search_restaurants_or_food(query: str = "restorani") -> str:
    """
    MANDATORY for any question about eating/drinking in Osijek.
    Strategy:
    1. First try local high-quality sources (jelo.hr + curated G&M/Telegram/etc.)
       - Grouped by useful categories for the user.
    2. Fall back to enhanced Tavily search for very fresh or specific info.
    """
    # Primary: local
    try:
        local = fetch_local_osijek_restaurants(use_cache=True)
        if local:
            # Smart filtering + formatting by category
            # Return nicely grouped output
            return format_restaurant_results(local, query)
    except Exception as e:
        print(f"[restaurant tool] Local error: {e}")

    # Fallback Tavily (existing _build_smart_food_query logic)
    ...
```

**Formatting strategy (critical for UX):**

Group results like this in responses:

**Tradicionalna slavonska kuhinja & čarde (must-try):**
- Crna Svinja (Čepin, 4.8/3496) — specijaliteti od crne svinje...
- Čingi Lingi Čarda (Bilje)...

**Riba i fiš paprikaš:**
- ...

**Pizza (neoapulitanska / dobra):**
- Pepe Pizza Place, Ventidue...

**Pogled na Dravu / moderna:**
- Projekt 9, Meandar (Hotel Osijek)...

**Baranja izlet (10-20 min):**
- Josić (4 toke Gault&Millau), Čingi Lingi...

**Ostalo / fusion / casual:**
- Lulu Fusion, Rustika, Lipov hlad...

Always include:
- Source attribution
- Key specialties + price hints when available
- Phone / address / booking note when known
- "Rezerviraj unaprijed vikendom" type practical advice

### 3.5 Smart Query Routing (inside the tool or before calling)

Detect intent similar to events:
- "riba", "fiš", "smuđ", "šaran" → boost fish/čarde category
- "pizza" → pizza category + jelo.hr pizza filter
- "Tvrđa", "centar", "obala" → location boosters
- "Baranja", "Čepin", "Bilje", "izlet" → day-trip / čarde
- "tradicionalna", "slavonska", "čobanac", "kulen" → traditional
- "jeftino", "dobra vrijednost" → price-aware ranking

## 4. Implementation Phases (recommended)

**Phase 1 (quick win, low risk)**
- Add curated static seed data (top 12-15 consensus restaurants from our research + G&M).
- Improve `search_restaurants_or_food` formatting + categorization using the seed.
- Update prompt/tool description.

**Phase 2**
- Implement `fetch_jelo_osijek_restaurants()` (BeautifulSoup on the listing + Top 10 page).
- Basic dedup + merging with curated.
- Wire into the tool as primary source.

**Phase 3**
- Add Gault&Millau highlights parser (from the 24sata article or future updates).
- Advanced categorization and ranking.
- Optional limited detail enrichment (like events title resolution).

**Phase 4**
- Optional: individual restaurant site scrapers for menus (only for top 5-6).
- Better freshness signals.

## 5. Top Consensus Restaurants (seed data for Phase 1)

From jelo.hr, Gault&Millau 2026, Telegram, Putnikofer, chef recommendations:

1. **Crna Svinja** (Terra Negra, Čepin) — undisputed #1 across almost all sources. Black Slavonian pig specialties.
2. **Čingi Lingi Čarda** (Bilje) — classic Baranja čarda, excellent fish.
3. **Corner** (Velebitska) — reliable grill, big portions, good value.
4. **Projekt 9** — boat on Drava, nice setting.
5. **Meandar / Zimska Luka** (Hotel Osijek) — 3 G&M toques, river view, modern Slavonian.
6. **Rustika** — central, long-time favorite, grill + pizza.
7. **Pepe Pizza Place** — highly rated Neapolitan-style.
8. **Ventidue Pizza & Bar**
9. **Lulu Fusion Bistro** — chef favorite for creative/Asian fusion.
10. **Čarda kod Baranjca**
11. **Lipov hlad**
12. **Didin Konak** (Kopačevo area)
13. **Batak Osijek**
14. **Karaka**
15. **Waldinger** (fine dining mentions)

Add G&M standouts: Josić (Zmajevac) for serious Baranja trips.

## 6. Risks & Mitigations

- jelo.hr HTML changes → defensive parsing + fallback to curated.
- Rate limiting / anti-bot → respectful headers, caching (already have 30min pattern), never aggressive.
- Over-reliance on one source → always keep curated + Tavily as safety net.
- Data staleness → last_updated field + explicit "as of 2026" notes in responses.

## 7. Next Steps (after approval)

1. User approves this design.
2. Implement Phase 1 (curated seed + improved formatting) in one focused session.
3. Then Phase 2 (real jelo.hr scraper) using the same iterative feedback style we used for events (test → fix parser → improve report → A/B/C/D style refinements).

This approach proved extremely effective for events and will deliver the same jump in quality for restaurants.

---

**Ready when you are.** Say "kreni" (or "2" / "3" if you changed your mind) and I'll start executing the chosen phase.