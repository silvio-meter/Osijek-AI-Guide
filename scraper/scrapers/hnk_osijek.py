"""
Scraper za HNK Osijek — HTML scraping rasporeda.
URL: https://hnk-osijek.hr/raspored/
"""

import re
import requests
from datetime import datetime
from dateutil import tz
from bs4 import BeautifulSoup

from base_scraper import BaseScraper

BASE_URL = "https://hnk-osijek.hr"
SCHEDULE_URLS = [
    f"{BASE_URL}/raspored/",
    f"{BASE_URL}/raspored?schedule_id=17",  # Dramski
    f"{BASE_URL}/raspored?schedule_id=18",  # Glazbeni
    f"{BASE_URL}/raspored?schedule_id=19",  # Ostali
]
LOCAL_TZ = tz.gettz("Europe/Zagreb")

HR_MONTH_NAMES = {
    "siječnja": 1, "veljače": 2, "ožujka": 3, "travnja": 4,
    "svibnja": 5, "lipnja": 6, "srpnja": 7, "kolovoza": 8,
    "rujna": 9, "listopada": 10, "studenog": 11, "prosinca": 12,
}

HEADERS = {"User-Agent": "LegaBot/1.0"}


class HnkOsijekScraper(BaseScraper):
    source_key = "hnk_osijek"
    source_label = "HNK Osijek"

    def scrape(self) -> list[dict]:
        print(f"[{self.source_label}] Fetching schedule pages...")
        seen_ids = set()
        events = []

        for url in SCHEDULE_URLS:
            page_events = self._fetch_page(url, seen_ids)
            events.extend(page_events)

        print(f"[{self.source_label}] Parsed {len(events)} events")
        return events

    def _fetch_page(self, url: str, seen_ids: set) -> list[dict]:
        try:
            resp = requests.get(url, timeout=15, headers=HEADERS)
            resp.raise_for_status()
        except Exception as e:
            print(f"[{self.source_label}] Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select(".schedule__item")
        results = []

        for item in items:
            event = self._parse_item(item)
            if event and event["id"] not in seen_ids:
                seen_ids.add(event["id"])
                results.append(event)

        return results

    def _parse_item(self, item) -> dict | None:
        try:
            title_el = item.select_one(".schedule__info__title")
            date_el = item.select_one(".schedule__date__full-date")
            daytime_el = item.select_one(".schedule__date__day-and-time")
            author_el = item.select_one(".schedule__info__author")
            genre_el = item.select_one(".schedule__info__genre")
            link_el = item.select_one(".schedule__buttons a")
            img_el = item.select_one(".image-container")

            title = self.clean_text(title_el.get_text() if title_el else "")
            if not title:
                return None

            date_text_raw = date_el.get_text(strip=True) if date_el else ""
            daytime_raw = daytime_el.get_text(strip=True) if daytime_el else ""

            start_dt = self._parse_date(date_text_raw, daytime_raw)
            if start_dt is None:
                return None

            author = self.clean_text(author_el.get_text() if author_el else "")
            genre = self.clean_text(genre_el.get_text() if genre_el else "")
            source_url = link_el["href"] if link_el and link_el.get("href") else ""
            image_url = self._extract_bg_image(img_el)

            description = self._build_description(title, author, genre)
            uid = f"hnk_{title}_{start_dt.strftime('%Y%m%d%H%M')}"
            doc_id = self.make_doc_id(uid)

            # Genre iz HNK-a mapiramo na naše kategorije
            category = self._map_genre(genre, title)
            date_display = self.format_date_text(start_dt, None)

            return {
                "id": doc_id,
                "title": title,
                "start_date": self.to_iso_date(start_dt),
                "end_date": self.to_iso_date(start_dt),  # HNK su jednodnevni eventi
                "date_text": date_display,
                "location": "Hrvatsko narodno kazalište u Osijeku",
                "short_description": self.short_description(description),
                "description": description,
                "category": category,
                "source": self.source_label,
                "source_url": source_url,
                "image_url": image_url,
                "is_active": True,
            }

        except Exception as e:
            print(f"[{self.source_label}] Skipping item: {e}")
            return None

    def _parse_date(self, date_text: str, daytime: str) -> datetime | None:
        """
        Parsira "26. lipnja 2026." + "Petak, 20:00h" u datetime.
        """
        # Datum: "26. lipnja 2026."
        m = re.search(r"(\d{1,2})\.\s+(\w+)\s+(\d{4})", date_text)
        if not m:
            return None

        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        month = HR_MONTH_NAMES.get(month_name)
        if not month:
            return None

        # Vrijeme: "Petak, 20:00h" ili "Subota, 19:30h"
        hour, minute = 20, 0  # fallback
        tm = re.search(r"(\d{1,2}):(\d{2})h?", daytime)
        if tm:
            hour = int(tm.group(1))
            minute = int(tm.group(2))

        try:
            return datetime(year, month, day, hour, minute, tzinfo=LOCAL_TZ)
        except ValueError:
            return None

    def _extract_bg_image(self, el) -> str | None:
        if el is None:
            return None
        style = el.get("style", "")
        m = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", style)
        return m.group(1) if m else None

    def _build_description(self, title: str, author: str, genre: str) -> str:
        parts = []
        if author:
            parts.append(f"Autor: {author}")
        if genre:
            parts.append(f"Žanr: {genre}")
        parts.append(title)
        return " | ".join(parts)

    def _map_genre(self, genre: str, title: str) -> str:
        g = genre.lower()
        t = title.lower()
        if any(kw in g or kw in t for kw in ["opera", "oratorij", "glazb", "koncert", "mjuzikl"]):
            return "glazba"
        if any(kw in g or kw in t for kw in ["balet", "ples"]):
            return "kultura"
        # Drama, komedija, predstava → kultura
        return "kultura"
