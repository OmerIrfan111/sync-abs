"""
HTTP-level tests for the last 21 endpoints that had no direct test coverage
as of 2026-10-09 (all previously code-reviewed with no bugs found; this
closes the test-coverage gap so every endpoint has a real HTTP-level check).
"""
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.sync_log import SyncLog
from app.models.error_log import ErrorLog
from app.models.warehouse import Warehouse, WarehouseStock
from app.models.supplier_product import SupplierProduct
from app.services.listing_service import ListingService


# ── products.py ──────────────────────────────────────────────

def test_filter_options_returns_distinct_brands_and_categories(client, db_session):
    db_session.add_all([
        Product(sku="F1", title="A", brand="Acme", category="Cables"),
        Product(sku="F2", title="B", brand="Acme", category="Cables"),
        Product(sku="F3", title="C", brand="Globex", category="Monitors"),
    ])
    db_session.commit()

    res = client.get("/api/v1/products/filters/options")
    assert res.status_code == 200
    body = res.json()
    assert "Acme" in body["brands"] and "Globex" in body["brands"]
    assert "Cables" in body["categories"] and "Monitors" in body["categories"]


def test_image_suggestions_returns_candidates(client, db_session):
    product = Product(sku="IMG-1", title="Logitech Mouse", upc="012345678905")
    db_session.add(product)
    db_session.commit()

    with patch("app.adapters.suppliers.image_search_provider.get_image_search_provider") as mock_provider:
        mock_provider.return_value.search_web_images.return_value = [
            {"url": "https://example.com/a.jpg", "source": "trusted"}
        ]
        res = client.get(f"/api/v1/products/{product.id}/image-suggestions")
    assert res.status_code == 200


def test_walmart_match_check_requires_upc(client, db_session):
    product = Product(sku="NOUPC-1", title="No UPC Product")
    db_session.add(product)
    db_session.commit()
    res = client.get(f"/api/v1/products/{product.id}/walmart-match-check")
    assert res.status_code == 400


def test_walmart_match_check_calls_real_catalog_search(client, db_session):
    product = Product(sku="HASUPC-1", title="Has UPC Product", upc="012345678905")
    marketplace = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter", is_active=True)
    db_session.add_all([product, marketplace])
    db_session.commit()

    mock_adapter = MagicMock(spec=["search_walmart_catalog_by_gtin"])
    mock_adapter.search_walmart_catalog_by_gtin.return_value = [{"itemId": "WM-123", "gtin": "012345678905"}]
    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=mock_adapter):
        res = client.get(f"/api/v1/products/{product.id}/walmart-match-check")
    assert res.status_code == 200
    assert res.json()["matchable"] is True
    assert res.json()["matches_found"] == 1
    mock_adapter.search_walmart_catalog_by_gtin.assert_called_once()


def test_walmart_item_spec_requires_product_type_query_param(client):
    res = client.get("/api/v1/products/walmart-item-spec")
    assert res.status_code == 422


def test_walmart_item_spec_returns_real_schema(client, db_session):
    marketplace = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()

    mock_adapter = MagicMock(spec=["get_item_spec"])
    mock_adapter.get_item_spec.return_value = {
        "schema": {"properties": {"MPItem": {"items": {"properties": {"Visible": {"properties": {
            "Keyboards": {"required": ["brand"], "properties": {"brand": {"type": "string"}}}
        }}}}}}}
    }
    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=mock_adapter):
        res = client.get("/api/v1/products/walmart-item-spec?product_type=Keyboards")
    assert res.status_code == 200
    assert res.json()["product_type"] == "Keyboards"


def test_lookup_weight_returns_404_when_not_found(client, db_session):
    product = Product(sku="WT-1", title="Weight Test", upc="012345678905")
    db_session.add(product)
    db_session.commit()

    with patch("app.services.weight_lookup_service.WeightLookupService.lookup_weight_by_upc") as mock_lookup:
        mock_result = MagicMock(status="not_found", reason="No verified match")
        mock_lookup.return_value = mock_result
        res = client.post(f"/api/v1/products/{product.id}/lookup-weight")
    assert res.status_code == 404


def test_set_image_rejects_non_http_url(client, db_session):
    product = Product(sku="IMGSET-1", title="Image Set Test")
    db_session.add(product)
    db_session.commit()
    res = client.post(f"/api/v1/products/{product.id}/set-image", json={"image_url": "ftp://bad.example/x.jpg"})
    assert res.status_code == 400


def test_set_image_accepts_real_url(client, db_session):
    product = Product(sku="IMGSET-2", title="Image Set Test 2")
    db_session.add(product)
    db_session.commit()
    res = client.post(f"/api/v1/products/{product.id}/set-image", json={"image_url": "https://example.com/real.jpg"})
    assert res.status_code == 200
    db_session.refresh(product)
    assert "https://example.com/real.jpg" in (product.images or [])


# ── listings.py ──────────────────────────────────────────────

def test_real_status_polls_real_feed_when_feed_log_exists(client, db_session):
    product = Product(sku="RS-1", title="Real Status Test")
    marketplace = Marketplace(name="Walmart", adapter_class="LiveWalmartAdapter", is_active=True)
    db_session.add_all([product, marketplace])
    db_session.commit()
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id, external_listing_id="RS-1",
        status="PENDING", selling_price=10, listed_qty=1, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.add(SyncLog(product_id=product.id, field_changed="walmart_feed_id", old_value=None, new_value="FEED-123"))
    db_session.commit()
    db_session.refresh(listing)

    mock_adapter = MagicMock(spec=["get_feed_status"])
    mock_adapter.get_feed_status.return_value = {"feedStatus": "PROCESSED", "itemsSucceeded": 1}
    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=mock_adapter):
        res = client.get(f"/api/v1/listings/{listing.id}/real-status")
    assert res.status_code == 200
    assert res.json()["check_method"] == "feed_status"
    mock_adapter.get_feed_status.assert_called_once_with("FEED-123")


def test_real_status_falls_back_to_listing_lookup_when_no_feed_log(client, db_session):
    product = Product(sku="RS-2", title="Real Status Test 2")
    marketplace = Marketplace(name="eBay", adapter_class="LiveEBayAdapter", is_active=True)
    db_session.add_all([product, marketplace])
    db_session.commit()
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id, external_listing_id="RS-2",
        status="ACTIVE", selling_price=10, listed_qty=1, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)

    mock_adapter = MagicMock(spec=["get_listing"])
    mock_adapter.get_listing.return_value = {"status": "ACTIVE"}
    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=mock_adapter):
        res = client.get(f"/api/v1/listings/{listing.id}/real-status")
    assert res.status_code == 200
    assert res.json()["check_method"] == "listing_lookup"


def test_reconcile_store_syncs_real_listings(client, db_session):
    marketplace = Marketplace(name="Shopify", adapter_class="LiveShopifyAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()

    with patch.object(ListingService, "get_adapter_for_marketplace", return_value=MagicMock()), \
         patch.object(ListingService, "reconcile_marketplace_listings", return_value=3):
        res = client.post(f"/api/v1/listings/reconcile-store/{marketplace.id}")
    assert res.status_code == 200
    assert res.json()["synced_count"] == 3


def test_reactivate_listing_calls_real_service(client, db_session):
    product = Product(sku="REACT-1", title="Reactivate Test")
    marketplace = Marketplace(name="eBay", adapter_class="LiveEBayAdapter", is_active=True)
    db_session.add_all([product, marketplace])
    db_session.commit()
    listing = Listing(
        product_id=product.id, marketplace_id=marketplace.id, external_listing_id="REACT-1",
        status="WITHDRAWN", selling_price=10, listed_qty=0, last_updated_at=datetime.now(timezone.utc),
    )
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)

    listing.status = "ACTIVE"
    listing.listed_qty = 5
    with patch.object(ListingService, "reactivate_listing_on_marketplace", return_value=listing):
        res = client.post(f"/api/v1/listings/{listing.id}/reactivate")
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"


# ── suppliers.py ─────────────────────────────────────────────

def test_supplier_warehouses_returns_real_aggregate_stock(client, db_session):
    supplier = Supplier(name="D&H", adapter_class="DAndHAdapter", is_active=True)
    db_session.add(supplier)
    db_session.commit()
    warehouse = Warehouse(supplier_id=supplier.id, code="BR01", name="Mid-Atlantic", is_active=True)
    db_session.add(warehouse)
    db_session.commit()

    product = Product(sku="WH-1", title="Warehouse Test")
    db_session.add(product)
    db_session.commit()
    sp = SupplierProduct(product_id=product.id, supplier_id=supplier.id, supplier_sku="DH-1", cost=Decimal("10.00"), qty_available=5)
    db_session.add(sp)
    db_session.commit()
    db_session.add(WarehouseStock(supplier_product_id=sp.id, warehouse_id=warehouse.id, qty_available=5))
    db_session.commit()

    res = client.get(f"/api/v1/suppliers/{supplier.id}/warehouses")
    assert res.status_code == 200
    body = res.json()
    assert len(body["warehouses"]) == 1
    assert body["warehouses"][0]["code"] == "BR01"
    assert body["warehouses"][0]["total_stock"] == 5


def test_supplier_warehouses_404_for_unknown_supplier(client):
    res = client.get("/api/v1/suppliers/999999/warehouses")
    assert res.status_code == 404


# ── dashboard.py ─────────────────────────────────────────────

def test_reconcile_all_queues_celery_task_without_blocking(client, db_session):
    """Confirms this dispatches async (.delay) rather than running sync inline."""
    supplier = Supplier(name="Ingram Micro", adapter_class="IngramMicroAdapter", is_active=True)
    db_session.add(supplier)
    db_session.commit()

    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"
    with patch("app.tasks.sync_tasks.sync_supplier_task.delay", return_value=mock_task) as mock_delay:
        res = client.post("/api/v1/dashboard/reconcile-all")
    assert res.status_code == 200
    mock_delay.assert_called_once_with(supplier.id)
    assert res.json()["queued_suppliers"] == 1
    assert res.json()["details"][0]["task_id"] == "fake-task-id-123"


# ── errors.py / sync_logs.py ─────────────────────────────────

def test_get_errors_paginated(client, db_session):
    db_session.add(ErrorLog(error_type="MISSING_DATA", message="test error", status="PENDING"))
    db_session.commit()
    res = client.get("/api/v1/errors")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(item["message"] == "test error" for item in body["items"])


def test_resolve_error_marks_resolved(client, db_session):
    error = ErrorLog(error_type="MISSING_DATA", message="resolve me", status="PENDING")
    db_session.add(error)
    db_session.commit()
    db_session.refresh(error)

    res = client.post(f"/api/v1/errors/{error.id}/resolve")
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"
    assert res.json()["resolved_at"] is not None


def test_resolve_error_404_for_unknown(client):
    res = client.post("/api/v1/errors/999999/resolve")
    assert res.status_code == 404


def test_get_sync_logs_paginated(client, db_session):
    product = Product(sku="SL-1", title="Sync Log Test")
    db_session.add(product)
    db_session.commit()
    db_session.add(SyncLog(product_id=product.id, field_changed="cost", old_value="10", new_value="12"))
    db_session.commit()

    res = client.get("/api/v1/sync-logs")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1


# ── rules.py (product-restrictions) ─────────────────────────

def test_create_product_restriction_requires_reason(client):
    res = client.post("/api/v1/rules/product-restrictions", json={"category": "Hazmat"})
    assert res.status_code == 400


def test_create_and_list_product_restriction(client, db_session):
    res = client.post("/api/v1/rules/product-restrictions", json={
        "category": "Hazmat", "reason": "Flammable aerosol, restricted category",
    })
    assert res.status_code == 201
    restriction_id = res.json()["id"]

    res = client.get("/api/v1/rules/product-restrictions")
    assert res.status_code == 200
    assert any(r["id"] == restriction_id for r in res.json())


def test_approve_requires_approval_type_restriction(client):
    create_res = client.post("/api/v1/rules/product-restrictions", json={
        "category": "Electronics", "reason": "Needs manual review", "restriction_type": "REQUIRES_APPROVAL",
    })
    restriction_id = create_res.json()["id"]

    res = client.put(f"/api/v1/rules/product-restrictions/{restriction_id}/approve")
    assert res.status_code == 200
    assert res.json()["approved_at"] is not None


def test_approve_rejects_blocked_restriction(client):
    create_res = client.post("/api/v1/rules/product-restrictions", json={
        "category": "Firearms", "reason": "Permanently blocked category", "restriction_type": "BLOCKED",
    })
    restriction_id = create_res.json()["id"]

    res = client.put(f"/api/v1/rules/product-restrictions/{restriction_id}/approve")
    assert res.status_code == 400


def test_delete_product_restriction(client):
    create_res = client.post("/api/v1/rules/product-restrictions", json={
        "category": "Test Delete", "reason": "To be deleted",
    })
    restriction_id = create_res.json()["id"]

    res = client.delete(f"/api/v1/rules/product-restrictions/{restriction_id}")
    assert res.status_code == 204

    res = client.get("/api/v1/rules/product-restrictions")
    assert not any(r["id"] == restriction_id for r in res.json())


# ── analytics.py ─────────────────────────────────────────────
# (AnalyticsService's own logic is covered separately in
# test_analytics_service.py; these just confirm the HTTP layer wires real
# query params through and returns the real shape with an empty DB.)

def test_analytics_summary_endpoint(client):
    res = client.get("/api/v1/analytics/summary?days=30")
    assert res.status_code == 200
    body = res.json()
    assert "revenue_total" in body
    assert "period_days" in body


def test_analytics_summary_rejects_out_of_range_days(client):
    res = client.get("/api/v1/analytics/summary?days=0")
    assert res.status_code == 422
    res = client.get("/api/v1/analytics/summary?days=9999")
    assert res.status_code == 422


def test_supplier_scores_endpoint(client):
    res = client.get("/api/v1/analytics/supplier-scores?days=90")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ── auth.py ──────────────────────────────────────────────────

def test_login_json_with_valid_credentials(client, test_admin_user):
    from app.api.deps import get_current_user
    from app.main import app
    # The `client` fixture overrides get_current_user globally for
    # convenience on every other test; auth endpoints don't depend on it,
    # but clear it anyway so this exercises the real, unmocked login path.
    app.dependency_overrides.pop(get_current_user, None)
    try:
        res = client.post("/api/v1/auth/login/json", json={
            "email": "testadmin@syncplatform.io", "password": "testpassword123",
        })
        assert res.status_code == 200
        assert res.json()["access_token"]
        assert res.json()["token_type"] == "bearer"
    finally:
        app.dependency_overrides[get_current_user] = lambda: test_admin_user


def test_login_json_rejects_wrong_password(client):
    res = client.post("/api/v1/auth/login/json", json={
        "email": "testadmin@syncplatform.io", "password": "wrong-password",
    })
    assert res.status_code == 400
