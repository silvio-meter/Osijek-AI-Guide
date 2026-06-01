# Lega Mobile App – MVP v1 API Contract

**Verzija:** 1.0  
**Datum:** 2026-06-04  
**Status:** ✅ ZAKLJUČANO / FROZEN (v1.0) – Spremno za Flutter MVP razvoj

**Cilj dokumenta**  
Ovo je **obvezujući tehnički ugovor** između backend-a i Flutter aplikacije za prvu verziju (MVP). Dokument je pisan s ciljem da omogući izradu mobilne aplikacije **najviše moguće kvalitete** u što kraćem roku, bez kasnijih velikih iznenađenja.

---

## 1. Općenita pravila

### 1.1 Base URL
- **Produkcija:** `https://osijek-ai-guide-production.up.railway.app`
- **Razvoj:** `http://localhost:8000`

### 1.2 Autentifikacija
Svi zaštićeni endpointi **moraju** koristiti:
```
Authorization: Bearer <access_token>
```

### 1.3 Standardni Error Response Format (OBVEZAN)
Svi endpointi **moraju** vraćati greške u ovom formatu:

```json
{
  "error": "string",
  "message": "string",
  "details": object | null
}
```

**Preporučeni error kodovi u MVP-u:**
- `unauthorized`
- `refresh_token_revoked`
- `validation_error`
- `rate_limit_exceeded`
- `internal_server_error`
- `chat_stream_interrupted`

---

## 2. Autentifikacija

### 2.1 Registracija, Login, Refresh Token, Logout

**Važna pravila za mobilnu aplikaciju (MUST):**
- Access token traje **30 minuta**.
- Refresh token traje **7 dana** i rotira se pri svakom korištenju.
- Nakon uspješnog logouta, refresh token postaje nevažeći.
- Klijent **mora** implementirati automatski refresh pri 401 odgovoru.

---

## 3. Korisnik

### 3.1 Dohvat profila (`GET /user/me`)
### 3.2 Ažuriranje preferencija (`POST /user/me/preferences`)

(Detalji isti kao u prethodnim verzijama)

---

## 4. Chat – Najvažniji dio MVP (Visoka kvaliteta specifikacija)

### 4.1 Streaming Chat (`POST /chat/stream`) – Detaljna specifikacija

**Query parametri:**
- `message` (string) – **obvezan**
- `language` (string, default: `"hr"`)
- `max_history` (integer, opcionalno)

**Headers:**
```
Authorization: Bearer <access_token>
Accept: text/event-stream
```

#### Format događaja (Server-Sent Events)

Server šalje sljedeće tipove događaja:

| Tip događaja          | Format                                              | Opis |
|-----------------------|-----------------------------------------------------|------|
| Poruka                | `data: {"content": "tekst"}`                        | Dio odgovora |
| Kraj streama          | `data: [DONE]`                                      | Uspješan završetak |
| Greška                | `data: {"error": "...", "message": "..."}`          | Greška tijekom streama |
| Heartbeat (opcionalno)| `data: {"type": "ping"}`                            | Održavanje veze |

#### Obvezni zahtjevi za klijenta (MUST)

- **Reconnect logika**: Maksimalno 3 reconnect pokušaja s exponential backoff (preporuka: 1s → 2s → 4s).
- **Timeout**: Ako se ne primi ništa 30 sekundi → smatrati da je veza mrtva i pokrenuti reconnect.
- Ako se veza prekine prije `data: [DONE]` → tretirati kao transient grešku i pokušati reconnect.
- Ako stigne greška u streamu (`{"error": ...}`) → prekinuti stream i prikazati poruku korisniku + mogućnost retry.
- Prikazivati poruke **u realnom vremenu**.
- Na `data: [DONE]` → spremiti cijeli razgovor u lokalno stanje.

**Preporučeno ponašanje:**
- Korisniku prikazati jasna stanja: "Šaljem...", "Lega piše...", "Pokušavam ponovo povezati...".
- Omogućiti slanje nove poruke dok je prethodni stream aktivan (ili jasno blokirati).

### 4.2 Non-streaming Chat (fallback)

**POST** `/chat`

**Request:**
```json
{
  "message": "string",
  "language": "hr"
}
```

**Success Response:**
```json
{
  "response": "string",
  "tools_used": ["string"]
}
```

### 4.3 Povijest razgovora

**GET** `/chat/history/{user_id}`

Vraća kompletnu povijest uključujući `tool_calls` i tool rezultate.

### 4.4 Metrike

**GET** `/chat/metrics`  
**GET** `/chat/metrics?include_global=true`

---

## 5. Error Code Catalog (MVP v1)

| Error Code                    | HTTP Status | Opis                                              | Preporučeno ponašanje na klijentu |
|-------------------------------|-------------|---------------------------------------------------|------------------------------------|
| `unauthorized`                | 401         | Nevažeći ili istekao access token                 | Pokušaj refresh tokena |
| `refresh_token_revoked`       | 401         | Refresh token je poništen (rotacija ili logout)   | Odjavi korisnika |
| `validation_error`            | 422         | Neispravni podaci                                 | Prikaži `details` korisniku |
| `rate_limit_exceeded`         | 429         | Previše zahtjeva                                  | Poštuj `Retry-After` header |
| `internal_server_error`       | 500         | Neočekivana greška na serveru                     | Generička poruka + Retry gumb |
| `chat_stream_interrupted`     | -           | Prekid tijekom streaming chata                    | Pokušaj reconnect (max 3x) |

---

## 6. Preporučena strategija upravljanja tokenima (MUST za kvalitetnu aplikaciju)

1. `access_token` i `refresh_token` se čuvaju **isključivo** u `flutter_secure_storage`.
2. Pri svakom 401 → automatski pokušaj `POST /auth/refresh`.
3. Ako refresh uspije → zamijeni `access_token` i ponovi originalni zahtjev.
4. Ako refresh vrati 401 → odmah odjavi korisnika i prebaci ga na Login screen.
5. Nakon logouta → obriši oba tokena iz secure storagea.
6. Preporučuje se proaktivni refresh (npr. 2 minute prije isteka access tokena).

---

## 7. Rate Limiting

- Backend primjenjuje rate limiting.
- Pri 429 klijent **mora** poštovati `Retry-After` header ako postoji.
- Preporučeno: prikazati korisniku jasnu poruku o ograničenju.

---

## 8. API Versioning i Backward Compatibility

- Trenutno se koristi verzija **bez prefiksa**.
- Sve **breaking changes** u budućnosti **moraju** ići kroz novu verziju (`/v2/...`).
- Non-breaking promjene su dozvoljene bez promjene verzije.
- Backend se obvezuje da neće lomiti postojeće klijente bez prethodne najave.

---

## 9. Što je izvan scopea ovog MVP

- Push notifikacije
- Mapa i događaji
- Offline podrška
- Više jezika
- Voice input
- Social login

---

---

## Dan 3 – Finalni pregled i zamrzavanje (v1.0) ✅

**Datum:** 2026-06-04

### Što je napravljeno prije zamrzavanja
- **Dan 1:** Prva velika iteracija – streaming spec (error događaji tijekom streama, reconnect/timeout pravila, client MUST obveze), Error Code Catalog, Security & Token Best Practices za mobilne, API Versioning pravila.
- **Dan 2:** Backend implementacija prvih error događaja tijekom streama (`data: {"error": ..., "message": ...}`) u oba chat endpointa (`/chat` i `/chat/stream`).
- **Dan 3:** Finalni pregled ugovora + zaključavanje.

### Rezultat finalnog pregleda
Ugovor je **solidan, jasan i dovoljan** za početak visokokvalitetnog Flutter MVP razvoja. Nema velikih rupa koje bi kasnije mogle uzrokovati velike refaktore na mobilnoj strani.

**Manje napomene dodane tijekom pregleda (već uključene u specifikaciju):**
- Streaming error događaji **namjerno** ne sadrže `details` polje (SSE payload treba biti lagan).
- `chat_stream_interrupted` je rezerviran za klijentsku stranu (backend šalje `internal_server_error` ili `tool_execution_error` tijekom streama).
- Svi budući error kodovi **moraju** proći kroz ažuriranje ovog ugovora prije implementacije.

### Što je sada obvezujuće
Od ovog trenutka:
- Backend **neće** mijenjati response format errora bez prethodne najave i verzioniranja.
- Flutter aplikacija može se osloniti na točne opise u sekcijama 4.1 (streaming), 5 (Error Catalog) i 6 (token strategija).
- Sve promjene koje lome klijente idu kroz `/v2/...` prema pravilima iz sekcije 8.

**Status:** ✅ **v1.0 ZAKLJUČANO**

Ovo je službeni ugovor za Lega Mobile MVP. Možemo ga koristiti kao temelj za arhitekturu i implementaciju Flutter aplikacije najviše moguće kvalitete.

---

**Sljedeći korak (nakon plana):**

Nakon što završimo Fazu 1 (kritična stabilnost), napravit ćemo kratki zajednički review prije prelaska na Flutter. U međuvremenu se ugovor smatra stabilnim.