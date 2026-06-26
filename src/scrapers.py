"""
Lightweight scrapers for local Osijek event sources.

Supported sources:
- osijek031.com (community-driven najave)
- osijeknews.hr (news + najave događanja)
- sib.net.hr (događanja sekcija)

Main entry point: fetch_local_osijek_events()
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import time
import concurrent.futures

NAJAVE_URL = "http://www.osijek031.com/osijek-najave-kino-kazaliste-koncerti.php"

# Simple module-level TTL cache
_cache: Dict[str, Dict] = {}


def _get_cached(key: str, ttl_seconds: int = 1800) -> Optional[List[Dict]]:
    """Returns cached value if still fresh."""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < ttl_seconds:
            return entry["data"]
    return None


def _set_cache(key: str, data: List[Dict]):
    _cache[key] = {
        "data": data,
        "timestamp": time.time()
    }


def fetch_osijek031_najave(days_ahead: int = 14, use_cache: bool = True, debug: bool = False) -> List[Dict]:
    """
    Structured parser for osijek031.com "Najave događaja".

    Approach:
    1. First collect all elements that contain valid dates (date headers).
    2. Then for each najava link, find the nearest preceding date header
       using find_previous. This is much more reliable for table-based
       calendars than pure streaming.
    """
    cache_key = f"osijek031_najave_{days_ahead}"

    if use_cache and not debug:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OsijekAI-Guide/1.0; +https://github.com)"
    }

    try:
        resp = requests.get(NAJAVE_URL, headers=headers, timeout=8)
        resp.encoding = "windows-1250"
        html = resp.text
    except Exception as e:
        print(f"[scraper] Failed to fetch osijek031: {e}")
        return []

    soup = BeautifulSoup(html, "lxml")

    # Step 1: Collect all valid date header elements
    date_headers = []
    for element in soup.descendants:
        if element.name is None:
            continue
        text = element.get_text(" ", strip=True)
        if _parse_croatian_date(text):
            date_headers.append(element)

    if debug:
        print(f"[DEBUG] Found {len(date_headers)} date headers")

    # Step 2: Find all najava links and associate them with the correct date
    events = []
    today = datetime.now().date()

    najava_links = soup.find_all("a", href=re.compile(r"najava_id=\d+"))

    for link in najava_links:
        href = link.get("href", "")
        if not href:
            continue

        # Try to get a better title (multiple strategies)
        title = link.get_text(strip=True)

        # Strategy 1: parent text (often contains full title)
        if len(title) < 15 and link.parent:
            parent_text = link.parent.get_text(" ", strip=True)
            if len(parent_text) > len(title):
                title = parent_text[:180]

        # Strategy 2: title attribute on the link
        if len(title) < 10:
            attr_title = link.get("title", "")
            if attr_title and len(attr_title) > len(title):
                title = attr_title[:180]

        # Strategy 3: clean common noise (CineStar, Kino Urania programs)
        title = re.sub(r'\s*\[\d{1,2}\.\d{1,2}\.?-?\d{1,2}\.\d{1,2}\.?\d{0,4}\]', '', title)

        if not title or len(title) < 4:
            continue

        # Find the closest preceding date header
        date_header = link.find_previous(lambda tag: tag in date_headers)

        event_date = None
        if date_header:
            event_date = _parse_croatian_date(date_header.get_text(" ", strip=True))

        # Pragmatic approach: keep the event even if we don't have a reliable date
        if event_date:
            if event_date < today:
                continue
            if (event_date - today).days > days_ahead:
                continue

        if not href.startswith("http"):
            href = "http://www.osijek031.com/" + href.lstrip("/")

        # crude but useful location + short desc extraction for better mobile cards and "blizu" matching
        loc = "Osijek"
        tlow = title.lower()
        if "tvrđa" in tlow or "tvrdja" in tlow:
            loc = "Tvrđa"
        elif "drava" in tlow:
            loc = "Drava / obala"
        elif "centar" in tlow or "trg" in tlow:
            loc = "Centar"
        elif "kopački" in tlow or "rit" in tlow:
            loc = "Kopački rit"

        short_desc = (title.strip()[:90] + "...") if len(title.strip()) > 90 else title.strip()

        events.append({
            "title": title.strip(),
            "url": href,
            "date": event_date.isoformat() if event_date else None,
            "source": "osijek031.com",
            "has_reliable_date": event_date is not None,
            "location": loc,
            "short_description": short_desc,
        })

    # Early noise filter (saves work and detail fetches)
    events = [e for e in events if not _is_noise_event(e)]

    # Deduplicate
    seen = set()
    unique_events = []
    for e in events:
        key = (e["title"][:90], e["url"])
        if key not in seen:
            seen.add(key)
            unique_events.append(e)

    # Sort: events with reliable dates first, then by date
    unique_events.sort(key=lambda x: (
        0 if x.get("has_reliable_date") else 1,
        x.get("date") or "9999-12-31"
    ))

    # === A) Enrich short/truncated titles from detail pages (limited calls) ===
    # Only for non-noise events that look truncated. Max 6 detail fetches per run.
    enriched = 0
    max_detail_fetches = 6
    for ev in unique_events:
        if enriched >= max_detail_fetches:
            break
        if _is_noise_event(ev):
            continue
        if not _looks_truncated(ev.get("title", "")):
            continue
        if not ev.get("url"):
            continue

        full = _resolve_full_title_from_detail(ev["url"])
        if full and len(full) > len(ev.get("title", "")):
            ev["title"] = full
            ev["title_enriched"] = True
            enriched += 1

    if debug and enriched:
        print(f"[DEBUG] Enriched {enriched} titles via detail pages")

    result = unique_events[:60]

    if use_cache and not debug:
        _set_cache(cache_key, result)

    return result


def _parse_croatian_date(text: str):
    """
    Improved date parser for osijek031.com format.
    Handles strings like:
      - "pet 29. 05. 2026."
      - "sub 30. 05. 2026."
      - "nedjelja 31. 05. 2026."
    """
    if not text:
        return None

    text = text.lower().strip()

    # Match patterns like "pet 29. 05. 2026" or "sub 30.05.2026."
    match = re.search(r"(\d{1,2})[.\s]+(\d{1,2})[.\s]+(\d{4})", text)
    if not match:
        return None

    try:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        # Basic sanity check
        if year < 2024 or year > 2030:
            return None
        if month < 1 or month > 12:
            return None
        if day < 1 or day > 31:
            return None

        return datetime(year, month, day).date()
    except ValueError:
        return None


# ============================================================
# Main aggregator
# ============================================================

def _normalize_title(title: str) -> str:
    """Normalizira naslov za deduplikaciju (uklanja datume u zagradama, višak spaceova itd.)."""
    if not title:
        return ""
    t = title.lower().strip()
    # Ukloni uobičajene obrasce datuma u zagradama
    t = re.sub(r'\s*\[\d{1,2}\.\d{1,2}\.?-?\d{1,2}\.\d{1,2}\.?\d{0,4}\]|\s*\(\d{1,2}\.\d{1,2}\.?-?\d{1,2}\.\d{1,2}\.?\d{0,4}\)', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def _is_noise_event(event: Dict) -> bool:
    """Filtrira šum (stalni programi kina, generic najave itd.)."""
    title = (event.get("title", "") or "").lower()
    # CineStar / Kino Urania weekly or daily programs (very common noise)
    if "cinestar" in title and any(k in title for k in ["program", "[", "(", "najava"]):
        return True
    if "kino urania" in title and any(k in title for k in ["program", "[", "(", "najava"]):
        return True
    # Generic truncated cinema listings
    if title.startswith("cinestar osijek") or title.startswith("kino urania"):
        return True
    # Other common repeating low-value entries
    if "program" in title and len(title) < 45:
        return True
    # Very generic or promotional repeats
    if any(x in title for x in ["nagradno darivanje", "besplatno za djecu"]) and len(title) < 60:
        return True
    return False


def _looks_truncated(title: str) -> bool:
    """Detects titles that were cut off in the listing page."""
    if not title:
        return True
    t = title.strip()
    if t.endswith("...") or t.endswith("…"):
        return True
    if len(t) <= 22:
        return True
    return False


def _resolve_full_title_from_detail(detail_url: str) -> Optional[str]:
    """
    Fetches a single najava detail page and extracts the real/full title.
    Used sparingly (max ~6 calls per run) to improve quality of important events.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OsijekAI-Guide/1.0)"
    }
    try:
        resp = requests.get(detail_url, headers=headers, timeout=8)
        resp.encoding = "windows-1250"
        soup = BeautifulSoup(resp.text, "lxml")

        # Best sources: title tag or h1
        candidates = []
        if soup.title and soup.title.string:
            candidates.append(soup.title.string.strip())
        h1 = soup.find("h1")
        if h1:
            candidates.append(h1.get_text(" ", strip=True))

        for c in candidates:
            # Clean obvious noise suffixes but keep real event info
            c = re.sub(r'\s*\[nagradno darivanje.*?\]', '', c, flags=re.I)
            if len(c) > 12 and "osijek031" not in c.lower():
                # Prefer the longer, more descriptive one
                return c[:220]
    except Exception:
        pass
    return None


def fetch_local_osijek_events(days_ahead: int = 14, use_cache: bool = True) -> List[Dict]:
    """
    Main function for Lega.
    Combines events from all supported local sources with improved deduplication.
    Scrapers run in parallel (ThreadPoolExecutor) with a 9s overall wall-clock cap
    so a single slow/hanging source can't block the public /events endpoint.
    """
    _scrapers = [
        ("osijek031",        lambda: fetch_osijek031_najave(days_ahead=days_ahead, use_cache=use_cache)),
        ("osijeknews",       lambda: fetch_osijeknews_events(days_ahead=days_ahead, use_cache=use_cache)),
        ("sib",              lambda: fetch_sib_events(days_ahead=days_ahead, use_cache=use_cache)),
        ("djecje-kazaliste", lambda: fetch_djecje_kazaliste_program(days_ahead=days_ahead, use_cache=use_cache)),
    ]

    all_events: List[Dict] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_name = {executor.submit(fn): name for name, fn in _scrapers}
        try:
            for future in concurrent.futures.as_completed(future_to_name, timeout=9):
                name = future_to_name[future]
                try:
                    all_events.extend(future.result())
                except Exception as e:
                    print(f"[scraper] {name} error: {e}")
        except concurrent.futures.TimeoutError:
            print("[scraper] 9s wall-clock cap hit — collecting results from completed scrapers")
            for future, name in future_to_name.items():
                if future.done():
                    try:
                        all_events.extend(future.result())
                    except Exception as e:
                        print(f"[scraper] {name} (late) error: {e}")

    # Filtriraj šum (CineStar, Kino Urania dnevni programi itd.)
    all_events = [e for e in all_events if not _is_noise_event(e)]

    # C) Bolja deduplikacija + pametno rangiranje
    # Source quality (lower number = higher priority/quality)
    SOURCE_PRIORITY = {
        "osijeknews.hr": 0,
        "sib.net.hr": 1,
        "osijek031.com": 2
    }

    # Deduplikacija po normaliziranom naslovu (jača normalizacija)
    seen = set()
    unique = []
    for e in all_events:
        norm_title = _normalize_title(e.get("title", ""))
        key = (norm_title[:120], e.get("url", "")[:100])  # slightly stronger key
        if key not in seen:
            seen.add(key)
            unique.append(e)

    # Poboljšano sortiranje (C):
    # 1. Prvo oni sa pouzdanim datumom (najvažnije za korisnika)
    # 2. Po prioritetu izvora (osijeknews > sib > 031)
    # 3. Po datumu
    # 4. Obogaćeni naslovi (bonus za 031)
    unique.sort(key=lambda x: (
        0 if x.get("has_reliable_date") else 1,
        SOURCE_PRIORITY.get(x.get("source"), 9),
        x.get("date") or "9999-12-31",
        0 if x.get("title_enriched") else 1
    ))

    return unique


# ============================================================
# osijeknews.hr scraper (to be implemented)
# ============================================================

def fetch_osijeknews_events(days_ahead: int = 14, use_cache: bool = True) -> List[Dict]:
    """
    Scraper for osijeknews.hr "NAJAVE DOGAĐANJA" section.

    Key invariants:
    - Finds the heading by tag type (h2/h3/h4 in <body>), NOT by string search.
      The old string search matched the JSON-LD <script> meta description first,
      causing find_all_next() to sweep the entire page body.
    - Stops collecting when the next unrelated section heading is encountered.
    - Requires an explicit future date on each item — events without a parseable
      weekday+date header are discarded (not assigned today's date).
    - Rejects non-event content (news articles, police reports, ads, etc.).
    """
    cache_key = f"osijeknews_events_{days_ahead}"

    if use_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

    url = "https://osijeknews.hr/"
    req_headers = {"User-Agent": "Mozilla/5.0 (compatible; OsijekAI-Guide/1.0)"}

    try:
        resp = requests.get(url, headers=req_headers, timeout=8)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"[scraper] osijeknews.hr fetch error: {e}")
        return []

    body = soup.body
    if not body:
        return []

    # Find the NAJAVE DOGAĐANJA heading in the visible body (h2/h3/h4 only).
    # Explicitly exclude <script> and <head> to avoid matching the JSON-LD meta.
    najave_heading = None
    for tag in body.find_all(["h2", "h3", "h4"]):
        if "NAJAVE" in tag.get_text(strip=True).upper():
            najave_heading = tag
            break

    if not najave_heading:
        print("[scraper] osijeknews.hr: NAJAVE DOGAĐANJA heading not found in body — returning empty")
        return []

    today = datetime.now().date()
    day_pattern = re.compile(
        r"(ponedjeljak|utorak|srijeda|četvrtak|petak|subota|nedjelja)"
        r"[,\s]+(\d{1,2})\.(\d{1,2})\.(\d{4})",
        re.I,
    )

    BAD_TITLES = {
        "afere", "politika", "gospodarstvo", "sport", "kultura",
        "kazalište i kino", "koncerti", "galerije", "najave", "vijesti", "osijek",
    }

    # Reject patterns for obvious non-event content.
    # These strings signal news articles, accidents, press releases, or ads —
    # none of which belong in an events feed.
    NEWS_NOISE = re.compile(
        r"nesreća|nesrecci|stradao|poginuo|poginula|uhićen|uhapšen|optužen|"
        r"osuđen|policij|požar|prometna|smrtno|preminuo|preminula|"
        r"influenc|natječ|sufinancir|konferencija za novinare|"
        r"priopćenj|izvješć",
        re.I,
    )

    events: List[Dict] = []
    current_date = None
    collected = 0

    for elem in najave_heading.find_all_next():
        if collected >= 25:
            break

        # Stop when we reach the next section-level heading that is NOT a date header.
        if elem.name in ("h2", "h3") and elem is not najave_heading:
            text_upper = elem.get_text(strip=True).upper()
            is_date_header = any(
                day in text_upper
                for day in ["PONEDJELJAK", "UTORAK", "SRIJEDA", "ČETVRTAK", "PETAK", "SUBOTA", "NEDJELJA"]
            )
            if not is_date_header:
                break

        text = elem.get_text(" ", strip=True)

        # Detect weekday + date headers ("Petak, 27.06.2026.")
        day_match = day_pattern.search(text)
        if day_match:
            try:
                d = int(day_match.group(2))
                m = int(day_match.group(3))
                y = int(day_match.group(4))
                current_date = datetime(y, m, d).date()
            except Exception:
                current_date = None
            continue

        # Only process <a> links
        if elem.name != "a" or not elem.get("href"):
            continue

        href = elem["href"]
        title = elem.get_text(strip=True)

        # Basic quality gates
        if not title or len(title) < 12:
            continue
        if title.lower() in BAD_TITLES:
            continue
        if "osijeknews.hr" not in href and not href.startswith("/"):
            continue
        if any(seg in href for seg in ["/kategorija/", "/tag/", "#", "/page/"]):
            continue
        if any(bad in title.lower() for bad in BAD_TITLES):
            continue

        # Reject items without an explicitly parsed future date.
        # This is the key change: we never fall back to "today" as a default.
        if current_date is None:
            continue
        if current_date < today:
            continue
        if (current_date - today).days > days_ahead:
            continue

        # Reject obvious non-event content (accidents, press releases, ads …)
        if NEWS_NOISE.search(title):
            continue

        events.append({
            "title": title[:160],
            "url": href if href.startswith("http") else "https://osijeknews.hr" + href,
            "date": current_date.isoformat(),
            "source": "osijeknews.hr",
            "has_reliable_date": True,
            "location": "Osijek",
            "short_description": title[:90],
        })
        collected += 1

    # Deduplicate by (normalised title, url)
    seen: set = set()
    unique: List[Dict] = []
    for e in events:
        key = (e["title"][:80], e["url"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    unique.sort(key=lambda x: x.get("date", "9999-12-31"))

    result = unique[:30]

    if use_cache:
        _set_cache(cache_key, result)

    return result


def fetch_sib_events(days_ahead: int = 14, use_cache: bool = True) -> List[Dict]:
    """
    Scraper for sib.net.hr "Događanja" section (https://sib.net.hr/dogadjaji/lista/).
    Good structure, includes dates and descriptions.
    """
    cache_key = f"sib_events_{days_ahead}"

    if use_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

    url = "https://sib.net.hr/dogadjaji/lista/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OsijekAI-Guide/1.0)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"[scraper] sib.net.hr fetch error: {e}")
        return []

    events = []
    today = datetime.now().date()

    # Look for event containers
    # Based on site structure, events are often in articles or list items with dates
    event_items = soup.find_all(["article", "div", "li"], class_=lambda x: x and ("dogadjanj" in str(x).lower() or "event" in str(x).lower() or "najava" in str(x).lower())) or \
                  soup.select(".dogadjaji-list .item, .events-list .event, article")

    for item in soup.find_all(["article", "div", "section"], limit=100):
        text = item.get_text(" ", strip=True)
        link = item.find("a", href=True)

        if not link:
            continue

        href = link.get("href", "")
        title = link.get_text(strip=True)

        if not title or len(title) < 5:
            continue

        if "sib.net.hr" not in href:
            continue

        # Try to extract date from the item or surrounding text
        date_text = text[:300]
        event_date = _parse_croatian_date(date_text)

        if event_date:
            if event_date < today or (event_date - today).days > days_ahead:
                continue
        else:
            # If no usable future date on sib, treat as low priority / uncertain
            pass

        # Skip obvious navigation
        if len(title) < 12 or title.lower() in {"naslovnica", "lista", "vijesti", "osijek"}:
            continue

        events.append({
            "title": title[:160],
            "url": href if href.startswith("http") else "https://sib.net.hr" + href,
            "date": event_date.isoformat() if event_date else None,
            "source": "sib.net.hr",
            "has_reliable_date": event_date is not None,
            "location": "Osijek",
            "short_description": title[:90],
        })

    # Deduplicate
    seen = set()
    unique = []
    for e in events:
        key = (e["title"][:80], e["url"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    unique.sort(key=lambda x: (0 if x["has_reliable_date"] else 1, x.get("date") or "9999-12-31"))

    result = unique[:40]

    if use_cache:
        _set_cache(cache_key, result)

    return result


def fetch_djecje_kazaliste_program(days_ahead: int = 14, use_cache: bool = True) -> List[Dict]:
    """
    Scraper for the official weekly/monthly program of Dječje kazalište Branka Mihaljevića.
    Tries tjedni-raspored first, falls back to mjesecni-raspored if the page has anti-bot protection.
    This ensures the AI has accurate, up-to-date info about shows in the next days at this specific venue.
    """
    cache_key = f"djecje_kazaliste_program_{days_ahead}"

    if use_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OsijekAI-Guide/1.0; +https://github.com)"
    }

    # Try tjedni first, fallback to mjesecni if we hit verification/loader page (anti-bot protection)
    urls_to_try = [
        "https://www.djecje-kazaliste.hr/tjedni-raspored/",
        "https://www.djecje-kazaliste.hr/mjesecni-raspored/"
    ]

    resp = None
    soup = None
    for u in urls_to_try:
        try:
            resp = requests.get(u, headers=headers, timeout=8)
            text = resp.text.lower()
            if "verification" in text or "please wait" in text or "loader" in text or len(resp.text) < 4000:
                print(f"[scraper] djecje hit verification on {u}, trying next...")
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            url = u  # remember which one worked
            break
        except Exception as e:
            print(f"[scraper] Dječje kazalište fetch error on {u}: {e}")
            continue

    if soup is None:
        print("[scraper] Dječje kazalište: could not bypass protection on either page, returning []")
        return []

    events = []
    today = datetime.now().date()

    # The page contains the weekly timetable. We look for performance entries.
    # Strategy: find blocks that contain time patterns (e.g. 10:00, 17:30) and a title/link for the play.
    # Also capture surrounding date context if available (day names + dates).

    day_pattern = re.compile(r"(ponedjeljak|utorak|srijeda|četvrtak|petak|subota|nedjelja)", re.I)
    time_pattern = re.compile(r"(\d{1,2}[:.]\d{2})")

    # Walk the page and group by day when possible
    current_date = None

    for elem in soup.find_all(["div", "section", "article", "li", "tr", "h2", "h3", "p"], limit=150):
        text = elem.get_text(" ", strip=True)
        if not text or len(text) < 8:
            continue

        # Update current date context if we see a day header
        day_match = day_pattern.search(text)
        if day_match:
            # Try to extract full date too
            date_from_text = _parse_croatian_date(text)
            if date_from_text:
                current_date = date_from_text
            continue

        # Look for time + performance title
        time_match = time_pattern.search(text)
        if not time_match:
            continue

        # Find a meaningful title - prefer links or longer descriptive text
        title = None
        link = elem.find("a", href=True)
        if link:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not href.startswith("http"):
                href = "https://www.djecje-kazaliste.hr" + href.lstrip("/")
        else:
            # Fallback: take a chunk that looks like a play title (avoid pure times)
            parts = [p.strip() for p in text.split() if len(p.strip()) > 3]
            if parts:
                title = " ".join(parts[:6])  # reasonable length

        if not title or len(title) < 5:
            continue

        # Skip if it looks like navigation or generic
        if any(bad in title.lower() for bad in ["početna", "kontakt", "o nama", "repertoar", "raspored"]):
            continue

        event_date = current_date
        if event_date and (event_date < today or (event_date - today).days > days_ahead):
            continue

        time_str = time_match.group(1).replace(".", ":")

        events.append({
            "title": f"{title} – Dječje kazalište Branka Mihaljevića",
            "url": href if 'href' in locals() and href else (url if 'url' in locals() else "https://www.djecje-kazaliste.hr/"),
            "date": event_date.isoformat() if event_date else None,
            "source": "djecje-kazaliste.hr",
            "has_reliable_date": event_date is not None,
            "location": "Dječje kazalište Branka Mihaljevića",
            "short_description": f"Predstava u {time_str}. {text[:120]}",
        })

    # Deduplicate
    seen = set()
    unique = []
    for e in events:
        key = (e["title"][:60], e.get("date"))
        if key not in seen:
            seen.add(key)
            unique.append(e)

    unique.sort(key=lambda x: (0 if x.get("has_reliable_date") else 1, x.get("date") or "9999-12-31"))

    result = unique[:15]

    if use_cache:
        _set_cache(cache_key, result)

    return result


# ============================================================
# RESTAURANTS - Hybrid Approach (Phase 1 + Phase 2)
# ============================================================
#
# STRATEGY DECISION (May 2026):
# After thorough investigation, jelo.hr was found to be heavily JavaScript-rendered
# with no easily accessible public API (Supabase is used only for image storage
# and is properly locked down).
#
# Therefore, we use a pragmatic hybrid model that has proven reliable:
#
# 1. CURATED SEED (primary source of truth)
#    - High-quality, manually maintained list based on:
#      - jelo.hr data
#      - Gault&Millau Croatia 2026 (Slavonija/Baranja edition)
#      - Telegram Super1, Putnikofer, Jutarnji/Dobra Hrana chef recommendations
#    - This ensures excellent coverage, accurate ratings, specialties, and practical notes.
#
# 2. DEFENSIVE jelo.hr SCRAPER (supplementary)
#    - `fetch_jelo_osijek_restaurants()` attempts light extraction.
#    - If it cannot extract meaningful structured data (very common due to JS rendering),
#      it gracefully returns [] and the system falls back to curated data.
#    - Goal: Capture any easy wins without introducing noise or fragility.
#
# 3. AGGREGATOR
#    - `fetch_local_osijek_restaurants()` merges both sources with deduplication
#      and smart ranking (Gault&Millau > rating > source quality).
#
# This approach mirrors the successful "best-effort" strategy used for events
# (osijek031.com + osijeknews.hr + sib.net.hr + curated fallback).
#
# Future improvements can include:
# - Occasional manual refresh of curated data from Top 10 page
# - If jelo.hr ever exposes a partner API, easy swap-in
# - More aggressive text parsing if the site structure changes
#
# ============================================================

def fetch_jelo_osijek_restaurants(use_cache: bool = True, debug: bool = False) -> List[Dict]:
    """
    Phase 2: Attempts to scrape data from jelo.hr.

    Note: The site is heavily JavaScript rendered. This function uses
    defensive text + link extraction. If it cannot extract meaningful data,
    it returns [] gracefully so the system falls back to curated data.
    """
    cache_key = "jelo_osijek_restaurants"

    if use_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OsijekAI-Guide/1.0; +https://github.com)"
    }

    restaurants = []

    # Try main listing page
    try:
        resp = requests.get("https://jelo.hr/restorani/osijek", headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # Extract using patterns observed in the site (ratings + names)
        # Pattern examples: "4.8(3496)" or "4.7· 4398 recenzija"
        rating_pattern = re.compile(r"(\d\.\d)[·\s(](\d{1,5})")

        # Look for known high-value restaurants in the text
        known_names = [
            "Crna svinja", "Čingi Lingi", "Rustika", "Projekt 9",
            "Meandar", "Pepe Pizza", "Ventidue", "Didin Konak"
        ]

        for name in known_names:
            if name.lower() in text.lower():
                # Very basic extraction - we will enrich from curated later
                match = rating_pattern.search(text, text.lower().find(name.lower()))
                rating = float(match.group(1)) if match else None
                reviews = int(match.group(2)) if match else None

                restaurants.append({
                    "name": name,
                    "address": None,
                    "phone": None,
                    "url": "https://jelo.hr/restorani/osijek",
                    "rating": rating,
                    "review_count": reviews,
                    "price_level": None,
                    "tags": [],
                    "specialties": [],
                    "distance_note": None,
                    "source": "jelo.hr (partial)",
                    "last_updated": "2026-05"
                })
    except Exception as e:
        if debug:
            print(f"[jelo scraper] Listing page error: {e}")

    # Try Top 10 page - this page tends to have more structured text even when JS-rendered
    try:
        resp = requests.get("https://jelo.hr/vodici/top-10-restorana-osijek-2026", headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # More aggressive extraction from Top 10 page
        # Pattern: Name followed by rating and reviews
        top10_pattern = re.compile(
            r'([A-ZČĆŽŠĐ][A-Za-zČĆŽŠĐčćžšđ\s\-\(\)]{3,50}?)\s*(\d\.\d)[·\s(](\d{1,5})'
        )

        for match in top10_pattern.finditer(text):
            name = match.group(1).strip()
            rating = float(match.group(2))
            reviews = int(match.group(3))

            # Avoid duplicates from the first pass
            if not any(r["name"].lower() in name.lower() for r in restaurants):
                restaurants.append({
                    "name": name,
                    "address": None,
                    "phone": None,
                    "url": "https://jelo.hr/vodici/top-10-restorana-osijek-2026",
                    "rating": rating,
                    "review_count": reviews,
                    "price_level": None,
                    "tags": [],
                    "specialties": [],
                    "distance_note": None,
                    "source": "jelo.hr Top 10 (text)",
                    "last_updated": "2026-05"
                })

        if debug:
            print(f"[jelo scraper] Top10 page: extracted {len([r for r in restaurants if 'Top 10' in r.get('source','')])} additional entries")

    except Exception as e:
        if debug:
            print(f"[jelo scraper] Top10 page error: {e}")

    # If we extracted almost nothing (common due to JS rendering), return empty
    # so the aggregator safely falls back to high-quality curated data.
    if len(restaurants) < 3:
        if debug:
            print("[jelo scraper] Insufficient data extracted (likely JS-rendered). Falling back to curated.")
        result = []
    else:
        result = restaurants

    if use_cache:
        _set_cache(cache_key, result)

    return result


# ============================================================
# RESTAURANTS - Phase 1: Curated high-quality seed data
# ============================================================

CURATED_OSIJEK_RESTAURANTS = [
    {
        "name": "Crna Svinja (Terra Negra)",
        "address": "Ul. Ovčara 3, 31431 Čepin",
        "phone": "091 451 2676",
        "url": "https://terranegra.hr/",
        "rating": 4.8,
        "review_count": 3496,
        "price_level": "€€",
        "tags": ["traditional", "slavonian", "grill", "pork", "fine"],
        "specialties": ["file crne svinje", "konfitirani obrazi", "ribeye od crne svinje", "uštipci"],
        "distance_note": "10-15 min od centra (Čepin)",
        "lat": 45.521,
        "lng": 18.606,
        "source": "jelo.hr + Gault&Millau 2026 (3 toke)",
        "last_updated": "2026-05"
    },
    {
        "name": "Čingi Lingi Čarda",
        "address": "Ul. kralja Zvonimira, 31327 Bilje",
        "phone": "031 281 700",
        "url": "https://cingi-lingi-carda.hr/",
        "rating": 4.7,
        "review_count": 4398,
        "price_level": "€€",
        "tags": ["traditional", "fish", "čarda", "baranja"],
        "specialties": ["fiš paprikaš od šarana", "smuđ sa žara", "perkelt od soma", "gulaš od divljači"],
        "distance_note": "10-15 min od centra (Bilje)",
        "lat": 45.605,
        "lng": 18.746,
        "source": "jelo.hr + Telegram + Putnikofer",
        "last_updated": "2026-05"
    },
    {
        "name": "Corner",
        "address": "Velebitska ulica, Jug II, Osijek",
        "phone": "031 333 584",
        "url": "https://corner-osijek.hr/",
        "rating": 4.6,
        "review_count": None,
        "price_level": "€€",
        "tags": ["traditional", "grill", "slavonian", "family", "fish"],
        "specialties": ["teleća peka", "fiš od šarana", "som sa žara", "smuđ orly", "leskovačka mućkalica"],
        "distance_note": "Jug II (Velebitska ulica)",
        "lat": 45.548,   # approximate
        "lng": 18.692,
        "source": "Službena stranica + jelo.hr + Putnikofer",
        "last_updated": "2026-05"
    },
    {
        "name": "Projekt 9",
        "address": "Gornjodravska obala bb, Osijek",
        "phone": "031 283 500",
        "url": "https://projekt9.hr/",
        "rating": 4.5,
        "review_count": 2648,
        "price_level": "€€",
        "tags": ["modern", "drava_view", "fusion", "romantic"],
        "specialties": ["steakovi", "pasta", "tradicionalna jela s twistom"],
        "distance_note": "brod na Dravi, centar",
        "source": "jelo.hr + Putnikofer",
        "last_updated": "2026-05"
    },
    {
        "name": "Meandar (Hotel Osijek)",
        "address": "Šamačka 4, 31000 Osijek",
        "phone": None,
        "url": "https://restoranmeandar.hr/",
        "rating": 4.6,
        "review_count": None,
        "price_level": "€€€",
        "tags": ["modern", "drava_view", "fine", "slavonian"],
        "specialties": ["lokalne namirnice", "riba i meso", "kreativna slavonska kuhinja"],
        "distance_note": "uz Dravu, centar",
        "source": "Gault&Millau 2026 (3 toke) + jelo.hr",
        "last_updated": "2026-05"
    },
    {
        "name": "Grill-Pizzeria Rustika",
        "address": "Ul. Pavla Pejačevića 32, Osijek",
        "phone": "031 369 400",
        "url": "https://www.rustika.hr/",
        "rating": 4.6,
        "review_count": 4163,
        "price_level": "€€",
        "tags": ["traditional", "pizza", "grill", "central"],
        "specialties": ["biftek", "lungić", "ražnjići", "dobre pizze"],
        "distance_note": "blizu Konkatedrale",
        "source": "jelo.hr + Putnikofer",
        "last_updated": "2026-05"
    },
    {
        "name": "Pepe Pizza Place",
        "address": "Šamačka 4, Osijek",
        "phone": "031 230 030",
        "url": "https://www.facebook.com/pepepizzaplace/",
        "rating": 4.7,
        "review_count": 1563,
        "price_level": "€",
        "tags": ["pizza", "italian", "central"],
        "specialties": ["neapolitanske pizze", "Pistacchio & mortadella", "Tartuffo & prosciutto"],
        "distance_note": "centar",
        "source": "jelo.hr + Telegram",
        "last_updated": "2026-05"
    },
    {
        "name": "Ventidue Pizza & Bar",
        "address": "Ul. Stjepana Radića 22, Osijek",
        "phone": "031 626 222",
        "url": "",
        "rating": 4.7,
        "review_count": 1579,
        "price_level": "€€",
        "tags": ["pizza", "italian", "modern"],
        "specialties": ["autentične napuljske pizze"],
        "distance_note": "centar",
        "source": "jelo.hr",
        "last_updated": "2026-05"
    },
    {
        "name": "Lulu Fusion Bistro",
        "address": "Sunčana ulica 5, Osijek",
        "phone": None,
        "url": "",
        "rating": 4.5,
        "review_count": None,
        "price_level": "€€",
        "tags": ["fusion", "asian", "modern", "chef_favorite"],
        "specialties": ["tuna poke", "green curry", "tonkotsu ramen"],
        "distance_note": "Osijek / blizu Čepina",
        "source": "Jutarnji Dobra Hrana (chef Kočiš) + Telegram",
        "last_updated": "2026-05"
    },
    {
        "name": "Čarda kod Baranjca",
        "address": "Biljska cesta 54, Podravlje, Osijek",
        "phone": "091 501 1722",
        "url": "",
        "rating": 4.7,
        "review_count": 1625,
        "price_level": "€€",
        "tags": ["traditional", "baranja", "čarda"],
        "specialties": ["baranjska kuhinja"],
        "distance_note": "blizu Osijeka",
        "source": "jelo.hr",
        "last_updated": "2026-05"
    },
    {
        "name": "Lipov hlad",
        "address": "Trg bana Josipa Jelačića 2, Osijek",
        "phone": "031 508 811",
        "url": "https://www.lipov-hlad.hr/",
        "rating": 4.5,
        "review_count": None,
        "price_level": "€€",
        "tags": ["traditional", "slavonian", "central"],
        "specialties": ["filet mignon", "kare iberijske svinje"],
        "distance_note": "Donji grad / centar",
        "source": "Telegram + jelo.hr",
        "last_updated": "2026-05"
    },
    {
        "name": "Josić (Baranja)",
        "address": "Zmajevac, Baranja",
        "phone": None,
        "url": "",
        "rating": None,
        "review_count": None,
        "price_level": "€€€",
        "tags": ["fine", "baranja", "wine", "traditional"],
        "specialties": ["moderna interpretacija tradicije"],
        "distance_note": "~25-30 min od Osijeka (preporučeno za izlet)",
        "source": "Gault&Millau 2026 (4 toke) - najbolji u regiji",
        "last_updated": "2026-05"
    },
    {
        "name": "Didin Konak",
        "address": "Petefi Šandora 93, 31327 Kopačevo (Bilje)",
        "phone": "031 752 100",
        "url": "",
        "rating": 4.6,
        "review_count": 2650,
        "price_level": "€€",
        "tags": ["traditional", "baranja"],
        "specialties": ["baranjska kuhinja"],
        "distance_note": "Baranja, blizu Kopačeva",
        "source": "jelo.hr",
        "last_updated": "2026-05"
    },
    {
        "name": "Waldinger",
        "address": "centar Osijek (hotel Waldinger)",
        "phone": None,
        "url": "",
        "rating": None,
        "review_count": None,
        "price_level": "€€€",
        "tags": ["fine", "international", "elegant"],
        "specialties": ["moderna europska kuhinja"],
        "distance_note": "centar",
        "source": "Jutarnji Dobra Hrana + chef preporuke",
        "last_updated": "2026-05"
    },
]


def _normalize_restaurant_name(name: str) -> str:
    """Normalizira naziv za deduplikaciju."""
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r'\s+', ' ', n)
    n = n.replace(" (terra negra)", "").replace(" (hotel osijek)", "")
    return n.strip()


def _categorize_restaurant(r: Dict) -> List[str]:
    """Vraća korisne kategorije za prikaz u odgovorima."""
    tags = r.get("tags", [])
    cats = []

    if "fish" in tags or "čarda" in tags:
        cats.append("Riba & Čarde")
    if "traditional" in tags and "slavonian" in tags:
        cats.append("Tradicionalna slavonska")
    if "pizza" in tags:
        cats.append("Pizza")
    if "drava_view" in tags or "modern" in tags:
        cats.append("Moderno / Pogled na Dravu")
    if "baranja" in tags:
        cats.append("Baranja izlet (10-25 min)")
    if "fusion" in tags or "asian" in tags:
        cats.append("Fusion / Moderna")
    if "fine" in tags:
        cats.append("Fine dining")
    if "grill" in tags:
        cats.append("Roštilj & Meso")
    if not cats:
        cats.append("Ostalo")

    return cats


def fetch_curated_restaurant_recommendations() -> List[Dict]:
    """Vraća kuriranu listu najboljih restorana (Phase 1 seed)."""
    return CURATED_OSIJEK_RESTAURANTS.copy()


def fetch_local_osijek_restaurants(use_cache: bool = True, structured: bool = False) -> List[Dict]:
    """
    Main entry point for restaurant data (Phase 2).
    Merges jelo.hr scraper results with curated high-quality seed.

    When `structured=True`, returns clean dicts suitable for mobile app map + cards.
    """
    all_restaurants = []

    # Try live jelo.hr data first (Phase 2)
    try:
        jelo_data = fetch_jelo_osijek_restaurants(use_cache=use_cache)
        all_restaurants.extend(jelo_data)
    except Exception as e:
        print(f"[restaurant scraper] jelo.hr error: {e}")

    # Always include strong curated seed (our golden source)
    curated = fetch_curated_restaurant_recommendations()
    all_restaurants.extend(curated)

    # Deduplication by normalized name (prefer richer entry)
    seen = {}
    for r in all_restaurants:
        key = _normalize_restaurant_name(r.get("name", ""))
        if not key:
            continue

        existing = seen.get(key)
        if not existing:
            seen[key] = r
        else:
            # Prefer entry with more complete data (rating, address, etc.)
            score_new = sum(1 for k in ["rating", "address", "phone", "specialties"] if r.get(k))
            score_old = sum(1 for k in ["rating", "address", "phone", "specialties"] if existing.get(k))
            if score_new > score_old:
                seen[key] = r

    unique = list(seen.values())

    # Ranking: Gault&Millau highest, then rating, then curated quality
    unique.sort(key=lambda x: (
        0 if "Gault" in str(x.get("source", "")) else 1,
        -(x.get("rating") or 0),
        0 if "curated" in str(x.get("source", "")).lower() or "jelo" in str(x.get("source", "")).lower() else 1,
        x.get("name", "")
    ))

    return unique


def _format_restaurant_results(restaurants: List[Dict], original_query: str = "") -> str:
    """
    Returns high-quality, categorized restaurant recommendations from curated sources.
    This is the authoritative output for food queries — the model should treat this data
    as the primary source for names, addresses, phones and specialties.
    """
    if not restaurants:
        return "Trenutno nemam kvalitetnih lokalnih podataka o restoranima."

    from collections import defaultdict
    groups = defaultdict(list)

    q_lower = original_query.lower() if original_query else ""

    for r in restaurants[:18]:
        cats = _categorize_restaurant(r)
        primary_cat = cats[0] if cats else "Ostalo"

        # Strong fish prioritization
        if any(k in q_lower for k in ["riba", "fiš", "smuđ", "šaran"]):
            if "Riba & Čarde" in cats:
                primary_cat = "Riba & Čarde"
            elif "fish" in r.get("tags", []):
                primary_cat = "Dobre opcije za ribu (centar / blizu)"

        name = r["name"]
        addr = r.get("address") or ""
        phone = r.get("phone")
        rating = r.get("rating")
        specs = r.get("specialties", [])
        dist = r.get("distance_note") or ""
        src = r.get("source", "")

        line = f"**{name}**"
        if rating:
            line += f" ({rating})"
        if dist:
            line += f" — {dist}"
        if addr:
            line += f"\n  Adresa: {addr}"
        if phone:
            line += f"\n  Tel: {phone}"
        if specs:
            line += f"\n  Specijaliteti: {', '.join(specs[:3])}"
        if src:
            line += f"\n  Izvor: {src}"

        groups[primary_cat].append(line)

    # Desired display order (fish boosted when relevant)
    category_order = [
        "Riba & Čarde",
        "Dobre opcije za ribu (centar / blizu)",
        "Tradicionalna slavonska",
        "Roštilj & Meso",
        "Pizza",
        "Moderno / Pogled na Dravu",
        "Fusion / Moderna",
        "Baranja izlet (10-25 min)",
        "Fine dining",
        "Ostalo"
    ]

    formatted = []
    for cat in category_order:
        if cat in groups:
            items = groups[cat]
            formatted.append(f"**{cat}:**\n" + "\n\n".join(items))

    # Add any remaining categories
    for cat, items in groups.items():
        if cat not in category_order:
            formatted.append(f"**{cat}:**\n" + "\n\n".join(items))

    header = "Kvalitetne preporuke restorana u Osijeku (iz kuriranih lokalnih izvora):\n\n"
    return header + "\n\n".join(formatted)


# ============================================================
# END RESTAURANTS (Phase 1)
# ============================================================


if __name__ == "__main__":
    print("=" * 70)
    print("RESTAURANT SCRAPER TEST (Phase 2)")
    print("=" * 70)

    from collections import Counter, defaultdict

    # === Restaurant test ===
    print("\n=== Pokrećem restaurant aggregator (jelo.hr + curated) ===\n")
    restaurants = fetch_local_osijek_restaurants(use_cache=True)

    print(f"Ukupno restorana: {len(restaurants)}\n")

    # Source breakdown
    source_count = Counter(r.get("source", "unknown") for r in restaurants)
    print("Po izvoru:")
    for src, cnt in source_count.most_common():
        print(f"  {src}: {cnt}")

    print("\n--- Top 10 (nakon spajanja i rangiranja) ---")
    for i, r in enumerate(restaurants[:10], 1):
        rating = f"{r.get('rating')}" if r.get("rating") else "?"
        dist = r.get("distance_note") or ""
        src = r.get("source", "")
        print(f"{i}. {r['name']} ({rating}) | {dist} | {src}")

    print("\n" + "=" * 70)

    # Also run events test for completeness
    print("\n=== Events (for comparison) ===")
    events = fetch_local_osijek_events(days_ahead=14)
    print(f"Events found: {len(events)}")