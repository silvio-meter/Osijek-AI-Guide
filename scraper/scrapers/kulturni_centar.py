"""
Scraper za Kulturni centar Osijek.
Listing: https://kulturni-centar.hr/dogadjanja/sva-dogadjanja
Detail:  https://kulturni-centar.hr/dogadjanja/{slug}
"""

import re
import time
import requests
from datetime import date, datetime
from dateutil import tz
from bs4 import BeautifulSoup

from base_scraper import BaseScraper

BASE_URL = "https://kulturni-centar.hr"
LISTING_URL = f"{BASE_URL}/dogadjanja/sva-dogadjanja"
LOCAL_TZ = tz.gettz("Europe/Zagreb")
HEADERS = {"User-Agent": "LegaBot/1.0"}

# Regex: "27.6. NASLOV" ili "27.6./20.00 sati NASLOV"
DATE_PREFIX_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.")


class KulturniCentarScraper(BaseScraper):
    source_key = "kulturni_centar"
    source_label = "Kulturni centar Osijek"

    def scrape(self) -> list[dict]:
        print(f"[{self.source_label}] Fetching listing...")
        candidates = self._fetch_listing()
        today = date.today()

        upcoming = [c for c in candidates if c["date"] >= today]
        print(f"[{self.source_label}] Budućih: {len(upcoming)} (od {len(candidates)} total)")

        events = []
        for c in upcoming:
            event = self._fetch_detail(c)
            if event:
                events.append(event)
            time.sleep(0.3)  # polite crawling

        print(f"[{self.source_label}] Parsed {len(events)} events")
        return events

    def _fetch_listing(self) -> list[dict]:
        try:
            resp = requests.get(LISTING_URL, timeout=15, headers=HEADERS)
            resp.raise_for_status()
        except Exception as e:
            print(f"[{self.source_label}] Listing fetch failed: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        seen_slugs = set()
        candidates = []
        today = date.today()

        for a in soup.select("a[href*='/dogadjanja/']"):
            href = a.get("href", "")
            # Isključi kategorijske/statične stranice
            if href in ("/dogadjanja/sva-dogadjanja", "/dogadjanja/kalendar-dogadjanja"):
                continue
            slug = href.split("/dogadjanja/")[-1].rstrip("/")
            if not slug or slug in seen_slugs:
                continue

            text = a.get_text(strip=True)
            parsed = self._parse_title_date(text, today.year)
            if parsed is None:
                continue

            event_date, clean_title = parsed
            seen_slugs.add(slug)
            candidates.append({
                "slug": slug,
                "title": clean_title,
                "date": event_date,
                "url": f"{BASE_URL}/dogadjanja/{slug}",
            })

        return candidates

    def _parse_title_date(self, text: str, year: int) -> tuple[date, str] | None:
        """
        Parsira "27.6. NASLOV" → (date(2026, 6, 27), "NASLOV")
        Vraća None ako nema datumskog prefiksa.
        """
        m = DATE_PREFIX_RE.match(text.strip())
        if not m:
            return None
        day = int(m.group(1))
        month = int(m.group(2))
        try:
            d = date(year, month, day)
        except ValueError:
            return None

        # Ukloni datum prefix iz naslova
        clean = DATE_PREFIX_RE.sub("", text).strip().lstrip("/").strip()
        # Ukloni moguće "20.00 sati " sufiks koji može ostati
        clean = re.sub(r"^\d{2}[.:]\d{2}\s*(sati)?\s*", "", clean).strip()
        if not clean:
            clean = text.strip()

        return d, clean

    def _fetch_detail(self, candidate: dict) -> dict | None:
        try:
            resp = requests.get(candidate["url"], timeout=15, headers=HEADERS)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            print(f"[{self.source_label}] Detail fetch failed ({candidate['slug']}): {e}")
            return None

        try:
            # Datum i vrijeme
            date_el = soup.select_one(".pattern--date")
            time_el = soup.select_one(".pattern--time")

            event_date = candidate["date"]
            hour, minute = 20, 0

            if time_el:
                tm = re.search(r"(\d{1,2}):(\d{2})", time_el.get_text())
                if tm:
                    hour, minute = int(tm.group(1)), int(tm.group(2))

            start_dt = datetime(event_date.year, event_date.month, event_date.day,
                                hour, minute, tzinfo=LOCAL_TZ)

            # Naslov — h2 na detail stranici sadrži datum + naslov
            title_el = soup.select_one("h2")
            title = candidate["title"]
            if title_el:
                raw = title_el.get_text(strip=True)
                parsed = self._parse_title_date(raw, event_date.year)
                if parsed:
                    _, title = parsed
                elif raw and len(raw) > 3:
                    title = raw

            title = self.clean_text(title)
            if not title:
                return None

            # Lokacija iz <p> koji sadrži datum/sati/dvorana tekst
            location = "Kulturni centar Osijek"
            for p in soup.select("p"):
                txt = p.get_text(strip=True)
                if "sati" in txt.lower() and ("dvorana" in txt.lower() or "centar" in txt.lower()):
                    # "Subota, 27.6. /20.00 sati/ Dvorana Franjo Krežma"
                    parts = re.split(r"[/|]+", txt)
                    for part in parts:
                        part = part.strip()
                        if (("dvorana" in part.lower() or "pozornica" in part.lower() or "sala" in part.lower())
                                and len(part) < 60):
                            location = f"{part}, Kulturni centar Osijek"
                            break
                    break

            # Slika
            image_url = None
            img = soup.select_one("img[src*='/uploads/images/event/']")
            if img:
                src = img.get("src", "")
                image_url = f"{BASE_URL}{src}" if src.startswith("/") else src

            # Opis — iz <p> koji nisu navigacija
            description_parts = []
            for p in soup.select("main p, article p, .content p"):
                txt = p.get_text(strip=True)
                if len(txt) > 40 and "sati" not in txt[:20]:
                    description_parts.append(txt)
            description = " ".join(description_parts[:3])[:2000]
            if not description:
                description = title

            uid = f"kc_{candidate['slug']}"
            doc_id = self.make_doc_id(uid)
            category = self.detect_category(title, description)
            date_text = self.format_date_text(start_dt, None)

            return {
                "id": doc_id,
                "title": title,
                "start_date": self.to_iso_date(start_dt),
                "end_date": self.to_iso_date(start_dt),
                "date_text": date_text,
                "location": location,
                "short_description": self.short_description(description or title),
                "description": description,
                "category": category,
                "source": self.source_label,
                "source_url": candidate["url"],
                "image_url": image_url,
                "is_active": True,
            }

        except Exception as e:
            print(f"[{self.source_label}] Parse error ({candidate['slug']}): {e}")
            return None
