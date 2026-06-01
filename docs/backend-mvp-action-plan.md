# Backend MVP – Kvalitetni Akcijski Plan (sa rezervom)

**Cilj:**  
Pripremiti backend na razini koja omogućuje izradu **Flutter aplikacije najviše moguće kvalitete** bez kasnijih većih iznenađenja i povrataka na backend.

**Filozofija plana:**
- "Što prije, ali ne na uštrb kvalitete"
- Ugrađena rezerva za kvalitetu, testiranje i male neočekivane probleme
- Fokus na ono što stvarno blokira visokokvalitetan Flutter razvoj

**Pretpostavke:**
- Radiš 10+ sati dnevno
- Prvo želimo zaključiti API Contract + Backend spremnost prije nego kreneš pisati Flutter kod
- Želimo malu, ali realnu rezervu za kvalitetu

---

## 1. Pregled faza (preporučeni redoslijed)

| Faza | Naziv                              | Trajanje (sa rezervom) | Cilj |
|------|------------------------------------|------------------------|------|
| 0    | Zaključivanje API Contracta        | 2–3 dana               | Imati jasan, stabilan ugovor |
| 1    | Kritična stabilnost (MUST)         | 5–7 dana               | Streaming, error handling, logging, auth |
| 2    | Visoka prioriteta + dokumentacija  | 4–6 dana               | Poliranje + spremnost za Flutter |
| -    | **Ukupno**                         | **11–16 dana**         | Backend spreman za kvalitetan Flutter start |

---

## 2. Detaljan plan po fazama

### Faza 0: Zaključivanje API Contracta (2–3 dana)

**Cilj:** Imati finalni, pregledani i prihvaćeni `mobile-mvp-api-contract.md`

**Zadaci:**
- [ ] Dovršiti sve preostale dijelove ugovora (streaming specifikacija, error catalog, token best practices, versioning)
- [ ] Pregledati ugovor zajedno (ti + ja)
- [ ] Zaključiti i označiti kao v1.0

**Rezultat faze:** Zamrznut API ugovor koji možemo koristiti kao temelj za Flutter razvoj.

---

### Faza 1: Kritična stabilnost (5–7 dana)

**Cilj:** Backend mora biti dovoljno stabilan i predvidiv da neće rušiti kvalitetu Flutter aplikacije.

**Prioritetni zadaci (po važnosti):**

1. **Streaming Chat stabilnost** (najveći prioritet)
   - Implementirati i testirati jasne error događaje tijekom streama
   - Definirati i dokumentirati ponašanje kod prekida LLM/tool poziva
   - Testirati reconnect scenarije s klijentske strane (u dogovoru s tobom)

2. **Error Handling**
   - Osigurati da svi endpointi (uključujući streaming) vraćaju greške u dogovorenom formatu
   - Ukloniti raw exceptione iz produkcijskih odgovora
   - Pripremiti korisniku prijateljske poruke na hrvatskom za najčešće slučajeve

3. **Logging & Vidljivost grešaka**
   - Osigurati da su svi važni događaji (posebno greške u chatu) dobro logirani
   - Imati pouzdan i brz način dohvaćanja tracebacka u produkciji (npr. `/debug/last-crash` ili bolje rješenje)
   - Testirati da se greške tijekom streaminga jasno vide u logovima

4. **Autentifikacija & Sigurnost**
   - Potvrditi da rotacija + blacklist rade pouzdano nakon svakog većeg deploya
   - Potvrditi da logout stvarno poništava refresh token
   - Provjeriti da nema curenja osjetljivih podataka u error porukama

5. **Tehnički debt (kritični dio)**
   - Ukloniti `/debug/last-crash` (i slične) iz produkcije
   - Provjeriti da `init_db()` radi pouzdano na svakom startu containera

**Rezultat faze:** Backend je "siguran za korištenje" iz Flutter aplikacije bez velikih rizika po kvalitetu.

---

### Faza 2: Poliranje i spremnost za Flutter (4–6 dana)

**Cilj:** Backend je ne samo funkcionalan, nego i ugodan za rad s njim iz mobilne aplikacije.

**Zadaci:**
- [ ] Bolje rukovanje grešaka tijekom LLM i tool poziva (graceful degradation)
- [ ] Dodati retry mehanizam za LLM pozive (barem 1 retry)
- [ ] Ažurirati `mobile-api.md` da bude usklađena s finalnim API Contractom
- [ ] Ukloniti ili sakriti nepotrebne admin/debug stvari iz javne Swagger dokumentacije
- [ ] Pripremiti bolje poruke grešaka za česte slučajeve (npr. "xAI servis trenutno nije dostupan")
- [ ] Opcionalno: jednostavan način praćenja troška xAI API-ja po korisniku

**Rezultat faze:** Backend je "production-ready" za početak ozbiljnog Flutter razvoja.

---

## 3. Predloženi timeline (sa rezervom za kvalitetu)

| Tjedan | Fokus                              | Očekivani rezultat |
|--------|------------------------------------|--------------------|
| Tjedan 1 | Faza 0 + početak Faze 1           | Zaključen API Contract + napredak na streamingu i error handlingu |
| Tjedan 2 | Faza 1 (nastavak)                 | Većina kritičnih stavki gotova |
| Tjedan 3 | Faza 1 završetak + Faza 2         | Backend spreman za Flutter |
| Tjedan 4 | Buffer / sitnice + finalni pregled| Backend je "čist" i dokumentiran |

**Ukupno:** 3–4 tjedna sa ugrađenom rezervom za kvalitetu.

---

## 4. Preporuke

- **Ne žuri previše** kroz Fazu 1. Streaming chat i error handling su područja koja najviše utječu na dojam aplikacije.
- Nakon Faze 1 predlažem da napravimo kratak review (ti + ja) prije nego krenemo u Fazu 2.
- Kad završimo Fazu 2, backend bi trebao biti u stanju da možeš raditi Flutter bez čestih prekida zbog backend problema.

---

**Sljedeći korak:**

Želiš li da sada:
1. Napravim **detaljan tjedni plan** (npr. što raditi od ponedjeljka do petka u sljedeća 3–4 tjedna)?
2. Ili prvo da ti dam prioritetnu listu zadataka iz ovog plana (sa oznakama što je najhitnije)?

Reci mi kako želiš nastaviti.