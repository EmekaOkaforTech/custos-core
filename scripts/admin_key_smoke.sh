#!/usr/bin/env bash
set -euo pipefail

ADMIN_URL=${CUSTOS_ADMIN_URL:-http://localhost:8000}
OLD_KEY=${CUSTOS_API_KEY:-}
NEW_KEY=${CUSTOS_NEW_API_KEY:-}

echo "WARNING: Run only against dev or disposable environments."
echo "WARNING: Do not run against production."

if [[ -z "$OLD_KEY" || -z "$NEW_KEY" ]]; then
  echo "CUSTOS_API_KEY and CUSTOS_NEW_API_KEY are required." >&2
  exit 1
fi

code() {
  curl -s -o /dev/null -w "%{http_code}" "$@"
}

assert_code() {
  local expected=$1
  local actual=$2
  if [[ "$expected" != "$actual" ]]; then
    echo "Expected $expected, got $actual" >&2
    exit 1
  fi
}

initial=$(code -H "X-API-Key: $OLD_KEY" "$ADMIN_URL/api/admin/settings")
if [[ "$initial" == "404" ]]; then
  echo "Admin API not found. Set CUSTOS_ADMIN_API_ENABLED=1 (and CUSTOS_ENV=dev for bootstrap)." >&2
  exit 1
fi
assert_code 200 "$initial"

after_rotate=$(curl -sS -X POST "$ADMIN_URL/api/admin/api-key/rotate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $OLD_KEY" \
  -d "{\"new_key\":\"$NEW_KEY\"}" | cat)

echo "Rotate response: $after_rotate"

old_code=$(code -H "X-API-Key: $OLD_KEY" "$ADMIN_URL/api/admin/settings")
assert_code 401 "$old_code"

new_code=$(code -H "X-API-Key: $NEW_KEY" "$ADMIN_URL/api/admin/settings")
assert_code 200 "$new_code"

clear_resp=$(curl -sS -X POST "$ADMIN_URL/api/admin/api-key/clear" \
  -H "X-API-Key: $NEW_KEY" | cat)

echo "Clear response: $clear_resp"

open_code=$(code "$ADMIN_URL/api/admin/settings")
assert_code 200 "$open_code"

echo "Admin API key smoke test: pass"
