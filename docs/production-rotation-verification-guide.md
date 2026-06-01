# Production Token Rotation Verification Guide

**Cilj:** Potvrditi da refresh token rotacija + blacklist rade 100% ispravno u produkciji nakon deploya.

Ovo je najvažnija preostala verifikacija prije nego kreneš s Flutterom.

## Pretpostavke
- Imaš pristup produkcijskom backendu (Railway).
- Možeš vidjeti logove (Railway logs).
- Imaš barem jedan testni korisnički račun.

## Korak 1: Priprema

1. Deployaj najnoviju verziju backend-a (ona koja sadrži poboljšanja iz Dana 11).
2. Pripremi si 2-3 curl komande ili Postman kolekciju za brzo testiranje.

## Korak 2: Osnovni rotation test (najvažniji)

### 2.1 Login
```bash
curl -X POST https://osijek-ai-guide-production.up.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@primjer.com",
    "password": "TvojaLozinka123!"
  }'
```

Zabilježi `access_token` i `refresh_token`.

### 2.2 Prvi refresh
Koristi refresh token iz prethodnog koraka:

```bash
curl -X POST https://osijek-ai-guide-production.up.railway.app/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token_iz_login>"
  }'
```

**Očekivano:**
- Dobiješ novi `access_token` i **novi** `refresh_token`.
- U logovima trebaš vidjeti:
  - `[AUTH] New refresh token created`
  - `[AUTH] Refresh rotation: old jti revoked=...`
  - `[AUTH] New refresh token issued successfully`

### 2.3 Drugi refresh (provjera da stari više ne radi)
Koristi **stari** refresh token iz koraka 2.1:

```bash
curl -X POST https://osijek-ai-guide-production.up.railway.app/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<stari_refresh_token>"
  }'
```

**Očekivano:** Greška (401) s porukom da je token poništen.

Ponovi ovaj korak još 2-3 puta zaredom s najnovijim refresh tokenom.

## Korak 3: Logout + Blacklist test

1. Login → dobiješ refresh token.
2. Logout s tim tokenom:

```bash
curl -X POST https://osijek-ai-guide-production.up.railway.app/auth/logout \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

3. Pokušaj refresh s istim tokenom → treba biti odbijeno.

## Korak 4: Edge slučajevi

- Pokušaj refresh s tokenom koji nije refresh tip (npr. access token) → jasna greška.
- Pokušaj refresh s nepostojećim / krivim tokenom → jasna greška.
- (Opcionalno) Brzi uzastopni refreshevi (2-3 paralelna curla) – provjeri da ne dođe do čudnog stanja.

## Korak 5: Provjera nakon restarta containera

1. Pokreni nekoliko rotacija.
2. Triggeraj redeploy / restart containera na Railwayju.
3. Nakon što se podigne, pokušaj refresh s tokenom koji je bio validan prije restarta.
4. Provjeri da blacklist stanje preživi restart (ako je korisnik logout-ao prije restarta, token ne smije više raditi).

## Što tražiti u logovima

Tijekom testiranja traži ove linije:

- `[AUTH] New refresh token created`
- `[AUTH] Refresh rotation: old jti revoked=`
- `[AUTH] New refresh token issued successfully`
- `[AUTH] Logout revocation`
- `[AUTH][CRITICAL]` ← ako se pojavi, odmah javi

## Ako nešto ne radi

Zabilježi:
- Točan curl koji si poslao
- Točan odgovor (status + body)
- Relevantne log linije oko tog vremena

Pošalji mi te informacije pa ćemo brzo ispraviti.

---

**Preporuka:** Pokreni ovaj vodič nakon sljedećeg deploya prije nego kreneš pisati veće dijelove Flutter aplikacije.
