from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    about: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    savings_target_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    emergency_months: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # { category_key: monthly_limit_uzs }
    category_budgets: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")
