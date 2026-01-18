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
## Run Locally
```bash
export CUSTOS_DATABASE_KEY="your-key"
make dev
```

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

## License
TBD
