#!/usr/bin/env bash
# Deploy rasxot_bot to Railway (FastAPI + Postgres) and register Telegram webhook.
#
# Required (export before running, or put in .env.deploy and `source .env.deploy`):
#   BOT_TOKEN              — from @BotFather (rotate if ever exposed)
#   OWNER_TELEGRAM_ID      — your numeric Telegram user id
#   RAILWAY_TOKEN          — Project token from Railway dashboard (Settings → Tokens)
#                            OR run `railway login` once and omit RAILWAY_TOKEN
#
# Optional:
#   PROJECT_NAME           — default: rasxot-bot
#   SERVICE_NAME           — default: api
#   SECRET_KEY             — auto-generated if unset
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v railway >/dev/null 2>&1; then
  echo "Install Railway CLI: npm install -g @railway/cli"
  exit 1
fi

: "${BOT_TOKEN:?Set BOT_TOKEN (from @BotFather)}"
: "${OWNER_TELEGRAM_ID:?Set OWNER_TELEGRAM_ID (your Telegram numeric id)}"

PROJECT_NAME="${PROJECT_NAME:-rasxot-bot}"
SERVICE_NAME="${SERVICE_NAME:-api}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"

if [[ -n "${RAILWAY_TOKEN:-}" ]]; then
  export RAILWAY_TOKEN
fi

if ! railway whoami >/dev/null 2>&1; then
  echo "Not logged in. Either:"
  echo "  1) export RAILWAY_TOKEN=<project-token>   (recommended for automation)"
  echo "  2) railway login"
  exit 1
fi

link_status="$(railway status --json 2>/dev/null || echo '{}')"
if ! echo "$link_status" | grep -q '"project"'; then
  echo "Creating Railway project: $PROJECT_NAME"
  railway init --name "$PROJECT_NAME" --json >/dev/null
fi

# Postgres (skip if already present)
if ! railway variable list --json 2>/dev/null | grep -q 'DATABASE_URL'; then
  echo "Adding PostgreSQL..."
  railway add --database postgres --json >/dev/null || true
fi

# App service
if ! railway service 2>/dev/null | grep -q "$SERVICE_NAME"; then
  echo "Adding service: $SERVICE_NAME"
  railway add --service "$SERVICE_NAME" --json >/dev/null || true
fi

railway service link "$SERVICE_NAME" 2>/dev/null || railway service "$SERVICE_NAME" 2>/dev/null || true

echo "Setting environment variables..."
railway variable set \
  APP_NAME="Oylik Rasxot Bot" \
  BOT_TOKEN="$BOT_TOKEN" \
  OWNER_TELEGRAM_ID="$OWNER_TELEGRAM_ID" \
  SECRET_KEY="$SECRET_KEY" \
  TIMEZONE="Asia/Tashkent" \
  --service "$SERVICE_NAME" \
  --skip-deploys

# Wire Postgres; config.py normalizes postgresql:// → postgresql+psycopg://
railway variable set DATABASE_URL='${{Postgres.DATABASE_URL}}' \
  --service "$SERVICE_NAME" \
  --skip-deploys 2>/dev/null || \
railway variable set DATABASE_URL='${{PostgreSQL.DATABASE_URL}}' \
  --service "$SERVICE_NAME" \
  --skip-deploys 2>/dev/null || true

echo "Generating public domain..."
DOMAIN_JSON="$(railway domain --service "$SERVICE_NAME" --json 2>/dev/null || echo '[]')"
BASE_URL="$(echo "$DOMAIN_JSON" | python3 -c "
import json, sys
raw = sys.stdin.read().strip()
if not raw:
    sys.exit(1)
data = json.loads(raw)
if isinstance(data, list) and data:
    print(data[0].get('domain') or data[0].get('url', ''))
elif isinstance(data, dict):
    print(data.get('domain') or data.get('url', ''))
" 2>/dev/null || true)"

if [[ -z "${BASE_URL:-}" ]]; then
  echo "Could not parse domain from CLI. Set APP_BASE_URL manually in Railway, then run:"
  echo "  ./scripts/set_webhook.sh https://YOUR_DOMAIN"
  railway up --service "$SERVICE_NAME" --detach
  exit 0
fi

[[ "$BASE_URL" != https://* ]] && BASE_URL="https://${BASE_URL}"

railway variable set \
  APP_BASE_URL="$BASE_URL" \
  WEBAPP_URL="${BASE_URL}/app" \
  --service "$SERVICE_NAME" \
  --skip-deploys

echo "Deploying to Railway..."
railway up --service "$SERVICE_NAME" --detach

echo "Waiting for health check..."
for i in $(seq 1 30); do
  if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    echo "Service is up: ${BASE_URL}/health"
    break
  fi
  sleep 5
done

echo "Registering Telegram webhook..."
"$ROOT/scripts/set_webhook.sh" "$BASE_URL"

echo ""
echo "Done."
echo "  App URL:    $BASE_URL"
echo "  Mini App:   ${BASE_URL}/app"
echo "  Webhook:    ${BASE_URL}/bot/webhook"
echo ""
echo "In Telegram, open @oylikrasxot_bot and send /start"
echo "In @BotFather → Bot Settings → Menu Button / Web App, set URL to: ${BASE_URL}/app"
