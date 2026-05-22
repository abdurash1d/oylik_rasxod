from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User


def ensure_owner(telegram_user_id: int):
    if telegram_user_id != settings.owner_telegram_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен для этого пользователя",
        )


def get_or_create_user(db: Session, telegram_user_id: int, username: Optional[str]) -> User:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if user:
        return user
    user = User(telegram_user_id=telegram_user_id, username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
