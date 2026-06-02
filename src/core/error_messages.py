"""
Centralizirani katalog korisniku prijateljskih poruka grešaka (na hrvatskom).

Ove poruke se koriste u custom exceptionima i globalnom error handleru.
Cilj: dosljedno, jasno i prijateljsko iskustvo u mobilnoj aplikaciji.

Kada dodaješ novu poruku, drži se ovih principa:
- Kratko i jasno
- Na hrvatskom (standardni jezik za MVP)
- Ne otkrivaj tehničke detalje korisniku
- Ponudi koristan savjet gdje je moguće
"""

from typing import Dict


# Glavni katalog poruka za najčešće greške (Sprint Day 1 - prošireno)
ERROR_MESSAGES: Dict[str, str] = {
    # === Autentifikacija ===
    "unauthorized": "Niste autentificirani. Molimo prijavite se ponovo.",
    "invalid_or_expired_token": "Vaša sesija je istekla ili je token nevažeći. Prijavite se ponovo.",
    "refresh_token_revoked": "Vaša sesija je poništena (odjavljeni ste na drugom uređaju ili na drugom mjestu).",
    "forbidden": "Nemate dozvolu za ovu radnju. Ako mislite da je riječ o grešci, kontaktirajte podršku.",
    "account_inactive": "Vaš korisnički račun je privremeno deaktiviran. Kontaktirajte podršku.",

    # === Validacija ===
    "validation_error": "Uneseni podaci nisu ispravni. Provjerite unos (npr. duljinu poruke) i pokušajte ponovo.",
    "invalid_email": "Molimo unesite ispravnu email adresu.",
    "weak_password": "Lozinka mora imati najmanje 8 znakova.",
    "invalid_rating": "Ocjena mora biti 1 (like) ili -1 (dislike).",
    "message_too_long": "Vaša poruka je predugačka. Molimo skratite je i pokušajte ponovo.",
    "message_empty": "Poruka ne može biti prazna.",

    # === Rate limiting ===
    "rate_limit_exceeded": "Previše zahtjeva u kratkom vremenu. Molimo pričekajte trenutak prije sljedećeg pokušaja.",

    # === Chat / AI ===
    "chat_stream_interrupted": "Odgovor je prekinut zbog problema s vezom. Možete pokušati ponovo poslati poruku.",
    "tool_execution_error": "Došlo je do problema pri dohvaćanju aktualnih podataka. Pokušajte s drugim pitanjem ili kasnije.",
    "llm_error": "Trenutno ne možemo generirati odgovor. Molimo pokušajte ponovo za nekoliko trenutaka.",
    "llm_unavailable": "AI servis je trenutno nedostupan. Molimo pokušajte kasnije.",
    "no_relevant_data": "Nisam pronašao dovoljno relevantnih informacija za tvoje pitanje. Pokušaj ga formulirati malo drugačije.",
    "question_too_vague": "Tvoje pitanje je malo preopćenito. Možeš li ga malo precizirati?",
    "internal_server_error": "Došlo je do neočekivane greške. Naš tim je obaviješten i radi na rješenju.",

    # === Općenito ===
    "not_found": "Traženi podatak nije pronađen. Provjerite je li poveznica ili identifikator ispravan.",
    "conflict": "Došlo je do konflikta s postojećim podacima. Molimo osvježite aplikaciju i pokušajte ponovo.",
    "service_unavailable": "Servis trenutno nije dostupan. Molimo pokušajte kasnije ili provjerite internetsku vezu.",
    "timeout": "Zahtjev je trajao predugo. Molimo pokušajte ponovo ili provjerite internetsku vezu.",
}


def get_friendly_message(error_code: str, default: str = None) -> str:
    """
    Vraća prijateljsku poruku za dani error code.
    Ako poruka ne postoji, vraća default ili generičku poruku.
    """
    if error_code in ERROR_MESSAGES:
        return ERROR_MESSAGES[error_code]

    if default:
        return default

    return "Došlo je do neočekivane greške. Molimo pokušajte ponovo ili kasnije."
