from decimal import Decimal
import pytest
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.pricing_rule import PricingRule
from app.models.inventory_rule import InventoryRule
from app.models.sync_log import SyncLog
from app.services.listing_service import ListingService

def test_spec_section_29_e2e_scenario(db_session):
    """
    Mandatory Specification Section 29 scenario test:
    - Product TEST-001
    - Supplier A has 20 units at $500. Supplier B has 8 units at $520.
    - Pricing Rule: 15% markup.
    - Safety buffer: 2 units.
    - Initial: Price $575, Qty 18 (from Supplier A: 20 - 2 = 18).
    - Step 1: Supplier A stock -> 0. System switches to Supplier B: Price $598 (520 * 1.15), Qty 6 (8 - 2 = 6).
    - Step 2: Supplier B stock -> 1. Qty drops to 0 (1 - 2 = -1 -> strict zero floor).
    - Step 3: Both out of stock. Status handles OOS action.
    - Step 4: Supplier A restocks 10 units at $510. Listing reactivates, Price $586.50, Qty 8 (10 - 2).
    - All transitions verified in database & SyncLog.
    """
    listing_service = ListingService(db_session)

    # Setup Suppliers
    supp_a = Supplier(name="Supplier A (Ingram)", adapter_class="MockSupplierAdapter", is_active=True)
    supp_b = Supplier(name="Supplier B (D&H)", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add_all([supp_a, supp_b])
    db_session.commit()

    # Setup Marketplace (eBay)
    marketplace = Marketplace(
        name="eBay US",
        adapter_class="MockEBayAdapter",
        is_active=True
    )
    db_session.add(marketplace)
    db_session.commit()

    # Setup Canonical Product TEST-001
    product = Product(
        sku="TEST-001",
        title="Enterprise 4K Monitor 27-inch",
        description="High dynamic range calibrated display",
        category="Electronics",
        brand="ViewMaster"
    )
    db_session.add(product)
    db_session.commit()

    # Supplier A: 20 units at $500
    sp_a = SupplierProduct(
        product_id=product.id,
        supplier_id=supp_a.id,
        supplier_sku="SUPP-A-001",
        cost=Decimal("500.00"),
        qty_available=20,
        availability_status="ACTIVE"
    )
    # Supplier B: 8 units at $520
    sp_b = SupplierProduct(
        product_id=product.id,
        supplier_id=supp_b.id,
        supplier_sku="SUPP-B-001",
        cost=Decimal("520.00"),
        qty_available=8,
        availability_status="ACTIVE"
    )
    db_session.add_all([sp_a, sp_b])
    db_session.commit()

    # Setup Rules:
    # 15% Percentage Markup for product
    pricing_rule = PricingRule(
        product_id=product.id,
        rule_type="PERCENTAGE_MARKUP",
        percentage=Decimal("15.00")
    )
    # Safety buffer: 2 units, OOS Action: DISABLE_LISTING
    inventory_rule = InventoryRule(
        product_id=product.id,
        safety_buffer=2,
        out_of_stock_action="DISABLE_LISTING"
    )
    db_session.add_all([pricing_rule, inventory_rule])
    db_session.commit()

    # INITIAL PUBLISH:
    # Selected supplier: Supp A (lowest cost $500, stock 20)
    # Qty: 20 - 2 = 18
    # Price: 500 * 1.15 = 575.00
    listing = listing_service.publish_product_to_marketplace(
        product_id=product.id,
        marketplace_id=marketplace.id
    )
    assert listing.status == "ACTIVE"
    assert listing.listed_qty == 18
    assert listing.selling_price == Decimal("575.00")

    # STEP 1: Supplier A goes out of stock (stock -> 0)
    sp_a.qty_available = 0
    db_session.commit()

    synced_listings = listing_service.sync_all_listings_for_product(product.id)
    assert len(synced_listings) == 1
    updated = synced_listings[0]

    # Switched to Supplier B ($520, stock 8):
    # Price: 520 * 1.15 = 598.00
    # Qty: 8 - 2 = 6
    assert updated.selling_price == Decimal("598.00")
    assert updated.listed_qty == 6
    assert updated.status == "ACTIVE"

    # STEP 2: Supplier B stock drops to 1
    sp_b.qty_available = 1
    db_session.commit()

    synced_listings = listing_service.sync_all_listings_for_product(product.id)
    updated = synced_listings[0]

    # Qty: max(1 - 2, 0) = 0 (strict zero floor)
    # Out of stock action DISABLE_LISTING sets status to PAUSED
    assert updated.listed_qty == 0
    assert updated.status == "PAUSED"

    # STEP 3: Both suppliers out of stock
    sp_b.qty_available = 0
    db_session.commit()

    synced_listings = listing_service.sync_all_listings_for_product(product.id)
    updated = synced_listings[0]
    assert updated.listed_qty == 0
    assert updated.status == "PAUSED"

    # STEP 4: Supplier A restocks 10 units at $510
    sp_a.qty_available = 10
    sp_a.cost = Decimal("510.00")
    db_session.commit()

    synced_listings = listing_service.sync_all_listings_for_product(product.id)
    updated = synced_listings[0]

    # Reactivates to ACTIVE:
    # Price: 510 * 1.15 = 586.50
    # Qty: 10 - 2 = 8
    assert updated.status == "ACTIVE"
    assert updated.listed_qty == 8
    assert updated.selling_price == Decimal("586.50")

    # Verify transitions logged in SyncLog
    logs = db_session.query(SyncLog).filter(SyncLog.product_id == product.id).all()
    assert len(logs) > 0
    log_fields = [log.field_changed for log in logs]
    assert "eBay US_quantity_update" in log_fields
    assert "eBay US_price_update" in log_fields
    assert "eBay US_status_update" in log_fields
