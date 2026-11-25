from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.app_setting import AppSetting

KEY_ENABLED = "auto_order_enabled"
KEY_MAX_VALUE = "auto_order_max_order_value"
KEY_MIN_PROFIT = "auto_order_min_profit"


@dataclass
class AutoOrderConfig:
    enabled: bool
    max_order_value: Decimal
    min_profit: Decimal


def _get(db: Session, key: str) -> Optional[str]:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else None


def _put(db: Session, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


def get_auto_order_config(db: Session) -> AutoOrderConfig:
    """What staff saved in the app wins; otherwise the deployment default
    (AUTO_ORDER_* env vars, which default to OFF)."""
    enabled = _get(db, KEY_ENABLED)
    max_value = _get(db, KEY_MAX_VALUE)
    min_profit = _get(db, KEY_MIN_PROFIT)
    return AutoOrderConfig(
        enabled=(enabled == "true") if enabled is not None else bool(settings.AUTO_ORDER_ENABLED),
        max_order_value=Decimal(max_value) if max_value is not None else Decimal(settings.AUTO_ORDER_MAX_ORDER_VALUE),
        min_profit=Decimal(min_profit) if min_profit is not None else Decimal(settings.AUTO_ORDER_MIN_PROFIT),
    )


def set_auto_order_config(
    db: Session,
    enabled: Optional[bool] = None,
    max_order_value: Optional[Decimal] = None,
    min_profit: Optional[Decimal] = None,
) -> AutoOrderConfig:
    if enabled is not None:
        _put(db, KEY_ENABLED, "true" if enabled else "false")
    if max_order_value is not None:
        _put(db, KEY_MAX_VALUE, str(max_order_value))
    if min_profit is not None:
        _put(db, KEY_MIN_PROFIT, str(min_profit))
    db.commit()
    return get_auto_order_config(db)
