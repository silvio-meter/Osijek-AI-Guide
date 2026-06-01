# Lega – MVP v1: Lista ekrana i API potrebe

**Cilj ovog dokumenta:** Točno definirati što mora postojati u prvoj verziji aplikacije i koje API pozive Flutter treba.

---

## 1. MVP Ekran + Flow Lista

### 1.1 Autentifikacija

| Ekran              | Opis                                      | Prioritet | API potrebe |
|--------------------|-------------------------------------------|---------|-------------|
| Login              | Email + password                          | P0      | POST /auth/login |
| Register           | Email, password, full_name                | P0      | POST /auth/register |
| Forgot Password    | (MVP: može biti placeholder)              | P2      | - |

### 1.2 Glavni Chat (najvažniji ekran)

| Ekran / Komponenta     | Opis                                           | Prioritet | API potrebe |
|------------------------|------------------------------------------------|---------|-------------|
| Chat Screen            | Streaming chat + prikaz toolova                | **P0**  | POST /chat/stream |
| Chat History List      | Lista svih prethodnih razgovora                | P0      | GET /chat/history/{user_id} |
| Chat Detail            | Otvaranje starog razgovora                     | P0      | GET /chat/history/{user_id} |
| Preferences u chatu    | Uticaj preferencija na odgovore                | P0      | GET /user/me + POST /user/me/preferences |

### 1.3 Profil & Preferencije

| Ekran                  | Opis                                      | Prioritet | API potrebe |
|------------------------|-------------------------------------------|---------|-------------|
| Profil                 | Osnovni podaci + pregled preferencija     | P0      | GET /user/me |
| Uredi preferencije     | Interests, preferred_areas, dietary       | P0      | POST /user/me/preferences |

### 1.4 Ostalo (minimalno)

| Ekran       | Opis                        | Prioritet | Napomena |
|-------------|-----------------------------|---------|----------|
| Postavke    | Logout + osnovne postavke   | P0      | POST /auth/logout |
| Onboarding  | Jednostavan uvod (1-2 ekrana) | P1    | Može biti jako jednostavan |

---

## 2. Obavezni API Endpoints za MVP v1

### Autentifikacija (već postoji)

- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/refresh`
- `POST /auth/logout`

### Chat (kritično)

- `POST /chat/stream` → **najvažniji**
- `GET /chat/history/{user_id}`
- `GET /chat/history/{user_id}/summary` (opcionalno, ali korisno)
- `GET /chat/metrics`

### Korisnik

- `GET /user/me`
- `POST /user/me/preferences`

### Javni (opcionalno za MVP, ali korisno)

- `GET /restaurants`
- `GET /events`

---

## 3. Preporučeni redoslijed implementacije (Flutter + Backend)

**Tjedan 1–2 (Foundation)**
- Flutter projekt setup + arhitektura (Riverpod + clean layers)
- Login + Register + Token management (secure storage + refresh)
- Backend cleanup (ukloniti debug stvari, standardizirati errore)

**Tjedan 2–4 (Core Chat)**
- Chat streaming ekran (najveći posao)
- Chat history
- Osnovni profil + preferencije

**Tjedan 4–6 (Poliranje)**
- UI/UX poliranje
- Error handling i edge caseovi
- Testiranje na više uređaja
- Priprema za beta testiranje

---

## 4. Kvaliteta iznad brzine – Pravila

- Ne gradimo "brzo i prljavo" pa kasnije popravljamo.
- Svaki ekran mora imati barem osnovni error handling i loading state.
- Chat streaming mora biti stabilan i lijep (ovo je srce aplikacije).
- Ne dodajemo nove feature-e dok core flowovi nisu na visokoj razini.

---

**Sljedeći korak:** 
Želiš li da sada napravim detaljan **API Contract** dokument (točno koji endpointi, koji parametri, koji response shape mora imati Flutter za ovaj MVP)? 

To bi nam dalo vrlo jasan "ugovor" između backend-a i mobilne aplikacije.