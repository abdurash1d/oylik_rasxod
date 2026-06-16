from datetime import date
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.models.debt import Debt, DebtRepayment
from app.schemas import (
    DebtCreate,
    DebtOut,
    DebtsResponse,
    DebtTotals,
    DebtUpdate,
    RepaymentCreate,
    RepaymentOut,
)


def _outstanding(debt: Debt) -> int:
    paid = sum(r.amount_uzs for r in debt.repayments)
    return debt.principal_amount_uzs - paid


def _get_debt(db: Session, user_id: int, debt_id: int) -> Debt:
    debt = (
        db.query(Debt)
        .options(selectinload(Debt.repayments))
        .filter(Debt.id == debt_id, Debt.user_id == user_id)
        .first()
    )
    if not debt:
        raise ValueError("Debt not found")
    return debt


def create_debt(db: Session, user_id: int, payload: DebtCreate) -> Debt:
    record = Debt(
        user_id=user_id,
        counterparty=payload.counterparty,
        direction=payload.direction,
        principal_amount_uzs=payload.principal_amount_uzs,
        debt_date=payload.debt_date,
        note=payload.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_debt(db: Session, user_id: int, debt_id: int, payload: DebtUpdate) -> Debt:
    debt = _get_debt(db, user_id, debt_id)
    if payload.counterparty is not None:
        debt.counterparty = payload.counterparty
    if payload.direction is not None:
        debt.direction = payload.direction
    if payload.principal_amount_uzs is not None:
        debt.principal_amount_uzs = payload.principal_amount_uzs
    if payload.debt_date is not None:
        debt.debt_date = payload.debt_date
    if "note" in payload.model_fields_set:
        debt.note = payload.note
    db.commit()
    db.refresh(debt)
    return debt


def delete_debt(db: Session, user_id: int, debt_id: int) -> bool:
    debt = db.query(Debt).filter(Debt.id == debt_id, Debt.user_id == user_id).first()
    if not debt:
        return False
    db.delete(debt)
    db.commit()
    return True


def add_repayment(
    db: Session, user_id: int, debt_id: int, payload: RepaymentCreate
) -> DebtRepayment:
    debt = _get_debt(db, user_id, debt_id)
    if payload.amount_uzs > _outstanding(debt):
        raise ValueError("Repayment exceeds outstanding")
    record = DebtRepayment(
        debt_id=debt.id,
        user_id=user_id,
        amount_uzs=payload.amount_uzs,
        repayment_date=payload.repayment_date,
        note=payload.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def settle_debt(db: Session, user_id: int, debt_id: int, on_date: date) -> Optional[DebtRepayment]:
    """Repay the full outstanding amount in one go. Returns None if already settled."""
    debt = _get_debt(db, user_id, debt_id)
    remaining = _outstanding(debt)
    if remaining <= 0:
        return None
    return add_repayment(
        db, user_id, debt_id,
        RepaymentCreate(amount_uzs=remaining, repayment_date=on_date, note=None),
    )


def delete_repayment(db: Session, user_id: int, debt_id: int, repayment_id: int) -> bool:
    record = (
        db.query(DebtRepayment)
        .filter(
            DebtRepayment.id == repayment_id,
            DebtRepayment.debt_id == debt_id,
            DebtRepayment.user_id == user_id,
        )
        .first()
    )
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def _to_out(debt: Debt) -> DebtOut:
    outstanding = _outstanding(debt)
    return DebtOut(
        id=debt.id,
        counterparty=debt.counterparty,
        direction=debt.direction,
        principal_amount_uzs=debt.principal_amount_uzs,
        debt_date=debt.debt_date,
        note=debt.note,
        outstanding_uzs=outstanding,
        settled=outstanding <= 0,
        repayments=[
            RepaymentOut(
                id=r.id,
                amount_uzs=r.amount_uzs,
                repayment_date=r.repayment_date,
                note=r.note,
            )
            for r in sorted(debt.repayments, key=lambda x: (x.repayment_date, x.id))
        ],
    )


def list_debts(db: Session, user_id: int) -> DebtsResponse:
    debts = (
        db.query(Debt)
        .options(selectinload(Debt.repayments))
        .filter(Debt.user_id == user_id)
        .all()
    )
    out = [_to_out(d) for d in debts]
    lent_outstanding = sum(d.outstanding_uzs for d in out if d.direction == "lent")
    borrowed_outstanding = sum(d.outstanding_uzs for d in out if d.direction == "borrowed")
    # Active (unsettled) debts first, then most recent.
    out.sort(key=lambda d: (d.settled, -d.id))
    return DebtsResponse(
        debts=out,
        totals=DebtTotals(
            lent_outstanding=lent_outstanding,
            borrowed_outstanding=borrowed_outstanding,
            net=lent_outstanding - borrowed_outstanding,
        ),
    )
