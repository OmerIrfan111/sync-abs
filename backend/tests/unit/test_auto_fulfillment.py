from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.models.marketplace import Marketplace
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.services.auto_fulfillment_service import AutoFulfillmentService
from app.services.order_service import OrderService
from app.services.sync_service import SyncService


class FakeAdapter:
    def __init__(self, live_qty):
        self.live_qty = live_qty

    def test_connection(self):
        return True

    def fetch_inventory(self, skus):
        return {} if self.live_qty is None else {str(s): self.live_qty for s in skus}


@pytest.fixture(autouse=True)
def auto_on(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_ORDER_ENABLED", True)
    monkeypatch.setattr(settings, "AUTO_ORDER_MAX_ORDER_VALUE", Decimal("1000.00"))
    monkeypatch.setattr(settings, "AUTO_ORDER_MIN_PROFIT", Decimal("0.00"))


def _order(db, *, supplier_name="Ingram Micro", adapter="IngramMicroAdapter", cost="89.00",
           qty_in_stock=25, qty=1, total="150.00", fees="15.00", with_product=True, tag="a"):
    sup = Supplier(name=f"{supplier_name} {tag}" if False else supplier_name, adapter_class=adapter, is_active=True)
    prod = Product(sku=f"AUTO-{tag}", title="Wall Mount", brand="Chief")
    mp = Marketplace(name=f"Auto MP {tag}", adapter_class="MockEBayAdapter", is_active=True)
    existing = db.query(Supplier).filter(Supplier.name == supplier_name).first()
    if existing:
        sup = existing
    else:
        db.add(sup)
    db.add_all([prod, mp])
    db.flush()
    db.add(SupplierProduct(product_id=prod.id, supplier_id=sup.id, supplier_sku=f"SKU-{tag}", cost=Decimal(cost),
                           qty_available=qty_in_stock, availability_status="ACTIVE"))
    order = Order(marketplace_id=mp.id, marketplace_order_id=f"MO-{tag}", order_total=Decimal(total),
                  marketplace_fees=Decimal(fees), shipping_address={"name": "Pat", "street": "1 Main", "city": "Dallas",
                                                                       "state": "TX", "zip": "75001", "country": "US"},
                  status="PENDING_ROUTING")
    db.add(order)
    db.flush()
    db.add(OrderItem(order_id=order.id, product_id=prod.id if with_product else None, sku=prod.sku, title="Wall Mount",
                     quantity=qty, unit_price=Decimal(total), status="PENDING"))
    db.commit()
    return order


def _run(db, order, live_qty=25, submit_side_effect=None):
    calls = []

    def fake_submit(self, po_id):
        calls.append(po_id)
        if submit_side_effect:
            raise submit_side_effect
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        po.status = "SUBMITTED"
        po.supplier_order_id = "REAL-123"
        db.commit()
        return po

    with patch.object(SyncService, "get_adapter_for_supplier", lambda self, s: FakeAdapter(live_qty)), \
         patch.object(OrderService, "submit_purchase_order_live", fake_submit):
        result = AutoFulfillmentService(db).fulfill_new_order(order.id)
    db.refresh(order)
    return result, calls


def test_disabled_does_nothing(db_session, monkeypatch):
    monkeypatch.setattr(settings, "AUTO_ORDER_ENABLED", False)
    order = _order(db_session, tag="off")
    result, calls = _run(db_session, order)
    assert result == "disabled" and calls == []
    assert order.status == "PENDING_ROUTING" and order.auto_order_status is None


def test_good_order_is_routed_and_placed_automatically(db_session):
    order = _order(db_session, tag="ok")
    result, calls = _run(db_session, order)
    assert result == "COMPLETED" and len(calls) == 1
    assert order.auto_order_status == "COMPLETED"
    assert db_session.query(PurchaseOrder).filter(PurchaseOrder.order_id == order.id).count() == 1
    assert any(e.event_type == "AUTO_ORDER_COMPLETED" for e in order.events)


def test_order_that_would_lose_money_is_held_not_ordered(db_session):
    order = _order(db_session, tag="loss", total="90.00", fees="10.00")  # 80 revenue vs 89 cost
    result, calls = _run(db_session, order)
    assert result == "HELD" and calls == []
    assert "Profit would be" in order.auto_order_note
    assert db_session.query(PurchaseOrder).filter(PurchaseOrder.order_id == order.id).count() == 0


def test_order_over_the_spending_cap_is_held(db_session):
    order = _order(db_session, tag="cap", cost="1200.00", total="2000.00", fees="100.00")
    result, calls = _run(db_session, order)
    assert result == "HELD" and calls == []
    assert "automatic-order limit" in order.auto_order_note


def test_live_stock_too_low_is_held(db_session):
    order = _order(db_session, tag="low", qty=2, total="400.00", fees="20.00")
    result, calls = _run(db_session, order, live_qty=1)
    assert result == "HELD" and calls == []
    assert "live stock" in order.auto_order_note


def test_unverifiable_live_stock_is_held(db_session):
    order = _order(db_session, tag="unk")
    result, calls = _run(db_session, order, live_qty=None)
    assert result == "HELD" and calls == []
    assert "Could not verify" in order.auto_order_note


def test_ma_labs_gets_a_draft_po_for_a_person_and_is_never_submitted(db_session):
    order = _order(db_session, tag="ml", supplier_name="Ma Labs", adapter="MaLabsAdapter")
    result, calls = _run(db_session, order)
    assert result == "MANUAL_NEEDED" and calls == []
    po = db_session.query(PurchaseOrder).filter(PurchaseOrder.order_id == order.id).one()
    assert po.status == "DRAFT"
    assert "manual ordering" in order.auto_order_note


def test_supplier_failure_is_not_retried_and_is_flagged(db_session):
    order = _order(db_session, tag="fail")
    result, calls = _run(db_session, order, submit_side_effect=ConnectionError("timeout"))
    assert result == "FAILED" and len(calls) == 1
    assert "not retried automatically" in order.auto_order_note
    po = db_session.query(PurchaseOrder).filter(PurchaseOrder.order_id == order.id).one()
    assert po.status == "DRAFT"


def test_running_twice_never_orders_twice(db_session):
    order = _order(db_session, tag="twice")
    first, calls1 = _run(db_session, order)
    second, calls2 = _run(db_session, order)
    assert first == "COMPLETED" and second == "skipped"
    assert len(calls1) == 1 and calls2 == []


def test_unroutable_item_holds_the_whole_order(db_session):
    order = _order(db_session, tag="nomatch", with_product=False)
    result, calls = _run(db_session, order)
    assert result == "HELD" and calls == []
    assert "Not every item could be routed" in order.auto_order_note
