from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.warehouse import Warehouse, WarehouseStock
from app.services.order_service import OrderService


def _setup_dandh_order(db_session, warehouse_stocks):
    """warehouse_stocks: list of (branch_code, qty_available) tuples."""
    product = Product(sku="DANDH-BRANCH-TEST", title="D&H Branch Test Product")
    db_session.add(product)
    supplier = Supplier(name="D&H", adapter_class="DAndHAdapter", is_active=True)
    db_session.add(supplier)
    marketplace = Marketplace(name="eBay Branch Test", adapter_class="MockEBayAdapter", is_active=True)
    db_session.add(marketplace)
    db_session.commit()

    sp = SupplierProduct(
        product_id=product.id, supplier_id=supplier.id, supplier_sku="DH-BR-001",
        cost=Decimal("50.00"), qty_available=sum(q for _, q in warehouse_stocks),
        availability_status="ACTIVE",
    )
    db_session.add(sp)
    db_session.commit()

    for code, qty in warehouse_stocks:
        wh = db_session.query(Warehouse).filter(Warehouse.supplier_id == supplier.id, Warehouse.code == code).first()
        if not wh:
            wh = Warehouse(supplier_id=supplier.id, code=code, name=f"Branch {code}", is_active=True)
            db_session.add(wh)
            db_session.commit()
        db_session.add(WarehouseStock(supplier_product_id=sp.id, warehouse_id=wh.id, qty_available=qty))
    db_session.commit()

    order = Order(
        marketplace_id=marketplace.id, marketplace_order_id="DANDH-BRANCH-ORDER",
        order_total=Decimal("100.00"), status="PENDING_ROUTING",
        shipping_address={"name": "Buyer", "street": "1 Main St", "city": "LA", "state": "CA", "zip": "90001", "country": "US"},
    )
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id, product_id=product.id, sku=product.sku,
        quantity=3, unit_price=Decimal("100.00"), status="PENDING",
    )
    db_session.add(item)
    db_session.commit()

    service = OrderService(db_session)
    service.route_order(order.id)
    pos = service.create_purchase_orders(order.id)
    return service, pos[0]


def test_submit_live_picks_branch_with_sufficient_real_stock(db_session, monkeypatch):
    """
    Real bug fixed 2026-10-09: submit_order() used to always default to
    branch="BR01" regardless of where the routed stock actually was. This
    verifies the real WarehouseStock data (not a guess) picks the branch
    that can actually fulfill the order quantity.
    """
    monkeypatch.setattr("app.services.order_service.settings.DRY_RUN", False)
    service, po = _setup_dandh_order(db_session, [("BR01", 1), ("BR02", 5)])

    mock_adapter = MagicMock()
    mock_adapter.submit_order.return_value = {"id": "DH-REAL-123", "orderNumber": "DH-REAL-123"}

    with patch("app.services.sync_service.SyncService.get_adapter_for_supplier", return_value=mock_adapter):
        result = service.submit_purchase_order_live(po.id)

    assert result.status == "SUBMITTED"
    assert result.supplier_order_id == "DH-REAL-123"
    _, kwargs = mock_adapter.submit_order.call_args
    assert kwargs["branch"] == "BR02"  # only BR02 has >= 3 units; BR01 only has 1


def test_submit_live_omits_branch_when_none_covers_full_order(db_session, monkeypatch):
    """
    Real schema confirmed 2026-10-09 (full OAS spec pasted): shipments[].branch
    is OPTIONAL — "D&H will select the best warehouse if one is not entered."
    So when no single real D&H branch covers the whole order (qty 3 split
    across BR01=1, BR02=2), the correct behavior is to omit "branch" entirely
    and let D&H's own system route it — never guess one, and never block the
    order either, since D&H already handles this case by design.
    """
    monkeypatch.setattr("app.services.order_service.settings.DRY_RUN", False)
    service, po = _setup_dandh_order(db_session, [("BR01", 1), ("BR02", 2)])

    mock_adapter = MagicMock()
    mock_adapter.submit_order.return_value = {"id": "DH-REAL-456", "orderNumber": "DH-REAL-456"}
    with patch("app.services.sync_service.SyncService.get_adapter_for_supplier", return_value=mock_adapter):
        result = service.submit_purchase_order_live(po.id)

    assert result.status == "SUBMITTED"
    _, kwargs = mock_adapter.submit_order.call_args
    assert "branch" not in kwargs


def test_submit_live_leaves_po_as_draft_when_real_adapter_call_fails(db_session, monkeypatch):
    """
    Explicit guarantee the user asked to confirm (2026-10-09): if the real
    supplier API call fails (down, rejected, network error, whatever), the
    PO must NOT advance to SUBMITTED. po.status/supplier_order_id are only
    ever written AFTER adapter.submit_order() returns successfully, so a
    raised exception leaves the PO exactly as it was — this proves it.
    """
    monkeypatch.setattr("app.services.order_service.settings.DRY_RUN", False)
    service, po = _setup_dandh_order(db_session, [("BR01", 5)])
    assert po.status == "DRAFT"

    mock_adapter = MagicMock()
    mock_adapter.submit_order.side_effect = ConnectionError("D&H API is down")

    with patch("app.services.sync_service.SyncService.get_adapter_for_supplier", return_value=mock_adapter):
        with pytest.raises(ConnectionError):
            service.submit_purchase_order_live(po.id)

    db_session.refresh(po)
    assert po.status == "DRAFT"
    assert po.supplier_order_id is None
