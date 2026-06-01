# Backend MVP – Detaljan Tjedni Plan (Kvalitetna varijanta)

**Cilj plana:**  
Pripremiti backend na razini koja omogućuje izradu Flutter aplikacije **najviše moguće kvalitete**, uz ugrađenu rezervu za kvalitetu, testiranje i male neočekivane probleme.

**Pretpostavke:**
- Radiš 10+ sati dnevno
- Želiš kvalitetu ispred brzine, ali ideš jako agresivno
- Prvo želimo dovršiti API Contract + Backend spremnost prije nego kreneš pisati Flutter kod

**Ukupno trajanje:** 3.5 – 4 tjedna (sa rezervom)

---

## Tjedan 1: Zaključivanje API Contracta + Početak kritičnih popravaka

**Fokus:** Dovesti API ugovor do visoke razine + početi najvažnije backend ispravke.

### Dani 1–3: API Contract
- **Dan 1:** Dovršiti preostale dijelove `mobile-mvp-api-contract.md` (detaljna streaming specifikacija, error catalog, token best practices, versioning)
- **Dan 2:** Pregled ugovora + tvoje primjedbe + finalne dorade
- **Dan 3:** Zaključiti i označiti ugovor kao v1.0 (zamrznuti)

**Kraj Tjedna 1 cilj:** API Contract je zaključan i odobren.

### Dani 4–7: Početak Faze 1 (Kritični popravci)

**Glavni fokus:**
- Početi rad na **streaming chat stabilnosti** (jasni error događaji tijekom streama, ponašanje kod prekida LLM/tool poziva)
- Početi rad na **konzistentnom error formatu** na svim endpointima
- Početi rad na **boljem logovanju** grešaka (posebno tijekom chat streama)

**Sporedni fokus:**
- Ukloniti prve debug stvari iz produkcije (npr. `/debug/last-crash`)
- Provjeriti trenutno stanje token rotacije + blacklista u produkciji

**Kraj Tjedna 1 očekivano stanje:**
- API Contract zaključan
- Početni napredak na najkritičnijim područjima (streaming + error handling + logging)

---

## Tjedan 2: Glavni dio Faze 1 – Kritična stabilnost

**Fokus:** Najvažniji dio plana – streaming chat + error handling + logging.

### Dani 8–14:

**Prioritet 1 (glavni fokus – najveći dio vremena):**
- Streaming chat – implementacija i testiranje jasnih error događaja tijekom streama
- Definiranje i implementacija ponašanja kod prekida LLM/tool poziva tijekom odgovora
- Testiranje reconnect scenarija (u suradnji s tobom)

**Prioritet 2:**
- Osigurati da **svi endpointi** (uključujući streaming) vraćaju greške u dogovorenom formatu
- Ukloniti raw exceptione iz produkcijskih odgovora
- Pripremiti korisniku prijateljske poruke grešaka

**Prioritet 3:**
- Poboljšati logovanje grešaka tijekom streaminga
- Osigurati da postoji pouzdan i brz način dohvaćanja tracebacka u produkciji

**Kraj Tjedna 2 cilj:**
- Većina kritičnih stavki iz Faze 1 je implementirana i testirana
- Streaming chat je značajno stabilniji i predvidiviji

---

## Tjedan 3: Završetak Faze 1 + Početak Faze 2

**Fokus:** Dovršiti kritične stvari + krenuti s poliranjem i dokumentacijom.

### Dani 15–21:

**Prioriteti:**
- Dovršiti preostale kritične stavke iz Faze 1 (ako ih je još)
- Potvrditi da rotacija + blacklist + logout rade pouzdano u produkciji
- Početi rad na visokim prioritetima:
  - Bolje rukovanje grešaka tijekom LLM/tool poziva (graceful degradation)
  - Dodati retry mehanizam za LLM pozive (barem 1 retry)
  - Ažurirati `mobile-api.md` u skladu s finalnim API Contractom
- Ukloniti preostale debug stvari iz produkcije

**Kraj Tjedna 3 cilj:**
- Svi kritični zadaci su gotovi
- Početak rada na poliranju i dokumentaciji

---

## Tjedan 4: Faza 2 + Buffer + Finalni pregled

**Fokus:** Poliranje, dokumentacija i finalna provjera spremnosti za Flutter.

### Dani 22–28 (sa rezervom):

- Dovršiti visoke prioritete iz Faze 2
- Bolje poruke grešaka za česte slučajeve (npr. "xAI servis trenutno nije dostupan")
- Priprema jednostavnog načina praćenja troška xAI API-ja po korisniku (opcionalno)
- Finalni pregled backend spremnosti prema checklistu
- Kratki review s tobom (da li je backend dovoljno stabilan za početak Fluttera)

**Kraj Tjedna 4 cilj:**
- Backend je spreman za početak ozbiljnog Flutter razvoja
- Postoji jasna potvrda da možemo krenuti s arhitekturom i projekt setupom

---

## Ukupni timeline (sa rezervom za kvalitetu)

| Tjedan     | Fokus                                      | Očekivani rezultat |
|------------|--------------------------------------------|--------------------|
| Tjedan 1   | API Contract + početak Faze 1              | Zaključen ugovor + napredak na najkritičnijim područjima |
| Tjedan 2   | Glavni dio Faze 1                          | Većina kritičnih stavki gotova |
| Tjedan 3   | Završetak Faze 1 + početak Faze 2          | Kritični dio gotov + početak poliranja |
| Tjedan 4   | Faza 2 + buffer + finalni pregled          | Backend spreman za Flutter |

**Ukupno:** 3.5 – 4 tjedna sa ugrađenom rezervom za kvalitetu.

---

## Preporuke

- **Ne žuri previše** kroz Tjedan 2. Streaming chat i error handling su područja koja najviše utječu na dojam aplikacije.
- Nakon Tjedna 2 predlažem kratak review (ti + ja) prije nego krenemo dalje.
- Nakon završetka ovog plana, backend bi trebao biti u stanju da možeš raditi Flutter bez čestih prekida zbog backend problema.

---

**Sljedeći korak:**

Želiš li da sada napravim **još detaljniju dnevnu verziju** ovog plana (npr. što raditi od ponedjeljka do petka u svakom tjednu), ili ti je ova tjedna razina dovoljno detaljna za početak?