from decimal import Decimal
import pytest
from datetime import datetime, timezone

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.pricing_rule import PricingRule
from app.models.shipping_history import ProductShippingHistory
from app.services.pricing_service import PricingService
from app.services.shipping_service import ShippingService
from app.services.listing_service import ListingService


def test_pricing_calculation_with_base_shipping_charge(db_session):
    """
    Feature 1: Verify final_price = base_price + base_shipping_charge (+ markup)
    using exact Decimal math across all rule types.
    """
    pricing = PricingService(db_session)
    cost = Decimal("100.00")
    shipping = Decimal("15.50")

    # 1. Default fallback rule (15% markup on total effective cost)
    # Total cost basis = 115.50 -> 115.50 * 1.15 = 132.825 -> 132.83
    default_price = pricing.calculate_price(cost=cost, shipping_charge=shipping)
    assert default_price == Decimal("132.83")
    assert isinstance(default_price, Decimal)

    # 2. FIXED_PROFIT: effective_cost + fixed_profit
    # 115.50 + 20.00 = 135.50
    rule_fixed = PricingRule(rule_type="FIXED_PROFIT", fixed_amount=Decimal("20.00"))
    price_fixed = pricing.calculate_price(cost=cost, shipping_charge=shipping, rule_override=rule_fixed)
    assert price_fixed == Decimal("135.50")

    # 3. PERCENTAGE_MARKUP: effective_cost + (effective_cost * 10%)
    # 115.50 + 11.55 = 127.05
    rule_pct = PricingRule(rule_type="PERCENTAGE_MARKUP", percentage=Decimal("10.00"))
    price_pct = pricing.calculate_price(cost=cost, shipping_charge=shipping, rule_override=rule_pct)
    assert price_pct == Decimal("127.05")

    # 4. FEE_MARGIN: accounts for 10% fee and 15% desired margin on effective cost basis
    # (115.50 * 1.15) / (1 - 0.10) = 132.825 / 0.90 = 147.5833... -> 147.58
    rule_fee = PricingRule(rule_type="FEE_MARGIN", marketplace_fee=Decimal("10.00"), desired_margin=Decimal("15.00"))
    price_fee = pricing.calculate_price(cost=cost, shipping_charge=shipping, rule_override=rule_fee)
    assert price_fee == Decimal("147.58")


def test_shipping_resolution_live_source(db_session):
    """
    Feature 1: Sourcing live ground shipping charge from supplier adapter.
    Stores charge, source='live', and updates SupplierProduct.
    """
    product = Product(sku="TEST-SKU-SHIP-01", title="Router A")
    supplier = Supplier(name="Mock Tech", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add_all([product, supplier])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="MOCK-ROUTER-01",
        cost=Decimal("50.00"),
        qty_available=10,
    )
    db_session.add(sp)
    db_session.commit()

    service = ShippingService(db_session)
    charge, source = service.resolve_shipping_charge(sp, destination_zip="90210")

    assert charge == Decimal("9.95")
    assert source == "live"
    assert sp.base_shipping_charge == Decimal("9.95")
    assert sp.shipping_source == "live"
    assert sp.shipping_status == "valid"
    assert sp.shipping_updated_at is not None

    # Check audit trail in ProductShippingHistory
    history = db_session.query(ProductShippingHistory).filter(ProductShippingHistory.product_id == product.id).first()
    assert history is not None
    assert history.shipping_charge == Decimal("9.95")
    assert history.source == "live"
    assert history.destination_zip == "90210"


def test_shipping_resolution_fallback_to_history(db_session):
    """
    Feature 1: When live shipping query is unavailable, falls back to the most recent historical rate.
    """
    product = Product(sku="TEST-SKU-SHIP-02", title="Switch B")
    supplier = Supplier(name="Mock Tech 2", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add_all([product, supplier])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="MOCK-SWITCH-02",
        cost=Decimal("75.00"),
        qty_available=5,
    )
    db_session.add(sp)
    db_session.commit()

    # Seed an earlier historical shipping record
    past_history = ProductShippingHistory(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_product_id=sp.id,
        shipping_charge=Decimal("12.45"),
        source="live",
        destination_zip="90210",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(past_history)
    db_session.commit()

    service = ShippingService(db_session)
    # Force fallback to test history lookup
    charge, source = service.resolve_shipping_charge(sp, force_history_fallback=True)

    assert charge == Decimal("12.45")
    assert source == "history"
    assert sp.base_shipping_charge == Decimal("12.45")
    assert sp.shipping_source == "history"
    assert sp.shipping_status == "valid"


def test_shipping_unknown_blocks_publishing(db_session):
    """
    Feature 1: If neither live nor historical shipping charge exists,
    flag product as 'shipping_unknown' and reject publishing with a clear error.
    """
    product = Product(sku="TEST-SKU-UNKNOWN-SHIP", title="Unknown Shipping Widget")
    supplier = Supplier(
        name="Unknown Supplier",
        adapter_class="MockSupplierAdapter",
        is_active=True,
    )
    supplier._adapter_config = {"simulate_shipping_unknown": True}
    marketplace = Marketplace(name="eBay Test", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add_all([product, supplier, marketplace])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="UNKNOWN-WIDGET-01",
        cost=Decimal("40.00"),
        qty_available=10,
    )
    db_session.add(sp)
    db_session.commit()

    shipping_service = ShippingService(db_session)
    charge, source = shipping_service.resolve_shipping_charge(sp)
    assert charge is None
    assert source == "shipping_unknown"
    assert sp.shipping_status == "shipping_unknown"

    # Attempting to publish must be blocked
    listing_service = ListingService(db_session)
    with pytest.raises(ValueError) as exc_info:
        listing_service.publish_product_to_marketplace(
            product_id=product.id,
            marketplace_id=marketplace.id,
        )

    assert "shipping_unknown" in str(exc_info.value)


def test_supplier_default_shipping_charge_fallback(db_session):
    """
    Verify that if no live or historical shipping charge is available,
    ShippingService falls back to supplier.default_shipping_charge.
    """
    product = Product(sku="TEST-SKU-DEF-SHIP", title="Gadget Default Ship")
    supplier = Supplier(
        name="Default Ship Supplier",
        adapter_class="MockSupplierAdapter",
        is_active=True,
        default_shipping_charge=Decimal("12.99"),
    )
    supplier._adapter_config = {"simulate_shipping_unknown": True}
    db_session.add_all([product, supplier])
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id,
        supplier_id=supplier.id,
        supplier_sku="DEF-SHIP-SKU",
        cost=Decimal("50.00"),
        qty_available=10,
    )
    db_session.add(sp)
    db_session.commit()

    shipping_service = ShippingService(db_session)
    charge, source = shipping_service.resolve_shipping_charge(sp)
    assert charge == Decimal("12.99")
    assert source == "default"
    assert sp.base_shipping_charge == Decimal("12.99")
    assert sp.shipping_status == "valid"


def test_catalog_sync_inherits_supplier_default_shipping(db_session):
    """
    Verify that newly synced products inherit supplier.default_shipping_charge.
    """
    from app.services.catalog_service import CatalogService
    from app.schemas.supplier import NormalizedProduct

    supplier = Supplier(
        name="Inherit Ship Supplier",
        adapter_class="MockSupplierAdapter",
        is_active=True,
        default_shipping_charge=Decimal("7.50"),
    )
    db_session.add(supplier)
    db_session.commit()

    norm_item = NormalizedProduct(
        supplier_sku="INHERIT-001",
        title="Sync Test Item",
        cost=Decimal("25.00"),
        quantity=15,
        stock_status="IN_STOCK",
        shipping_info={},
        availability_status="ACTIVE",
    )

    catalog_svc = CatalogService(db_session)
    product, sp, logs = catalog_svc.upsert_supplier_product(supplier, norm_item)

    assert sp.base_shipping_charge == Decimal("7.50")
    assert sp.shipping_source == "default"
    assert sp.shipping_status == "valid"

