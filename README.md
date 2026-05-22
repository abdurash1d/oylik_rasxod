# oylikrasxot_bot (Telegram Mini App, RU, UZS)

Telegram Mini App for monthly spending tracking in UZS by categories.

## Features
- FastAPI backend with PostgreSQL
- Telegram bot commands: `/start`, `/help`
- Mini App form for manual expense entry
- Monthly summary + category chart
- Single-user access by `OWNER_TELEGRAM_ID`

## Categories
- transportation
- market
- health
- shopping
- personal_care
- miscellaneous
- food_groceries
- utilities
- housing
- others

## Quick start (local)
1. Create `.env` from `.env.example`
2. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Deploy on Render

### Option A: Blueprint (recommended)
1. Push this repo to GitHub.
2. In Render: **New +** -> **Blueprint** -> connect the repo.
3. Render reads `render.yaml` and creates:
   - Web service `oylikrasxot-bot`
   - Postgres database `oylikrasxot-db`
4. In web service Environment variables, set:
   - `BOT_TOKEN`
   - `OWNER_TELEGRAM_ID`
   - `APP_BASE_URL` = `https://YOUR-SERVICE.onrender.com`
   - `WEBAPP_URL` = `https://YOUR-SERVICE.onrender.com/app`
5. Deploy.

### Option B: Manual in Render UI
1. Create Postgres on Render.
2. Create Web Service from this repo.
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars from `.env.render.example` and attach `DATABASE_URL` from Postgres.

## Set Telegram webhook
After service is live:

```bash
./scripts/set_webhook.sh https://YOUR-SERVICE.onrender.com
```

## Final Telegram steps
1. Open `@oylikrasxot_bot`
2. Send `/start`
3. In BotFather, set Mini App/Menu Button URL to:
   `https://YOUR-SERVICE.onrender.com/app`

## Security note
Your old token was exposed in chat. Keep only the rotated token and never commit `.env`.
