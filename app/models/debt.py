from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Debt(Base):
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False)
    # 'lent'     -> I gave money, they owe me
    # 'borrowed' -> I took money, I owe them
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    principal_amount_uzs: Mapped[int] = mapped_column(Integer, nullable=False)
    debt_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    repayments: Mapped[List["DebtRepayment"]] = relationship(
        "DebtRepayment",
        back_populates="debt",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DebtRepayment.repayment_date",
    )


class DebtRepayment(Base):
    __tablename__ = "debt_repayments"

    id: Mapped[int] = mapped_column(primary_key=True)
    debt_id: Mapped[int] = mapped_column(
        ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount_uzs: Mapped[int] = mapped_column(Integer, nullable=False)
    repayment_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    debt = relationship("Debt", back_populates="repayments")


Index("ix_debts_user_direction", Debt.user_id, Debt.direction)
Index("ix_debts_user_counterparty", Debt.user_id, Debt.counterparty)
Index("ix_debt_repayments_user_date", DebtRepayment.user_id, DebtRepayment.repayment_date)
