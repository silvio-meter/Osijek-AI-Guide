# Lega API – Vodič za mobilnu aplikaciju (Flutter / React Native)

**VAŽNO:** Ovo je **praktični implementacijski vodič**. 

**Autoritativni izvor specifikacije je:**
→ [`mobile-mvp-api-contract.md` (v1.0 Frozen)](mobile-mvp-api-contract.md)

Sve što je napisano u ovom dokumentu treba biti usklađeno s ugovorom. Ako postoji neslaganje, vrijedi ugovor.

## Osnovne informacije

- **Base URL (development):** `http://localhost:8000`
- **Base URL (production):** `https://osijek-ai-guide-production.up.railway.app`
- **OpenAPI dokumentacija:** `/docs` (Swagger) i `/redoc`
- **Verzija API-ja:** 0.6.0+ (vidi ugovor za točnu specifikaciju)

---

## Autentifikacija (JWT)

Većina javnih endpointa **ne zahtijeva** token (`/events`, `/restaurants`, `/points_of_interest`).

Zaštićeni endpointi (`/chat`, `/user/me`, `/chat/*`) zahtijevaju JWT access token.

### Flow autentifikacije

1. **Registracija**
   ```http
   POST /auth/register
   Content-Type: application/json

   {
     "email": "ana@example.com",
     "password": "lozinka123",
     "full_name": "Ana Kovač"
   }
   ```

2. **Login**
   ```http
   POST /auth/login
   {
     "email": "ana@example.com",
     "password": "lozinka123"
   }
   ```

   Odgovor:
   ```json
   {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "token_type": "bearer"
   }
   ```

3. **Korištenje tokena**
   ```http
   Authorization: Bearer <access_token>
   ```

4. **Refresh token (kada access token istekne)**
   ```http
   POST /auth/refresh
   {
     "refresh_token": "<refresh_token>"
   }
   ```

5. **Logout**
   ```http
   POST /auth/logout
   {
     "refresh_token": "<refresh_token>"
   }
   ```

**Preporuka za mobilnu app (obvezno prema ugovoru):**
- Spremaj oba tokena **isključivo** u `flutter_secure_storage`.
- Implementiraj automatski refresh na 401.
- Ako refresh vrati 401 → odmah odjavi korisnika.
- Preporučuje se proaktivni refresh (npr. 2 minute prije isteka access tokena).

Detalji: vidi sekciju 6 u `mobile-mvp-api-contract.md`.

---

## Javni endpointi (bez autentifikacije)

### 1. Događaji (`/events`) — Najvažniji za mapu

**Preporučeni način korištenja za mobilnu aplikaciju:**

```http
GET /events?structured=true&days_ahead=14&category=festival&limit=20
```

Query parametri:
| Parametar     | Tip     | Default | Opis |
|---------------|---------|---------|------|
| `structured`  | bool    | true    | `true` = čisti JSON (preporučeno) |
| `days_ahead`  | int     | 14      | Koliko dana unaprijed |
| `category`    | string  | -       | Filter (festival, koncert, izložba, sport, gastro...) |
| `limit`       | int     | 30      | Maksimalan broj rezultata |
| `query`       | string  | -       | Slobodna pretraga po naslovu/opisu |

**Primjer odgovora (skraćeno):**

```json
{
  "events": [
    {
      "title": "Paulinafest 2026",
      "description": "...",
      "short_description": "Glazbeno-kulturni festival",
      "start_date": "2026-06-15T18:00:00",
      "date_text": "15. lipnja 2026. od 18h",
      "location": "Tvrđa",
      "address": "Tvrđa, Osijek",
      "lat": null,
      "lng": null,
      "category": "Festival",
      "tags": ["glazba", "tvrda", "besplatno"],
      "url": "https://...",
      "source": "curated",
      "has_reliable_date": true
    }
  ],
  "count": 12,
  "days_ahead": 14,
  "category": "festival",
  "source": "hybrid_curated_scraped"
}
```

**Napomena:** Hibridni sustav uvijek daje prioritet kuriranim događajima.

### 2. Restorani

```http
GET /restaurants?structured=true
```

Vraća strukturirane podatke pogodne za karte i liste.

### 3. Points of Interest (točke interesa za mapu)

**Preporučeni endpoint (bogatiji):**

```http
GET /points_of_interest/?lat=45.56&lng=18.69&radius=2&sort=distance
```

Podržava:
- Proximity pretragu (`lat`, `lng`, `radius`)
- Filtriranje po kategoriji, tagovima, `is_featured`, `price_level`
- Pametno sortiranje (kada se pošalje lokacija, default je `distance`)

---

## Zaštićeni endpointi (zahtijevaju JWT)

### Chat

#### Slanje poruke
```http
POST /chat
Authorization: Bearer <token>

{
  "message": "Što večeras ima u Tvrđi?",
  "language": "hr"
}
```

#### Streaming (preporučeno za mobilne app)
```http
POST /chat/stream?message=Što večeras ima u Tvrđi?&language=hr
Authorization: Bearer <token>
Accept: text/event-stream
```

Odgovor je **Server-Sent Events (SSE)**.

**Važni formati događaja (točno prema ugovoru v1.0):**
- `data: {"content": "tekst"}` → token odgovora
- `data: [DONE]` → uspješan završetak
- `data: {"error": "tool_execution_error", "message": "..."}` → greška tijekom streama

**Obvezno ponašanje na klijentu (MUST iz ugovora):**
- Reconnect max 3x s exponential backoff (1s → 2s → 4s)
- Timeout 30s bez podataka → reconnect
- Ako stigne error event → prekini stream i prikaži poruku + retry gumb

Puni detalji u sekciji 4.1 `mobile-mvp-api-contract.md`.

#### Reset razgovora
```http
POST /chat/reset?keep_preferences=true
Authorization: Bearer <token>
```

#### Povijest i sažetak
```http
GET /chat/history/{user_id}/summary?format=medium
GET /chat/metrics
```

#### Feedback
```http
POST /chat/feedback
{
  "message_index": 3,
  "rating": 1,           // 1 = thumbs up, -1 = thumbs down
  "comment": "Odlična preporuka!"
}
```

### Korisnik

```http
GET  /user/me
POST /user/me/preferences
```

---

## Error Handling (važno za kvalitetan UX)

Svi endpointi vraćaju greške u standardiziranom formatu:

```json
{
  "error": "string",      // npr. "unauthorized", "tool_execution_error", "rate_limit_exceeded"
  "message": "string",    // korisniku prijateljska poruka (hrvatski)
  "details": object | null
}
```

**Preporučeni error kodovi i ponašanje** detaljno su opisani u sekciji 5 `mobile-mvp-api-contract.md` (Error Code Catalog).

## Najbolje prakse za Flutter aplikaciju

1. **Koristi Dio** ili **http** + interceptor za automatsko dodavanje `Authorization` headera.
2. **Cache** javne podatke (events, POI) lokalno (npr. Hive ili SharedPreferences + TTL).
3. **Streaming chat** koristi `SSE` client. **Obvezno** implementiraj reconnect logiku prema ugovoru (max 3 pokušaja + timeout 30s).
4. **Error handling** — koristi standardizirani `ErrorResponse` format + Error Code Catalog iz ugovora.
5. **Rate limiting** — backend ima zaštitu. Ako dobiješ 429, poštuj `Retry-After` header ako postoji.
6. **Token management** — slijedi točno strategiju iz sekcije 6 ugovora (flutter_secure_storage + auto-refresh + logout na failed refresh).

---

## Korisni linkovi u developmentu

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/`

---

## Kontakt / Pitanja

Za pitanja oko integracije javi se u projektu ili otvori issue na GitHubu.

**Sretno s razvojem mobilne aplikacije!** 🏛️
