from sqlalchemy.orm import Session

from app.models.user_settings import UserSettings
from app.schemas import SettingsOut, SettingsUpdate


def get_or_create_settings(db: Session, user_id: int) -> UserSettings:
    record = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if record is None:
        record = UserSettings(user_id=user_id, category_budgets={})
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def settings_out(record: UserSettings) -> SettingsOut:
    return SettingsOut(
        display_name=record.display_name,
        about=record.about,
        savings_target_pct=record.savings_target_pct,
        emergency_months=record.emergency_months,
        category_budgets=dict(record.category_budgets or {}),
    )


def update_settings(db: Session, user_id: int, payload: SettingsUpdate) -> UserSettings:
    record = get_or_create_settings(db, user_id)
    if "display_name" in payload.model_fields_set:
        record.display_name = (payload.display_name or "").strip() or None
    if "about" in payload.model_fields_set:
        record.about = (payload.about or "").strip() or None
    if payload.savings_target_pct is not None:
        record.savings_target_pct = payload.savings_target_pct
    if payload.emergency_months is not None:
        record.emergency_months = payload.emergency_months
    if payload.category_budgets is not None:
        # reassign a fresh dict so SQLAlchemy detects the JSON change
        record.category_budgets = dict(payload.category_budgets)
    db.commit()
    db.refresh(record)
    return record
