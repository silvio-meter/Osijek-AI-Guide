"""
Firestore writer — batch upis događaja u kolekciju `events`.

Strategija:
- set() s merge=False → prepisuje cijeli dokument ako postoji (svježi podaci)
- Deterministički ID → isti event nikad nije duplikat
- Stari eventi (end_date ili start_date < danas) → is_active = False
"""

import os
import json
from datetime import date, datetime, timezone
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

COLLECTION = "events"


def init_firebase() -> firestore.client:
    """Inicijalizira Firebase Admin SDK iz env varijable ili service account fajla."""
    if firebase_admin._apps:
        return firestore.client()

    cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if cred_json:
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
    elif cred_path:
        cred = credentials.Certificate(cred_path)
    else:
        raise EnvironmentError(
            "Postavi FIREBASE_SERVICE_ACCOUNT_JSON (JSON string) "
            "ili GOOGLE_APPLICATION_CREDENTIALS (path) env varijablu."
        )

    firebase_admin.initialize_app(cred)
    return firestore.client()


def write_events(db, events: list[dict]) -> tuple[int, int]:
    """
    Batch upisuje događaje u Firestore.
    Vraća (written, skipped).
    Firestore batch limit je 500 operacija.
    """
    if not events:
        return 0, 0

    collection = db.collection(COLLECTION)
    written = 0
    skipped = 0
    now = datetime.now(tz=timezone.utc)

    # Procesiramo u batchevima od 400 (sigurnosni margin ispod 500 limita)
    BATCH_SIZE = 400
    for chunk_start in range(0, len(events), BATCH_SIZE):
        batch = db.batch()
        chunk = events[chunk_start:chunk_start + BATCH_SIZE]

        for event in chunk:
            doc_id = event.pop("id")  # ID se ne sprema kao polje
            if not doc_id:
                skipped += 1
                continue

            # Dodaj timestamp polja
            doc_ref = collection.document(doc_id)
            existing = doc_ref.get()

            payload = {
                **event,
                "scraped_at": now,
                "created_at": existing.get("created_at") if existing.exists else now,
            }

            batch.set(doc_ref, payload)  # merge=False → svježi podaci
            written += 1

        batch.commit()

    return written, skipped


def deactivate_past_events(db) -> int:
    """
    Postavlja is_active=False za događaje čiji je end_date (ili start_date) prošao.
    Pokretati nakon write_events().
    """
    today = date.today().isoformat()
    collection = db.collection(COLLECTION)

    # Dohvati sve događaje čiji start_date je u prošlosti.
    # Ne filtriramo is_active ovdje jer bi trebao composite index —
    # provjeru radimo u Pythonu ispod (end_date >= today = ostaje aktivan).
    stale_docs = (
        collection
        .where(filter=FieldFilter("start_date", "<", today))
        .stream()
    )

    batch = db.batch()
    count = 0

    for doc in stale_docs:
        data = doc.to_dict()
        end_date = data.get("end_date") or data.get("start_date", "")

        # Za multi-day evente — deaktiviraj tek kad prođe end_date
        if end_date and end_date >= today:
            continue

        batch.update(doc.reference, {"is_active": False})
        count += 1

        if count % 400 == 0:  # flush batch na svakih 400
            batch.commit()
            batch = db.batch()

    if count % 400 != 0:
        batch.commit()

    return count
