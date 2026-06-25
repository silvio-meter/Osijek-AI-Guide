"""
Scraper za Turističku zajednicu grada Osijeka — text-based kalendar manifestacija.
URL: https://www.tzosijek.hr/kalendar-manifestacija-2026-1485
"""

import re
import requests
from datetime import date, datetime
from dateutil import tz
from bs4 import BeautifulSoup

from base_scraper import BaseScraper

CALENDAR_URL = "https://www.tzosijek.hr/kalendar-manifestacija-2026-1485"
LOCAL_TZ = tz.gettz("Europe/Zagreb")
HEADERS = {"User-Agent": "LegaBot/1.0"}

HR_MONTHS_NOM = {
    "SIJEČANJ": 1, "VELJAČA": 2, "OŽUJAK": 3, "TRAVANJ": 4,
    "SVIBANJ": 5, "LIPANJ": 6, "SRPANJ": 7, "KOLOVOZ": 8,
    "RUJAN": 9, "LISTOPAD": 10, "STUDENI": 11, "PROSINAC": 12,
}

# "27.06.2026." ili "25. – 28.06.2026." ili "17.6. - 18.7.2026."
DATE_RE = re.compile(
    r"(\d{1,2})[.\s]+"        # start day
    r"(?:–|-|do\s+\d{1,2}[.\s]+)?"  # optional range separator
    r"(\d{1,2})\."            # month
    r"(\d{4})\."              # year
)

DATE_RANGE_RE = re.compile(
    r"(\d{1,2})[.\s]*(?:–|-)\s*"   # start day + separator
    r"(\d{1,2})[.\s]+"              # end day
    r"(\d{1,2})\."                  # month
    r"(\d{4})\."                    # year
)

# "17.6. - 18.7.2026." — cross-month range
CROSS_MONTH_RE = re.compile(
    r"(\d{1,2})\.(\d{1,2})\."      # start day.month.
    r"\s*[-–]\s*"
    r"(\d{1,2})\.(\d{1,2})\.(\d{4})\."  # end day.month.year.
)

HASHTAG_TO_CATEGORY = {
    "glazba": "glazba", "koncert": "glazba", "kocerti": "glazba",
    "plesovi": "kultura", "ples": "kultura", "kazaliste": "kultura",
    "art": "kultura", "umjetnost": "kultura", "izlozba": "kultura",
    "gastro": "hrana", "enogastro": "hrana", "vino": "hrana", "sajam": "hrana",
    "priroda": "priroda", "biciklizam": "priroda", "nordic": "priroda",
}


class TzOsijekScraper(BaseScraper):
    source_key = "tzosijek"
    source_label = "TZ Osijek"

    def scrape(self) -> list[dict]:
        print(f"[{self.source_label}] Fetching calendar...")
        try:
            resp = requests.get(CALENDAR_URL, timeout=15, headers=HEADERS)
            resp.raise_for_status()
        except Exception as e:
            print(f"[{self.source_label}] Fetch failed: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        content = soup.select_one(".postcontent")
        if not content:
            print(f"[{self.source_label}] .postcontent not found")
            return []

        lines = [l.strip() for l in content.get_text(separator="\n").split("\n")]
        events = self._parse_lines(lines)

        today = date.today()
        upcoming = [e for e in events if e["_end_date_obj"] >= today]
        for e in upcoming:
            del e["_end_date_obj"]

        print(f"[{self.source_label}] Parsed {len(upcoming)} upcoming events (from {len(events)} total)")
        return upcoming

    def _parse_lines(self, lines: list[str]) -> list[dict]:
        events = []
        current_month = 0
        current_year = 2026
        i = 0

        while i < len(lines):
            line = lines[i]
            if not line:
                i += 1
                continue

            # Month header: "LIPANJ 2026."
            month_match = None
            for name, num in HR_MONTHS_NOM.items():
                if name in line.upper() and "2026" in line:
                    month_match = num
                    break
            if month_match:
                current_month = month_match
                i += 1
                continue

            # Date line
            parsed = self._parse_date_line(line, current_month, current_year)
            if parsed is None or current_month == 0:
                i += 1
                continue

            start_date, end_date = parsed

            # Collect remaining event fields (title, optional location, website(s), hashtags)
            i += 1
            title = ""
            location_hint = ""
            websites = []
            hashtags = []

            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                # Stop at next date line or month header
                if self._parse_date_line(next_line, current_month, current_year) is not None:
                    break
                if any(name in next_line.upper() for name in HR_MONTHS_NOM):
                    break
                if next_line.startswith("*"):  # disclaimer note
                    i += 1
                    continue

                if next_line.startswith("#"):
                    hashtags = [h.lstrip("#") for h in next_line.split()]
                elif next_line.startswith("http") or (next_line.startswith("www.") and "." in next_line):
                    websites.append(next_line)
                elif next_line.startswith("(") and next_line.endswith(")"):
                    location_hint = next_line[1:-1]
                elif not title:
                    title = next_line
                i += 1

            if not title:
                continue

            title = self.clean_text(title)
            category = self._category_from_hashtags(hashtags) or self.detect_category(title)
            date_text = self._format_tz_date(start_date, end_date)
            location = location_hint or "Osijek"
            source_url = websites[0] if websites else CALENDAR_URL
            uid = f"tz_{title}_{start_date.isoformat()}"
            doc_id = self.make_doc_id(uid)

            start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=LOCAL_TZ)

            events.append({
                "id": doc_id,
                "title": title,
                "start_date": self.to_iso_date(start_dt),
                "end_date": end_date.isoformat(),
                "date_text": date_text,
                "location": location,
                "short_description": f"{title} — {date_text}",
                "description": title,
                "category": category,
                "source": self.source_label,
                "source_url": source_url,
                "image_url": None,
                "is_active": True,
                "_end_date_obj": end_date,  # temp, removed before returning
            })

        return events

    def _parse_date_line(self, line: str, current_month: int, year: int):
        """
        Vraća (start_date, end_date) ili None.
        Podržava:
          27.06.2026.        → single day
          25. – 28.06.2026.  → same-month range
          17.6. - 18.7.2026. → cross-month range
        """
        # Cross-month: "17.6. - 18.7.2026."
        m = CROSS_MONTH_RE.match(line)
        if m:
            try:
                start = date(int(m.group(5)), int(m.group(2)), int(m.group(1)))
                end = date(int(m.group(5)), int(m.group(4)), int(m.group(3)))
                return start, end
            except ValueError:
                return None

        # Same-month range: "25. – 28.06.2026."
        m = DATE_RANGE_RE.match(line)
        if m:
            try:
                start = date(int(m.group(4)), int(m.group(3)), int(m.group(1)))
                end = date(int(m.group(4)), int(m.group(3)), int(m.group(2)))
                return start, end
            except ValueError:
                return None

        # Single date: "27.06.2026."
        m = DATE_RE.match(line)
        if m:
            try:
                d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                return d, d
            except ValueError:
                return None

        return None

    def _category_from_hashtags(self, hashtags: list[str]) -> str | None:
        for tag in hashtags:
            for key, cat in HASHTAG_TO_CATEGORY.items():
                if key in tag.lower():
                    return cat
        return None

    def _format_tz_date(self, start: date, end: date) -> str:
        months = [
            "", "siječnja", "veljače", "ožujka", "travnja", "svibnja", "lipnja",
            "srpnja", "kolovoza", "rujna", "listopada", "studenog", "prosinca",
        ]
        if start == end:
            return f"{start.day}. {months[start.month]} {start.year}."
        if start.month == end.month:
            return f"{start.day}. – {end.day}. {months[start.month]} {start.year}."
        return f"{start.day}. {months[start.month]} – {end.day}. {months[end.month]} {end.year}."
