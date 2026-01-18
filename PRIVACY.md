# Privacy

Custos Core is local-first.

## What data Custos stores
- Meetings, people, and participants
- Source records (notes/transcripts you provide)
- Commitments and risk flags derived from stored sources
- Audit logs of changes and system actions
- Backup metadata

## Where data lives
All data is stored locally on the host running Custos Core. By default, no data is sent to external services.

## What Custos does not do by default
- No outbound network calls
- No cloud processing
- No telemetry

## Deleting data
You can delete local data by removing the database file and backups. For a clean reset:

1. Stop the running service.
2. Remove the data directory (default: `custos-core/backend/custos-data`).
3. Remove the database file (default: `custos-core/backend/test.db` or your configured path).

Custos Core does not retain any hidden caches once local data is removed.
