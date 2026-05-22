from calendar import monthrange
from datetime import date
from typing import Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.categories import CATEGORY_LABELS_RU, CategoryKey
from app.models.expense import Expense
from app.schemas import CategorySummary, ChartSummary, ExpenseCreate, MonthlySummary


def month_date_range(year: int, month: int) -> Tuple[date, date]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return start, end


def create_expense(db: Session, user_id: int, payload: ExpenseCreate) -> Expense:
    record = Expense(
        user_id=user_id,
        category=payload.category_key,
        amount_uzs=payload.amount_uzs,
        expense_date=payload.expense_date,
        note=payload.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def monthly_summary(db: Session, user_id: int, year: int, month: int) -> MonthlySummary:
    start, end = month_date_range(year, month)

    rows = (
        db.query(Expense.category, func.sum(Expense.amount_uzs).label("total"))
        .filter(Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .group_by(Expense.category)
        .all()
    )

    count = (
        db.query(func.count(Expense.id))
        .filter(Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .scalar()
    )

    by_category = [
        CategorySummary(
            category_key=category,
            category_label_ru=CATEGORY_LABELS_RU[CategoryKey(category)],
            total_uzs=int(total or 0),
        )
        for category, total in rows
    ]

    return MonthlySummary(
        month_total_uzs=sum(item.total_uzs for item in by_category),
        by_category=sorted(by_category, key=lambda x: x.total_uzs, reverse=True),
        entry_count=int(count or 0),
    )


def chart_summary(db: Session, user_id: int, year: int, month: int) -> ChartSummary:
    summary = monthly_summary(db, user_id, year, month)
    return ChartSummary(
        labels=[item.category_label_ru for item in summary.by_category],
        values=[item.total_uzs for item in summary.by_category],
        keys=[item.category_key for item in summary.by_category],
    )
