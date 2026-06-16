from calendar import monthrange
from datetime import date
from typing import List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.categories import CATEGORY_LABELS_RU, CATEGORY_LABELS_UZ, CategoryKey
from app.models.expense import Expense
from app.models.income import Income
from app.models.income_types import INCOME_LABELS_RU, INCOME_LABELS_UZ, IncomeType
from app.schemas import (
    CategorySummary,
    ChartSummary,
    ExpenseCreate,
    ExpenseUpdate,
    IncomeCreate,
    IncomeUpdate,
    LedgerRow,
    MonthlySummary,
)


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


def create_income(db: Session, user_id: int, payload: IncomeCreate) -> Income:
    record = Income(
        user_id=user_id,
        income_type=payload.income_type_key,
        amount_uzs=payload.amount_uzs,
        income_date=payload.income_date,
        note=payload.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_monthly_ledger(db: Session, user_id: int, year: int, month: int) -> List[LedgerRow]:
    start, end = month_date_range(year, month)
    expense_rows = (
        db.query(Expense)
        .filter(Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .all()
    )
    income_rows = (
        db.query(Income)
        .filter(Income.user_id == user_id, Income.income_date >= start, Income.income_date <= end)
        .all()
    )

    rows: List[LedgerRow] = [
        LedgerRow(
            entry_type="expense",
            id=item.id,
            date=item.expense_date,
            amount_uzs=item.amount_uzs,
            note=item.note,
            label_ru=CATEGORY_LABELS_RU[CategoryKey(item.category)],
            label_uz=CATEGORY_LABELS_UZ[CategoryKey(item.category)],
            raw_key=item.category,
        )
        for item in expense_rows
    ] + [
        LedgerRow(
            entry_type="income",
            id=item.id,
            date=item.income_date,
            amount_uzs=item.amount_uzs,
            note=item.note,
            label_ru=INCOME_LABELS_RU[IncomeType(item.income_type)],
            label_uz=INCOME_LABELS_UZ[IncomeType(item.income_type)],
            raw_key=item.income_type,
        )
        for item in income_rows
    ]
    return sorted(rows, key=lambda x: (x.date, x.id), reverse=True)


def update_expense(db: Session, user_id: int, expense_id: int, payload: ExpenseUpdate) -> Expense:
    record = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == user_id).first()
    if not record:
        raise ValueError("Expense not found")
    if payload.category_key is not None:
        record.category = payload.category_key
    if payload.amount_uzs is not None:
        record.amount_uzs = payload.amount_uzs
    if payload.expense_date is not None:
        record.expense_date = payload.expense_date
    if "note" in payload.model_fields_set:
        record.note = payload.note
    db.commit()
    db.refresh(record)
    return record


def delete_expense(db: Session, user_id: int, expense_id: int) -> bool:
    record = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == user_id).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def update_income(db: Session, user_id: int, income_id: int, payload: IncomeUpdate) -> Income:
    record = db.query(Income).filter(Income.id == income_id, Income.user_id == user_id).first()
    if not record:
        raise ValueError("Income not found")
    if payload.income_type_key is not None:
        record.income_type = payload.income_type_key
    if payload.amount_uzs is not None:
        record.amount_uzs = payload.amount_uzs
    if payload.income_date is not None:
        record.income_date = payload.income_date
    if "note" in payload.model_fields_set:
        record.note = payload.note
    db.commit()
    db.refresh(record)
    return record


def delete_income(db: Session, user_id: int, income_id: int) -> bool:
    record = db.query(Income).filter(Income.id == income_id, Income.user_id == user_id).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def monthly_summary(db: Session, user_id: int, year: int, month: int) -> MonthlySummary:
    start, end = month_date_range(year, month)

    rows = (
        db.query(Expense.category, func.sum(Expense.amount_uzs).label("total"))
        .filter(Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .group_by(Expense.category)
        .all()
    )

    expense_count = (
        db.query(func.count(Expense.id))
        .filter(Expense.user_id == user_id, Expense.expense_date >= start, Expense.expense_date <= end)
        .scalar()
    )
    income_total = (
        db.query(func.sum(Income.amount_uzs))
        .filter(Income.user_id == user_id, Income.income_date >= start, Income.income_date <= end)
        .scalar()
    )
    income_count = (
        db.query(func.count(Income.id))
        .filter(Income.user_id == user_id, Income.income_date >= start, Income.income_date <= end)
        .scalar()
    )

    by_category = [
        CategorySummary(
            category_key=category,
            category_label_ru=CATEGORY_LABELS_RU[CategoryKey(category)],
            category_label_uz=CATEGORY_LABELS_UZ[CategoryKey(category)],
            total_uzs=int(total or 0),
        )
        for category, total in rows
    ]

    expense_total = sum(item.total_uzs for item in by_category)
    income_total_value = int(income_total or 0)
    return MonthlySummary(
        expense_total_uzs=expense_total,
        income_total_uzs=income_total_value,
        balance_uzs=income_total_value - expense_total,
        by_category=sorted(by_category, key=lambda x: x.total_uzs, reverse=True),
        expense_entry_count=int(expense_count or 0),
        income_entry_count=int(income_count or 0),
    )


def chart_summary(db: Session, user_id: int, year: int, month: int) -> ChartSummary:
    summary = monthly_summary(db, user_id, year, month)
    return ChartSummary(
        labels=[item.category_label_ru for item in summary.by_category],
        values=[item.total_uzs for item in summary.by_category],
        keys=[item.category_key for item in summary.by_category],
    )
