from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import ExpenseCreate


def test_expense_validation_success():
    payload = ExpenseCreate(
        category_key="food_groceries",
        amount_uzs=35000,
        expense_date=date(2026, 5, 1),
    )
    assert payload.amount_uzs == 35000


def test_expense_validation_invalid_category():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            category_key="invalid",
            amount_uzs=10000,
            expense_date=date(2026, 5, 1),
        )


def test_expense_validation_amount_positive():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            category_key="market",
            amount_uzs=0,
            expense_date=date(2026, 5, 1),
        )
