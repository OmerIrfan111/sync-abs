from decimal import Decimal
from datetime import datetime, timezone

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.order import Order
from app.models.order_item import OrderItem


def _setup_order(db_session, supplier_name="Ingram Micro"):
    product = Product(sku="ENDPT-TEST-SKU", title="Endpoint Test Product")
    db_session.add(product)
    supplier = Supplier(name=supplier_name, adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(supplier)
    marketplace = Marketplace(name="eBay Endpoint Test", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id, supplier_id=supplier.id, supplier_sku="EP-001",
        cost=Decimal("50.00"), qty_available=10, availability_status="ACTIVE",
    )
    db_session.add(sp)

    order = Order(
        marketplace_id=marketplace.id, marketplace_order_id="ENDPT-ORDER-1",
        order_total=Decimal("100.00"), status="PENDING_ROUTING",
        shipping_address={"name": "Buyer", "street": "1 Main St", "city": "LA", "state": "CA", "zip": "90001", "country": "US"},
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id, product_id=product.id, sku=product.sku,
        quantity=1, unit_price=Decimal("100.00"), status="PENDING",
    )
    db_session.add(item)
    db_session.commit()
    return order, product, supplier, marketplace


def test_full_route_create_po_submit_live_cycle_via_http(client, db_session):
    """
    End-to-end HTTP-layer test of the exact click path a user follows in the
    UI: Route -> Create PO -> Place Order (Live). Only the service layer had
    direct test coverage before this; this verifies the API wiring itself
    (status codes, response shape) end to end under DRY_RUN sandbox mode.
    """
    order, product, supplier, marketplace = _setup_order(db_session)

    res = client.post(f"/api/v1/orders/{order.id}/route")
    assert res.status_code == 200
    assert res.json()["routed_count"] == 1

    res = client.post(f"/api/v1/orders/{order.id}/create-po")
    assert res.status_code == 200
    pos = res.json()["purchase_orders"]
    assert len(pos) == 1
    po_number = pos[0]["po_number"]

    from app.models.purchase_order import PurchaseOrder
    po = db_session.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()
    assert po.status == "DRAFT"

    res = client.post(f"/api/v1/orders/purchase-orders/{po.id}/submit-live")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["status"] == "SUBMITTED"
    assert body["supplier_order_id"].startswith("SANDBOX-")


def test_submit_live_rejects_non_draft_po_via_http(client, db_session):
    order, product, supplier, marketplace = _setup_order(db_session)
    client.post(f"/api/v1/orders/{order.id}/route")
    res = client.post(f"/api/v1/orders/{order.id}/create-po")
    po_number = res.json()["purchase_orders"][0]["po_number"]

    from app.models.purchase_order import PurchaseOrder
    po = db_session.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()

    client.post(f"/api/v1/orders/purchase-orders/{po.id}/submit-live")
    res = client.post(f"/api/v1/orders/purchase-orders/{po.id}/submit-live")
    assert res.status_code == 400


def test_manual_submit_endpoint_records_supplier_confirmation(client, db_session):
    order, product, supplier, marketplace = _setup_order(db_session)
    client.post(f"/api/v1/orders/{order.id}/route")
    res = client.post(f"/api/v1/orders/{order.id}/create-po")
    po_number = res.json()["purchase_orders"][0]["po_number"]

    from app.models.purchase_order import PurchaseOrder
    po = db_session.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()

    res = client.put(
        f"/api/v1/orders/purchase-orders/{po.id}/submit",
        json={"supplier_order_id": "MANUAL-CONF-123"},
    )
    assert res.status_code == 200
    assert res.json()["supplier_order_id"] == "MANUAL-CONF-123"


def test_cancel_blocked_returns_409_and_leaves_status_unchanged(client, db_session):
    order, product, supplier, marketplace = _setup_order(db_session)
    client.post(f"/api/v1/orders/{order.id}/route")
    res = client.post(f"/api/v1/orders/{order.id}/create-po")
    po_number = res.json()["purchase_orders"][0]["po_number"]

    from app.models.purchase_order import PurchaseOrder
    po = db_session.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()
    client.post(f"/api/v1/orders/purchase-orders/{po.id}/submit-live")

    res = client.put(f"/api/v1/orders/{order.id}/cancel")
    assert res.status_code == 409
    assert "could NOT be cancelled" in res.json()["detail"]

    db_session.refresh(order)
    assert order.status == "PO_SUBMITTED"


def test_cancel_then_reopen_round_trip_via_http(client, db_session):
    order, product, supplier, marketplace = _setup_order(db_session)
    client.post(f"/api/v1/orders/{order.id}/route")

    res = client.put(f"/api/v1/orders/{order.id}/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"

    res = client.put(f"/api/v1/orders/{order.id}/reopen")
    assert res.status_code == 200
    assert res.json()["status"] == "ROUTED"


def test_reopen_rejects_non_cancelled_order_via_http(client, db_session):
    order, product, supplier, marketplace = _setup_order(db_session)
    res = client.put(f"/api/v1/orders/{order.id}/reopen")
    assert res.status_code == 400
