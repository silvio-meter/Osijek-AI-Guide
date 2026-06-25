"""
Base scraper — zajednički utilities za sve Lega event scrapere.
"""

import hashlib
import re
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional


# ── Kategorije (mora se podudarati s filter chipovima u Flutter UI-u) ─────────
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("glazba",  ["koncert", "jazz", "glazb", "festival", "band", "orkestar",
                 "filharmonij", "opera", "pjevačk", "tambur", "rock", "pop"]),
    ("kultura", ["izložb", "muzej", "galerij", "kazalište", "teatar", "film",
                 "predstav", "književn", "kulturni", "arhiv", "baština",
                 "radionica", "lutkarski", "mjuzikl"]),
    ("hrana",   ["gastro", "hrana", "restoran", "fiš", "vino", "sajam",
                 "kulinars", "food", "picerij"]),
    ("priroda", ["šetnja", "drava", "park", "izlet", "priroda", "bicikl",
                 "hiking", "trekking", "eko"]),
]

HR_MONTHS = [
    "", "siječnja", "veljače", "ožujka", "travnja", "svibnja", "lipnja",
    "srpnja", "kolovoza", "rujna", "listopada", "studenog", "prosinca",
]
HR_DAYS = ["Ponedjeljak", "Utorak", "Srijeda", "Četvrtak", "Petak", "Subota", "Nedjelja"]


class BaseScraper(ABC):
    """Apstraktni scraper. Svaki izvor implementira `scrape()` koji vraća list[dict]."""

    source_key: str  # npr. "osijek_in", "hnk_osijek"
    source_label: str  # npr. "osijek.in"

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Dohvati i parsiraj događaje. Vraća listu event dict-ova."""
        ...

    # ── Utilities ─────────────────────────────────────────────────────────────

    def make_doc_id(self, uid: str) -> str:
        """Deterministički Firestore document ID: {source_key}_{md5(uid)[:12]}"""
        h = hashlib.md5(uid.encode()).hexdigest()[:12]
        return f"{self.source_key}_{h}"

    def detect_category(self, *texts: Optional[str]) -> str:
        combined = " ".join(t.lower() for t in texts if t).strip()
        for category, keywords in CATEGORY_RULES:
            if any(kw in combined for kw in keywords):
                return category
        return "ostalo"

    def format_date_text(self, start: datetime, end: Optional[datetime] = None) -> str:
        """
        Formatira datum za prikaz u UI-u.
        Primjeri:
          Subota, 5. srpnja u 20:00
          Subota, 5. srpnja – Nedjelja, 6. srpnja  (multi-day bez vremena)
          5. srpnja – 30. kolovoza 2026            (dugi period)
        """
        day_name = HR_DAYS[start.weekday()]
        month = HR_MONTHS[start.month]
        has_time = start.hour != 0 or start.minute != 0

        if end is None or (end.date() == start.date()):
            base = f"{day_name}, {start.day}. {month}"
            if has_time:
                return f"{base} u {start.strftime('%H:%M')}"
            return base

        # Multi-day event
        days_span = (end.date() - start.date()).days
        if days_span <= 7:
            end_day = HR_DAYS[end.weekday()]
            end_month = HR_MONTHS[end.month]
            start_str = f"{day_name}, {start.day}. {month}"
            end_str = f"{end_day}, {end.day}. {end_month}"
            if has_time:
                start_str += f" u {start.strftime('%H:%M')}"
            return f"{start_str} – {end_str}"

        # Dugotrajni event (izložbe, festivali)
        end_month = HR_MONTHS[end.month]
        return f"{start.day}. {month} – {end.day}. {end_month} {end.year}"

    def clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def short_description(self, description: str, max_chars: int = 150) -> str:
        """Kraća verzija opisa za event card."""
        desc = self.clean_text(description)
        if len(desc) <= max_chars:
            return desc
        cut = desc[:max_chars].rsplit(" ", 1)[0]
        return cut.rstrip(".,;:") + "…"

    def to_iso_date(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")
