from decimal import Decimal
import pytest

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.order import Order
from app.services.order_service import OrderService


def _setup_catalog(db_session):
    product = Product(sku="ING-LOGI-MXKEYS", title="Logitech MX Keys")
    db_session.add(product)
    supplier = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(supplier)
    marketplace = Marketplace(name="eBay Order Test", adapter_class="MockEBayAdapter", is_active=True)
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


def test_ingest_marketplace_orders_creates_order_and_items(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)

    orders = service.ingest_marketplace_orders(marketplace.id)

    assert len(orders) == 1
    order = orders[0]
    assert order.status == "PENDING_ROUTING"
    assert order.marketplace_id == marketplace.id
    assert len(order.items) == 1
    assert order.items[0].sku == "ING-LOGI-MXKEYS"
    assert order.items[0].product_id == product.id


def test_ingest_marketplace_orders_deduplicates_by_marketplace_order_id(db_session, monkeypatch):
    from app.adapters.marketplaces import mock_ebay

    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)

    def fixed_fetch_orders(self, since_datetime=None):
        return [
            {
                "order_id": "ebay-order-fixed-001",
                "buyer_username": "test_buyer_ebay",
                "buyer_name": "Test Buyer",
                "shipping_address": {},
                "order_total": Decimal("149.99"),
                "marketplace_fees": Decimal("18.75"),
                "currency": "USD",
                "ordered_at": None,
                "items": [
                    {
                        "item_id": "ebay-item-fixed-001",
                        "sku": "ING-LOGI-MXKEYS",
                        "title": "Logitech MX Keys",
                        "quantity": 1,
                        "unit_price": Decimal("149.99"),
                    }
                ],
            }
        ]

    monkeypatch.setattr(mock_ebay.MockEBayAdapter, "fetch_orders", fixed_fetch_orders)

    first_pass = service.ingest_marketplace_orders(marketplace.id)
    assert len(first_pass) == 1

    second_pass = service.ingest_marketplace_orders(marketplace.id)
    assert len(second_pass) == 0
    assert db_session.query(Order).count() == 1


def test_route_order_assigns_supplier_and_cost(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)
    order = service.ingest_marketplace_orders(marketplace.id)[0]

    routed = service.route_order(order.id)

    assert routed.status == "ROUTED"
    item = routed.items[0]
    assert item.status == "ROUTED"
    assert item.supplier_id == supplier.id
    assert item.supplier_cost == Decimal("89.00")


def test_create_purchase_orders_requires_routed_status(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)
    order = service.ingest_marketplace_orders(marketplace.id)[0]

    with pytest.raises(ValueError):
        service.create_purchase_orders(order.id)

    service.route_order(order.id)
    pos = service.create_purchase_orders(order.id)

    assert len(pos) == 1
    po = pos[0]
    assert po.supplier_id == supplier.id
    assert po.total_cost == Decimal("89.00")
    assert po.status == "DRAFT"

    db_session.refresh(order)
    assert order.status == "PO_SUBMITTED"
    assert order.items[0].status == "ORDERED"


def test_submit_purchase_order_records_supplier_confirmation(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)
    order = service.ingest_marketplace_orders(marketplace.id)[0]
    service.route_order(order.id)
    pos = service.create_purchase_orders(order.id)
    po = pos[0]
    assert po.status == "DRAFT"

    updated = service.submit_purchase_order(po.id, "DANDH-CONF-12345")

    assert updated.status == "SUBMITTED"
    assert updated.supplier_order_id == "DANDH-CONF-12345"
    assert updated.submitted_at is not None

    # Cannot submit twice
    with pytest.raises(ValueError):
        service.submit_purchase_order(po.id, "ANOTHER-CONF")

    # Cannot submit a nonexistent PO
    with pytest.raises(ValueError):
        service.submit_purchase_order(99999, "SOME-ID")


def test_update_tracking_marks_order_shipped(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)
    order = service.ingest_marketplace_orders(marketplace.id)[0]
    service.route_order(order.id)
    service.create_purchase_orders(order.id)

    updated = service.update_tracking(order.id, "1Z999AA10123456784", "UPS")

    assert updated.status == "SHIPPED"
    assert updated.shipped_at is not None
    assert updated.purchase_orders[0].tracking_number == "1Z999AA10123456784"
    assert updated.purchase_orders[0].carrier == "UPS"
    assert updated.purchase_orders[0].status == "SHIPPED"


def test_cancel_order_resets_items_and_pos(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)
    order = service.ingest_marketplace_orders(marketplace.id)[0]
    service.route_order(order.id)
    service.create_purchase_orders(order.id)

    cancelled = service.cancel_order(order.id, reason="Buyer requested cancellation")

    assert cancelled.status == "CANCELLED"
    assert cancelled.purchase_orders[0].status == "CANCELLED"
    assert cancelled.items[0].status == "PENDING"

    with pytest.raises(ValueError):
        service.cancel_order(999999)


def test_cancel_order_warns_when_po_already_submitted_to_supplier(db_session):
    from app.models.error_log import ErrorLog

    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)
    order = service.ingest_marketplace_orders(marketplace.id)[0]
    service.route_order(order.id)
    pos = service.create_purchase_orders(order.id)
    service.submit_purchase_order(pos[0].id, "DANDH-CONF-999")

    service.cancel_order(order.id, reason="Buyer changed their mind after we already ordered")

    warning = db_session.query(ErrorLog).filter(
        ErrorLog.error_type == "INVENTORY_MISMATCH",
        ErrorLog.supplier_id == supplier.id,
    ).first()
    assert warning is not None
    assert "DANDH-CONF-999" in warning.message
    assert "cannot cancel a real supplier order automatically" in warning.message


def test_get_stats_reports_accurate_counts(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    service = OrderService(db_session)
    order = service.ingest_marketplace_orders(marketplace.id)[0]

    stats = service.get_stats()

    assert stats["total_orders"] == 1
    assert stats["pending_routing"] == 1
    assert stats["orders_today"] == 1
