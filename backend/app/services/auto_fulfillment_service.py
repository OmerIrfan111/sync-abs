import logging
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.app_settings_service import get_auto_order_config
from app.models.order import Order
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)

ZERO = Decimal("0")


class AutoFulfillmentService:
    """
    Hands-free fulfillment of a NEW marketplace order: route it, create the
    purchase order(s), and place them with D&H / Ingram Micro / TD SYNNEX.
    It spends real money, so every order must clear these checks first, and
    any order that doesn't is HELD for a person and never ordered:

      - every item routes to a supplier with stock
      - supplier cost + shipping is within AUTO_ORDER_MAX_ORDER_VALUE
      - revenue - marketplace fees - cost >= AUTO_ORDER_MIN_PROFIT
      - the supplier's LIVE stock (not the last sync) covers the quantity

    Safeguards against ordering twice: the order is claimed with one atomic
    update before anything happens, so a repeated or concurrent run skips it;
    only orders created by the current ingestion run are ever processed (never
    old ones); and a failed supplier submission is NEVER retried automatically,
    because a timeout can mean the supplier did accept it.
    Suppliers with no order API (Ma Labs) get a draft purchase order and the
    order is flagged MANUAL_NEEDED.
    """

    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderService(db)

    def fulfill_new_order(self, order_id: int) -> str:
        config = get_auto_order_config(self.db)
        if not config.enabled:
            return "disabled"

        claimed = (
            self.db.query(Order)
            .filter(Order.id == order_id, Order.auto_order_status.is_(None), Order.status == "PENDING_ROUTING")
            .update({"auto_order_status": "PROCESSING"}, synchronize_session=False)
        )
        self.db.commit()
        if not claimed:
            return "skipped"

        try:
            return self._run(order_id, config)
        except Exception as exc:
            logger.exception(f"Automatic fulfillment crashed for order {order_id}")
            self.db.rollback()
            return self._finish(
                order_id, "FAILED",
                f"Unexpected error; nothing further was ordered automatically: {exc}",
            )

    def _run(self, order_id: int, config) -> str:
        order = self.orders.route_order(order_id)
        items = list(order.items)

        unrouted = [i for i in items if i.status != "ROUTED"]
        if unrouted:
            reasons = "; ".join(sorted({i.routing_note or f"item {i.id} was not routed" for i in unrouted}))
            return self._finish(order_id, "HELD", f"Not every item could be routed: {reasons}")

        if any(i.supplier_cost is None for i in items):
            return self._finish(order_id, "HELD", "A routed item has no supplier cost on file.")

        cost = sum(
            ((i.supplier_cost or ZERO) * i.quantity) + (i.shipping_cost or ZERO) for i in items
        )
        if cost > config.max_order_value:
            return self._finish(
                order_id, "HELD",
                f"Supplier cost ${cost:.2f} is over the ${config.max_order_value:.2f} automatic-order limit.",
            )

        revenue = (order.order_total or ZERO) - (order.marketplace_fees or ZERO)
        profit = revenue - cost
        if profit < config.min_profit:
            return self._finish(
                order_id, "HELD",
                f"Profit would be ${profit:.2f} (revenue ${revenue:.2f} - supplier cost and shipping ${cost:.2f}), "
                f"below the ${config.min_profit:.2f} minimum.",
            )

        for item in items:
            problem = self._stock_problem(item)
            if problem:
                return self._finish(order_id, "HELD", problem)

        pos = [(p.id, p.po_number, p.supplier_id) for p in self.orders.create_purchase_orders(order_id)]

        submitted: List[str] = []
        manual: List[str] = []
        failed: List[str] = []
        for po_id, po_number, supplier_id in pos:
            supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
            if not supplier or not OrderService.supports_live_submission(supplier):
                manual.append(f"{po_number} ({supplier.name if supplier else 'unknown supplier'})")
                continue
            try:
                self.orders.submit_purchase_order_live(po_id)
                submitted.append(po_number)
            except Exception as exc:
                if isinstance(exc, SQLAlchemyError):
                    self.db.rollback()  # only a broken DB session needs this; a supplier error leaves it clean
                failed.append(f"{po_number}: {exc}")

        parts = []
        if submitted:
            parts.append("Placed with suppliers: " + ", ".join(submitted) + ".")
        if manual:
            parts.append("Needs manual ordering (no supplier order API): " + ", ".join(manual) + ".")
        if failed:
            parts.append(
                "FAILED, not retried automatically; check with the supplier before ordering again: "
                + " | ".join(failed)
            )
        status = "FAILED" if failed else ("MANUAL_NEEDED" if manual else "COMPLETED")
        return self._finish(order_id, status, " ".join(parts))

    def _stock_problem(self, item) -> Optional[str]:
        supplier = self.db.query(Supplier).filter(Supplier.id == item.supplier_id).first()
        sp = (
            self.db.query(SupplierProduct)
            .filter(SupplierProduct.product_id == item.product_id, SupplierProduct.supplier_id == item.supplier_id)
            .first()
        )
        if not supplier or not sp:
            return f"No supplier listing found for '{item.title}'."
        if sp.qty_available < item.quantity:
            return (
                f"{supplier.name} shows only {sp.qty_available} of '{item.title}' "
                f"(order needs {item.quantity})."
            )
        if not OrderService.supports_live_submission(supplier):
            return None  # will be a draft PO for a person; no live check possible

        from app.services.sync_service import SyncService
        try:
            adapter = SyncService(self.db).get_adapter_for_supplier(supplier)
            live_qty = adapter.fetch_inventory([sp.supplier_sku]).get(str(sp.supplier_sku))
        except Exception as exc:
            return f"Could not verify {supplier.name}'s live stock for '{item.title}' ({exc})."
        if live_qty is None:
            return f"Could not verify {supplier.name}'s live stock for '{item.title}'."
        if int(live_qty) < item.quantity:
            return f"{supplier.name} live stock is {int(live_qty)} for '{item.title}' (order needs {item.quantity})."
        return None

    def _finish(self, order_id: int, status: str, note: str) -> str:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.auto_order_status = status
            order.auto_order_note = note
            self.orders._add_event(order_id, f"AUTO_ORDER_{status}", {"note": note})
            self.db.commit()
        logger.info(f"Automatic fulfillment for order {order_id}: {status}. {note}")
        return status
