from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    CategoriesResponse,
    DebtCreate,
    DebtsResponse,
    DebtUpdate,
    InsightsResponse,
    TrendResponse,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    IncomeCreate,
    IncomeOut,
    IncomeUpdate,
    LedgerResponse,
    IncomeTypesResponse,
    MonthlySummary,
    RepaymentCreate,
    categories_payload,
    category_key_to_label,
    category_key_to_label_uz,
    income_type_key_to_label_ru,
    income_type_key_to_label_uz,
    income_types_payload,
)
from app.services.auth import ensure_owner, get_or_create_user
from app.services.debts import (
    add_repayment,
    create_debt,
    delete_debt,
    delete_repayment,
    list_debts,
    settle_debt,
    update_debt,
)
from app.services.insights import build_insights
from app.services.stats import monthly_trend
from app.services.expenses import (
    chart_summary,
    create_expense,
    create_income,
    delete_expense,
    delete_income,
    list_monthly_ledger,
    monthly_summary,
    update_expense,
    update_income,
)


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


@router.get("/income-types", response_model=IncomeTypesResponse)
def get_income_types():
    return income_types_payload()


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
        category_label_uz=category_key_to_label_uz(record.category),
        amount_uzs=record.amount_uzs,
        expense_date=record.expense_date,
        note=record.note,
    )


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut)
def edit_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    try:
        record = update_expense(db, user.id, expense_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Расход не найден")
    return ExpenseOut(
        id=record.id,
        category_key=record.category,
        category_label_ru=category_key_to_label(record.category),
        category_label_uz=category_key_to_label_uz(record.category),
        amount_uzs=record.amount_uzs,
        expense_date=record.expense_date,
        note=record.note,
    )


@router.delete("/expenses/{expense_id}")
def remove_expense(
    expense_id: int,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    ok = delete_expense(db, user.id, expense_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Расход не найден")
    return {"status": "ok"}


@router.post("/incomes", response_model=IncomeOut)
def add_income(
    payload: IncomeCreate,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    record = create_income(db, user.id, payload)
    return IncomeOut(
        id=record.id,
        income_type_key=record.income_type,
        income_type_label_ru=income_type_key_to_label_ru(record.income_type),
        income_type_label_uz=income_type_key_to_label_uz(record.income_type),
        amount_uzs=record.amount_uzs,
        income_date=record.income_date,
        note=record.note,
    )


@router.patch("/incomes/{income_id}", response_model=IncomeOut)
def edit_income(
    income_id: int,
    payload: IncomeUpdate,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    try:
        record = update_income(db, user.id, income_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Доход не найден")
    return IncomeOut(
        id=record.id,
        income_type_key=record.income_type,
        income_type_label_ru=income_type_key_to_label_ru(record.income_type),
        income_type_label_uz=income_type_key_to_label_uz(record.income_type),
        amount_uzs=record.amount_uzs,
        income_date=record.income_date,
        note=record.note,
    )


@router.delete("/incomes/{income_id}")
def remove_income(
    income_id: int,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    ok = delete_income(db, user.id, income_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Доход не найден")
    return {"status": "ok"}


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


@router.get("/ledger/month", response_model=LedgerResponse)
def get_month_ledger(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    return LedgerResponse(entries=list_monthly_ledger(db, user.id, year, month))


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


# ===== Insights & statistics =====

@router.get("/insights", response_model=InsightsResponse)
def get_insights(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    return build_insights(db, user.id, year, month)


@router.get("/stats/trend", response_model=TrendResponse)
def get_trend(
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
    months: int = Query(default=6, ge=1, le=24),
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    return monthly_trend(db, user.id, year, month, months)


# ===== Debts (qarz) =====

def _debt_value_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "not found" in message:
        return HTTPException(status_code=404, detail="Долг не найден")
    if "exceeds outstanding" in message:
        return HTTPException(status_code=400, detail="Сумма больше остатка долга")
    return HTTPException(status_code=400, detail=message)


@router.get("/debts", response_model=DebtsResponse)
def get_debts(
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    return list_debts(db, user.id)


@router.post("/debts", response_model=DebtsResponse)
def add_debt(
    payload: DebtCreate,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    create_debt(db, user.id, payload)
    return list_debts(db, user.id)


@router.patch("/debts/{debt_id}", response_model=DebtsResponse)
def edit_debt(
    debt_id: int,
    payload: DebtUpdate,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    try:
        update_debt(db, user.id, debt_id, payload)
    except ValueError as exc:
        raise _debt_value_error(exc)
    return list_debts(db, user.id)


@router.delete("/debts/{debt_id}")
def remove_debt(
    debt_id: int,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    if not delete_debt(db, user.id, debt_id):
        raise HTTPException(status_code=404, detail="Долг не найден")
    return {"status": "ok"}


@router.post("/debts/{debt_id}/repayments", response_model=DebtsResponse)
def add_debt_repayment(
    debt_id: int,
    payload: RepaymentCreate,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    try:
        add_repayment(db, user.id, debt_id, payload)
    except ValueError as exc:
        raise _debt_value_error(exc)
    return list_debts(db, user.id)


@router.post("/debts/{debt_id}/settle", response_model=DebtsResponse)
def settle_debt_route(
    debt_id: int,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    try:
        settle_debt(db, user.id, debt_id, datetime.now().date())
    except ValueError as exc:
        raise _debt_value_error(exc)
    return list_debts(db, user.id)


@router.delete("/debts/{debt_id}/repayments/{repayment_id}")
def remove_debt_repayment(
    debt_id: int,
    repayment_id: int,
    x_telegram_user_id: Optional[int] = Header(default=None, alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(default=None, alias="X-Telegram-Username"),
    db: Session = Depends(get_db),
):
    user = owner_user(db, x_telegram_user_id, x_telegram_username)
    if not delete_repayment(db, user.id, debt_id, repayment_id):
        raise HTTPException(status_code=404, detail="Платёж не найден")
    return {"status": "ok"}
