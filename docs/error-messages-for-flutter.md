# Najčešće greške i poruke za Flutter aplikaciju

Ovaj dokument sadrži pregled najvažnijih error kodova koje backend vraća, zajedno s preporučenim ponašanjem u mobilnoj aplikaciji.

**Izvor istine:** `mobile-mvp-api-contract.md` (v1.0) + centralni katalog u `src/core/error_messages.py`.

## Format odgovora na grešku

```json
{
  "error": "string",      // machine-readable kod
  "message": "string",    // korisniku prijateljska poruka (hrvatski)
  "details": object | null
}
```

## Važni error kodovi i preporučeno ponašanje

| error_code                    | Kada se događa                                      | Preporučeno ponašanje u Flutteru                          | Poruka (primjer) |
|-------------------------------|-----------------------------------------------------|------------------------------------------------------------|------------------|
| `unauthorized`                | Nevažeći / istekao token                            | Pokušaj refresh tokena                                     | Niste autentificirani. Molimo prijavite se ponovo. |
| `refresh_token_revoked`       | Refresh token poništen (logout ili rotacija)        | Odjavi korisnika i prebaci na login screen                 | Vaša sesija je poništena (odjavljeni ste na drugom uređaju). |
| `validation_error`            | Neispravni podaci (uključujući predugu/ praznu poruku) | Prikaži `message` korisniku + omogući ispravak         | Vaša poruka je predugačka. Molimo skratite je... |
| `rate_limit_exceeded`         | Previše zahtjeva                                    | Prikaži poruku + poštuj `Retry-After` header ako postoji   | Previše zahtjeva u kratkom vremenu... |
| `tool_execution_error`        | Greška pri izvršavanju toolova                      | Prikaži poruku + omogući retry ili drugačije pitanje       | Došlo je do problema pri dohvaćanju aktualnih podataka... |
| `llm_error`                   | Privremeni problem s generiranjem odgovora          | Prikaži "Pokušaj ponovo za nekoliko trenutaka" + retry     | Trenutno ne možemo generirati odgovor... |
| `llm_unavailable`             | AI servis trenutno nedostupan                       | Prikaži poruku i onemogući chat privremeno                   | AI servis je trenutno nedostupan. Molimo pokušajte kasnije. |
| `chat_stream_interrupted`     | Prekid streama (disconnect / timeout / refresh)     | Prikaži da je odgovor prekinut + gumb "Pokušaj ponovo"     | Odgovor je prekinut zbog problema s vezom... |
| `no_relevant_data`            | Nema dovoljno podataka za pitanje                   | Prikaži poruku + predloži preciznije pitanje                 | Nisam pronašao dovoljno relevantnih informacija... |
| `internal_server_error`       | Neočekivana greška na serveru                       | Generička poruka + Retry gumb                              | Došlo je do neočekivane greške... |

## Preporučene poruke (iz kataloga)

Najčešće korištene poruke koje možeš direktno prikazati:

- **Preduga poruka:** "Vaša poruka je predugačka. Molimo skratite je i pokušajte ponovo."
- **Prazna poruka:** "Poruka ne može biti prazna."
- **Rate limit:** "Previše zahtjeva u kratkom vremenu. Molimo pričekajte trenutak prije sljedećeg pokušaja."
- **Tool greška:** "Došlo je do problema pri dohvaćanju aktualnih podataka. Pokušajte s drugim pitanjem ili kasnije."
- **AI nedostupan / LLM error:** "Trenutno ne možemo generirati odgovor. Molimo pokušajte ponovo za nekoliko trenutaka."
- **AI servis nedostupan:** "AI servis je trenutno nedostupan. Molimo pokušajte kasnije."
- **Prekinut stream:** "Odgovor je prekinut zbog problema s vezom. Možete pokušati ponovo poslati poruku."
- **Nema relevantnih podataka:** "Nisam pronašao dovoljno relevantnih informacija za tvoje pitanje. Pokušaj ga formulirati malo drugačije."

## Preporuke za implementaciju u Flutteru

1. Centraliziraj mapiranje `error_code` → UI poruka (ili koristi `message` direktno iz backend-a).
2. Za streaming: ako dobiješ error event unutar SSE streama, prekini stream i prikaži poruku + retry gumb.
3. Na 401 → automatski pokušaj refresh. Ako refresh vrati 401 → odmah odjavi korisnika.
4. Na 429 → prikaži poruku i poštuj `Retry-After` header ako postoji.
5. Koristi `performance` podatke iz historyja (kada budu dostupni) za prikaz "koliko je brzo Lega odgovarala".

---

Ovaj dokument možeš koristiti kao brzi reference za developere mobilne aplikacije.
