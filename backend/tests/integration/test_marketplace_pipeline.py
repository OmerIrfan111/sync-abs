import pytest
from decimal import Decimal
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.sync_log import SyncLog
from app.models.error_log import ErrorLog
from app.services.listing_service import ListingService, distributed_lock
from app.services.sync_service import SyncService
from app.schemas.supplier import NormalizedProduct

def test_publish_product_to_marketplace_and_propagation(db_session):
    # 1. Setup Supplier, Marketplace, and Product
    supplier = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay", adapter_class="MockEBayAdapter", is_active=True)
    product = Product(
        sku="TEST-MXKEYS-PIPE",
        title="Logitech MX Keys Keyboard",
        is_enabled=True
    )
    db_session.add_all([supplier, marketplace, product])
    db_session.commit()

    # Link supplier product with 20 in stock at $50 cost
    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="ING-MXKEYS",
        cost=Decimal("50.00"),
        qty_available=20,
        stock_status="IN_STOCK",
        availability_status="ACTIVE",
        shipping_info={}
    )
    db_session.add(sp)
    db_session.commit()

    listing_service = ListingService(db_session)

    # 2. Publish Product to Mock eBay (Spec Section 31 QA: 'Product can be selected and published to mock eBay')
    listing = listing_service.publish_product_to_marketplace(
        product_id=product.id,
        marketplace_id=marketplace.id
    )

    assert listing.id is not None
    assert listing.external_listing_id is not None
    assert listing.external_listing_id.startswith("ebay_listing_")
    assert listing.status == "ACTIVE"
    assert listing.listed_qty == 20
    assert listing.selling_price == Decimal("57.50") # $50 * 1.15 markup

    # Verify SyncLog recorded publication
    publish_log = db_session.query(SyncLog).filter(
        SyncLog.product_id == product.id,
        SyncLog.field_changed == "published_to_ebay"
    ).first()
    assert publish_log is not None

    # 3. Simulate Supplier Stock Change (20 -> 8) and Price Change ($50 -> $52)
    # (Spec Section 31 QA: 'Supplier stock changes propagate through Celery to marketplace quantity')
    sp.qty_available = 8
    sp.cost = Decimal("52.00")
    db_session.commit()

    # Propagate to marketplace
    updated_listings = listing_service.sync_all_listings_for_product(product.id)
    assert len(updated_listings) == 1

    db_session.refresh(listing)
    assert listing.listed_qty == 8
    assert listing.selling_price == Decimal("59.80") # $52 * 1.15 markup

    # 4. Withdraw Listing (Spec Section 31 QA: 'Listing creation/update/withdrawal works')
    withdrawn = listing_service.withdraw_listing_from_marketplace(listing.id)
    assert withdrawn.status == "WITHDRAWN"
    assert withdrawn.listed_qty == 0

def test_distributed_lock_behavior():
    # Test distributed lock context manager
    with distributed_lock("sync:test:lock:1") as acquired:
        assert acquired is True

def test_listings_api_lifecycle(client, db_session):
    # Setup test data
    m = Marketplace(name="eBay US", adapter_class="MockEBayAdapter", is_active=True)
    p = Product(sku="API-TEST-SKU", title="API Test Product", is_enabled=True)
    db_session.add_all([m, p])
    db_session.commit()

    # 1. Publish via REST API
    publish_resp = client.post("/api/v1/listings/publish", json={
        "product_id": p.id,
        "marketplace_id": m.id,
        "custom_price": "79.99",
        "custom_qty": 15
    })
    assert publish_resp.status_code == 201
    data = publish_resp.json()
    assert data["status"] == "ACTIVE"
    assert data["selling_price"] == "79.99"
    assert data["listed_qty"] == 15
    listing_id = data["id"]

    # 2. List listings
    list_resp = client.get(f"/api/v1/listings?marketplace_id={m.id}")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 3. Sync listing
    sync_resp = client.post(f"/api/v1/listings/{listing_id}/sync")
    assert sync_resp.status_code == 200
    assert sync_resp.json()["id"] == listing_id

    # 4. Withdraw listing
    withdraw_resp = client.post(f"/api/v1/listings/{listing_id}/withdraw")
    assert withdraw_resp.status_code == 200
    assert withdraw_resp.json()["status"] == "WITHDRAWN"
    assert withdraw_resp.json()["listed_qty"] == 0
