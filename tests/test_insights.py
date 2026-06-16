from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.income_types import IncomeType
from app.models.user import User
from app.schemas import DebtCreate, ExpenseCreate, IncomeCreate
from app.services.debts import create_debt
from app.services.expenses import create_expense, create_income
from app.services.insights import build_insights
from app.services.stats import monthly_trend, savings_rate


def make_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    user = User(telegram_user_id=1, username="owner")
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user.id


def add_expense(db, user_id, cat, amount, d):
    create_expense(db, user_id, ExpenseCreate(category_key=cat, amount_uzs=amount, expense_date=d, note=None))


def add_income(db, user_id, amount, d):
    create_income(db, user_id, IncomeCreate(income_type_key=IncomeType.SALARY.value, amount_uzs=amount, income_date=d, note=None))


def codes(resp):
    return {i.code for i in resp.insights}


def test_savings_rate_function():
    assert savings_rate(1000, 800) == 20
    assert savings_rate(0, 500) == 0
    assert savings_rate(1000, 1200) == -20


def test_no_data_month():
    db, uid = make_db()
    resp = build_insights(db, uid, 2026, 6)
    assert codes(resp) == {"no_data"}
    assert resp.savings_level == "none"


def test_healthy_month_is_positive():
    db, uid = make_db()
    add_income(db, uid, 1_000_000, date(2026, 6, 1))
    # Spread across categories so none dominates (>=35%).
    add_expense(db, uid, "food_groceries", 100_000, date(2026, 6, 3))
    add_expense(db, uid, "transportation", 80_000, date(2026, 6, 4))
    add_expense(db, uid, "housing", 70_000, date(2026, 6, 5))
    add_expense(db, uid, "shopping", 50_000, date(2026, 6, 6))
    resp = build_insights(db, uid, 2026, 6)
    assert resp.savings_rate_pct == 70
    assert resp.savings_level == "good"
    c = codes(resp)
    assert "savings_rate" in c
    assert "emergency_fund" in c
    assert "doing_great" in c
    assert "overspend" not in c


def test_overspend_flagged():
    db, uid = make_db()
    add_income(db, uid, 500_000, date(2026, 6, 1))
    add_expense(db, uid, "shopping", 800_000, date(2026, 6, 4))
    resp = build_insights(db, uid, 2026, 6)
    c = codes(resp)
    assert "overspend" in c
    assert "doing_great" not in c
    # Bad severity should sort first.
    assert resp.insights[0].severity == "bad"


def test_top_category_warns():
    db, uid = make_db()
    add_income(db, uid, 2_000_000, date(2026, 6, 1))
    add_expense(db, uid, "housing", 900_000, date(2026, 6, 2))
    add_expense(db, uid, "food_groceries", 100_000, date(2026, 6, 3))
    resp = build_insights(db, uid, 2026, 6)
    top = next(i for i in resp.insights if i.code == "top_category")
    assert top.params["category_key"] == "housing"
    assert top.params["pct"] == 90


def test_emergency_fund_target_and_months():
    db, uid = make_db()
    add_income(db, uid, 1_000_000, date(2026, 6, 1))
    add_expense(db, uid, "food_groceries", 200_000, date(2026, 6, 3))
    resp = build_insights(db, uid, 2026, 6)
    ef = next(i for i in resp.insights if i.code == "emergency_fund")
    assert ef.params["target"] == 600_000  # 3 x 200_000
    assert ef.params["months"] == 1  # saved 800_000 covers 600_000 in 1 month


def test_debt_owe_insight():
    db, uid = make_db()
    add_income(db, uid, 1_000_000, date(2026, 6, 1))
    add_expense(db, uid, "food_groceries", 300_000, date(2026, 6, 3))
    create_debt(db, uid, DebtCreate(counterparty="Bank", direction="borrowed",
                                    principal_amount_uzs=400_000, debt_date=date(2026, 6, 1), note=None))
    resp = build_insights(db, uid, 2026, 6)
    debt = next(i for i in resp.insights if i.code == "debt_owe")
    assert debt.params["amount"] == 400_000


def test_monthly_trend_length_and_values():
    db, uid = make_db()
    add_income(db, uid, 1_000_000, date(2026, 6, 1))
    add_expense(db, uid, "market", 400_000, date(2026, 6, 5))
    trend = monthly_trend(db, uid, 2026, 6, months=6)
    assert len(trend.months) == 6
    # Oldest first, current month last.
    assert (trend.months[-1].year, trend.months[-1].month) == (2026, 6)
    assert (trend.months[0].year, trend.months[0].month) == (2026, 1)
    last = trend.months[-1]
    assert last.income_total_uzs == 1_000_000
    assert last.expense_total_uzs == 400_000
    assert last.saved_uzs == 600_000
    assert last.savings_rate_pct == 60
