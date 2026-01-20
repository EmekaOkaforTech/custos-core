# Changelog

## Unreleased
- Admin API endpoints with opt-in dev gating and bootstrap rotation
- Admin key smoke and rotation scripts under `scripts/`
- Frontend API base configuration (`config.js`) and apiUrl wiring for briefings/status/people
- Dev-only CORS allowlist support for UI on `:5173`
- Seed script module `python -m app.scripts.seed_data` and wrapper
- Dev bind address toggle (`CUSTOS_BIND_ADDR`) for LAN testing
- SQLCipher driver support via `sqlcipher3-binary` with non-compile install path

