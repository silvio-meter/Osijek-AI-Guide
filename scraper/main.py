#!/usr/bin/env python3
"""
Lega Event Scraper — orchestrator.

Pokretanje:
    export FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
    python main.py

Na Railwayu: ovaj fajl se pokreće kao cron job (0 6,18 * * *).
"""

import sys
import traceback
from datetime import datetime

# Dodaj scraper root u Python path (za relative imports)
sys.path.insert(0, ".")
sys.path.insert(0, "./scrapers")

from firestore_writer import init_firebase, write_events, deactivate_past_events
from scrapers.osijek_in import OsijekInScraper
from scrapers.hnk_osijek import HnkOsijekScraper
from scrapers.kulturni_centar import KulturniCentarScraper
from scrapers.tzosijek import TzOsijekScraper

# ── Registrirani scraperi ────────────────────────────────────────────────────
SCRAPERS = [
    OsijekInScraper(),
    HnkOsijekScraper(),
    KulturniCentarScraper(),
    TzOsijekScraper(),
]


def main():
    start = datetime.now()
    print(f"=== Lega Event Scraper — {start.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    # Inicijalizacija Firestorea
    try:
        db = init_firebase()
        print("Firebase: OK\n")
    except Exception as e:
        print(f"Firebase init FAILED: {e}")
        sys.exit(1)

    total_written = 0
    total_skipped = 0
    failed_sources = []

    for scraper in SCRAPERS:
        print(f"── {scraper.source_label} ──────────────────────")
        try:
            events = scraper.scrape()

            if not events:
                print(f"  ⚠ Nema događaja.")
                continue

            written, skipped = write_events(db, events)
            total_written += written
            total_skipped += skipped
            print(f"  ✓ Upisano: {written}  |  Preskočeno: {skipped}")

        except Exception as e:
            failed_sources.append(scraper.source_label)
            print(f"  ✗ GREŠKA: {e}")
            traceback.print_exc()

        print()

    # Deaktiviraj prošle događaje
    print("── Deaktivacija prošlih događaja ──────────────")
    try:
        deactivated = deactivate_past_events(db)
        print(f"  ✓ Deaktivirano: {deactivated} dokumenata")
    except Exception as e:
        print(f"  ✗ Deaktivacija GREŠKA: {e}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n=== Završeno za {elapsed:.1f}s ===")
    print(f"    Upisano ukupno: {total_written}")
    print(f"    Preskočeno:     {total_skipped}")

    if failed_sources:
        print(f"    Neuspješni izvori: {', '.join(failed_sources)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
