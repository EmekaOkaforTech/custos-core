# Custos Core

Open-source core for Custos. This repository contains the backend API, data models, ingestion pipeline, and audit logic.

## Scope
- Local-first data store and memory model
- Deterministic source attribution
- Async ingestion pipeline
- API contracts for briefing, people, commitments, sources, and status

## Open Core
Custos Core is open source and contains all data formats, storage, and audit logic.

Planned paid layers (not in this repo):
- Pro: performance and advanced briefing features
- Enterprise: governance, compliance, and SSO

These paid layers will be feature-gated without restricting data access or portability.
Custos Core is the public open-source foundation. Paid tiers add features without restricting data access or portability.

## Local-First Promise
Custos Core stores and processes data locally by default. It makes no outbound network calls unless you explicitly enable an integration.

## Distribution
Custos Core is software-first. A certified device option may exist later, but the core product runs as a local service on your own hardware.

## Dev Tools (Non-Production)
Development-only utilities live in `dev_tools/`. These are never used in production runtime.

Calendar demo provider is available only when:
- `CUSTOS_ENV=dev`
- `CUSTOS_CALENDAR_PROVIDER=demo`
- `CUSTOS_CALENDAR_ENABLED=1`

## Performance Fixtures (Non-Production)
Perf tooling must run against sanctioned non-production fixtures only. No real user or customer data is permitted.

Generate deterministic fixture dataset and payloads:
```bash
export CUSTOS_ENV=dev
export CUSTOS_ALLOW_PLAINTEXT_DB=1
export CUSTOS_DATABASE_URL=sqlite:///./dev-tools/fixtures/nonprod.db
export CUSTOS_INGESTION_PAYLOADS_PATH=./dev-tools/fixtures/ingestion-payloads.jsonl
python dev_tools/scripts/generate_nonprod_fixtures.py
```

Run ingestion throughput benchmark using fixtures:
```bash
export CUSTOS_ENV=dev
export CUSTOS_ALLOW_PLAINTEXT_DB=1
export CUSTOS_DATABASE_URL=sqlite:///./dev-tools/fixtures/nonprod.db
export CUSTOS_INGESTION_PAYLOADS_PATH=./dev-tools/fixtures/ingestion-payloads.jsonl
python dev_tools/scripts/perf_ingest.py
```

## Development Setup (Python)
Use a Python virtual environment. Conda base environments are not supported and can contaminate SQLCipher builds.
```bash
python -m venv .venv
. .venv/bin/activate
pip install -r custos-core/backend/requirements.txt
```
SQLCipher (encrypted SQLite) uses the `sqlcipher3-binary` wheel via SQLAlchemy's module override. No local compilation is required.

## Encrypted Dev DB Quick-Start
```bash
python -m venv .venv
. .venv/bin/activate
pip install -r custos-core/backend/requirements.txt
export CUSTOS_DATABASE_KEY="your-key"
bash custos-core/scripts/dev.sh
```

## Run Locally
```bash
export CUSTOS_DATABASE_KEY="your-key"
# Local-only (default)
export CUSTOS_BIND_ADDR=127.0.0.1
make dev
```

LAN testing (dev/disposable only):
```bash
export CUSTOS_DATABASE_KEY="your-key"
export CUSTOS_BIND_ADDR=0.0.0.0
make dev
```

## Frontend ↔ Backend Dev Wiring
Frontend defaults to same-origin `/api/*`. For local dev with the static server on `:5173`, set:
```js
// custos-core/frontend/config.js
window.CUSTOS_API_BASE = "http://127.0.0.1:8000";
```
For cross-device browsing, use the host IP instead of loopback:
```js
// custos-core/frontend/config.js
window.CUSTOS_API_BASE = "http://192.168.10.50:8000";
```
Leave it empty to keep same-origin behavior in production.

Quick verify (dev server):
```bash
curl -s http://127.0.0.1:5173/people.html | grep -n config.js
```

## Seed Data (Non-Production)
Run a deterministic seed against the configured database:
```bash
cd custos-core/backend
python -m app.scripts.seed_data
```
Or run the wrapper script from the backend directory:
```bash
cd custos-core/backend
python scripts/seed-data.py
```

## Admin Settings (Enterprise)
Network exposure (local-only by default):
```bash
export CUSTOS_NETWORK_MODE=local   # local | lan
export CUSTOS_BIND_HOST=127.0.0.1  # set 0.0.0.0 for LAN binding
```

API key authentication (optional):
```bash
export CUSTOS_API_KEY="change-me"
```
When `CUSTOS_API_KEY` is set, pass `X-API-Key` on all `/api/*` requests.
Frontend usage (browser):
```bash
localStorage.setItem('custos_api_key', 'change-me')
```

## Compliance Notes
See `custos-core/COMPLIANCE.md` for data flow, retention, consent, and deletion posture.

## Hardware Profiles
See `custos-core/HARDWARE_PROFILES.md` for certified deployment envelopes.

## Provisioning & Updates
See `custos-core/PROVISIONING.md` for clean install and update workflow guidance.

## Admin Key Ops
Scripts for key rotation and recovery live in `custos-core/scripts/admin_key.sh` and `custos-core/scripts/admin_key_smoke.sh`.

## Frontend UI Verification (Offline/Cached)
```bash
node custos-core/frontend/tests/ui-state.test.mjs
```

## Backup & Restore (Core)
Backup:
```bash
python -m app.ops.backup
```

Restore:
```bash
python -m app.ops.restore /path/to/backup.db
```

## Backup Automation (Core)
Scheduled backups are local-only and use the configured interval to meet recovery targets.

RPO target: <= 24 hours via scheduled backups.  
RTO target: <= 1 hour via restore drills using the latest backup.

Run a scheduled backup (suitable for cron/systemd timers):
```bash
export CUSTOS_BACKUP_ENABLED=1
export CUSTOS_BACKUP_INTERVAL_HOURS=24
python -m app.ops.backup_schedule
```

Restore drill (verify RTO manually):
```bash
python -m app.ops.restore /path/to/backup.db
```

## License
TBD
