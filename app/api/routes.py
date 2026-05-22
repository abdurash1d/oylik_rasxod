from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    CategoriesResponse,
    ExpenseCreate,
    ExpenseOut,
    MonthlySummary,
    categories_payload,
    category_key_to_label,
)
from app.services.auth import ensure_owner, get_or_create_user
from app.services.expenses import chart_summary, create_expense, monthly_summary


router = APIRouter(prefix="/api", tags=["api"])


def owner_user(
    db: Session,
    x_telegram_user_id: Optional[int],
    x_telegram_username: Optional[str],
):
    if x_telegram_user_id is None:
        raise HTTPException(status_code=400, detail="Отсутствует заголовок X-Telegram-User-Id")
    ensure_owner(x_telegram_user_id)
    return get_or_create_user(db, x_telegram_user_id, x_telegram_username)


@router.get("/categories", response_model=CategoriesResponse)
def get_categories():
    return categories_payload()


@router.post("/expenses", response_model=ExpenseOut)
def add_expense(
    payload: ExpenseCreate,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    record = create_expense(db, user.id, payload)
    return ExpenseOut(
        id=record.id,
        category_key=record.category,
        category_label_ru=category_key_to_label(record.category),
        amount_uzs=record.amount_uzs,
        expense_date=record.expense_date,
        note=record.note,
    )


@router.get("/summary/month", response_model=MonthlySummary)
def get_month_summary(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    return monthly_summary(db, user.id, year, month)


@router.get("/summary/charts")
def get_chart_summary(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    return chart_summary(db, user.id, year, month)
