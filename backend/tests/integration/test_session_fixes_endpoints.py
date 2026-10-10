"""
HTTP-level tests for the endpoint bugs found and fixed in this session's
audit (2026-10-09) that didn't already have dedicated coverage: product
delete cascade-retirement, order deliver/complete status-transition guards,
RBAC gaps on marketplace credential/fee endpoints, and Walmart new-item
price/weight validation.
"""
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.api.deps import get_current_user
from app.main import app
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.core.security import get_password_hash
from app.services.listing_service import ListingService


def test_delete_product_retires_listing_before_cascade_delete(client, db_session):
    """
    Real bug fixed 2026-10-09: DELETE /products/{id} used to cascade-delete
    any attached Listing rows with no attempt to retire/withdraw them on the
    real marketplace first — the same bug class as the real 00TF99 incident
    already fixed for DELETE /listings/{id}.
    """
    product = Product(sku="DEL-CASCADE-TEST", title="Test Product", is_enabled=True)
    db_session.add(product)
    marketplace = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter")
    db_session.add(marketplace)
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(marketplace)

    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id,
        external_listing_id=product.sku, status="ACTIVE",
        selling_price=10, listed_qty=3, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.commit()

    mock_adapter = MagicMock(spec=["retire_item", "withdraw_listing"])
    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=mock_adapter):
        res = client.delete(f"/api/v1/products/{product.id}")

    assert res.status_code == 200
    mock_adapter.retire_item.assert_called_once_with(product.sku)
    body = res.json()
    assert body["success"] is True
    assert body["marketplace_cleanup"][0]["cleanup"] == "retired"
    assert db_session.query(Product).filter(Product.id == product.id).first() is None


def test_deliver_order_requires_shipped_status(client, db_session):
    """Real bug fixed 2026-10-09: mark_delivered() had no status-transition check at all."""
    marketplace = Marketplace(name="eBay Deliver Test", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()
    order = Order(
        marketplace_id=marketplace.id, marketplace_order_id="DELIVER-TEST-1",
        order_total=Decimal("10.00"), status="PENDING_ROUTING",
        shipping_address={},
    )
    db_session.add(order)
    db_session.commit()

    res = client.put(f"/api/v1/orders/{order.id}/deliver")
    assert res.status_code == 400
    assert "must be SHIPPED" in res.json()["detail"]


def test_complete_order_requires_delivered_status(client, db_session):
    """Real bug fixed 2026-10-09: complete_order() had no status-transition check at all."""
    marketplace = Marketplace(name="eBay Complete Test", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()
    order = Order(
        marketplace_id=marketplace.id, marketplace_order_id="COMPLETE-TEST-1",
        order_total=Decimal("10.00"), status="SHIPPED",
        shipping_address={},
    )
    db_session.add(order)
    db_session.commit()

    res = client.put(f"/api/v1/orders/{order.id}/complete")
    assert res.status_code == 400
    assert "must be DELIVERED" in res.json()["detail"]


def _operator_client(db_session):
    """Non-admin staff client, per conftest's documented override pattern."""
    operator = User(
        email="testoperator@syncplatform.io",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test Operator",
        is_active=True,
        is_superuser=False,
        role="operator",
    )
    db_session.add(operator)
    db_session.commit()
    db_session.refresh(operator)

    from fastapi.testclient import TestClient

    def override_get_current_user():
        return operator

    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def test_fee_schedule_update_rejects_non_admin(client, db_session):
    """Real RBAC gap fixed 2026-10-09: PUT fee-schedule had no admin gate, unlike every sibling route."""
    marketplace = Marketplace(name="Amazon Fee Test", adapter_class="LiveAmazonAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()

    operator_client = _operator_client(db_session)
    try:
        res = operator_client.put(f"/api/v1/marketplaces/{marketplace.id}/fee-schedule", json={"fee_percentage": "15.0"})
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_ebay_exchange_code_rejects_non_admin(client, db_session):
    """Real RBAC gap fixed 2026-10-09: this writes live eBay OAuth credentials, more sensitive than update_marketplace (which was already admin-gated)."""
    operator_client = _operator_client(db_session)
    try:
        res = operator_client.post("/api/v1/marketplaces/ebay/exchange-code", json={"code": "fake-code"})
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_walmart_create_new_item_rejects_zero_price(client):
    """Real bug fixed 2026-10-09: no gt=0 validation meant a $0 item could be submitted to Walmart's real catalog."""
    res = client.post(
        "/api/v1/products/1/walmart-create-new-item",
        json={
            "product_type": "Keyboards",
            "price": "0",
            "weight_lbs": 1.0,
            "visible_attributes": {},
        },
    )
    assert res.status_code == 422


def test_walmart_create_new_item_rejects_negative_weight(client):
    res = client.post(
        "/api/v1/products/1/walmart-create-new-item",
        json={
            "product_type": "Keyboards",
            "price": "19.99",
            "weight_lbs": -2.0,
            "visible_attributes": {},
        },
    )
    assert res.status_code == 422
