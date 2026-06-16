from typing import List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.income import Income
from app.schemas import MonthStat, TrendResponse
from app.services.expenses import month_date_range


def month_totals(db: Session, user_id: int, year: int, month: int) -> Tuple[int, int]:
    """Return (income_total, expense_total) for the given month."""
    start, end = month_date_range(year, month)
    income = (
        db.query(func.coalesce(func.sum(Income.amount_uzs), 0))
        .filter(Income.user_id == user_id, Income.income_date >= start, Income.income_date <= end)
        .scalar()
    )
    expense = (
        db.query(func.coalesce(func.sum(Expense.amount_uzs), 0))
        .filter(Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .scalar()
    )
    return int(income or 0), int(expense or 0)


def total_saved(db: Session, user_id: int) -> int:
    """Lifetime accumulated savings: all income minus all expenses."""
    income = (
        db.query(func.coalesce(func.sum(Income.amount_uzs), 0))
        .filter(Income.user_id == user_id)
        .scalar()
    )
    expense = (
        db.query(func.coalesce(func.sum(Expense.amount_uzs), 0))
        .filter(Expense.user_id == user_id)
        .scalar()
    )
    return int(income or 0) - int(expense or 0)


def savings_rate(income: int, expense: int) -> int:
    """Saved share of income as a whole-number percent (can be negative)."""
    if income <= 0:
        return 0
    return round((income - expense) / income * 100)


def prev_month(year: int, month: int) -> Tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def monthly_trend(db: Session, user_id: int, year: int, month: int, months: int = 6) -> TrendResponse:
    """Oldest-first list of monthly stats ending at (year, month)."""
    sequence: List[Tuple[int, int]] = []
    y, m = year, month
    for _ in range(months):
        sequence.append((y, m))
        y, m = prev_month(y, m)
    sequence.reverse()

    rows: List[MonthStat] = []
    for yy, mm in sequence:
        income, expense = month_totals(db, user_id, yy, mm)
        rows.append(
            MonthStat(
                year=yy,
                month=mm,
                income_total_uzs=income,
                expense_total_uzs=expense,
                saved_uzs=income - expense,
                savings_rate_pct=savings_rate(income, expense),
            )
        )
    return TrendResponse(months=rows)
