from decimal import Decimal
import pytest
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.pricing_rule import PricingRule
from app.models.inventory_rule import InventoryRule
from app.models.supplier_priority import SupplierPriority
from app.services.pricing_service import PricingService
from app.services.inventory_service import InventoryService
from app.services.supplier_selection_service import SupplierSelectionService

def test_pricing_formulas(db_session):
    pricing_service = PricingService(db_session)

    # 1. Default fallback (15% markup)
    cost = Decimal("100.00")
    price_default = pricing_service.calculate_price(cost=cost)
    assert price_default == Decimal("115.00")

    # 2. FIXED_PROFIT formula: cost + fixed_amount
    rule_fixed = PricingRule(rule_type="FIXED_PROFIT", fixed_amount=Decimal("25.00"))
    price_fixed = pricing_service.calculate_price(cost=cost, rule_override=rule_fixed)
    assert price_fixed == Decimal("125.00")

    # 3. PERCENTAGE_MARKUP formula: cost + (cost * percentage)
    rule_pct = PricingRule(rule_type="PERCENTAGE_MARKUP", percentage=Decimal("20.00"))
    price_pct = pricing_service.calculate_price(cost=cost, rule_override=rule_pct)
    assert price_pct == Decimal("120.00")

    # 4. FEE_MARGIN formula: (cost * (1 + desired_margin)) / (1 - marketplace_fee)
    # cost 100, margin 15%, fee 10%: (100 * 1.15) / 0.90 = 127.777... -> 127.78
    rule_fee = PricingRule(
        rule_type="FEE_MARGIN",
        marketplace_fee=Decimal("10.00"),
        desired_margin=Decimal("15.00")
    )
    price_fee = pricing_service.calculate_price(cost=cost, rule_override=rule_fee)
    assert price_fee == Decimal("127.78")


def test_pricing_hierarchy_resolution(db_session):
    pricing_service = PricingService(db_session)

    # Setup Product & Marketplaces
    product = Product(sku="TEST-SKU-PRICING", title="Pricing Test Widget")
    db_session.add(product)
    mp1 = Marketplace(name="eBay US", adapter_class="MockEBayAdapter")
    mp2 = Marketplace(name="Amazon US", adapter_class="MockEBayAdapter")
    db_session.add_all([mp1, mp2])
    db_session.commit()

    # 1. Global rule (product=None, marketplace=None): 10%
    global_rule = PricingRule(rule_type="PERCENTAGE_MARKUP", percentage=Decimal("10.00"))
    db_session.add(global_rule)
    db_session.commit()

    price = pricing_service.calculate_price(Decimal("100.00"), product_id=product.id, marketplace_id=mp1.id)
    assert price == Decimal("110.00")

    # 2. Marketplace-specific rule: 20%
    mp_rule = PricingRule(marketplace_id=mp1.id, rule_type="PERCENTAGE_MARKUP", percentage=Decimal("20.00"))
    db_session.add(mp_rule)
    db_session.commit()

    price = pricing_service.calculate_price(Decimal("100.00"), product_id=product.id, marketplace_id=mp1.id)
    assert price == Decimal("120.00")

    # 3. Product-specific rule: Fixed $35
    prod_rule = PricingRule(product_id=product.id, rule_type="FIXED_PROFIT", fixed_amount=Decimal("35.00"))
    db_session.add(prod_rule)
    db_session.commit()

    price = pricing_service.calculate_price(Decimal("100.00"), product_id=product.id, marketplace_id=mp1.id)
    assert price == Decimal("135.00")

    # 4. Product + Marketplace exact rule: Fixed $50
    exact_rule = PricingRule(
        product_id=product.id,
        marketplace_id=mp1.id,
        rule_type="FIXED_PROFIT",
        fixed_amount=Decimal("50.00")
    )
    db_session.add(exact_rule)
    db_session.commit()

    price = pricing_service.calculate_price(Decimal("100.00"), product_id=product.id, marketplace_id=mp1.id)
    assert price == Decimal("150.00")

    # Different marketplace (mp2) falls back to product-specific rule ($35)
    price_mp2 = pricing_service.calculate_price(Decimal("100.00"), product_id=product.id, marketplace_id=mp2.id)
    assert price_mp2 == Decimal("135.00")


def test_inventory_safety_buffer_and_zero_floor(db_session):
    inventory_service = InventoryService(db_session)

    rule = InventoryRule(safety_buffer=2, out_of_stock_action="SET_QUANTITY_ZERO")

    # Case 1: stock 20, buffer 2 -> 18
    qty, action = inventory_service.calculate_marketplace_quantity(20, rule_override=rule)
    assert qty == 18
    assert action == "SET_QUANTITY_ZERO"

    # Case 2: stock 8, buffer 2 -> 6
    qty, _ = inventory_service.calculate_marketplace_quantity(8, rule_override=rule)
    assert qty == 6

    # Case 3: stock 1, buffer 2 -> 0 (Zero floor, never negative!)
    qty, _ = inventory_service.calculate_marketplace_quantity(1, rule_override=rule)
    assert qty == 0

    # Case 4: stock 0, buffer 2 -> 0
    qty, _ = inventory_service.calculate_marketplace_quantity(0, rule_override=rule)
    assert qty == 0


def test_inventory_out_of_stock_status_actions(db_session):
    inventory_service = InventoryService(db_session)

    # SET_QUANTITY_ZERO: status remains ACTIVE with qty 0
    status_1 = inventory_service.determine_listing_status(0, oos_action="SET_QUANTITY_ZERO")
    assert status_1 == "ACTIVE"

    # DISABLE_LISTING: status becomes PAUSED
    status_2 = inventory_service.determine_listing_status(0, oos_action="DISABLE_LISTING")
    assert status_2 == "PAUSED"

    # MARK_UNAVAILABLE: status becomes UNAVAILABLE
    status_3 = inventory_service.determine_listing_status(0, oos_action="MARK_UNAVAILABLE")
    assert status_3 == "UNAVAILABLE"

    # Reactivation when stock returns: any qty > 0 returns ACTIVE
    reactivated = inventory_service.determine_listing_status(10, oos_action="DISABLE_LISTING", current_status="PAUSED")
    assert reactivated == "ACTIVE"


def test_supplier_selection_service(db_session):
    selection_service = SupplierSelectionService(db_session)

    s1 = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    s2 = Supplier(name="D&H", adapter_class="MockSupplierAdapter", is_active=True)
    s3 = Supplier(name="TD SYNNEX", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    product = Product(sku="TEST-MULTI-SUPP", title="Multi Supplier Widget")
    db_session.add(product)
    db_session.commit()

    # s1: Cost $500, stock 20, lead_time 3 days
    sp1 = SupplierProduct(
        product_id=product.id,
        supplier_id=s1.id,
        supplier_sku="IM-1",
        cost=Decimal("500.00"),
        qty_available=20,
        availability_status="ACTIVE",
        shipping_info={"lead_time_days": 3}
    )
    # s2: Cost $520, stock 8, lead_time 1 day
    sp2 = SupplierProduct(
        product_id=product.id,
        supplier_id=s2.id,
        supplier_sku="DH-1",
        cost=Decimal("520.00"),
        qty_available=8,
        availability_status="ACTIVE",
        shipping_info={"lead_time_days": 1}
    )
    # s3: Cost $490, stock 0 (Out of stock), lead_time 2 days
    sp3 = SupplierProduct(
        product_id=product.id,
        supplier_id=s3.id,
        supplier_sku="TD-1",
        cost=Decimal("490.00"),
        qty_available=0,
        availability_status="ACTIVE",
        shipping_info={"lead_time_days": 2}
    )
    db_session.add_all([sp1, sp2, sp3])
    db_session.commit()
    db_session.refresh(product)

    # 1. LOWEST_COST rule: should select sp1 ($500) because sp3 ($490) is out of stock
    best = selection_service.select_best_supplier(product, selection_rule_override="LOWEST_COST")
    assert best.supplier_id == s1.id
    assert best.cost == Decimal("500.00")

    # 2. HIGHEST_STOCK rule: selects sp1 (stock 20 > 8)
    best_stock = selection_service.select_best_supplier(product, selection_rule_override="HIGHEST_STOCK")
    assert best_stock.supplier_id == s1.id
    assert best_stock.qty_available == 20

    # 3. SHIPPING_LOCATION rule: selects sp2 (lead_time 1 day < 3 days)
    best_shipping = selection_service.select_best_supplier(product, selection_rule_override="SHIPPING_LOCATION")
    assert best_shipping.supplier_id == s2.id
    assert best_shipping.shipping_info["lead_time_days"] == 1

    # 4. PRIORITY_RANK rule: configure s2 rank 1, s1 rank 2
    pr1 = SupplierPriority(product_id=product.id, supplier_id=s2.id, priority_rank=1, selection_rule="PRIORITY_RANK")
    pr2 = SupplierPriority(product_id=product.id, supplier_id=s1.id, priority_rank=2, selection_rule="PRIORITY_RANK")
    db_session.add_all([pr1, pr2])
    db_session.commit()

    best_priority = selection_service.select_best_supplier(product, selection_rule_override="PRIORITY_RANK")
    assert best_priority.supplier_id == s2.id
