from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User
from app.schemas import ExpenseCreate
from app.services.expenses import create_expense, monthly_summary


def test_create_and_monthly_summary_flow():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    user = User(telegram_user_id=1, username="owner")
    db.add(user)
    db.commit()
    db.refresh(user)

    create_expense(
        db,
        user.id,
        ExpenseCreate(
            category_key="transportation",
            amount_uzs=15000,
            expense_date=date(2026, 5, 10),
            note="taxi",
        ),
    )
    create_expense(
        db,
        user.id,
        ExpenseCreate(
            category_key="market",
            amount_uzs=45000,
            expense_date=date(2026, 5, 11),
            note=None,
        ),
    )

    summary = monthly_summary(db, user.id, 2026, 5)
    assert summary.month_total_uzs == 60000
    assert summary.entry_count == 2
    assert len(summary.by_category) == 2
