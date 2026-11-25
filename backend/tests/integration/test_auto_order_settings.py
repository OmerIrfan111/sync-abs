from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import get_password_hash
from app.api.deps import get_current_user
from app.main import app
from app.models.user import User
from app.services.app_settings_service import get_auto_order_config, set_auto_order_config
from app.services.auto_fulfillment_service import AutoFulfillmentService

from tests.unit.test_auto_fulfillment import _order, _run


def test_defaults_to_off_and_shows_state(client, db_session):
    res = client.get("/api/v1/orders/auto-order")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    assert body["max_order_value"] == "1000.00" and body["min_profit"] == "0.00"
    assert set(body["counts"]) == {"COMPLETED", "HELD", "MANUAL_NEEDED", "FAILED", "PROCESSING"}


def test_admin_can_turn_on_change_limits_and_turn_off(client, db_session):
    res = client.put("/api/v1/orders/auto-order", json={"enabled": True, "max_order_value": "500", "min_profit": "5"})
    assert res.status_code == 200 and res.json()["enabled"] is True
    cfg = get_auto_order_config(db_session)
    assert cfg.enabled and cfg.max_order_value == Decimal("500") and cfg.min_profit == Decimal("5")
    assert client.put("/api/v1/orders/auto-order", json={"enabled": False}).json()["enabled"] is False


def test_operator_cannot_change_it(client, db_session):
    operator = User(email="op-auto@syncplatform.io", hashed_password=get_password_hash("x" * 12),
                    full_name="Op", is_active=True, is_superuser=False, role="operator")
    db_session.add(operator)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: operator
    res = TestClient(app).put("/api/v1/orders/auto-order", json={"enabled": True})
    assert res.status_code in (401, 403)
    assert get_auto_order_config(db_session).enabled is False


def test_rejects_nonsense_limits(client):
    assert client.put("/api/v1/orders/auto-order", json={"max_order_value": "0"}).status_code == 422
    assert client.put("/api/v1/orders/auto-order", json={"min_profit": "-5"}).status_code == 422


def test_switch_in_the_app_overrides_the_environment_default(db_session, monkeypatch):
    """Saved choice wins: turning it off in the app stops ordering even if the env default is on."""
    monkeypatch.setattr(settings, "AUTO_ORDER_ENABLED", True)
    monkeypatch.setattr(settings, "AUTO_ORDER_MAX_ORDER_VALUE", Decimal("1000.00"))
    monkeypatch.setattr(settings, "AUTO_ORDER_MIN_PROFIT", Decimal("0.00"))
    set_auto_order_config(db_session, enabled=False)
    order = _order(db_session, tag="switch-off")
    result, calls = _run(db_session, order)
    assert result == "disabled" and calls == []
    assert order.auto_order_status is None


def test_turning_it_on_in_the_app_works_without_the_env_default(db_session, monkeypatch):
    monkeypatch.setattr(settings, "AUTO_ORDER_ENABLED", False)
    set_auto_order_config(db_session, enabled=True, max_order_value=Decimal("1000"), min_profit=Decimal("0"))
    order = _order(db_session, tag="switch-on")
    result, calls = _run(db_session, order)
    assert result == "COMPLETED" and len(calls) == 1


def test_limits_saved_in_the_app_are_used(db_session):
    set_auto_order_config(db_session, enabled=True, max_order_value=Decimal("50"), min_profit=Decimal("0"))
    order = _order(db_session, tag="low-cap")  # $89 cost > $50 cap
    result, calls = _run(db_session, order)
    assert result == "HELD" and calls == []
    assert "$50.00" in order.auto_order_note
