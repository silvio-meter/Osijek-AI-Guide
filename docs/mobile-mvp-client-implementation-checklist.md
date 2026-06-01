# Lega Mobile App – MVP v1: Client Implementation Checklist

**Svrha:**  
Ovo je **praktični i obvezujući checklist** za Flutter razvoj. Sadrži sve što mobilna aplikacija **mora** implementirati da bi postigla visoku kvalitetu, stabilnost i sigurnost u skladu s API Contractom.

Cilj je omogućiti izradu aplikacije **najviše moguće kvalitete** u što kraćem roku.

---

## 1. Autentifikacija i Token Management (MUST)

### Obvezne implementacije:

- [ ] `access_token` i `refresh_token` se čuvaju **isključivo** u `flutter_secure_storage` (nikada u SharedPreferences ili običnom storageu)
- [ ] Prilikom svakog `401` odgovora → automatski pokušaj `POST /auth/refresh`
- [ ] Ako refresh vrati `401` (refresh token revoked) → odmah odjavi korisnika i prebaci ga na Login screen
- [ ] Nakon uspješnog refresha → zamijeni `access_token` i ponovi originalni zahtjev (ako je bio 401)
- [ ] Nakon logouta → obriši oba tokena iz secure storagea
- [ ] Implementiraj centralni `TokenManager` (kao Riverpod provider ili service) koji upravlja svim token operacijama
- [ ] Preporučuje se proaktivni refresh (npr. 2 minute prije isteka access tokena)
- [ ] Nikada ne logiraj tokene (niti djelomično)

**Preporučeni pattern:** Dio Interceptor + TokenManager za transparentan refresh.

---

## 2. Streaming Chat – Obvezni zahtjevi (MUST)

Ovo je najkritičniji dio za korisničko iskustvo.

### Obvezne funkcionalnosti:

- [ ] Koristiti pravi SSE klijent (EventSource ili custom stream implementacija)
- [ ] Implementirati **reconnect logiku**:
  - Maksimalno 3 reconnect pokušaja
  - Exponential backoff (preporuka: 1s → 2s → 4s)
- [ ] Timeout: Ako se ne primi ništa 30 sekundi → smatrati da je veza mrtva i pokrenuti reconnect
- [ ] Ako se veza prekine prije `data: [DONE]` → prikazati korisniku "Veza je prekinuta" + gumb "Pokušaj ponovo"
- [ ] Prikazivati poruke **u realnom vremenu** (token po token ili u malim grupama)
- [ ] Na `data: [DONE]` → spremiti cijeli razgovor u lokalno stanje i osvježiti history ako je potrebno
- [ ] Podržati slanje nove poruke dok je prethodni stream aktivan (ili jasno blokirati slanje)

### Preporučena UI stanja tijekom streaminga:

- `Idle`
- `Sending`
- `Streaming` (dolaze tokeni)
- `Reconnecting`
- `Error` (s Retry gumbom)
- `Completed`

### Error handling tijekom streama:

- Ako stigne `{"error": "..."}` → prekinuti stream i prikazati poruku
- Implementirati "Retry last message" funkcionalnost

---

## 3. Error Handling – Standardi za visoku kvalitetu

### Opća pravila:

- [ ] 401 → pokušaj refresh (prema token strategiji)
- [ ] 429 → prikaži "Previše zahtjeva. Pokušaj za X sekundi." (poštuj `Retry-After` ako postoji)
- [ ] 500 / network error → generička poruka + **Retry** gumb
- [ ] 422 (validation) → prikaži konkretne poruke iz `details`

### Posebno za Chat:

- [ ] Ako stream pukne → korisnik može ponovo poslati istu poruku bez gubitka konteksta
- [ ] Implementirati "Retry" za zadnju poruku
- [ ] Jasno razlikovati transient greške (može se retryati) od permanentnih

---

## 4. Security Best Practices (MUST)

- [ ] Koristiti `flutter_secure_storage` s najjačim dostupnim opcijama na iOS-u i Androidu
- [ ] Implementirati **biometric authentication** za otključavanje aplikacije (preporučeno za kvalitetu)
- [ ] Nakon logouta obriši sve osjetljive podatke (tokene + eventualno keširane razgovore)
- [ ] Koristiti certificate pinning u produkciji (ako je tehnički izvedivo)
- [ ] Nikada ne šalji refresh token u `Authorization` header (samo u body `/auth/refresh`)

---

## 5. Preporučena arhitektura za ove dijelove

**Preporučeni slojevi:**

- `TokenManager` – centralno mjesto za sve token operacije (refresh, storage, validacija)
- `ChatRepository` – apstrahira streaming i non-streaming chat
- `ChatStreamHandler` – poseban service koji upravlja SSE konekcijom, reconnectima, errorima i stateom
- `ErrorHandler` / `Failure` model – za standardizirano rukovanje greškama

**Zašto ovo?**
- Omogućuje testabilnost
- Centralizira složenu logiku (reconnect, token refresh)
- Lakše je održavati i skalirati
- Smanjuje duplikaciju koda

---

## 6. Što bi trebalo biti spremno prije nego krene ozbiljan Flutter razvoj

- [ ] API Contract je zaključan
- [ ] Streaming reconnect i error handling strategija je definirana
- [ ] Token management flow je definiran i testiran na backendu
- [ ] Error Code Catalog je dogovoren
- [ ] Postoji jasan dogovor oko ponašanja pri rate limitingu

---

**Napomena:**  
Ovaj checklist je napisan tako da podrži **visoku kvalitetu od prvog dana**, a ne "brzo pa popravljamo kasnije".

Želiš li da sada napravim **detaljan prijedlog Flutter arhitekture** (folder struktura, package organizacija, state management patterni, dependency injection, itd.) na temelju ovog checklist-a i ranije dogovorene arhitekture (Riverpod + layered)?

Ili želiš prvo da dovršimo još neke dijelove API Contracta?