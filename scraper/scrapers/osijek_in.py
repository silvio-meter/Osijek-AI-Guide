"""
Scraper za osijek.in — koristi iCal feed (The Events Calendar WordPress plugin).
Feed URL: https://osijek.in/dogadaji/?ical=1
"""

import re
import requests
from datetime import datetime, timezone
from icalendar import Calendar
from dateutil import tz

from base_scraper import BaseScraper

ICAL_URL = "https://osijek.in/dogadaji/?ical=1&tribe_display=list"
LOCAL_TZ = tz.gettz("Europe/Zagreb")


class OsijekInScraper(BaseScraper):
    source_key = "osijek_in"
    source_label = "osijek.in"

    def scrape(self) -> list[dict]:
        print(f"[{self.source_label}] Fetching iCal feed...")
        response = requests.get(ICAL_URL, timeout=20, headers={"User-Agent": "LegaBot/1.0"})
        response.raise_for_status()

        cal = Calendar.from_ical(response.content)
        events = []

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            event = self._parse_component(component)
            if event:
                events.append(event)

        print(f"[{self.source_label}] Parsed {len(events)} events")
        return events

    def _parse_component(self, component) -> dict | None:
        try:
            uid = str(component.get("UID", ""))
            title = self.clean_text(str(component.get("SUMMARY", "")))
            if not title or not uid:
                return None

            # Datumi — iCal može vratiti date ili datetime
            dtstart = component.get("DTSTART").dt
            dtend_raw = component.get("DTEND")
            dtend = dtend_raw.dt if dtend_raw else None

            # Normalizacija na datetime s lokalnom vremenskom zonom
            if isinstance(dtstart, datetime):
                if dtstart.tzinfo is None:
                    dtstart = dtstart.replace(tzinfo=LOCAL_TZ)
                start_dt = dtstart.astimezone(LOCAL_TZ)
            else:
                # date objekt (all-day event) — tretiraj kao ponoć
                start_dt = datetime(dtstart.year, dtstart.month, dtstart.day,
                                    0, 0, tzinfo=LOCAL_TZ)

            end_dt = None
            if dtend is not None:
                if isinstance(dtend, datetime):
                    if dtend.tzinfo is None:
                        dtend = dtend.replace(tzinfo=LOCAL_TZ)
                    end_dt = dtend.astimezone(LOCAL_TZ)
                else:
                    end_dt = datetime(dtend.year, dtend.month, dtend.day,
                                      23, 59, tzinfo=LOCAL_TZ)

            description_raw = str(component.get("DESCRIPTION", ""))
            description = self._clean_ical_text(description_raw)
            location = self.clean_text(str(component.get("LOCATION", "")))
            location = self._clean_location(location)
            source_url = str(component.get("URL", ""))
            image_url = self._extract_image(component)

            category = self.detect_category(title, description)
            date_text = self.format_date_text(start_dt, end_dt)
            doc_id = self.make_doc_id(uid)

            return {
                "id": doc_id,
                "title": title,
                "start_date": self.to_iso_date(start_dt),
                "end_date": self.to_iso_date(end_dt) if end_dt else None,
                "date_text": date_text,
                "location": location,
                "short_description": self.short_description(description),
                "description": description[:2000],  # Firestore limit
                "category": category,
                "source": self.source_label,
                "source_url": source_url,
                "image_url": image_url,
                "is_active": True,
            }

        except Exception as e:
            title_raw = str(component.get("SUMMARY", "?"))
            print(f"[{self.source_label}] Skipping event '{title_raw}': {e}")
            return None

    def _clean_ical_text(self, text: str) -> str:
        """Uklanja iCal escape znakove i HTML ostatke."""
        text = text.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";")
        text = re.sub(r"<[^>]+>", "", text)  # ukloni HTML tagove
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _clean_location(self, location: str) -> str:
        """Uklanja duplikate i poštanski broj iz iCal lokacije."""
        # iCal lokacija često izgleda: "Muzej Slavonije, Muzej Slavonije, Osijek, Hrvatska, 31400, Croatia"
        parts = [p.strip() for p in location.split(",")]
        seen = set()
        clean_parts = []
        for p in parts:
            # Preskoči duplikate, poštanske brojeve, nazive država
            normalized = p.lower().strip()
            is_country = (normalized in {"croatia", "hrvatska"}
                          or "local name" in normalized
                          or re.match(r"^\d{5}$", p.strip()))
            if p.strip() and normalized not in seen and not is_country:
                seen.add(normalized)
                clean_parts.append(p)
        return ", ".join(clean_parts[:3])  # Maksimalno 3 dijela

    def _extract_image(self, component) -> str | None:
        attach = component.get("ATTACH")
        if attach is None:
            return None
        url = str(attach)
        if url.startswith("http") and any(url.lower().endswith(ext)
                                          for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            return url
        return None
