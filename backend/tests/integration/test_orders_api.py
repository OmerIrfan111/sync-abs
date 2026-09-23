from decimal import Decimal

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace


def _setup_catalog(db_session):
    product = Product(sku="ING-LOGI-MXKEYS", title="Logitech MX Keys")
    db_session.add(product)
    supplier = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(supplier)
    marketplace = Marketplace(name="eBay Order API Test", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="LOGI-MXK-001",
        cost=Decimal("89.00"),
        qty_available=25,
        availability_status="ACTIVE",
    )
    db_session.add(sp)
    db_session.commit()
    return product, supplier, marketplace


def test_orders_full_lifecycle_via_api(client, db_session):
    product, supplier, marketplace = _setup_catalog(db_session)

    # 1. POST /orders/sync - ingest a mock order
    sync_resp = client.post("/api/v1/orders/sync")
    assert sync_resp.status_code == 200, sync_resp.text
    sync_data = sync_resp.json()
    assert sync_data["total_new_orders"] == 1

    # 2. GET /orders - list orders
    list_resp = client.get("/api/v1/orders")
    assert list_resp.status_code == 200
    orders = list_resp.json()["orders"]
    assert len(orders) == 1
    order_id = orders[0]["id"]
    assert orders[0]["status"] == "PENDING_ROUTING"

    # 3. GET /orders/stats
    stats_resp = client.get("/api/v1/orders/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_orders"] == 1
    assert stats["pending_routing"] == 1

    # 4. GET /orders/{id} - detail view
    detail_resp = client.get(f"/api/v1/orders/{order_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["items"]) == 1
    assert detail["items"][0]["sku"] == "ING-LOGI-MXKEYS"

    # 5. POST /orders/{id}/route
    route_resp = client.post(f"/api/v1/orders/{order_id}/route")
    assert route_resp.status_code == 200, route_resp.text
    assert route_resp.json()["status"] == "ROUTED"

    # 6. POST /orders/{id}/create-po
    po_resp = client.post(f"/api/v1/orders/{order_id}/create-po")
    assert po_resp.status_code == 200, po_resp.text
    po_data = po_resp.json()
    assert len(po_data["purchase_orders"]) == 1
    assert po_data["purchase_orders"][0]["supplier_id"] == supplier.id

    # Attempting a second PO creation should now fail (order no longer ROUTED)
    po_resp_again = client.post(f"/api/v1/orders/{order_id}/create-po")
    assert po_resp_again.status_code == 400

    # 7. PUT /orders/{id}/tracking
    tracking_resp = client.put(
        f"/api/v1/orders/{order_id}/tracking",
        json={"tracking_number": "1Z999AA10123456784", "carrier": "UPS"},
    )
    assert tracking_resp.status_code == 200, tracking_resp.text
    assert tracking_resp.json()["status"] == "SHIPPED"

    detail_after_tracking = client.get(f"/api/v1/orders/{order_id}").json()
    assert detail_after_tracking["purchase_orders"][0]["tracking_number"] == "1Z999AA10123456784"
    assert any(ev["event_type"] == "TRACKING_UPDATED" for ev in detail_after_tracking["events"])


def test_cancel_order_via_api(client, db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    client.post("/api/v1/orders/sync")
    order_id = client.get("/api/v1/orders").json()["orders"][0]["id"]

    cancel_resp = client.put(f"/api/v1/orders/{order_id}/cancel")
    assert cancel_resp.status_code == 200, cancel_resp.text
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Cannot route a cancelled order
    route_resp = client.post(f"/api/v1/orders/{order_id}/route")
    assert route_resp.status_code == 400


def test_get_nonexistent_order_returns_404(client, db_session):
    resp = client.get("/api/v1/orders/999999")
    assert resp.status_code == 404
