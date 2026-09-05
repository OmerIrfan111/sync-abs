from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.pricing_rule import PricingRule
from app.models.inventory_rule import InventoryRule
from app.models.error_log import ErrorLog
from app.schemas.supplier import NormalizedProduct
from app.services.catalog_service import CatalogService
from app.services.listing_service import ListingService, distributed_lock
from app.services.pricing_service import PricingService
from app.services.inventory_service import InventoryService
from app.services.supplier_selection_service import SupplierSelectionService


def test_scenario_1_new_product_to_listing(db_session):
    """
    Scenario 1: New product created in supplier -> catalog entry -> rules applied -> listing created.
    """
    supplier = Supplier(name="Ingram Phase5", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="Amazon US", adapter_class="MockAmazonAdapter", is_active=True)
    db_session.add_all([supplier, marketplace])
    db_session.commit()

    # Ingest supplier item
    cat_service = CatalogService(db_session)
    item = NormalizedProduct(
        supplier_sku="ING-4001",
        sku="SKU-SCENARIO-1",
        title="Dell UltraSharp 32-inch 4K Monitor",
        cost=Decimal("400.00"),
        quantity=15,
        brand="Dell",
        category="Monitors"
    )
    product, sp, _ = cat_service.upsert_supplier_product(supplier, item)
    assert product.id is not None
    assert product.sku == "ING-4001"
    assert sp.cost == Decimal("400.00")
    assert sp.qty_available == 15

    # Configure 20% markup pricing rule and 2 unit buffer inventory rule
    pricing_rule = PricingRule(
        marketplace_id=marketplace.id,
        rule_type="PERCENTAGE_MARKUP",
        percentage=Decimal("20.00")
    )
    inventory_rule = InventoryRule(
        product_id=product.id,
        safety_buffer=2,
        out_of_stock_action="SET_QUANTITY_ZERO"
    )
    db_session.add_all([pricing_rule, inventory_rule])
    db_session.commit()

    # Publish to marketplace
    listing_service = ListingService(db_session)
    listing = listing_service.publish_product_to_marketplace(product.id, marketplace.id)

    assert listing is not None
    assert listing.status == "ACTIVE"
    # Cost 400 * 1.20 = 480.00
    assert listing.selling_price == Decimal("480.00")
    # Quantity 15 - 2 = 13
    assert listing.listed_qty == 13


def test_scenario_2_stock_change_with_buffer(db_session):
    """
    Scenario 2: Supplier stock changes from 25 to 8 -> safety buffer 2 applied -> marketplace stock updated to 6.
    """
    supplier = Supplier(name="D&H Phase5", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay US", adapter_class="MockEBayAdapter", is_active=True)
    product = Product(sku="SKU-SCENARIO-2", title="Logitech MX Master 3S", brand="Logitech")
    db_session.add_all([supplier, marketplace, product])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="DH-2001",
        cost=Decimal("70.00"),
        qty_available=25,
        availability_status="ACTIVE"
    )
    inv_rule = InventoryRule(
        product_id=product.id,
        safety_buffer=2,
        out_of_stock_action="SET_QUANTITY_ZERO"
    )
    db_session.add_all([sp, inv_rule])
    db_session.commit()

    listing_service = ListingService(db_session)
    listing = listing_service.publish_product_to_marketplace(product.id, marketplace.id)
    assert listing.listed_qty == 23  # 25 - 2

    # Stock changes to 8
    sp.qty_available = 8
    db_session.commit()

    listing_service.sync_all_listings_for_product(product.id)
    db_session.refresh(listing)

    # 8 - 2 = 6
    assert listing.listed_qty == 6
    assert listing.status == "ACTIVE"


def test_scenario_3_cost_change_with_markup(db_session):
    """
    Scenario 3: Supplier cost changes from $500 to $520 -> 15% markup rule applied -> marketplace price updated from $575 to $598.
    """
    supplier = Supplier(name="TDSynnex Phase5", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="Walmart US", adapter_class="MockWalmartAdapter", is_active=True)
    product = Product(sku="SKU-SCENARIO-3", title="Enterprise Switch 24-Port", brand="Cisco")
    db_session.add_all([supplier, marketplace, product])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="TD-3001",
        cost=Decimal("500.00"),
        qty_available=10,
        availability_status="ACTIVE"
    )
    price_rule = PricingRule(
        marketplace_id=marketplace.id,
        rule_type="PERCENTAGE_MARKUP",
        percentage=Decimal("15.00")
    )
    db_session.add_all([sp, price_rule])
    db_session.commit()

    listing_service = ListingService(db_session)
    listing = listing_service.publish_product_to_marketplace(product.id, marketplace.id)
    # 500 * 1.15 = 575.00
    assert listing.selling_price == Decimal("575.00")

    # Cost changes from 500 to 520
    sp.cost = Decimal("520.00")
    db_session.commit()

    listing_service.sync_all_listings_for_product(product.id)
    db_session.refresh(listing)

    # 520 * 1.15 = 598.00
    assert listing.selling_price == Decimal("598.00")


def test_scenario_4_supplier_stock_zero_oos_action(db_session):
    """
    Scenario 4: Supplier stock drops to 0 -> marketplace stock updated to 0 / listing handled per OOS action.
    """
    supplier = Supplier(name="MaLabs Phase5", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="Newegg US", adapter_class="MockNeweggAdapter", is_active=True)
    product = Product(sku="SKU-SCENARIO-4", title="NVMe SSD 2TB", brand="Samsung")
    db_session.add_all([supplier, marketplace, product])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="ML-4001",
        cost=Decimal("120.00"),
        qty_available=12,
        availability_status="ACTIVE"
    )
    inv_rule = InventoryRule(
        product_id=product.id,
        safety_buffer=2,
        out_of_stock_action="DISABLE_LISTING"
    )
    db_session.add_all([sp, inv_rule])
    db_session.commit()

    listing_service = ListingService(db_session)
    listing = listing_service.publish_product_to_marketplace(product.id, marketplace.id)
    assert listing.listed_qty == 10

    # Stock drops to 0
    sp.qty_available = 0
    db_session.commit()

    listing_service.sync_all_listings_for_product(product.id)
    db_session.refresh(listing)

    assert listing.listed_qty == 0
    assert listing.status == "PAUSED"


def test_scenario_5_stock_recovery_reactivation(db_session):
    """
    Scenario 5: Supplier stock recovers from 0 to 10 -> safety buffer 2 applied -> marketplace stock updated to 8 and listing reactivated.
    """
    supplier = Supplier(name="VoiceComm Phase5", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="Shopify US", adapter_class="MockShopifyAdapter", is_active=True)
    product = Product(sku="SKU-SCENARIO-5", title="Fast Wireless Charger", brand="Anker")
    db_session.add_all([supplier, marketplace, product])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="VC-5001",
        cost=Decimal("25.00"),
        qty_available=0,
        availability_status="ACTIVE"
    )
    inv_rule = InventoryRule(
        product_id=product.id,
        safety_buffer=2,
        out_of_stock_action="DISABLE_LISTING"
    )
    db_session.add_all([sp, inv_rule])
    db_session.commit()

    listing_service = ListingService(db_session)
    listing = listing_service.publish_product_to_marketplace(product.id, marketplace.id)
    assert listing.listed_qty == 0
    assert listing.status == "PAUSED"

    # Restock from 0 to 10
    sp.qty_available = 10
    db_session.commit()

    listing_service.sync_all_listings_for_product(product.id)
    db_session.refresh(listing)

    # 10 - 2 = 8
    assert listing.listed_qty == 8
    assert listing.status == "ACTIVE"


def test_scenario_6_multiple_suppliers_routing(db_session):
    """
    Scenario 6: Product available from multiple suppliers -> rules engine picks correct supplier based on price/priority.
    """
    supp_cheap = Supplier(name="Supp Cheap", adapter_class="MockSupplierAdapter", is_active=True)
    supp_costly = Supplier(name="Supp Costly", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay Multi", adapter_class="MockEBayAdapter", is_active=True)
    product = Product(sku="SKU-SCENARIO-6", title="Mechanical Keyboard RGB", brand="Corsair")
    db_session.add_all([supp_cheap, supp_costly, marketplace, product])
    db_session.commit()

    sp_cheap = SupplierProduct(
        product_id=product.id,
        supplier_id=supp_cheap.id,
        supplier_sku="CHEAP-01",
        cost=Decimal("80.00"),
        qty_available=5,
        availability_status="ACTIVE"
    )
    sp_costly = SupplierProduct(
        product_id=product.id,
        supplier_id=supp_costly.id,
        supplier_sku="COSTLY-01",
        cost=Decimal("100.00"),
        qty_available=15,
        availability_status="ACTIVE"
    )
    price_rule = PricingRule(
        marketplace_id=marketplace.id,
        rule_type="PERCENTAGE_MARKUP",
        percentage=Decimal("10.00")
    )
    db_session.add_all([sp_cheap, sp_costly, price_rule])
    db_session.commit()

    selection_service = SupplierSelectionService(db_session)
    pricing_service = PricingService(db_session)

    # Best supplier selection picks lowest cost ($80.00)
    best_sp = selection_service.select_best_supplier(product)
    assert best_sp.id == sp_cheap.id
    calculated_price = pricing_service.calculate_price(cost=best_sp.cost, marketplace_id=marketplace.id)
    # 80 * 1.10 = 88.00
    assert calculated_price == Decimal("88.00")

    # If cheap supplier runs out of stock, system falls back to costly supplier ($100.00)
    sp_cheap.qty_available = 0
    db_session.commit()

    fallback_sp = selection_service.select_best_supplier(product)
    assert fallback_sp.id == sp_costly.id
    fallback_price = pricing_service.calculate_price(cost=fallback_sp.cost, marketplace_id=marketplace.id)
    # 100 * 1.10 = 110.00
    assert fallback_price == Decimal("110.00")


def test_scenario_7_marketplace_failure_and_error_logging(db_session):
    """
    Scenario 7: Marketplace API returns error -> retry triggered -> error logged -> dashboard reflects attention.
    """
    from app.api.v1.endpoints.dashboard import get_dashboard_summary

    supplier = Supplier(name="Ingram Fail", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="Flaky Marketplace", adapter_class="MockAmazonAdapter", is_active=True)
    product = Product(sku="SKU-SCENARIO-7", title="Test Failure SKU", brand="Generic")
    db_session.add_all([supplier, marketplace, product])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="FAIL-01",
        cost=Decimal("50.00"),
        qty_available=10,
        availability_status="ACTIVE"
    )
    db_session.add(sp)
    db_session.commit()

    listing_service = ListingService(db_session)

    # Mock adapter's create_listing to simulate an API exception
    with patch.object(listing_service, "get_adapter_for_marketplace") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_adapter.create_listing.side_effect = Exception("500 Internal Server Error from Marketplace API")
        mock_get_adapter.return_value = mock_adapter

        with pytest.raises(Exception) as exc_info:
            listing_service.publish_product_to_marketplace(product.id, marketplace.id)
        assert "500 Internal Server Error" in str(exc_info.value)

    # Verify ErrorLog was recorded
    err = db_session.query(ErrorLog).filter(
        ErrorLog.product_id == product.id,
        ErrorLog.marketplace_id == marketplace.id
    ).first()
    assert err is not None
    assert err.error_type == "LISTING_ERROR"
    assert err.status == "FAILED"
    assert "500 Internal Server Error" in err.message

    # Verify Dashboard stats reflects needs_attention
    summary = get_dashboard_summary(db=db_session)
    assert summary.needs_attention >= 1
    recent_err_ids = [e.id for e in summary.recent_errors]
    assert err.id in recent_err_ids


def test_scenario_8_redis_concurrency_lock():
    """
    Scenario 8: Concurrent workers processing same product -> Redis distributed lock prevents duplicate/conflicting updates.
    """
    mock_redis = MagicMock()
    mock_lock1 = MagicMock()
    mock_lock2 = MagicMock()

    # Worker 1 acquires lock successfully
    mock_lock1.acquire.return_value = True
    # Worker 2 fails to acquire lock because worker 1 holds it
    mock_lock2.acquire.return_value = False

    def side_effect(key, **kwargs):
        if not hasattr(side_effect, "called"):
            side_effect.called = True
            return mock_lock1
        return mock_lock2

    mock_redis.lock.side_effect = side_effect

    with patch("app.services.listing_service.get_redis_client", return_value=mock_redis):
        # Worker 1 enters critical section
        with distributed_lock("lock:product:TEST-CONCURRENCY") as acquired1:
            assert acquired1 is True

            # Worker 2 tries to enter simultaneously
            with distributed_lock("lock:product:TEST-CONCURRENCY") as acquired2:
                assert acquired2 is False

        # After worker 1 exits, lock.release is called
        mock_lock1.release.assert_called_once()
