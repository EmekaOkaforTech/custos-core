# Database Migrations

## Requirements
- `CUSTOS_DATABASE_KEY` must be set for SQLCipher.
- Optional: `CUSTOS_DB_PATH` (defaults to `custos.db`).

## Initialize Database
```bash
export CUSTOS_DATABASE_KEY="your-key"
cd custos-core/backend
alembic -c alembic.ini upgrade head
```

## Run Migrations
```bash
export CUSTOS_DATABASE_KEY="your-key"
cd custos-core/backend
alembic -c alembic.ini upgrade head
```

## Rollback
```bash
export CUSTOS_DATABASE_KEY="your-key"
cd custos-core/backend
alembic -c alembic.ini downgrade -1
```
