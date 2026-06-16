from datetime import date
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, field_validator

DEBT_DIRECTIONS = {"lent", "borrowed"}

from app.models.categories import CategoryKey, CATEGORY_LABELS_RU, CATEGORY_LABELS_UZ, category_options
from app.models.income_types import IncomeType, INCOME_LABELS_RU, INCOME_LABELS_UZ, income_type_options


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
    category_label_uz: str
    amount_uzs: int
    expense_date: date
    note: Optional[str]


class ExpenseUpdate(BaseModel):
    category_key: Optional[str] = None
    amount_uzs: Optional[int] = Field(default=None, gt=0)
    expense_date: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=1024)

    @field_validator("category_key")
    @classmethod
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        valid = {k.value for k in CategoryKey}
        if value not in valid:
            raise ValueError("Неверная категория")
        return value


class CategorySummary(BaseModel):
    category_key: str
    category_label_ru: str
    category_label_uz: str
    total_uzs: int


class MonthlySummary(BaseModel):
    expense_total_uzs: int
    income_total_uzs: int
    balance_uzs: int
    by_category: List[CategorySummary]
    expense_entry_count: int
    income_entry_count: int


class ChartSummary(BaseModel):
    labels: List[str]
    values: List[int]
    keys: List[str]


class CategoriesResponse(BaseModel):
    categories: List[Dict[str, str]]


class IncomeTypeItem(BaseModel):
    key: str
    label_ru: str
    label_uz: str


class IncomeTypesResponse(BaseModel):
    income_types: List[IncomeTypeItem]


class IncomeCreate(BaseModel):
    income_type_key: str
    amount_uzs: int = Field(gt=0)
    income_date: date
    note: Optional[str] = Field(default=None, max_length=1024)

    @field_validator("income_type_key")
    @classmethod
    def validate_income_type(cls, value: str) -> str:
        valid = {k.value for k in IncomeType}
        if value not in valid:
            raise ValueError("Неверный тип дохода")
        return value


class IncomeOut(BaseModel):
    id: int
    income_type_key: str
    income_type_label_ru: str
    income_type_label_uz: str
    amount_uzs: int
    income_date: date
    note: Optional[str]


class IncomeUpdate(BaseModel):
    income_type_key: Optional[str] = None
    amount_uzs: Optional[int] = Field(default=None, gt=0)
    income_date: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=1024)

    @field_validator("income_type_key")
    @classmethod
    def validate_income_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        valid = {k.value for k in IncomeType}
        if value not in valid:
            raise ValueError("Неверный тип дохода")
        return value


class LedgerRow(BaseModel):
    entry_type: str
    id: int
    date: date
    amount_uzs: int
    note: Optional[str]
    label_ru: str
    label_uz: str
    raw_key: str


class LedgerResponse(BaseModel):
    entries: List[LedgerRow]


class DebtCreate(BaseModel):
    counterparty: str = Field(min_length=1, max_length=255)
    direction: str
    principal_amount_uzs: int = Field(gt=0)
    debt_date: date
    note: Optional[str] = Field(default=None, max_length=1024)

    @field_validator("counterparty")
    @classmethod
    def trim_counterparty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Укажите имя")
        return trimmed

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in DEBT_DIRECTIONS:
            raise ValueError("Неверный тип долга")
        return value


class DebtUpdate(BaseModel):
    counterparty: Optional[str] = Field(default=None, max_length=255)
    direction: Optional[str] = None
    principal_amount_uzs: Optional[int] = Field(default=None, gt=0)
    debt_date: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=1024)

    @field_validator("counterparty")
    @classmethod
    def trim_counterparty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Укажите имя")
        return trimmed

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in DEBT_DIRECTIONS:
            raise ValueError("Неверный тип долга")
        return value


class RepaymentCreate(BaseModel):
    amount_uzs: int = Field(gt=0)
    repayment_date: date
    note: Optional[str] = Field(default=None, max_length=1024)


class RepaymentOut(BaseModel):
    id: int
    amount_uzs: int
    repayment_date: date
    note: Optional[str]


class DebtOut(BaseModel):
    id: int
    counterparty: str
    direction: str
    principal_amount_uzs: int
    debt_date: date
    note: Optional[str]
    outstanding_uzs: int
    settled: bool
    repayments: List[RepaymentOut]


class DebtTotals(BaseModel):
    lent_outstanding: int
    borrowed_outstanding: int
    net: int


class DebtsResponse(BaseModel):
    debts: List[DebtOut]
    totals: DebtTotals


def category_key_to_label(key: str) -> str:
    return CATEGORY_LABELS_RU[CategoryKey(key)]


def category_key_to_label_uz(key: str) -> str:
    return CATEGORY_LABELS_UZ[CategoryKey(key)]


def categories_payload() -> CategoriesResponse:
    return CategoriesResponse(categories=category_options())


def income_type_key_to_label_ru(key: str) -> str:
    return INCOME_LABELS_RU[IncomeType(key)]


def income_type_key_to_label_uz(key: str) -> str:
    return INCOME_LABELS_UZ[IncomeType(key)]


def income_types_payload() -> IncomeTypesResponse:
    return IncomeTypesResponse(
        income_types=[
            IncomeTypeItem(
                key=item["key"],
                label_ru=item["label_ru"],
                label_uz=item["label_uz"],
            )
            for item in income_type_options()
        ]
    )
