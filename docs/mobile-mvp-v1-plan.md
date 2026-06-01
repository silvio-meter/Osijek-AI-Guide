# Lega – Mobile App MVP v1 Plan

**Cilj:** Napraviti mobilnu aplikaciju najviše moguće kvalitete u što kraćem roku.

**Prioritet:** Brzina + Kvaliteta (nema žrtvovanja kvalitete radi brzine).

**Trenutni status (lipanj 2026):** Backend je stabilan i testiran. Glavni fokus sada prelazi na izradu Flutter aplikacije.

---

## 1. MVP Definicija (Što mora biti u prvoj verziji)

### Core Flows (must have)

1. **Onboarding & Autentifikacija**
   - Registracija
   - Login
   - Refresh token + automatsko osvježavanje
   - Logout

2. **Glavni Chat** (najvažniji dio aplikacije)
   - Streaming chat (token po token)
   - Tool calling (vidljivo korisniku)
   - Razgovor s memorijom
   - Personalizacija na temelju preferencija

3. **Povijest razgovora**
   - Lista prethodnih razgovora
   - Otvaranje starog razgovora

4. **Profil & Preferencije**
   - Pregled profila
   - Uređivanje interesa, područja i prehrambenih preferencija
   - Da se vidi utjecaj na chat

### Što NIJE u MVP v1 (svjesno izbačeno)

- Push notifikacije
- Mapa + događaji (osim ako se ne pokaže kritično)
- Više jezika (osim hrvatskog)
- Voice input
- Offline podrška
- Social login
- Napredna administracija

**Pravilo:** Ako nešto nije gore navedeno, ne ulazi u prvu verziju.

---

## 2. Lista ekrana (MVP v1)

| Prioritet | Ekran                        | Opis                                      | Kvaliteta cilj      |
|-----------|------------------------------|-------------------------------------------|---------------------|
| 1         | Login / Register             | Čist, brz, dobar error handling           | Visoka              |
| 2         | Chat (glavni)                | Streaming, lijep UI, tool indikatori      | **Najviša**         |
| 3         | Chat History                 | Lista razgovora + pretraga                | Visoka              |
| 4         | Profil                       | Osnovni podaci + uređivanje preferencija  | Visoka              |
| 5         | Postavke / Logout            | Jednostavno                               | Srednja             |

---

## 3. Tehničke odluke (preporuka)

### Flutter arhitektura (preporučena za visoku kvalitetu + brzinu)

- **State management:** Riverpod (v2) + `riverpod_annotation`
- **Arhitektura:** Feature-first + Clean Architecture (layers: data / domain / presentation)
- **Routing:** go_router
- **Networking:** dio + retrofit ili dio + freezed models
- **Local storage:** flutter_secure_storage (tokens) + hive / drift (cache)
- **Design:** Custom design system od početka (ne Material default)

**Zašto ovo?** Ova kombinacija daje dobru ravnotežu između brzine razvoja i dugoročne kvalitete/maintainability.

### Backend spremnost

Trebamo dovesti backend u stanje gdje Flutter tim (ti) može raditi bez konstantnih iznenađenja:

- Ukloniti sve `/debug/*` endpointe iz produkcije
- Standardizirati error response format
- Poboljšati streaming chat error handling
- Napraviti dobru, ažuriranu `mobile-api.md`

---

## 4. Predloženi pristup (kako idemo brzo + kvalitetno)

1. **Prvo zaključati scope** (ovo je trenutno najvažnije)
2. **Paralelno raditi:**
   - Backend cleanup + API stabilizacija
   - Flutter projekt setup + arhitektura
3. **Raditi u kratkim, visoko-kvalitetnim iteracijama** (7–10 dana)
4. **Svaki tjedan imati nešto što se može testirati** (čak i ako nije lijepo dizajnirano)

---

## 5. Sljedeći koraci (odmah)

**Trenutni prioritet (sljedećih 7–10 dana):**

1. **Zaključati točan MVP scope** (lista ekrana + što točno radi svaki ekran)
2. Napraviti detaljan API ugovor (što Flutter treba od backend-a)
3. Očistiti backend od nepotrebnih stvari
4. Pokrenuti Flutter projekt s pravom arhitekturom

---

**Pitanje za tebe:**

Želiš li da odmah krenemo s izradom detaljnog MVP Scope dokumenta + API ugovora za prvu verziju?

Ako da, reći ću ti točno što ćemo raditi u sljedećih par dana.