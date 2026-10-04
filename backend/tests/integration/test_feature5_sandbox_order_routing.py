from decimal import Decimal
import pytest
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services.order_service import OrderService, SandboxViolationError
from app.services.upc_protection_service import UpcProtectionService
from app.core.upc_utils import normalize_upc
from app.core.config import settings


def _create_test_order(db_session, product, marketplace, qty=1):
    order = Order(
        marketplace_id=marketplace.id,
        marketplace_order_id=f"TEST-ORD-{product.id}-{qty}",
        order_total=Decimal("150.00"),
        status="PENDING_ROUTING",
        shipping_address={"name": "Buyer", "street": "123 Main", "zip": "90210", "city": "LA", "state": "CA", "country": "US"}
    )
    db_session.add(order)
    db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        sku=product.sku,
        quantity=qty,
        unit_price=Decimal("150.00"),
        status="PENDING"
    )
    db_session.add(item)
    db_session.commit()
    return order, item


def test_scenario1_cheapest_supplier_wins(db_session):
    """
    Scenario 1: Cheapest supplier wins when both are in stock with equal shipping.
    """
    product = Product(sku="SCENARIO-1-PROD", title="Product Scenario 1")
    s1 = Supplier(name="Supplier Cheap", adapter_class="MockSupplierAdapter", is_active=True)
    s2 = Supplier(name="Supplier Expensive", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay Mkt", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add_all([product, s1, s2, marketplace])
    db_session.commit()

    sp1 = SupplierProduct(product_id=product.id, supplier_id=s1.id, supplier_sku="S1-SKU", cost=Decimal("50.00"), base_shipping_charge=Decimal("5.00"), qty_available=10)
    sp2 = SupplierProduct(product_id=product.id, supplier_id=s2.id, supplier_sku="S2-SKU", cost=Decimal("70.00"), base_shipping_charge=Decimal("5.00"), qty_available=10)
    db_session.add_all([sp1, sp2])
    db_session.commit()

    order, item = _create_test_order(db_session, product, marketplace)
    service = OrderService(db_session)
    routed_order = service.route_order(order.id)

    assert routed_order.status == "ROUTED"
    assert item.status == "ROUTED"
    assert item.supplier_id == s1.id
    assert "Supplier Cheap" in item.routing_note
    assert "[SANDBOX]" in item.routing_note


def test_scenario2_cheapest_supplier_out_of_stock_fallback(db_session):
    """
    Scenario 2: Cheapest supplier is out of stock -> fallback to next available supplier.
    """
    product = Product(sku="SCENARIO-2-PROD", title="Product Scenario 2")
    s1 = Supplier(name="Supplier OOS", adapter_class="MockSupplierAdapter", is_active=True)
    s2 = Supplier(name="Supplier InStock", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay Mkt 2", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add_all([product, s1, s2, marketplace])
    db_session.commit()

    # S1 is cheaper ($40) but 0 stock; S2 is $60 with 5 in stock
    sp1 = SupplierProduct(product_id=product.id, supplier_id=s1.id, supplier_sku="S1-OOS", cost=Decimal("40.00"), base_shipping_charge=Decimal("5.00"), qty_available=0)
    sp2 = SupplierProduct(product_id=product.id, supplier_id=s2.id, supplier_sku="S2-STOCK", cost=Decimal("60.00"), base_shipping_charge=Decimal("5.00"), qty_available=5)
    db_session.add_all([sp1, sp2])
    db_session.commit()

    order, item = _create_test_order(db_session, product, marketplace, qty=1)
    service = OrderService(db_session)
    service.route_order(order.id)

    assert item.status == "ROUTED"
    assert item.supplier_id == s2.id
    assert "Supplier InStock" in item.routing_note


def test_scenario3_shipping_makes_cheaper_base_price_more_expensive(db_session):
    """
    Scenario 3: Supplier A has cheaper base price ($50) but high shipping ($20) = $70 total.
    Supplier B has higher base price ($60) but low shipping ($5) = $65 total.
    Supplier B must win based on total delivered cost!
    """
    product = Product(sku="SCENARIO-3-SHIP", title="Product Scenario 3")
    s_a = Supplier(name="Supplier HighShipping", adapter_class="MockSupplierAdapter", is_active=True)
    s_b = Supplier(name="Supplier LowShipping", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay Mkt 3", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add_all([product, s_a, s_b, marketplace])
    db_session.commit()

    sp_a = SupplierProduct(product_id=product.id, supplier_id=s_a.id, supplier_sku="SA-SKU", cost=Decimal("50.00"), base_shipping_charge=Decimal("20.00"), qty_available=10)
    sp_b = SupplierProduct(product_id=product.id, supplier_id=s_b.id, supplier_sku="SB-SKU", cost=Decimal("60.00"), base_shipping_charge=Decimal("5.00"), qty_available=10)
    db_session.add_all([sp_a, sp_b])
    db_session.commit()

    order, item = _create_test_order(db_session, product, marketplace)
    service = OrderService(db_session)
    service.route_order(order.id)

    assert item.status == "ROUTED"
    assert item.supplier_id == s_b.id
    assert "Supplier LowShipping" in item.routing_note


def test_scenario4_supplier_api_error_fallback(db_session):
    """
    Scenario 4: Supplier API error on primary supplier -> fallback to next available supplier.
    """
    product = Product(sku="SCENARIO-4-ERR", title="Product Scenario 4")
    s_failing = Supplier(name="Supplier Broken", adapter_class="MockSupplierAdapter", is_active=True)
    s_failing._adapter_config = {"simulate_connection_failure": True}
    s_healthy = Supplier(name="Supplier Healthy", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay Mkt 4", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add_all([product, s_failing, s_healthy, marketplace])
    db_session.commit()

    sp_failing = SupplierProduct(product_id=product.id, supplier_id=s_failing.id, supplier_sku="FAIL-SKU", cost=Decimal("30.00"), base_shipping_charge=Decimal("5.00"), qty_available=10)
    sp_healthy = SupplierProduct(product_id=product.id, supplier_id=s_healthy.id, supplier_sku="OK-SKU", cost=Decimal("45.00"), base_shipping_charge=Decimal("5.00"), qty_available=10)
    db_session.add_all([sp_failing, sp_healthy])
    db_session.commit()

    order, item = _create_test_order(db_session, product, marketplace)
    service = OrderService(db_session)
    service.route_order(order.id)

    assert item.status == "ROUTED"
    assert item.supplier_id == s_healthy.id
    assert "Supplier Healthy" in item.routing_note


def test_scenario5_duplicate_upc_order_routing_protection(db_session):
    """
    Scenario 5: Attempting to route/publish items with conflicting duplicate UPCs is blocked.
    """
    valid_upc = "012345678905"
    p_phone = Product(sku="PROD-PHONE", title="Smartphone Pro 128GB", upc=valid_upc)
    p_cable = Product(sku="PROD-CABLE", title="HDMI Cable 6ft", upc=valid_upc)
    db_session.add_all([p_phone, p_cable])
    db_session.commit()

    upc_service = UpcProtectionService(db_session)
    upc_service.register_listing(product=p_phone, marketplace_name="Amazon", marketplace_listing_id="AMZ-001")

    # Cable sharing same UPC is detected and blocked
    result = upc_service.check_product_for_upload(product=p_cable, marketplace_name="Amazon")
    assert result.status == "blocked_upc_conflict"
    assert result.is_blocked()


def test_scenario6_upc_conflict_cross_marketplace(db_session):
    """
    Scenario 6: Cross-marketplace conflict blocked when different product shares UPC.
    """
    valid_upc = "012345678905"
    p_phone = Product(sku="PROD-PHONE-AMZ", title="Smartphone Pro 128GB", upc=valid_upc)
    p_cable = Product(sku="PROD-CABLE-EBAY", title="USB-C Charging Cable", upc=valid_upc)
    db_session.add_all([p_phone, p_cable])
    db_session.commit()

    upc_service = UpcProtectionService(db_session)
    upc_service.register_listing(product=p_phone, marketplace_name="Amazon", marketplace_listing_id="AMZ-PHONE")

    result = upc_service.check_product_for_upload(product=p_cable, marketplace_name="eBay")
    assert result.status == "blocked_cross_marketplace_conflict"


def test_sandbox_hard_guard_throws_on_real_money_attempt(db_session):
    """
    Feature 5 Safeguard: Hard guard throws SandboxViolationError if a real money transaction is attempted while DRY_RUN is active.
    """
    product = Product(sku="SAFEGUARD-PROD", title="Safeguard Product")
    supplier = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    marketplace = Marketplace(name="eBay Guard", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add_all([product, supplier, marketplace])
    db_session.commit()

    sp = SupplierProduct(product_id=product.id, supplier_id=supplier.id, supplier_sku="ING-001", cost=Decimal("100.00"), qty_available=5)
    db_session.add(sp)
    db_session.commit()

    order, item = _create_test_order(db_session, product, marketplace)
    service = OrderService(db_session)
    service.route_order(order.id)
    pos = service.create_purchase_orders(order.id)
    po = pos[0]

    # Normal sandbox simulation succeeds
    simulated_po = service.submit_purchase_order_live(po.id)
    assert simulated_po.status == "SUBMITTED"
    assert "SANDBOX" in simulated_po.supplier_order_id

    # If force_real_money is set while DRY_RUN is on, must raise SandboxViolationError
    service.force_real_money = True
    po.status = "DRAFT"
    db_session.commit()

    with pytest.raises(SandboxViolationError) as exc:
        service.submit_purchase_order_live(po.id)
    assert "Real money transaction blocked" in str(exc.value)
