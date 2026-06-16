from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.income_types import IncomeType
from app.models.user import User
from app.schemas import ExpenseCreate, IncomeCreate, SettingsUpdate
from app.services.expenses import create_expense, create_income
from app.services.insights import build_insights
from app.services.settings import get_or_create_settings, settings_out, update_settings


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


def test_defaults_created():
    db, uid = make_db()
    s = settings_out(get_or_create_settings(db, uid))
    assert s.savings_target_pct == 20
    assert s.emergency_months == 3
    assert s.category_budgets == {}
    assert s.display_name is None


def test_update_profile_and_targets():
    db, uid = make_db()
    update_settings(db, uid, SettingsUpdate(
        display_name="  Abdurashid  ", about="Saving for a car",
        savings_target_pct=30, emergency_months=6,
    ))
    s = settings_out(get_or_create_settings(db, uid))
    assert s.display_name == "Abdurashid"  # trimmed
    assert s.about == "Saving for a car"
    assert s.savings_target_pct == 30
    assert s.emergency_months == 6


def test_budget_validation_drops_nonpositive():
    db, uid = make_db()
    update_settings(db, uid, SettingsUpdate(
        category_budgets={"food_groceries": 500000, "housing": 0, "market": -5},
    ))
    s = settings_out(get_or_create_settings(db, uid))
    assert s.category_budgets == {"food_groceries": 500000}


def test_configurable_savings_target_changes_level():
    db, uid = make_db()
    create_income(db, uid, IncomeCreate(income_type_key=IncomeType.SALARY.value, amount_uzs=1_000_000, income_date=date(2026, 6, 1), note=None))
    create_expense(db, uid, ExpenseCreate(category_key="food_groceries", amount_uzs=750_000, expense_date=date(2026, 6, 3), note=None))
    # rate = 25%
    assert build_insights(db, uid, 2026, 6).savings_level == "good"  # default target 20
    update_settings(db, uid, SettingsUpdate(savings_target_pct=40))
    assert build_insights(db, uid, 2026, 6).savings_level == "ok"  # 25 >= 20 (half of 40)


def test_budget_over_insight():
    db, uid = make_db()
    create_income(db, uid, IncomeCreate(income_type_key=IncomeType.SALARY.value, amount_uzs=2_000_000, income_date=date(2026, 6, 1), note=None))
    create_expense(db, uid, ExpenseCreate(category_key="food_groceries", amount_uzs=600_000, expense_date=date(2026, 6, 3), note=None))
    update_settings(db, uid, SettingsUpdate(category_budgets={"food_groceries": 400_000}))
    resp = build_insights(db, uid, 2026, 6)
    over = next(i for i in resp.insights if i.code == "budget_over")
    assert over.params["category_key"] == "food_groceries"
    assert over.params["spent"] == 600_000
    assert over.params["limit"] == 400_000
    assert over.params["pct"] == 150
