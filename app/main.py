from datetime import datetime

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.routes import router as api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, get_db
from app.models import Debt, DebtRepayment, Expense, Income, User  # noqa: F401
from app.services.auth import ensure_owner, get_or_create_user
from app.services.telegram import send_message, set_webhook


app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/bot/webhook")
async def telegram_webhook(update: dict, db: Session = Depends(get_db)):
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    text = (message.get("text") or "").strip()

    chat_id = chat.get("id")
    telegram_user_id = from_user.get("id")
    username = from_user.get("username")

    if not chat_id or not telegram_user_id:
        return JSONResponse({"ok": True})

    try:
        ensure_owner(int(telegram_user_id))
    except Exception:
        await send_message(chat_id, "Доступ только для владельца бота.")
        return JSONResponse({"ok": True})

    get_or_create_user(db, int(telegram_user_id), username)

    if text.startswith("/start"):
        await send_message(
            chat_id,
            "Привет! Я помогу вести ежемесячные расходы в UZS. Нажмите кнопку ниже, чтобы открыть мини-приложение.",
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "Открыть приложение",
                            "web_app": {"url": settings.webapp_url},
                        }
                    ]
                ]
            },
        )
    elif text.startswith("/help"):
        await send_message(
            chat_id,
            "Помощь / Yordam:\n"
            "/start — открыть мини-приложение / mini-ilovani ochish\n"
            "/help — эта подсказка / shu yordam matni\n\n"
            "Как использовать / Qanday ishlatish:\n"
            "1) Добавьте расход в разделе «Добавить расход».\n"
            "   1) «Xarajat qo‘shish» bo‘limida xarajat kiriting.\n"
            "2) Добавьте доход (salary/bonus/KPI) в разделе «Добавить доход».\n"
            "   2) «Daromad qo‘shish» bo‘limida salary/bonus/KPI kiriting.\n"
            "3) В «Сводка за месяц» выберите год и месяц, нажмите «Обновить».\n"
            "   3) «Oylik hisobot»da yil va oyni tanlab «Yangilash» bosing.\n"
            "4) В «Операции за месяц» можно исправить или удалить ошибочную запись.\n"
            "   4) «Oylik operatsiyalar»da noto‘g‘ri yozuvni tahrirlash yoki o‘chirish mumkin.\n"
            "5) Во вкладке «Долги» ведите, кому вы дали в долг и кому должны, "
            "с частичными платежами.\n"
            "   5) «Qarzlar» bo‘limida kimga qarz bergan va kimdan qarz olganingizni, "
            "qisman to‘lovlar bilan yuriting.\n"
            "Язык интерфейса можно переключать кнопкой RU/UZ.\n"
            "Interfeys tilini RU/UZ tugmasi bilan almashtirish mumkin.\n"
            "Сводка и график обновляются автоматически после изменений.\n"
            "O‘zgartirishdan keyin hisobot va grafik avtomatik yangilanadi.",
        )

    return JSONResponse({"ok": True})


@app.post("/bot/set-webhook")
async def configure_webhook():
    webhook = f"{settings.app_base_url}/bot/webhook"
    await set_webhook(webhook)
    return {"status": "ok", "webhook": webhook}


@app.get("/app", response_class=HTMLResponse)
def webapp_page(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "api_base": "/api",
            "year": datetime.now().year,
            "month": datetime.now().month,
        },
    )


app.include_router(api_router)
