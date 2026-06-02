# Pripreme dok si na pauzi (2.6.2026)

Sve što si tražio je napravljeno i pushano.

## 1. Repair endpoint (backend)
- `POST /chat/history/{user_id}/repair?also_reset_main=true`
- Također integrirano u postojeće reset endpointove (`/chat/reset` i `/chat/history/{user_id}/reset`) — automatski čisti `.bad*` datoteke.
- Vidi `src/api.py` oko linije 1540+.

## 2. Admin / ops script
- `scripts/repair_user_chat_history.py`
- Primjeri:
  ```bash
  python scripts/repair_user_chat_history.py --user-id 13 --dry-run
  python scripts/repair_user_chat_history.py --email silvio-test-0602@osijek.ai --reset-main
  ```
- Podržava --dry-run, --reset-main, --user-id ili --email (pokuša resolve preko local DB).

## 3. Ažurirani testing dokument
- `lega_mobile/TESTING_DETAILED_2026-06.md` — dodana cijela sekcija "Novi slučaj: Corrupted chat history" na kraju, s checklistom, primjerima curl/script i objašnjenjem simptoma + oporavka.
- Kratki pointer: `lega_mobile/TESTING_INSTRUCTIONS.md` je također ažuriran.

## 4. Bonus (mala sigurnosna napomena)
- Repair endpoint sada prima `current_user` (vlasništvo se može kasnije pojačati admin role-om).

Svi commitovi su na mainu i pushani na GitHub (Railway će ih pokupiti na sljedećem deployu).

Kad se vratiš, prvo provjeri Railway deploys, pa pokreni testove po ažuriranom `TESTING_DETAILED_2026-06.md`.

Uživaj u pauzi!
