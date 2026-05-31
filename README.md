# 🏛️ Osijek AI Guide - Lega

**Lega** je napredni AI vodič za Osijek koji pokreće produkcijski FastAPI backend dizajniran za mobilne aplikacije.

Projekt je prošao kroz 6 tjedana intenzivnog razvoja (Faza 1) i sada nudi stabilan, siguran i dobro dokumentiran backend spreman za Flutter / React Native aplikaciju.

---

## Trenutno stanje (nakon Tjedna 6)

| Područje                    | Status          | Napomena |
|----------------------------|------------------|----------|
| Autentifikacija (JWT)      | ✅ Stabilno     | Refresh rotacija + blacklist |
| Sigurnost & Rate Limiting  | ✅ Jako dobro   | Conditional limiting u testovima |
| Points of Interest         | ✅ Zreo         | 40+ lokacija, proximity, filteri, sortiranje |
| Events (hibridni model)    | ✅ Zreo         | Kurirani + scraperi + fallback |
| Chat (Week 5)              | ✅ Napredan     | Puna memorija toolova, summary, feedback, personalizacija |
| Dokumentacija              | ✅ Dobra        | OpenAPI + `docs/mobile-api.md` |
| Deployment priprema        | 🚧 U tijeku     | Docker + README overhaul (Tjedan 6) |

**Glavni deliverable Faze 1:** Stabilan backend koji može pouzdano podržati pravu mobilnu aplikaciju.

---

## ✨ Ključne značajke backend-a

- **Hibridni sustav podataka** — Kurirani podaci imaju prioritet nad scraperima (restorani + događaji)
- **Pametan chat s memorijom** — Puni kontekst razgovora uključujući tool calls
- **Personalizacija** — Korisničke preferencije utječu na preporuke
- **Javni API za mapu** — Events, Restaurants i Points of Interest s bogatim filtrima
- **Streaming chat** — Server-Sent Events za glatko mobilno iskustvo
- **Sigurnost** — JWT + refresh rotacija, rate limiting, security headers, standardizirane greške
- **Admin alati** — Skripte za unos i održavanje kuriranih podataka

---

## 🚀 Quick Start

### Opcija A: Docker (preporučeno za deployment)

```bash
cp .env.example .env   # ako već nemaš .env
docker compose up --build
```

**Napomena za macOS korisnike:**  
Ako ti `docker` nije pronađen, instaliraj **Docker Desktop**:
→ https://www.docker.com/products/docker-desktop/

Nakon instalacije pokreni Docker Desktop aplikaciju i pokušaj ponovo.

### Opcija B: Lokalno pokretanje (bez Dockera)

Najlakši način:

```bash
# 1. Kopiraj i uredi environment varijable
cp .env.example .env
# 2. Pokreni helper skriptu
./scripts/run.sh
```

Ili ručno:

```bash
pip install -r requirements.txt
PYTHONPATH=src uvicorn src.api:app --reload --port 8000
```

API je dostupan na: `http://localhost:8000`

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 📡 API Dokumentacija

Za mobilne developere preporučujemo:

- **[Mobilni API vodič (Flutter / React Native)](docs/mobile-api.md)** — Najvažniji dokument
- **OpenAPI / Swagger:** `http://localhost:8000/docs`
- **Pojedinačne teme:**
  - [Autentifikacija](docs/auth.md)
  - [Chat sustav](docs/chat.md)
  - [Points of Interest](docs/points_of_interest.md)
  - [Events (hibridni model)](docs/events.md)
  - [Sigurnost](docs/security.md)

---

## 🗂️ Struktura projekta

> **Napomena o bazi:** Trenutno koristimo SQLite (jednostavno za development). Za produkciju s većim opterećenjem preporučujemo prelazak na PostgreSQL (vidi [docs/deployment.md](docs/deployment.md)).

```
Osijek-AI-Guide/
├── src/
│   ├── api.py                 # Glavni FastAPI aplikacija
│   ├── models/                # SQLAlchemy modeli (User, Event, POI...)
│   ├── routers/               # Auth, Events, Points of Interest
│   ├── schemas/               # Pydantic modeli
│   ├── tools.py               # LangChain toolovi (hibridni eventi, restorani...)
│   ├── scrapers.py            # Lokalni scraperi
│   └── core/                  # Rate limiter, security, logging, exceptions
├── scripts/                   # Admin & import skripte
│   ├── import_pois.py
│   ├── import_events.py
│   ├── add_curated_event.py
│   └── ...
├── data/
│   ├── lega.db                # SQLite baza
│   ├── events_curated_seed.json
│   └── pois_example.json
├── docs/                      # Detaljna dokumentacija
├── tests/
├── STATUS_AFTER_5_WEEKS.md
├── PHASE1_BACKEND_PLAN.md
└── README.md
```

---

## 🛠️ Upravljanje podacima (Admin skripte)

Projekt koristi **hibridni pristup** — najbolji podaci su ručno kurirani.

### Unified Admin CLI (preporučeno)

Od Tjedna 6 imamo jedinstveni admin alat:

```bash
# Općeniti pregled
PYTHONPATH=. python3 scripts/admin.py stats

# Korisnici
PYTHONPATH=. python3 scripts/admin.py users list
PYTHONPATH=. python3 scripts/admin.py users show 5

# Chat history
PYTHONPATH=. python3 scripts/admin.py chat reset 5

# Events i POI
PYTHONPATH=. python3 scripts/admin.py events --curated
PYTHONPATH=. python3 scripts/admin.py pois --limit 20

# Feedback
PYTHONPATH=. python3 scripts/admin.py feedback summary
```

Za sve komande: `python3 scripts/admin.py --help`

### Events (stare skripte još rade)
```bash
# Bulk import / update
PYTHONPATH=. python3 scripts/import_events.py data/events_curated_seed.json

# Interaktivno dodavanje jednog događaja
PYTHONPATH=. python3 scripts/add_curated_event.py
```

### Points of Interest
```bash
PYTHONPATH=. python3 scripts/import_pois.py data/pois_example.json
```

Ove skripte koriste upsert logiku i označavaju podatke kao `is_curated`.

---

## 🧪 Testiranje

```bash
# Normalni testovi (rate limiting isključen)
TESTING=1 PYTHONPATH=src python -m pytest tests/ -q

# Samo auth testovi
TESTING=1 PYTHONPATH=src python -m pytest tests/test_auth.py -v
```

**Važno:** Normalni testovi nikad ne bi smjeli ići na `/auth/register` endpoint. Koristi `auth_headers` fixture koja kreira korisnike direktno u bazi.

---

## 🧠 Tehnički stack

- **Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic v2
- **Autentifikacija:** JWT (python-jose) + refresh token rotacija + blacklist
- **Chat & Tools:** LangChain + Grok-3-mini (xAI)
- **Baza:** SQLite (lako migrirati na PostgreSQL)
- **Sigurnost:** slowapi (rate limiting), custom security middleware
- **Testiranje:** pytest + dependency overrides

---

## 🐳 Docker (Tjedan 6)

Projekt je dockeriziran za jednostavno pokretanje i deployment.

**Detaljan vodič:** pogledaj [docs/docker.md](docs/docker.md)

### Brzi start s Dockerom

```bash
docker compose up --build
```

**Važno za macOS:** Ako ti `docker` nije pronađen, instaliraj Docker Desktop s:
https://www.docker.com/products/docker-desktop/

### Dostupni targeti

- `development` → hot reload (default)
- `production` → optimizirana slika

Napomena: Docker CLI nije bio dostupan tijekom razvoja ovog dijela, stoga je Docker trenutno opcionalan.

## 🚀 Deployment

Projekt je spreman za deployment.

**Glavni vodič:** [docs/deployment.md](docs/deployment.md)

### Brzi pregled

- Najlakša platforma za solo developere: **Railway**
- Imamo `docker-compose.prod.yml` za produkciju
- `/health` endpoint je dostupan za monitoring

Za detaljne upute (Railway, Fly.io, VPS, prelazak na PostgreSQL) pogledaj dokumentaciju.

## 📚 Dokumentacija

Sva dokumentacija se nalazi u mapi `docs/`:

- `mobile-api.md` — Glavni vodič za mobilnu integraciju
- `auth.md`, `chat.md`, `events.md`, `points_of_interest.md`
- `security.md`, `architecture.md`

Također pogledaj:
- `STATUS_AFTER_5_WEEKS.md` — Detaljan status nakon 5 tjedana + stalna rješenja
- `PHASE1_BACKEND_PLAN.md` — Izvorni plan Faze 1

---

## 🗺️ Što slijedi (Tjedan 6 i dalje)

Tjedan 6 fokus je na:
- Dockerizacija
- Deployment pipeline (Railway / Fly.io / VPS)
- Unificirani admin CLI alati
- Još bolja dokumentacija

Nakon Faze 1 planiramo prelazak na **Fazu 2: Flutter mobilna aplikacija**.

---

## 👤 Autor

Projekt razvija **Silvio Meter** solo, iterativno, tjedan po tjedan.

---

## 📄 Licenca

Korištenje dopušteno u osobne i edukacijske svrhe.

---

**Lega je spremna za mobilnu aplikaciju.** 🏛️

Za pitanja oko integracije ili doprinosa — javi se.