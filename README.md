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

## OAuth Calendar Integration (Google/Microsoft)

Custos supports OAuth2 calendar integration with Google Calendar and Microsoft Outlook. This requires registering an OAuth application with the respective provider.

### Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Calendar API" and enable it
4. Configure OAuth consent screen:
   - Navigate to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type (or "Internal" for Workspace)
   - Fill in required app information
   - Add scope: `https://www.googleapis.com/auth/calendar.readonly`
5. Create OAuth credentials:
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URI: `http://localhost:5173/oauth-callback.html` (dev) or your production URL
   - Copy the Client ID and Client Secret

Set environment variables:
```bash
export CUSTOS_GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export CUSTOS_GOOGLE_CLIENT_SECRET="your-client-secret"
```

### Microsoft Outlook Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to "Azure Active Directory" > "App registrations"
3. Click "New registration":
   - Name: "Custos Calendar"
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: Web, `http://localhost:5173/oauth-callback.html` (dev) or your production URL
4. Configure API permissions:
   - Navigate to "API permissions"
   - Click "Add a permission" > "Microsoft Graph" > "Delegated permissions"
   - Add: `Calendars.Read`, `User.Read`, `offline_access`
   - Click "Grant admin consent" if required by your organization
5. Create client secret:
   - Navigate to "Certificates & secrets"
   - Click "New client secret"
   - Copy the secret value (shown only once)

Set environment variables:
```bash
export CUSTOS_MICROSOFT_CLIENT_ID="your-application-client-id"
export CUSTOS_MICROSOFT_CLIENT_SECRET="your-client-secret-value"
```

### OAuth Environment Variables Summary

```bash
# Google Calendar OAuth
CUSTOS_GOOGLE_CLIENT_ID       # OAuth client ID from Google Cloud Console
CUSTOS_GOOGLE_CLIENT_SECRET   # OAuth client secret from Google Cloud Console

# Microsoft Outlook OAuth
CUSTOS_MICROSOFT_CLIENT_ID    # Application (client) ID from Azure Portal
CUSTOS_MICROSOFT_CLIENT_SECRET # Client secret value from Azure Portal

# Enable calendar integration
CUSTOS_CALENDAR_ENABLED=1
```

### OAuth Security Notes

- OAuth state tokens are stored in the database for CSRF protection
- Tokens are encrypted at rest when using SQLCipher
- Refresh tokens are used to maintain access without re-authorization
- Token revocation is supported for Google; Microsoft tokens are invalidated by deletion

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

## Migrations (SQLCipher)
If Alembic reports tables already exist, your database likely has an empty `alembic_version` table. In dev, you can opt-in to auto-stamp:
```bash
export CUSTOS_ENV=dev
export CUSTOS_AUTO_STAMP=1
```
Otherwise, use the repair helper:
```bash
export CUSTOS_DATABASE_KEY="your-key"
python custos-core/backend/scripts/alembic_repair.py stamp --head 0007_relevant_at
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

## Dev CORS (Frontend on 5173)
CORS is disabled by default. Enable for dev UI access only:
```bash
export CUSTOS_DEV_CORS=1
```

## Vector Memory (Qdrant Local)
Vector recall uses Qdrant locally. The embedded store cannot be opened by multiple processes at once. For the dev stack (API + worker), run a local Qdrant server and set:
```bash
export CUSTOS_QDRANT_URL="http://127.0.0.1:6333"
```
Example (Docker):
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```
Alternate port (if 6333/6334 are in use):
```bash
export CUSTOS_QDRANT_URL="http://127.0.0.1:17633"
docker run -d --name qdrant-custos -p 17633:6333 -p 17634:6334 qdrant/qdrant
```
If you choose embedded local storage instead, run a single process (no concurrent worker) to avoid lock errors.
Or set an explicit allowlist:
```bash
export CUSTOS_CORS_ORIGINS="http://127.0.0.1:5173,http://192.168.10.50:5173"
```
Verify preflight + response headers:
```bash
curl -i -X OPTIONS http://192.168.10.50:8000/api/briefings/next -H "Origin: http://192.168.10.50:5173" -H "Access-Control-Request-Method: GET" | sed -n '1,30p'
curl -i http://192.168.10.50:8000/api/health -H "Origin: http://192.168.10.50:5173" | sed -n '1,30p'
```
Backfill vector memory after switching to a Qdrant server:
```bash
cd custos-core/backend
python scripts/backfill_qdrant.py
```

## Admin API (Dev Only)
Admin endpoints are disabled by default.
```bash
export CUSTOS_ADMIN_API_ENABLED=1
export CUSTOS_ENV=dev
export CUSTOS_ADMIN_BOOTSTRAP_KEY="bootstrap-key"
```
Verification:
```bash
curl -i http://192.168.10.50:8000/api/admin/settings | sed -n '1,30p'
curl -i -X POST http://192.168.10.50:8000/api/admin/api-key/rotate -H "X-API-Key: bootstrap-key" -H "Content-Type: application/json" -d '{"new_key":"temp-key"}' | sed -n '1,30p'
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
Admin key material is persisted at `backend/custos-data/admin_api_key.json`.

Dev reset procedure (disposable environments only):
```bash
rm -f backend/custos-data/admin_api_key.json
export CUSTOS_ADMIN_API_ENABLED=1
export CUSTOS_ENV=dev
export CUSTOS_ADMIN_BOOTSTRAP_KEY="bootstrap-key"
```
Restart the dev server and rotate once to a known key before running the smoke test.

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
