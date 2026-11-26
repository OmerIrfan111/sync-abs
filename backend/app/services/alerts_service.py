from typing import Optional

from sqlalchemy.orm import Session

from app.models.error_log import ErrorLog

ORDER_ATTENTION = "ORDER_ATTENTION"
BACKUP_PROBLEM = "BACKUP_PROBLEM"


def raise_alert(db: Session, error_type: str, message: str, order_id: Optional[int] = None) -> ErrorLog:
    """Create an in-app alert (shown in the bell and on the dashboard until a
    person marks it handled). Never duplicates an unresolved alert for the same
    order, or for the same message when there's no order."""
    query = db.query(ErrorLog).filter(ErrorLog.error_type == error_type, ErrorLog.status == "PENDING")
    query = query.filter(ErrorLog.order_id == order_id) if order_id is not None else query.filter(ErrorLog.message == message)
    existing = query.first()
    if existing:
        existing.message = message
        db.commit()
        return existing
    alert = ErrorLog(error_type=error_type, message=message, order_id=order_id, status="PENDING", retry_count=0)
    db.add(alert)
    db.commit()
    return alert


def resolve_alerts(db: Session, error_type: str) -> int:
    """Close every unresolved alert of one kind (e.g. once a backup succeeds)."""
    from datetime import datetime, timezone
    rows = db.query(ErrorLog).filter(ErrorLog.error_type == error_type, ErrorLog.status == "PENDING").all()
    for row in rows:
        row.status = "RESOLVED"
        row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return len(rows)
