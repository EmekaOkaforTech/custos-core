#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CUSTOS_DATABASE_KEY:-}" ]]; then
  echo "CUSTOS_DATABASE_KEY is required for SQLCipher."
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BACKEND_DIR="$ROOT_DIR/custos-core/backend"
FRONTEND_DIR="$ROOT_DIR/custos-core/frontend"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${WORKER_PID:-}" ]]; then
    kill "$WORKER_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${CALENDAR_PID:-}" ]]; then
    kill "$CALENDAR_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

cd "$BACKEND_DIR"
HOST=${CUSTOS_BIND_ADDR:-127.0.0.1}
python -m uvicorn app.main:app --reload --port 8000 --host "$HOST" &
BACKEND_PID=$!

python -m http.server 5173 --directory "$FRONTEND_DIR" &
FRONTEND_PID=$!

python -m app.ingestion.worker 2>&1 | sed 's/^/worker: /' &
WORKER_PID=$!

python -m app.calendar.runner 2>&1 | sed 's/^/calendar: /' &
CALENDAR_PID=$!

echo "Backend: http://$HOST:8000"
echo "Frontend: http://localhost:5173"
wait
