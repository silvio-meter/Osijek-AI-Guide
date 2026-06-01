# Backend MVP – Detaljan Dnevni Plan (Kvalitetna varijanta)

**Cilj:** Pripremiti backend na razini koja omogućuje izradu Flutter aplikacije **najviše moguće kvalitete**, uz ugrađenu rezervu.

**Pretpostavke:**
- 10+ sati dnevno
- Kvaliteta ispred brzine
- Prvo želimo dovršiti API Contract + Backend spremnost prije ozbiljnog Flutter razvoja

**Ukupno:** 20 radnih dana (4 tjedna) sa rezervom.

---

## Tjedan 1: Zaključivanje API Contracta + Početak kritičnih popravaka

### Dan 1 (Ponedjeljak)
- **Fokus:** API Contract – prva velika iteracija
- Detaljno napisati / proširiti sekcije:
  - Streaming Chat specifikacija (error događaji, reconnect, timeoutovi, disconnect scenariji)
  - Error Code Catalog (s preporučenim ponašanjem na klijentu)
  - Security & Token Best Practices (mobilna perspektiva)
  - API Versioning sekcija
- Napisati prve realne primjere za streaming error scenarije
- Poslati prvu verziju na review

**Kraj dana cilj:** Prva solidna verzija API Contracta spremna za feedback.

### Dan 2 (Utorak)
- **Fokus:** API Contract – iteracija na osnovu feedbacka
- Uključiti sve relevantne primjedbe
- Dodati nedostajuće primjere i edge caseove
- Započeti rad na backend strani streaming chat stabilnosti:
  - Definirati strukturu error događaja tijekom streama (`data: {"error": ...}`)
  - Početi implementaciju

**Kraj dana cilj:** API Contract blizu finalne verzije + početak implementacije error događaja.

### Dan 3 (Srijeda) ✅ ZAVRŠENO
- **Fokus:** Zaključivanje API Contracta + početak error handlinga
- ✅ Finalni pregled i zamrzavanje `mobile-mvp-api-contract.md` kao **v1.0** (Frozen)
- ✅ Početak konzistentnog error formata: dodan `ConflictException`, migrirani register/refresh u auth.py na custom exceptione + HR poruke, poboljšan http_exception_handler (409 + bolji fallback message), popravljen jedan raw 403 u user profilu
- ✅ Poboljšani logovi grešaka tijekom chat streama (svi phaseovi sada imaju `[CHAT][STREAM] ... | user_id=...` + preview poruke)

**Kraj dana cilj:** ✅ Postignut – API Contract zaključan + solidan napredak na error handlingu i logovanju (Faza 1 u tijeku).

### Dan 4 (Četvrtak) ✅ ZAVRŠENO
- **Fokus:** Streaming chat error handling + čišćenje + auth observability
- ✅ Popravljena preostala rupa u streaming error handlingu: `stream_direct()` u `/chat?stream=true` sada ima puni try/except + structured SSE error event (prije nije bio zaštićen)
- ✅ Početak uklanjanja debug endpointa iz produkcije: `/debug/last-crash` sada vraća 404 u produkciji (dostupan samo uz `TESTING=1` ili `ENABLE_DEBUG_ENDPOINTS=1`)
- ✅ Detaljan review token rotacije + blacklist logike (logika je ispravna)
- ✅ Dodani produkcijski logovi za login, refresh rotation (old jti revoked + new issued) i logout revocation – sada se sve ključne auth operacije vide u Railway logovima
- ✅ Poboljšana konzistentnost error kodova u streaming putovima

**Kraj dana cilj:** ✅ Postignut – značajan napredak na stabilnosti streama + početak čišćenja produkcije + vidljivost auth rotacije.

### Dan 5 (Petak) ✅ ZAVRŠENO (Buffer dan + Tjedan 1 review)
- **Fokus:** Uklanjanje raw exceptiona + početak prijateljskih poruka + pregled Tjedna 1
- ✅ Audit i uklanjanje većine preostalih raw HTTPException (events.py, points_of_interest.py, api.py feedback)
- ✅ Početak korisniku prijateljskih poruka na hrvatskom (NotFound, Conflict, Validation, bolji default u handleru)
- ✅ Značajno poboljšana konzistentnost error formata na većini endpointa
- ✅ Detaljan pregled napretka Tjedna 1 prema checklisti

**Kraj Tjedna 1 cilj:** ✅ Uglavnom postignut
- API Contract zaključan (v1.0 Frozen)
- Solidan napredak na streaming error handlingu, error formatu, logovanju i auth observability
- Početak čišćenja produkcije (debug endpointi)

---

## Tjedan 1 – Zaključak (Dani 1–5)

**Cilj tjedna:** Zaključiti API Contract + napraviti značajan početni napredak na najkritičnijim područjima Faze 1 (streaming stabilnost, error handling, logging, auth).

**Status:** ✅ **Postignut na visokoj razini kvalitete** (bez žurbe)

### Ključni rezultati Tjedna 1
- **API Contract** → `mobile-mvp-api-contract.md` zamrznut kao **v1.0** (Dan 3). Obvezujući dokument za Flutter MVP.
- **Streaming chat error handling** → Strukturirani error događaji (`data: {"error":..., "message":...}`) implementirani i ojačani na svim putovima (`/chat/stream` i `/chat?stream=true`). Svi generatori zaštićeni try/except + phase-specific logovi s `user_id`.
- **Error format konzistentnost** → Globalni handler + custom exceptioni (`NotFoundException`, `ConflictException`, `ValidationException`...). Većina raw `HTTPException` uklonjena iz auth, POI, events i feedback putova.
- **Observability** → Odlični logovi za chat stream greške i cijeli auth lifecycle (login → refresh rotacija → logout revocation). Spremno za brzi debug na Railwayu.
- **Produkcijska čistoća** → `/debug/last-crash` sada vraća 404 u produkciji (gated na `TESTING=1` ili `ENABLE_DEBUG_ENDPOINTS=1`).
- **Korisničke poruke** → Početak prijateljskih poruka na hrvatskom za najčešće greške.

### Napredak prema Checklisti (Kritični prioriteti)
| Područje                    | Status          | Napomena |
|-----------------------------|-----------------|----------|
| API Contract                | ✅ Zaključan    | v1.0 Frozen |
| Streaming error events      | ✅ Veliki napredak | Svi putovi zaštićeni |
| Error response format       | ✅ Veliki napredak | Većina endpointa čista |
| Auth rotacija + blacklist   | ✅ Verificirano + logovi | Potrebna produkcijska potvrda |
| Logging & crash visibility  | ✅ Jako dobro   | Phase + user_id logovi |
| Debug endpoint cleanup      | ✅ Početak      | Ključni endpoint sakriven |

### Preostali rizici / fokus Tjedna 2 (Faza 1)
- Graceful degradation + retry mehanizam za LLM i tool pozive
- Potpuno uklanjanje preostalih raw exceptiona
- Daljnje poboljšanje poruka grešaka za česte slučajeve
- Testiranje reconnect scenarija i ponašanja pri prekidu streama
- Potvrda da rotacija radi pouzdano nakon zadnjih deployeva

**Preporuka za Tjedan 2:** Nastaviti agresivno s Faza 1 (streaming stabilnost + error handling + retry). Kada većina kritičnih stavki bude gotova, napraviti kratki review prije prelaska na Flutter.

---

## Tjedan 2: Glavni dio Faze 1 – Kritična stabilnost

### Dan 6 (Ponedjeljak) ✅ ZAVRŠENO
- **Glavni fokus:** Streaming chat – error događaji tijekom streama + graceful degradation
- ✅ Uveden `sse_error()` helper za konzistentne SSE error događaje (DRY)
- ✅ Napravljeno konzistentno rukovanje tool grešaka u oba streaming endpointa (`/chat?stream=true` i `/chat/stream`)
- ✅ Kad tool padne tijekom streaminga → šalje se `tool_execution_error`, ne radi se finalni LLM call, pokušava se spasiti history
- ✅ Poboljšana graceful degradation i history saving u error/tool-failure slučajevima
- ✅ Svi SSE error yieldovi sada koriste helper (lakše održavanje)

### Dan 7 (Utorak) ✅ ZAVRŠENO
- **Fokus:** Streaming interruption handling + partial history saving
- ✅ Dodano `asyncio` cancellation handling u sve streaming generatore (`stream_real`, `stream_direct`, `stream_after_tools`)
- ✅ Jasno ponašanje na client disconnect / stream cancellation:
  - Logira se kao `[CHAT][STREAM] ... cancelled (client disconnect)`
  - Spasiti se partial generirani odgovor označen s ` [STREAM INTERRUPTED]`
- ✅ Preporučeni endpoint (`/chat/stream`) sada akumulira odgovor tijekom streama i spašava partial history čak i na prekidu
- ✅ Definirano i implementirano ponašanje za prekid streama tijekom LLM/tool poziva (graceful + vidljivo u historyju)

### Dan 8 (Srijeda) ✅ ZAVRŠENO
- **Fokus:** Konzistentan error format + priprema reconnect testiranja
- ✅ Veliki napredak na error consistency: `dependencies/auth.py` kompletno prebačeno na custom exceptions (UnauthorizedException / ForbiddenException) → svi protected endpointi sada imaju dosljedne HR poruke i error code-ove
- ✅ Dodatno čišćenje u auth routeru (register password validation)
- ✅ Pripremljeni detaljni reconnect test scenariji (u suradnji s tobom) na osnovu mehanizama iz Dana 7 (partial history + [STREAM INTERRUPTED] marker)

### Dan 9 (Četvurtak) ✅ ZAVRŠENO
- **Fokus:** Uklanjanje raw exceptiona + priprema prijateljskih poruka
- ✅ Audit: raw HTTPException gotovo potpuno eliminirani (samo gated `/debug/last-crash`)
- ✅ Kreiran `core/error_messages.py` – centralizirani katalog prijateljskih poruka na hrvatskom
- ✅ Poboljšani default poruke u UnauthorizedException, NotFoundException i ValidationException
- ✅ Globalni error handler integriran s katalogom poruka
- ✅ Početak sistematizacije poruka za najčešće scenarije (auth, rate limit, chat greške, validation)

### Dan 10 (Petak) ✅ ZAVRŠENO (Buffer + Tjedan 2 review)
- **Fokus:** Poboljšanje logovanja + traceback vidljivost + pregled Tjedna 2
- ✅ Dodan timing (duration) u sve streaming generatore + početni log za stream request
- ✅ Bolja struktura logova na uspjeh / grešku / prekid (s duration + length)
- ✅ Pregled traceback sustava: već vrlo robustan (forced multi-output + persistent file + gated endpoint)
- ✅ Detaljan pregled napretka Tjedna 2 / Faze 1

**Kraj Tjedna 2 cilj:** ✅ Uglavnom postignut
- Većina kritičnih stavki iz Faze 1 je implementirana i testirana
- Streaming chat je značajno stabilniji, predvidiviji i bolje logiran

---

## Tjedan 2 – Zaključak (Dani 6–10)

**Cilj tjedna:** Glavni dio Faze 1 – dubinsko ojačavanje streaming stabilnosti, error handlinga i observabilityja.

**Status:** ✅ **Postignut na visokoj razini**

### Ključni rezultati Tjedna 2
- Streaming error handling → Potpuna pokrivenost svih generatora + structured SSE errors.
- Graceful degradation → Tool failure → `tool_execution_error` + history save (konzistentno).
- Interruption handling → Client disconnect → partial history s `[STREAM INTERRUPTED]` + detaljni logovi.
- Error format → Ogroman napredak (auth dependencies prebačene na custom exceptions).
- Friendly messages → Kreiran centralizirani katalog + integracija.
- Logging & Tracebacks → Timing + duration + phase + user_id; vrlo robustan traceback sustav.

**Preporuka za Tjedan 3:** Završiti preostale dijelove Faze 1 (retry mehanizmi, dodatno poliranje) i napraviti kratki zajednički review.

---

## Tjedan 3: Završetak Faze 1 + Početak Faze 2

### Dan 11 (Ponedjeljak) ✅ ZAVRŠENO
- **Fokus:** Pouzdanost token rotacije + blacklist u produkciji
- ✅ Detaljan code review refresh rotation logic
- ✅ Poboljšana sigurnost rotacije: novi refresh token se prvo kreira i persistira, tek onda se stari poništava (manji rizik gubitka sesije)
- ✅ `revoke_refresh_token` sada idempotentan
- ✅ Pripremljen jasan **Production Verification Checklist** za testiranje rotacije, blacklist i logout nakon deploya
- ✅ Pregled preostalih Faza 1 stavki

### Dan 12 (Utorak) ✅ ZAVRŠENO
- **Fokus:** Graceful degradation + retry za LLM pozive
- ✅ Dodan `invoke_llm_with_retry` helper (1 retry + delay)
- ✅ Primijenjen na ključne LLM pozive: inicijalnu odluku (chain.invoke) i generiranje finalnog odgovora
- ✅ Poboljšana graceful degradation: čak i ako neki toolovi padnu, pokušava se generirati finalni LLM odgovor (umjesto hard errora)
- ✅ Bolje logiranje retry pokušaja i finalnih grešaka

### Dan 13 (Srijeda) ✅ ZAVRŠENO
- **Fokus:** Dokumentacija + cleanup produkcije
- ✅ `mobile-api.md` ažuriran i usklađen s `mobile-mvp-api-contract.md` (v1.0 Frozen)
  - Dodana jasna napomena da je ugovor autoritativan izvor
  - Sinkronizirani auth flow, streaming spec (error eventi + reconnect pravila), error handling i token best practices
- ✅ Debug cleanup:
  - `/debug/last-crash` sada ima `include_in_schema=False` (ne pojavljuje se u Swaggeru ni u produkciji ni u developmentu)
  - Već bio gated preko env varijabli (TESTING / ENABLE_DEBUG_ENDPOINTS)

### Dan 14 (Četvrtak) ✅ ZAVRŠENO
- **Fokus:** Bolje poruke grešaka + poboljšani retry
- ✅ Proširen centralni katalog `ERROR_MESSAGES` s 10+ novih čestih scenarija
- ✅ Bolja integracija poruka u custom exceptione i globalni handler
- ✅ Poboljšani retry helper (jitter, bolji logovi, konfigurabilniji)
- ✅ Chat error putevi sada koriste prijateljske poruke iz kataloga
- ✅ Pripremljene jasne poruke za najčešće slučajeve (auth, rate limit, LLM/tool, validacija)

### Dan 15 (Petak) ✅ ZAVRŠENO (Buffer + Tjedan 3 review)
- **Fokus:** Pregled napretka + realna procjena spremnosti za Flutter
- ✅ Detaljan pregled svih kritičnih stavki iz Faze 1
- ✅ Iskrena procjena preostalih rizika
- ✅ Ažurirana dokumentacija s jasnim statusom

**Kraj Tjedna 3 cilj:** ✅ **Uglavnom postignut**
- Većina kritičnih zadataka Faze 1 je završena
- Backend je u dobrom stanju za početak ozbiljnog Flutter razvoja (uz nekoliko preostalih provjera u produkciji)

---

## Tjedan 3 – Zaključak (Dani 11–15)

**Cilj tjedna:** Završetak Faze 1 (kritična stabilnost) + početak Faze 2 (poliranje).

**Status:** ✅ **Uglavnom postignut**

### Ključni rezultati Tjedna 3
- **Token rotacija sigurnost** → Poboljšana (Dan 11): novi token se kreira prije nego se stari poništi. Idempotentan revoke.
- **LLM retry + Graceful degradation** → Implementirano i poboljšano (Dan 12 + 14): retry s jitterom + nastavak generiranja odgovora čak i kad neki toolovi padnu.
- **Prijateljske poruke grešaka** → Značajno poboljšano (Dan 9 + 14): centralni katalog + dobra integracija u exceptione i handler.
- **Dokumentacija** → `mobile-api.md` usklađena s ugovorom + debug stvari uklonjene iz Swaggera (Dan 13).

**Preporuka nakon Dana 18 (korisnik odabrao put minimalnog rizika):**
- Ne krećemo još s Flutterom.
- Radimo kratak **Polishing + Production Verification Sprint** (2–4 dana).

### Polishing + Production Verification Sprint

#### Sprint Dan 1 (Poliranje poruka + priprema verifikacije) ✅ ZAVRŠENO
- ✅ Proširen katalog prijateljskih poruka (`error_messages.py`)
- ✅ Zamijenjen veći broj hardkodiranih poruka u kodu s porukama iz kataloga
- ✅ Poboljšan dokument `error-messages-for-flutter.md`
- ✅ Pripremljen / poboljšan detaljan vodič za produkcijsku verifikaciju rotacije

#### Sprint Dan 2 ✅ ZAVRŠENO
- ✅ Poboljšani rate limit odgovori (sada koriste katalog + bolji logovi)
- ✅ Dodatno logiranje rate limitinga (key + path + retry_after)
- ✅ Mala higijenska poboljšanja u rotaciji (bolji critical log s emailom)
- ✅ Brzi audit potvrdio da nema značajnih preostalih raw exceptiona u javnim putovima

#### Sprint Dan 3
- Korisnik radi produkcijsku verifikaciju rotacije (po vodiču)
- Brzi fixovi ako se nešto pokaže

#### Sprint Dan 4
- Finalno poliranje + priprema snapshota
- Kratki finalni review i odluka o prelasku na Flutter

---

## Tjedan 4: Faza 2 + Buffer + Finalni pregled (Detaljan plan)

**Cilj tjedna:** Dovršiti preostale visoke prioritete, napraviti finalni pregled i pripremiti backend za početak Flutter razvoja.

### Dan 16 (Ponedjeljak) ✅ ZAVRŠENO
- **Fokus:** Poliranje poruka + validacija
- ✅ Proširen i finaliziran katalog prijateljskih poruka (dodane `message_empty`, bolje varijante za chat/AI)
- ✅ Dodana eksplicitna validacija maksimalne duljine poruke (4000 znakova) u `/chat/stream` + korištenje poruke iz kataloga
- ✅ Kreiran novi dokument `docs/error-messages-for-flutter.md` (kratak reference za Flutter tim)
- ✅ Provjera da se ključne error poruke koriste iz centralnog kataloga

### Dan 17 (Utorak) ✅ ZAVRŠENO
- **Fokus:** Metrike + poliranje
- ✅ Dodane osnovne performanse metrike za streaming (`time_to_first_token` + `total_duration`) i spremljene uz history turn (u `performance` polju)
- ✅ Brzi audit: nema značajnih preostalih raw exceptiona u javnim putovima
- ✅ Početa priprema materijala za finalni review

### Dan 18 (Srijeda) ✅ ZAVRŠENO
- **Fokus:** Finalni pregled + priprema reviewa
- ✅ Detaljan prolazak kroz cijeli readiness checklist
- ✅ Kreiran `docs/backend-readiness-status.md` (jasan 1-stranični status report za review)
- ✅ Identificirani najveći preostali rizici (glavni = produkcijska verifikacija rotacije)
- ✅ Pripremljene točke za zajednički review s tobom (Dan 19)
- Pokrenuti sve postojeće testove / curl scenarije koje imamo

### Dan 19 (Četvrtak) – Zajednički review
- Kratki review s tobom (30–60 min): da li je backend dovoljno stabilan i predvidiv za početak ozbiljnog Flutter razvoja?
- Eventualne brze dorade na osnovu reviewa
- Dogovoriti što ide u "known limitations" za MVP, a što se može raditi paralelno s Flutterom

### Dan 20 (Petak) – Završetak i priprema
- Završiti sve preostale sitnice iz reviewa
- Ažurirati dokumentaciju (contract, checklist, mobile-api.md) na finalno stanje
- Pripremiti kratak "Backend Handoff" dokument za početak Fluttera (što radi, što očekivati, poznati rizici)
- Buffer za neočekivane stvari

**Kraj Tjedna 4 cilj:**
- Backend je u stanju da možeš početi ozbiljan Flutter razvoj s visokom razinom povjerenja
- Svi kritični i većina visokih prioriteta su gotovi ili jasno dokumentirani
- Imate jasan plan što još treba raditi paralelno s mobilnom aplikacijom

---

**Napomena:** Tjedan 4 je dizajniran kao kombinacija poliranja + finalnog reviewa. Ako se pokaže da ima više posla nego što očekujemo, možemo produžiti buffer na Dan 20 i eventualno jedan dodatni dan. Cilj nije "sve savršeno", nego "dovoljno dobro da ne blokira kvalitetan Flutter razvoj".

---

## Ukupni timeline (sa rezervom za kvalitetu)

| Tjedan     | Fokus                              | Očekivani rezultat |
|------------|------------------------------------|--------------------|
| Tjedan 1   | API Contract + početak Faze 1      | Ugovor zaključak + napredak na najkritičnijim područjima |
| Tjedan 2   | Glavni dio Faze 1                  | Većina kritičnih stavki gotova |
| Tjedan 3   | Završetak Faze 1 + početak Faze 2  | Kritični dio gotov + početak poliranja |
| Tjedan 4   | Faza 2 + buffer + finalni pregled  | Backend spreman za Flutter |

**Ukupno:** 4 tjedna sa ugrađenom rezervom za kvalitetu.

---

**Sljedeći korak:**

Želiš li da sada napravim **još detaljniju verziju** ovog plana (npr. sa dnevnim zadacima + očekivanim outputom za svaki dan), ili ti je ova razina dovoljna da krenemo izvršavati?

Također reci ako želiš negdje ubaciti više rezerve ili promijeniti redoslijed.