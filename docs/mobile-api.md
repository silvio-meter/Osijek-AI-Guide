# Lega API – Vodič za mobilnu aplikaciju (Flutter / React Native)

Ovaj dokument je **glavni referentni vodič** za developere mobilne aplikacije Osijek AI Guide (Lega).

## Osnovne informacije

- **Base URL (development):** `http://localhost:8000`
- **Base URL (production):** (bit će definirano nakon deploya)
- **OpenAPI dokumentacija:** `/docs` (Swagger) i `/redoc`
- **Verzija API-ja:** 0.6.0+

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

**Preporuka za mobilnu app:** Spremaj `access_token` u secure storage (Flutter: `flutter_secure_storage`). Koristi refresh token za automatsko osvježavanje.

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
```

Odgovor je Server-Sent Events (SSE).

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

## Najbolje prakse za Flutter aplikaciju

1. **Koristi Dio** ili **http** + interceptor za automatsko dodavanje `Authorization` headera.
2. **Cache** javne podatke (events, POI) lokalno (npr. Hive ili SharedPreferences + TTL).
3. **Streaming chat** koristi `SSE` client (postoje dobri Flutter paketi: `sse` ili `eventsource`).
4. **Error handling** — koristi standardizirani `ErrorResponse` format koji backend vraća.
5. **Rate limiting** — backend ima zaštitu. Ako dobiješ 429, prikaži korisniku "Previše zahtjeva, pokušaj malo kasnije".

---

## Korisni linkovi u developmentu

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/`

---

## Kontakt / Pitanja

Za pitanja oko integracije javi se u projektu ili otvori issue na GitHubu.

**Sretno s razvojem mobilne aplikacije!** 🏛️
