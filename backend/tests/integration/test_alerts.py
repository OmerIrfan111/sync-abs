from decimal import Decimal

from app.core.config import settings
from app.models.error_log import ErrorLog
from app.services.alerts_service import ORDER_ATTENTION, raise_alert, resolve_alerts
from app.services.app_settings_service import record_backup, set_auto_order_config

from tests.unit.test_auto_fulfillment import _order, _run


def test_held_order_raises_one_in_app_alert_linked_to_the_order(db_session, monkeypatch):
    set_auto_order_config(db_session, enabled=True, max_order_value=Decimal("1000"), min_profit=Decimal("0"))
    order = _order(db_session, tag="alert-loss", total="90.00", fees="10.00")
    result, _ = _run(db_session, order)
    assert result == "HELD"
    alerts = db_session.query(ErrorLog).filter(ErrorLog.error_type == ORDER_ATTENTION).all()
    assert len(alerts) == 1 and alerts[0].order_id == order.id and alerts[0].status == "PENDING"
    assert "held for your review" in alerts[0].message and "Profit would be" in alerts[0].message


def test_completed_order_raises_no_alert(db_session):
    set_auto_order_config(db_session, enabled=True, max_order_value=Decimal("1000"), min_profit=Decimal("0"))
    order = _order(db_session, tag="alert-ok")
    result, _ = _run(db_session, order)
    assert result == "COMPLETED"
    assert db_session.query(ErrorLog).filter(ErrorLog.error_type == ORDER_ATTENTION).count() == 0


def test_alerts_are_not_duplicated_and_can_be_resolved(db_session):
    first = raise_alert(db_session, "BACKUP_PROBLEM", "backup is late")
    again = raise_alert(db_session, "BACKUP_PROBLEM", "backup is late")
    assert first.id == again.id
    assert resolve_alerts(db_session, "BACKUP_PROBLEM") == 1
    assert db_session.query(ErrorLog).filter(ErrorLog.status == "PENDING").count() == 0


def test_summary_endpoint_counts_unresolved_alerts_and_shows_backup_status(client, db_session):
    raise_alert(db_session, ORDER_ATTENTION, "Order #1 was held")
    record_backup(db_session, "ok", "backup-x.jsonl.gz: 10 rows, 0.1 MB")
    body = client.get("/api/v1/errors/summary").json()
    assert body["pending_total"] >= 1 and body["orders_attention"] >= 1
    assert body["backup"]["status"] == "ok" and body["backup"]["last_backup_at"]


def test_resolving_an_alert_removes_it_from_the_dashboard_list(client, db_session):
    alert = raise_alert(db_session, ORDER_ATTENTION, "Order #2 failed")
    assert any(e["id"] == alert.id for e in client.get("/api/v1/dashboard/summary").json()["recent_errors"])
    client.post(f"/api/v1/errors/{alert.id}/resolve")
    assert not any(e["id"] == alert.id for e in client.get("/api/v1/dashboard/summary").json()["recent_errors"])


def test_routine_data_gaps_and_old_supplier_blips_do_not_flood_the_alerts(client, db_session):
    """Live finding 2026-11-26: 4,262 'supplier returned no price' notices made the bell read 99+."""
    from datetime import datetime, timedelta, timezone
    for i in range(5):
        db_session.add(ErrorLog(error_type="MISSING_DATA", message=f"SKU {i}: no price", status="PENDING"))
    db_session.add(ErrorLog(error_type="SUPPLIER_CONNECTION_ERROR", message="old D&H blip", status="PENDING",
                            created_at=datetime.now(timezone.utc) - timedelta(days=3)))
    db_session.add(ErrorLog(error_type="SUPPLIER_CONNECTION_ERROR", message="D&H is down right now", status="PENDING"))
    db_session.commit()
    raise_alert(db_session, ORDER_ATTENTION, "Order #9 was held")

    body = client.get("/api/v1/errors/summary").json()
    assert body["pending_total"] == 2          # the fresh outage + the held order
    listed = client.get("/api/v1/errors?unresolved=true&page_size=50").json()["items"]
    assert {e["message"] for e in listed} == {"D&H is down right now", "Order #9 was held"}
    # the Logs page can still see everything
    assert client.get("/api/v1/errors?page_size=50").json()["total"] >= 8
