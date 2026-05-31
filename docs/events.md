# Events – Hybrid Model (Tjedan 4 + polish)

## Philosophy

Pure scraping of event data is unreliable for a production mobile app.  
Lega uses a **hybrid curated-first** strategy:

1. **Curated events** (manually maintained, highest priority and quality) live in the database with `is_curated=true`.
2. **Scraped events** from local sources (osijek031.com, sib.net.hr, osijeknews.hr) as secondary source.
3. **Tavily web fallback** only when the combined curated+scraped result is empty/weak.

This matches the successful pattern used for restaurants.

## Model (Event)

Key fields:
- `title`, `description`, `short_description`
- `start_date`, `end_date`, `date_text` (human readable)
- `location`, `address`, `lat`, `lng`
- `category` (Festival, Koncert, Izložba, Sport, Kazalište, Gastro, Kultura...)
- `tags` (JSON array, e.g. ["tvrda", "besplatno", "obitelj"])
- `url`, `source` ("curated", "osijek031.com", "sib.net.hr", "osijeknews.hr", "tavily")
- `has_reliable_date`, `is_curated`, `is_active` (soft delete)
- `source_id` for future deduplication

## Public API (for Mobile App)

**Recommended endpoint:**

```
GET /events?structured=true&days_ahead=14&category=festival&limit=20
```

Response (structured):

```json
{
  "events": [ ... ],
  "count": 12,
  "days_ahead": 14,
  "category": "festival",
  "source": "hybrid_curated_scraped"
}
```

Parameters:
- `structured` (bool, default true) – clean JSON for lists/maps
- `category` – filter by category or tag
- `days_ahead`
- `limit`
- `query` – free text search in title/desc (when structured)

When `structured=false` or for natural-language questions, it falls back to the full LLM tool (which can still do Tavily if needed).

## Admin / Management API (Protected)

All routes require valid JWT.

- `GET    /admin/events` – list with filters + `include_inactive`
- `GET    /admin/events/{id}`
- `POST   /admin/events` – create curated event
- `PUT    /admin/events/{id}` – full update
- `DELETE /admin/events/{id}` – soft delete (`is_active=false`)

## Adding Curated Events

Two recommended ways:

1. **JSON import (bulk, idempotent)**

```bash
PYTHONPATH=. python3 scripts/import_events.py data/my_events.json
```

See `data/events_curated_seed.json` for the reference format and 17+ high-quality examples.

Supports upsert by (title + start_date).

2. **Interactive single event**

```bash
PYTHONPATH=. python3 scripts/add_curated_event.py
```

## Tool for Chat / LLM

`search_osijek_events` (LangChain tool) is the primary way the chat uses events.

It internally calls the same hybrid logic + Tavily only as last resort.

The tool is marked MANDATORY for any event-related question.

## Current Curated Data (as of latest seed)

17 high-quality events covering:
- Paulinafest, jazz evenings, BBQ, beer days
- Kazalište, simfonijski koncerti
- Noć muzeja, izložbe (Mursa)
- Sport (Half Marathon, Biciklijada)
- Božićni sajam, književni dani, dječji festival...

Goal: keep 20–30 active curated events with reliable dates at all times.

## Soft Delete

Events are never hard-deleted. `DELETE` sets `is_active=false`.  
Admin list supports `?include_inactive=true`.

All public/hybrid queries automatically exclude inactive records.

## Future Improvements (nice to have)

- Slug field + unique constraint
- Richer recurrence support (for weekly jazz etc.)
- Admin web UI (simple)
- Automatic expiration of very old scraped events

## Related Files

- `src/models/event.py`
- `src/routers/events.py`
- `src/schemas/event.py`
- `src/tools.py` (`get_hybrid_upcoming_events`, `search_osijek_events`)
- `scripts/import_events.py`, `add_curated_event.py`
- `data/events_curated_seed.json`
- Public consumption: `GET /events` in `src/api.py`

This module is now at parity with the mature POI system for data quality and mobile readiness.
