#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-}"
if [[ -z "$BASE_URL" ]]; then
  echo "Usage: ./scripts/set_webhook.sh https://your-domain"
  exit 1
fi

curl -sS -X POST "$BASE_URL/bot/set-webhook"
echo
