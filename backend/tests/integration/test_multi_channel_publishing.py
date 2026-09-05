from decimal import Decimal
import pytest
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.pricing_rule import PricingRule
from app.models.inventory_rule import InventoryRule
from app.services.listing_service import ListingService

def test_multi_channel_publishing_and_sync(db_session, client, admin_auth_headers):
    """
    Integration test verifying that a product can be published across all 5 channels:
    eBay, Amazon, Walmart, Shopify, and Newegg.
    """
    listing_service = ListingService(db_session)

    # 1. Setup Suppliers
    supplier = Supplier(name="Test Ingram", adapter_class="IngramMicroAdapter", is_active=True)
    db_session.add(supplier)
    db_session.commit()

    # 2. Setup All 5 Marketplaces
    marketplaces = [
        Marketplace(name="eBay US", adapter_class="MockEBayAdapter", is_active=True),
        Marketplace(name="Amazon US", adapter_class="MockAmazonAdapter", is_active=True),
        Marketplace(name="Walmart US", adapter_class="MockWalmartAdapter", is_active=True),
        Marketplace(name="Shopify Store", adapter_class="MockShopifyAdapter", is_active=True),
        Marketplace(name="Newegg", adapter_class="MockNeweggAdapter", is_active=True),
    ]
    db_session.add_all(marketplaces)
    db_session.commit()

    # 3. Setup Product
    product = Product(
        sku="CROSS-CHANNEL-001",
        title="Cross Channel Fast Charger 65W",
        description="High efficiency GaN adapter",
        category="Mobile Accessories"
    )
    db_session.add(product)
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="CHG-001",
        cost=Decimal("20.00"),
        qty_available=50,
        availability_status="ACTIVE"
    )
    db_session.add(sp)

    # 4. Rules: 20% markup, 2 buffer
    pr = PricingRule(product_id=product.id, rule_type="PERCENTAGE_MARKUP", percentage=Decimal("20.00"))
    ir = InventoryRule(product_id=product.id, safety_buffer=2, out_of_stock_action="SET_QUANTITY_ZERO")
    db_session.add_all([pr, ir])
    db_session.commit()

    # 5. Publish to all 5 channels
    listings = []
    for mp in marketplaces:
        l = listing_service.publish_product_to_marketplace(product.id, mp.id)
        assert l.status == "ACTIVE"
        assert l.listed_qty == 48  # 50 - 2
        assert l.selling_price == Decimal("24.00")  # 20 * 1.20
        assert l.external_listing_id is not None
        listings.append(l)

    assert len(listings) == 5

    # 6. Test Channel Connection API endpoint for all 5
    for mp in marketplaces:
        resp = client.post(f"/api/v1/marketplaces/{mp.id}/test", headers=admin_auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    # 7. Test Marketplaces list endpoint
    list_resp = client.get("/api/v1/marketplaces", headers=admin_auth_headers)
    assert list_resp.status_code == 200
    mps_data = list_resp.json()
    assert len(mps_data) >= 5
    for item in mps_data:
        assert item["active_listings_count"] >= 1
