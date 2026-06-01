# Backend MVP Readiness Checklist

**Svrha dokumenta:**  
Ovo je **akcijski i prioritetni checklist** što backend mora imati ili popraviti prije nego što krenemo u ozbiljan razvoj Flutter aplikacije najviše kvalitete.

Cilj: Svesti rizik da se kasnije vraćamo na backend dok radimo mobilnu aplikaciju (što usporava razvoj i kvari kvalitetu).

**MVP Scope za koji se pripremamo:**
- Autentifikacija (register, login, refresh, logout + rotacija + blacklist)
- Chat (streaming + non-streaming + tool calling + history)
- Korisnički profil + preferencije
- Osnovne metrike

---

## 1. Kritični prioriteti (MUST HAVE prije nego krene Flutter razvoj)

### 1.1 API Contract & Stabilnost
- [x] `mobile-mvp-api-contract.md` je zaključan i obje strane su se složile oko njega **(v1.0 Frozen – Dan 3)**
- [~] Svi endpointi navedeni u ugovoru su implementirani i rade točno prema specifikaciji – većina je. Message length validation dodana (Dan 16). Ostalo su male stvari u javnim fallback putovima.
- [~] Error response format je **potpuno konzistentan** na svim endpointima – **veliki napredak Dan 8 + 14**: dependencies/auth.py potpuno prebačen na custom exceptione. Većina chat i user putova čista. Još uvijek ima nekoliko manjih fallback javnih putova.
- [x] Streaming chat (`/chat/stream`) ima jasno definirane error događaje tijekom streama (`data: {"error": ...}`) **(implementirano Dan 2)**
- [~] Nema "sirovih" exceptiona ili stack traceova u produkcijskim odgovorima – vrlo malo ih je ostalo (uglavnom u fallback javnim putovima) – napredak kroz Dane 5, 8, 13, 16

### 1.2 Streaming Chat – Stabilnost i Predvidivost (najveći rizik za kvalitetu)
- [x] Definirana i implementirana jasna specifikacija grešaka tijekom streama **(u ugovoru + implementacija Dan 2)**
- [x] Backend šalje `data: [DONE]` samo kada je stream uspješno završio
- [~] Definirano ponašanje kada tool poziv padne tijekom streaming odgovora **(Dan 6: konzistentno u oba endpointa – šalje tool_execution_error + pokušaj spašavanja historyja)**
- [~] Definirani timeoutovi i disconnect scenariji (backend strana) – **Dan 7**: cancellation handling + partial history saving s oznakom [STREAM INTERRUPTED]
- [~] Testirano ponašanje kod prekida LLM poziva usred streama – **početak Dan 7** (cancellation + logging + partial save)

### 1.3 Autentifikacija & Sigurnost
- [~] Refresh token rotacija + blacklist radi 100% ispravno (logika + poboljšana sigurnost rotacije Dan 11). **Najvažnije preostalo**: produkcijska verifikacija nakon deploya (checklist pripremljen Dan 11)
- [~] Logout stvarno i pouzdano poništava refresh token (logika + novi logovi)
- [~] Nema curenja osjetljivih podataka u error porukama – većina je čista, još uvijek treba finalni pregled
- [~] Rate limiting je predvidiv i ima jasne poruke (429 + `Retry-After`) – poruke su u katalogu, treba provjeriti header u produkciji

### 1.4 Error Handling
- [~] Svi endpointi vraćaju greške u dogovorenom formatu (`error`, `message`, `details`) – većina je, ostalo su manji javni fallbackovi
- [~] Postoje jasne, korisniku prijateljske poruke na hrvatskom za najčešće slučajeve – **Dan 9, 14, 16**: Solidan centralni katalog + dobar reference dokument za Flutter
- [~] Nema generičkih "Internal Server Error" poruka bez korisnog konteksta – dobar napredak Dan 9+14+16

### 1.5 Logging & Observability (ključno za tebe)
- [~] Svi važni događaji u chatu se logiraju (ulazna poruka, tool pozivi, završetak, greške) – **napredak Dan 3** (phase-specific + user_id u svim stream error logovima)
- [~] Greške tijekom streaminga se jasno i detaljno logiraju **(Dan 10: dodan timing/duration + bolja struktura)**
- [x] Postoji pouzdan i brz način da se dođe do tracebacka greške u produkciji (`/debug/last-crash` + forced multi-output + file)
- [~] Logovi su čitljivi i korisni – **značajan napredak kroz Tjedan 2** (phase + user_id + duration)

### 1.6 Tehnički Debt & Čistoća (prije Fluttera)
- [~] Uklonjeni svi `/debug/*` endpointi iz produkcije (ili barem `/debug/last-crash`) – **Dan 4**: `/debug/last-crash` sada 404 u produkciji + dodatno čišćenje raw exceptiona Dan 5
- [ ] `init_db()` se pouzdano i vidljivo pokreće na svakom startu containera (već radi – treba samo održavati)
- [ ] Nema hardkodiranih tajni ili testnih podataka u produkcijskom kodu

---

## 2. Visoki prioriteti (treba biti gotovo prije ili tijekom ranih faza Fluttera)

- [~] Bolje rukovanje grešaka tijekom LLM i tool poziva – **Dan 12+14**: retry helper (poboljšan s jitterom) + graceful continuation + integracija prijateljskih poruka
- [~] Dodan retry mehanizam za LLM pozive (barem 1 retry) – **implementirano i poboljšano Dan 12+14**
- [x] Jasno definirana maksimalna duljina poruke + validacija – **Dodano Dan 16** (4000 znakova + prijateljska poruka)
- [ ] `chat_history_manager` i `user_context_manager` su stabilni pod većim opterećenjem
- [~] Dodane osnovne metrike performansi – **Dan 17**: `time_to_first_token` + `total_duration` spremljeni uz history za streaming turnove

---

## 3. Srednji prioritet (može ići paralelno s Flutterom)

- [x] `mobile-api.md` ažurirana i usklađena s `mobile-mvp-api-contract.md` (v1.0) – **Dan 13**
- [x] Uklonjeni ili sakriveni nepotrebni admin/debug endpointi iz javne Swagger dokumentacije – **Dan 13** (`/debug/last-crash` sada `include_in_schema=False` + gated)
- [~] Bolje poruke grešaka za česte slučajeve – **Dan 16**: Proširen katalog + novi reference dokument za Flutter (`error-messages-for-flutter.md`)
- [ ] Pripremljen jednostavan način praćenja troška xAI API-ja po korisniku (opcionalno, ali korisno)

---

## 4. Što može pričekati nakon MVP-ja

- Prava admin uloga i zaštita admin endpointa
- Prebacivanje na PostgreSQL + prave migracije (Alembic)
- Napredni monitoring, alerting i cost tracking
- Push notifikacije
- Više jezika
- Napredna zaštita od zloupotrebe (abuse protection)

---

## 5. Preporučeni redoslijed rada (prijedlog)

1. Dovršiti i zaključati `mobile-mvp-api-contract.md`
2. Proći kroz ovaj **Backend Readiness Checklist** i napraviti realan akcijski plan
3. Riješiti sve **Kritičke** stavke (posebno streaming + error handling + logging)
4. Riješiti većinu **Visokih** prioriteta
5. Tek tada krenuti s Flutter projektom i arhitekturom

---

**Napomena:**  
Ovaj checklist je napisan realistično, s obzirom na tvoj cilj (najviša kvaliteta što brže) i tvoj tempo (10+ sati dnevno).

Želiš li da sada napravim **konkretan, prioritetan akcijski plan** iz ovog checklist-a (sa zadacima, prioritetima i predloženim redoslijedom za sljedećih 7–14 dana)? 

To bi ti dalo jasan backlog za backend pripremu prije nego kreneš s Flutterom.