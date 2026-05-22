from datetime import date
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, field_validator

from app.models.categories import CategoryKey, CATEGORY_LABELS_RU, category_options


class ExpenseCreate(BaseModel):
    category_key: str
    amount_uzs: int = Field(gt=0)
    expense_date: date
    note: Optional[str] = Field(default=None, max_length=1024)

    @field_validator("category_key")
    @classmethod
    def validate_category(cls, value: str) -> str:
        valid = {k.value for k in CategoryKey}
        if value not in valid:
            raise ValueError("Неверная категория")
        return value


class ExpenseOut(BaseModel):
    id: int
    category_key: str
    category_label_ru: str
    amount_uzs: int
    expense_date: date
    note: Optional[str]


class CategorySummary(BaseModel):
    category_key: str
    category_label_ru: str
    total_uzs: int


class MonthlySummary(BaseModel):
    month_total_uzs: int
    by_category: List[CategorySummary]
    entry_count: int


class ChartSummary(BaseModel):
    labels: List[str]
    values: List[int]
    keys: List[str]


class CategoriesResponse(BaseModel):
    categories: List[Dict[str, str]]


def category_key_to_label(key: str) -> str:
    return CATEGORY_LABELS_RU[CategoryKey(key)]


def categories_payload() -> CategoriesResponse:
    return CategoriesResponse(categories=category_options())
