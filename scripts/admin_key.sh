#!/usr/bin/env bash
set -euo pipefail

ADMIN_URL=${CUSTOS_ADMIN_URL:-http://localhost:8000}
API_KEY=${CUSTOS_API_KEY:-}

usage() {
  echo "Usage: $0 rotate <new_key> | clear" >&2
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

command=$1
shift

case "$command" in
  rotate)
    if [[ $# -lt 1 ]]; then
      usage
      exit 1
    fi
    if [[ -z "$API_KEY" ]]; then
      echo "CUSTOS_API_KEY is required for rotation." >&2
      exit 1
    fi
    new_key=$1
    curl -sS -X POST "$ADMIN_URL/api/admin/api-key/rotate" \
      -H "Content-Type: application/json" \
      -H "X-API-Key: $API_KEY" \
      -d "{\"new_key\":\"$new_key\"}"
    echo
    ;;
  clear)
    if [[ -z "$API_KEY" ]]; then
      echo "CUSTOS_API_KEY is required to clear." >&2
      exit 1
    fi
    curl -sS -X POST "$ADMIN_URL/api/admin/api-key/clear" \
      -H "X-API-Key: $API_KEY"
    echo
    ;;
  *)
    usage
    exit 1
    ;;
esac
