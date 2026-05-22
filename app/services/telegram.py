from typing import Optional

import httpx

from app.core.config import settings


API_BASE = "https://api.telegram.org/bot"


def api_url(method: str) -> str:
    return "{0}{1}/{2}".format(API_BASE, settings.bot_token, method)


async def send_message(chat_id: int, text: str, reply_markup: Optional[dict] = None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=20.0) as client:
        await client.post(api_url("sendMessage"), json=payload)


async def set_webhook(webhook_url: str):
    async with httpx.AsyncClient(timeout=20.0) as client:
        await client.post(api_url("setWebhook"), json={"url": webhook_url})
