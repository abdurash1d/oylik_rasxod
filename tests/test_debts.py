from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User
from app.schemas import DebtCreate, DebtUpdate, RepaymentCreate
from app.services.debts import (
    add_repayment,
    create_debt,
    delete_debt,
    delete_repayment,
    list_debts,
    settle_debt,
    update_debt,
)


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


def test_create_repay_and_totals():
    db, user_id = make_db()
    debt = create_debt(
        db,
        user_id,
        DebtCreate(
            counterparty="Aziz",
            direction="lent",
            principal_amount_uzs=500000,
            debt_date=date(2026, 6, 1),
            note=None,
        ),
    )
    add_repayment(
        db,
        user_id,
        debt.id,
        RepaymentCreate(amount_uzs=200000, repayment_date=date(2026, 6, 10), note=None),
    )

    response = list_debts(db, user_id)
    assert len(response.debts) == 1
    out = response.debts[0]
    assert out.outstanding_uzs == 300000
    assert out.settled is False
    assert len(out.repayments) == 1
    assert response.totals.lent_outstanding == 300000
    assert response.totals.borrowed_outstanding == 0
    assert response.totals.net == 300000


def test_overpayment_rejected():
    db, user_id = make_db()
    debt = create_debt(
        db,
        user_id,
        DebtCreate(
            counterparty="Aziz",
            direction="lent",
            principal_amount_uzs=300000,
            debt_date=date(2026, 6, 1),
            note=None,
        ),
    )
    add_repayment(
        db, user_id, debt.id,
        RepaymentCreate(amount_uzs=300000, repayment_date=date(2026, 6, 5), note=None),
    )
    with pytest.raises(ValueError):
        add_repayment(
            db, user_id, debt.id,
            RepaymentCreate(amount_uzs=1, repayment_date=date(2026, 6, 6), note=None),
        )


def test_settle_marks_paid():
    db, user_id = make_db()
    debt = create_debt(
        db, user_id,
        DebtCreate(
            counterparty="Dilshod", direction="borrowed",
            principal_amount_uzs=200000, debt_date=date(2026, 6, 1), note=None,
        ),
    )
    settle_debt(db, user_id, debt.id, date(2026, 6, 12))
    response = list_debts(db, user_id)
    out = response.debts[0]
    assert out.outstanding_uzs == 0
    assert out.settled is True
    assert response.totals.borrowed_outstanding == 0
    assert response.totals.net == 0


def test_delete_debt_cascades_repayments():
    db, user_id = make_db()
    debt = create_debt(
        db, user_id,
        DebtCreate(
            counterparty="Aziz", direction="lent",
            principal_amount_uzs=500000, debt_date=date(2026, 6, 1), note=None,
        ),
    )
    add_repayment(
        db, user_id, debt.id,
        RepaymentCreate(amount_uzs=100000, repayment_date=date(2026, 6, 5), note=None),
    )
    assert delete_debt(db, user_id, debt.id) is True
    assert len(list_debts(db, user_id).debts) == 0


def test_update_debt_fields():
    db, user_id = make_db()
    debt = create_debt(
        db, user_id,
        DebtCreate(
            counterparty="Aziz", direction="lent",
            principal_amount_uzs=500000, debt_date=date(2026, 6, 1), note=None,
        ),
    )
    update_debt(db, user_id, debt.id, DebtUpdate(counterparty="Aziz K.", principal_amount_uzs=600000))
    out = list_debts(db, user_id).debts[0]
    assert out.counterparty == "Aziz K."
    assert out.principal_amount_uzs == 600000
    assert out.outstanding_uzs == 600000


def test_delete_single_repayment_restores_outstanding():
    db, user_id = make_db()
    debt = create_debt(
        db, user_id,
        DebtCreate(
            counterparty="Aziz", direction="lent",
            principal_amount_uzs=500000, debt_date=date(2026, 6, 1), note=None,
        ),
    )
    rep = add_repayment(
        db, user_id, debt.id,
        RepaymentCreate(amount_uzs=200000, repayment_date=date(2026, 6, 5), note=None),
    )
    assert delete_repayment(db, user_id, debt.id, rep.id) is True
    out = list_debts(db, user_id).debts[0]
    assert out.outstanding_uzs == 500000
