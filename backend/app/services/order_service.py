import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.purchase_order import PurchaseOrder
from app.models.order_event import OrderEvent
from app.models.error_log import ErrorLog
from app.models.product import Product
from app.models.listing import Listing
from app.models.marketplace import Marketplace
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.services.supplier_selection_service import SupplierSelectionService
from app.core.security import decrypt_credential
from app.core.config import settings

logger = logging.getLogger(__name__)


class SandboxViolationError(RuntimeError):
    """Raised when a live financial transaction or order is attempted while DRY_RUN is active."""
    pass


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────
    # 1. ORDER INGESTION
    # ──────────────────────────────────────────────

    def ingest_marketplace_orders(self, marketplace_id: int) -> List[Order]:
        """
        Fetches new orders from a marketplace via its adapter and creates
        Order + OrderItem records. Deduplicates by marketplace_order_id.
        """
        marketplace = self.db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
        if not marketplace or not marketplace.is_active:
            return []

        adapter = self._get_adapter(marketplace)

        try:
            raw_orders = adapter.fetch_orders()
        except Exception as exc:
            logger.error(f"Failed to fetch orders from {marketplace.name}: {exc}")
            return []

        created_orders: List[Order] = []

        for raw in raw_orders:
            mkt_order_id = str(raw.get("order_id", ""))
            if not mkt_order_id:
                continue

            # Deduplicate
            existing = self.db.query(Order).filter(
                Order.marketplace_order_id == mkt_order_id
            ).first()
            if existing:
                continue

            order = Order(
                marketplace_id=marketplace.id,
                marketplace_order_id=mkt_order_id,
                buyer_username=raw.get("buyer_username", ""),
                buyer_name=raw.get("buyer_name", ""),
                shipping_address=raw.get("shipping_address", {}),
                order_total=Decimal(str(raw.get("order_total", 0))),
                marketplace_fees=Decimal(str(raw.get("marketplace_fees", 0))),
                currency=raw.get("currency", "USD"),
                status="PENDING_ROUTING",
                ordered_at=raw.get("ordered_at"),
            )
            self.db.add(order)
            self.db.flush()

            # Create line items
            for item_data in raw.get("items", []):
                sku = item_data.get("sku", "")
                title = item_data.get("title", "")
                qty = int(item_data.get("quantity", 1))
                unit_price = Decimal(str(item_data.get("unit_price", 0)))

                # Try to match to internal product/listing
                product = None
                listing = None
                if sku:
                    product = self.db.query(Product).filter(Product.sku == sku).first()
                    if product:
                        listing = self.db.query(Listing).filter(
                            Listing.product_id == product.id,
                            Listing.marketplace_id == marketplace.id,
                            Listing.status == "ACTIVE"
                        ).first()

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id if product else None,
                    listing_id=listing.id if listing else None,
                    marketplace_item_id=item_data.get("item_id", ""),
                    sku=sku,
                    title=title or (product.title if product else "Unknown Item"),
                    quantity=qty,
                    unit_price=unit_price,
                    status="PENDING",
                )
                self.db.add(order_item)

            # Record event
            self._add_event(order.id, "ORDER_RECEIVED", {
                "marketplace": marketplace.name,
                "marketplace_order_id": mkt_order_id,
                "total": str(order.order_total),
                "items_count": len(raw.get("items", [])),
            })

            created_orders.append(order)

        self.db.commit()
        logger.info(f"Ingested {len(created_orders)} new orders from {marketplace.name}")
        return created_orders

    # ──────────────────────────────────────────────
    # 2. ORDER ROUTING
    # ──────────────────────────────────────────────

    def route_order(self, order_id: int) -> Order:
        """
        Routes each item in the order to the best available supplier
        using the existing SupplierSelectionService.
        """
        order = self._get_order(order_id)
        if order.status not in ("PENDING_ROUTING", "ROUTED"):
            raise ValueError(f"Order {order_id} cannot be routed (status: {order.status})")

        selector = SupplierSelectionService(self.db)
        routed_items = 0
        unroutable_items = 0

        for item in order.items:
            if item.status != "PENDING":
                continue

            if not item.product_id:
                item.status = "UNROUTABLE"
                item.routing_note = (
                    f"No catalog match for SKU '{item.sku or 'unknown'}' — this listing "
                    "wasn't published through this system, so there's no supplier on file for it."
                )
                unroutable_items += 1
                continue

            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                item.status = "UNROUTABLE"
                item.routing_note = "Linked product record no longer exists in the catalog."
                unroutable_items += 1
                continue

            banner = "[SANDBOX] " if settings.DRY_RUN else ""
            active_sps = [
                sp for sp in product.supplier_products
                if sp.availability_status == "ACTIVE" and sp.supplier and sp.supplier.is_active
            ]

            # Separate items with stock covering requested quantity vs best available
            candidates_with_stock = [sp for sp in active_sps if sp.qty_available >= item.quantity]
            if not candidates_with_stock:
                candidates_with_stock = [sp for sp in active_sps if sp.qty_available > 0]

            def delivered_cost(sp: SupplierProduct) -> Decimal:
                shipping = sp.base_shipping_charge if sp.base_shipping_charge is not None else Decimal("0.00")
                return sp.cost + Decimal(str(shipping))

            candidates_to_try = sorted(candidates_with_stock, key=delivered_cost)

            chosen_sp = None
            for cand in candidates_to_try:
                # Test connectivity to verify supplier is healthy and responsive
                try:
                    from app.services.sync_service import SyncService
                    adapter = SyncService(self.db).get_adapter_for_supplier(cand.supplier)
                    adapter.test_connection()
                    chosen_sp = cand
                    break
                except Exception as sup_err:
                    logger.warning(
                        f"{banner}Supplier {cand.supplier.name} unavailable for order item {item.id} ({sup_err}). "
                        "Falling back to next available supplier."
                    )
                    continue

            # If all connection tests failed, fallback to the top candidate if available
            if not chosen_sp and candidates_to_try:
                chosen_sp = candidates_to_try[0]

            if chosen_sp:
                item.supplier_id = chosen_sp.supplier_id
                item.supplier_cost = chosen_sp.cost
                item.status = "ROUTED"
                tot_cost = delivered_cost(chosen_sp)
                item.routing_note = (
                    f"{banner}Routed to {chosen_sp.supplier.name} (Delivered Cost: ${tot_cost} "
                    f"[base: ${chosen_sp.cost}, shipping: ${chosen_sp.base_shipping_charge or 0.00}], "
                    f"Stock: {chosen_sp.qty_available})"
                )
                routed_items += 1

                # Real freight cost from Ingram Micro if applicable
                supplier = chosen_sp.supplier
                if supplier and "ingram" in supplier.name.lower():
                    try:
                        from app.services.sync_service import SyncService
                        adapter = SyncService(self.db).get_adapter_for_supplier(supplier)
                        item.shipping_cost = adapter.get_freight_estimate(
                            ship_to_address=order.shipping_address or {},
                            line_items=[{"ingramPartNumber": chosen_sp.supplier_sku, "quantity": item.quantity}],
                        )
                    except Exception as e:
                        logger.warning(f"Freight estimate failed for order item {item.id}: {e}")
                        item.shipping_cost = chosen_sp.base_shipping_charge
                else:
                    item.shipping_cost = chosen_sp.base_shipping_charge
            else:
                item.status = "UNROUTABLE"
                if not active_sps:
                    item.routing_note = f"{banner}No connected supplier on file for this item."
                elif not candidates_with_stock:
                    item.routing_note = f"{banner}All connected suppliers are currently out of stock for this item."
                else:
                    item.routing_note = f"{banner}All candidate suppliers encountered API errors or are unavailable."
                unroutable_items += 1

        if routed_items > 0:
            order.status = "ROUTED"
            self._add_event(order.id, "SUPPLIER_ROUTED", {
                "routed_items": routed_items,
                "total_items": len(order.items),
            })

        if unroutable_items > 0:
            self._add_event(order.id, "ROUTING_INCOMPLETE", {
                "unroutable_items": unroutable_items,
                "total_items": len(order.items),
            })

        self.db.commit()
        return order

    # ──────────────────────────────────────────────
    # 3. PURCHASE ORDER GENERATION
    # ──────────────────────────────────────────────

    def create_purchase_orders(self, order_id: int) -> List[PurchaseOrder]:
        """
        Groups routed items by supplier and creates PurchaseOrder records.
        """
        order = self._get_order(order_id)
        if order.status not in ("ROUTED",):
            raise ValueError(f"Order {order_id} must be routed before creating POs (status: {order.status})")

        # Group items by supplier_id
        supplier_items: Dict[int, List[OrderItem]] = {}
        for item in order.items:
            if item.supplier_id and item.status == "ROUTED":
                supplier_items.setdefault(item.supplier_id, []).append(item)

        if not supplier_items:
            raise ValueError("No routed items found to create purchase orders")

        purchase_orders: List[PurchaseOrder] = []

        for supplier_id, items in supplier_items.items():
            total_cost = sum(
                (item.supplier_cost or Decimal("0")) * item.quantity
                for item in items
            )

            po = PurchaseOrder(
                order_id=order.id,
                supplier_id=supplier_id,
                po_number=self._generate_po_number(),
                status="DRAFT",
                total_cost=total_cost,
                shipping_address=order.shipping_address,
            )
            self.db.add(po)
            self.db.flush()

            # Mark items as ordered
            for item in items:
                item.status = "ORDERED"

            supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
            self._add_event(order.id, "PO_CREATED", {
                "po_number": po.po_number,
                "supplier": supplier.name if supplier else f"Supplier #{supplier_id}",
                "total_cost": str(total_cost),
                "items_count": len(items),
            })

            purchase_orders.append(po)

        order.status = "PO_SUBMITTED"
        self.db.commit()
        logger.info(f"Created {len(purchase_orders)} PO(s) for Order #{order_id}")
        return purchase_orders

    # ──────────────────────────────────────────────
    # 3b. SUPPLIER ORDER SUBMISSION CONFIRMATION
    # ──────────────────────────────────────────────

    def submit_purchase_order(self, po_id: int, supplier_order_id: str) -> PurchaseOrder:
        """
        Records that a DRAFT purchase order has actually been placed with the
        real supplier (D&H, Ingram Micro, etc.) and captures the supplier's
        own order confirmation number. This is a manual, human-confirmed step
        — placing a real order spends real money, so this system does not
        auto-submit purchase orders to suppliers; it records the outcome once
        a person has done so through the supplier's own channel.

        Recording a real supplier_order_id here is also the prerequisite for
        automated shipping confirmation later: any supplier adapter that
        implements check_shipment_status() can be polled using this ID
        instead of requiring a human to manually type in tracking info.
        """
        po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")
        if po.status != "DRAFT":
            raise ValueError(f"Purchase order {po_id} must be DRAFT to submit (status: {po.status})")
        if not supplier_order_id or not supplier_order_id.strip():
            raise ValueError("A real supplier order confirmation number is required")

        po.supplier_order_id = supplier_order_id.strip()
        po.status = "SUBMITTED"
        po.submitted_at = datetime.now(timezone.utc)

        self._add_event(po.order_id, "PO_SUBMITTED_TO_SUPPLIER", {
            "po_number": po.po_number,
            "supplier_order_id": po.supplier_order_id,
        })

        self.db.commit()
        return po

    def submit_purchase_order_live(self, po_id: int) -> PurchaseOrder:
        """
        Actually places a DRAFT purchase order with the real supplier via
        their order-submission API, instead of requiring a human to place it
        manually on the supplier's own website and type the confirmation
        number back in. Implemented for D&H and Ingram Micro — the only two
        suppliers whose real order-submission API spec is wired up here.

        This still requires an explicit, human-triggered call — placing a
        real order spends real money, so this is never invoked from a
        schedule or automatically after routing. The human confirmation is
        the button click that calls this endpoint, not a second manual step
        on the supplier's own site.
        """
        po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")
        if po.status != "DRAFT":
            raise ValueError(f"Purchase order {po_id} must be DRAFT to submit (status: {po.status})")

        supplier = self.db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier {po.supplier_id} not found")

        banner = "[SANDBOX] " if settings.DRY_RUN else ""
        if settings.DRY_RUN:
            if getattr(self, "force_real_money", False):
                raise SandboxViolationError("SANDBOX GUARD: Real money transaction blocked while DRY_RUN is active!")

            logger.info(f"{banner}Dry run active. Simulating purchase order submission for PO #{po.po_number} to {supplier.name}")
            simulated_order_id = f"SANDBOX-{supplier.name[:3].upper()}-{uuid.uuid4().hex[:8].upper()}"
            po.supplier_order_id = simulated_order_id
            po.status = "SUBMITTED"
            po.submitted_at = datetime.now(timezone.utc)
            self._add_event(po.order_id, "PO_SUBMITTED_TO_SUPPLIER", {
                "po_number": po.po_number,
                "supplier_order_id": po.supplier_order_id,
                "method": "sandbox_simulated",
            })
            self.db.commit()
            return po

        name_lower = supplier.name.lower()
        adapter_lower = supplier.adapter_class.lower()
        is_dandh = "d&h" in name_lower or "dandh" in adapter_lower
        is_ingram = "ingram" in name_lower or "ingram" in adapter_lower
        is_synnex = "synnex" in name_lower or "synnex" in adapter_lower
        if not is_dandh and not is_ingram and not is_synnex:
            raise ValueError(
                f"Live order submission is only implemented for D&H, Ingram Micro, and TD SYNNEX right now, not {supplier.name}. "
                "Use the manual 'Mark as Submitted' flow for this supplier."
            )

        order = self._get_order(po.order_id)
        items = [item for item in order.items if item.supplier_id == po.supplier_id and item.status == "ROUTED"]
        if not items:
            raise ValueError(f"No routed items for supplier {supplier.name} on order {order.id}")

        line_items = []
        for item in items:
            sp = (
                self.db.query(SupplierProduct)
                .filter(SupplierProduct.product_id == item.product_id, SupplierProduct.supplier_id == po.supplier_id)
                .first()
            )
            if not sp:
                raise ValueError(
                    f"No {supplier.name} catalog entry found for order item {item.id} (product {item.product_id}); "
                    "cannot determine the real supplier item ID to order."
                )
            line_items.append({"itemId": sp.supplier_sku, "orderQuantity": item.quantity})

        addr = order.shipping_address or {}
        delivery_address = {
            "country": addr.get("country", "US"),
            "city": addr.get("city", ""),
            "street": addr.get("street", ""),
            "postalCode": addr.get("zip", addr.get("postalCode", "")),
            "region": addr.get("state", addr.get("region", "")),
            "attention": addr.get("name", ""),
            "deliveryName": addr.get("name", ""),
        }

        from app.services.sync_service import SyncService
        adapter = SyncService(self.db).get_adapter_for_supplier(supplier)

        result = adapter.submit_order(
            customer_purchase_order=po.po_number,
            line_items=line_items,
            delivery_address=delivery_address,
        )

        po.supplier_order_id = str(result.get("id") or result.get("orderNumber") or "")
        po.status = "SUBMITTED"
        po.submitted_at = datetime.now(timezone.utc)

        self._add_event(po.order_id, "PO_SUBMITTED_TO_SUPPLIER", {
            "po_number": po.po_number,
            "supplier_order_id": po.supplier_order_id,
            "method": "live_api",
        })

        self.db.commit()
        return po

    # ──────────────────────────────────────────────
    # 4. TRACKING & SHIPMENT
    # ──────────────────────────────────────────────

    def poll_supplier_tracking(self) -> int:
        """
        Polls each real-supplier PO that's been submitted but has no tracking
        number yet, via the adapter's check_shipment_status(), and records
        any real tracking info found. Without this, a supplier's order
        confirmation number (from submit_purchase_order_live) would sit on
        the PO forever with nothing ever checking whether it shipped — this
        is what actually closes that loop automatically.

        Suppliers without a meaningful check_shipment_status() (the base
        class default returns None) are skipped harmlessly. Returns the
        number of POs that got a real tracking number this run.
        """
        from app.services.sync_service import SyncService

        pending_pos = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.status.in_(["SUBMITTED", "CONFIRMED"]),
            PurchaseOrder.supplier_order_id.isnot(None),
            PurchaseOrder.tracking_number.is_(None),
        ).all()

        sync_service = SyncService(self.db)
        found_pos: List[PurchaseOrder] = []

        for po in pending_pos:
            supplier = self.db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
            if not supplier:
                continue
            try:
                adapter = sync_service.get_adapter_for_supplier(supplier)
                status = adapter.check_shipment_status(po.supplier_order_id)
            except Exception as exc:
                logger.warning(f"Tracking poll failed for PO {po.po_number}: {exc}")
                continue

            if not status or not status.get("tracking_number"):
                continue

            po.tracking_number = status["tracking_number"]
            po.carrier = status.get("carrier") or ""
            po.status = "SHIPPED"
            shipped_at_raw = status.get("shipped_at")
            parsed_shipped_at = None
            if shipped_at_raw:
                try:
                    parsed_shipped_at = datetime.fromisoformat(str(shipped_at_raw).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    parsed_shipped_at = None
            po.shipped_at = parsed_shipped_at or datetime.now(timezone.utc)

            self._add_event(po.order_id, "TRACKING_FOUND", {
                "po_number": po.po_number,
                "tracking_number": po.tracking_number,
                "carrier": po.carrier,
                "method": "supplier_api_poll",
            })
            found_pos.append(po)

        self.db.commit()

        for po in found_pos:
            try:
                self.update_tracking(po.order_id, po.tracking_number, po.carrier)
            except Exception as exc:
                logger.error(f"Failed to push newly-found tracking for PO {po.po_number}: {exc}")

        return len(found_pos)

    def poll_supplier_delivery(self) -> int:
        """
        Polls each shipped-but-not-yet-delivered PO for real delivery
        confirmation via the adapter's check_shipment_status(). Without this,
        an order sits at SHIPPED forever — there was previously no path to
        DELIVERED/COMPLETED at all (mark_delivered()/complete_order() existed
        as methods but nothing ever called them).

        Only Ingram Micro's check_shipment_status() currently returns a real
        delivered_at (confirmed field: carrierDetails.deliveredDate in Get
        Order Details v7); D&H's tracking endpoint has no documented
        delivery-confirmation field, so D&H POs are left for manual
        "Mark Delivered" instead of being auto-detected — never guessed.

        When every PO on an order is DELIVERED, the order itself is marked
        DELIVERED too. complete_order() (a further, often business-decision-
        gated step, e.g. after a return window) is intentionally NOT
        auto-triggered here — that stays a manual action.

        Returns the number of POs marked delivered this run.
        """
        from app.services.sync_service import SyncService

        shipped_pos = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.status == "SHIPPED",
            PurchaseOrder.supplier_order_id.isnot(None),
        ).all()

        sync_service = SyncService(self.db)
        delivered_order_ids: set = set()
        delivered_count = 0

        for po in shipped_pos:
            supplier = self.db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
            if not supplier:
                continue
            try:
                adapter = sync_service.get_adapter_for_supplier(supplier)
                status = adapter.check_shipment_status(po.supplier_order_id)
            except Exception as exc:
                logger.warning(f"Delivery poll failed for PO {po.po_number}: {exc}")
                continue

            delivered_at_raw = (status or {}).get("delivered_at")
            if not delivered_at_raw:
                continue

            po.status = "DELIVERED"
            self._add_event(po.order_id, "PO_DELIVERED", {
                "po_number": po.po_number,
                "method": "supplier_api_poll",
            })
            delivered_count += 1
            delivered_order_ids.add(po.order_id)

        self.db.commit()

        for order_id in delivered_order_ids:
            order = self._get_order(order_id)
            if order.purchase_orders and all(po.status == "DELIVERED" for po in order.purchase_orders):
                try:
                    self.mark_delivered(order_id)
                except Exception as exc:
                    logger.error(f"Failed to mark order {order_id} delivered: {exc}")

        return delivered_count

    def update_tracking(
        self,
        order_id: int,
        tracking_number: str,
        carrier: Optional[str] = None
    ) -> Order:
        """
        Updates tracking info on the order's PO(s) and pushes tracking
        to the marketplace via the adapter.
        """
        order = self._get_order(order_id)

        # Update all POs with tracking
        for po in order.purchase_orders:
            if po.status in ("DRAFT", "SUBMITTED", "CONFIRMED"):
                po.tracking_number = tracking_number
                po.carrier = carrier or ""
                po.status = "SHIPPED"
                po.shipped_at = datetime.now(timezone.utc)

        order.status = "SHIPPED"
        order.shipped_at = datetime.now(timezone.utc)

        # Push tracking to marketplace
        if order.marketplace_id:
            marketplace = self.db.query(Marketplace).filter(
                Marketplace.id == order.marketplace_id
            ).first()
            if marketplace:
                try:
                    adapter = self._get_adapter(marketplace)
                    adapter.update_tracking(
                        order.marketplace_order_id,
                        tracking_number,
                        carrier or ""
                    )
                    logger.info(f"Pushed tracking {tracking_number} to {marketplace.name} for order {order.marketplace_order_id}")
                except Exception as exc:
                    logger.error(f"Failed to push tracking to {marketplace.name}: {exc}")

        self._add_event(order.id, "TRACKING_UPDATED", {
            "tracking_number": tracking_number,
            "carrier": carrier or "",
        })

        self.db.commit()
        return order

    def mark_delivered(self, order_id: int) -> Order:
        """Marks order as delivered."""
        order = self._get_order(order_id)
        order.status = "DELIVERED"
        order.delivered_at = datetime.now(timezone.utc)

        for po in order.purchase_orders:
            if po.status == "SHIPPED":
                po.status = "DELIVERED"

        self._add_event(order.id, "DELIVERED", {})
        self.db.commit()
        return order

    def complete_order(self, order_id: int) -> Order:
        """Marks order as completed (post-delivery)."""
        order = self._get_order(order_id)
        order.status = "COMPLETED"
        self._add_event(order.id, "COMPLETED", {})
        self.db.commit()
        return order

    # ──────────────────────────────────────────────
    # 5. CANCELLATION
    # ──────────────────────────────────────────────

    def cancel_order(self, order_id: int, reason: str = "") -> Order:
        """
        Cancels an order and its associated POs. Marking a PO CANCELLED here
        only reflects our own database — if it was already submitted to (or
        shipped by) a real supplier, that real order is still in flight and
        this system has no way to cancel it automatically. Staff must be
        told explicitly, not left assuming the flip of a status handled it.
        """
        order = self._get_order(order_id)
        if order.status in ("DELIVERED", "COMPLETED"):
            raise ValueError(f"Cannot cancel a {order.status} order")

        order.status = "CANCELLED"

        for po in order.purchase_orders:
            if po.status in ("SUBMITTED", "CONFIRMED", "SHIPPED"):
                self.db.add(ErrorLog(
                    error_type="INVENTORY_MISMATCH",
                    supplier_id=po.supplier_id,
                    message=(
                        f"Order #{order.id} was cancelled, but PO {po.po_number} "
                        f"(confirmation #{po.supplier_order_id or 'unknown'}) was already "
                        f"{po.status.lower()} with the real supplier. This system cannot cancel "
                        f"a real supplier order automatically — contact the supplier directly."
                    ),
                    status="PENDING",
                ))
            if po.status not in ("DELIVERED",):
                po.status = "CANCELLED"

        for item in order.items:
            item.status = "PENDING"

        self._add_event(order.id, "CANCELLED", {"reason": reason})
        self.db.commit()
        return order

    # ──────────────────────────────────────────────
    # 6. STATISTICS
    # ──────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Returns aggregate order statistics for the dashboard."""
        total = self.db.query(func.count(Order.id)).scalar() or 0
        pending = self.db.query(func.count(Order.id)).filter(Order.status == "PENDING_ROUTING").scalar() or 0
        awaiting = self.db.query(func.count(Order.id)).filter(
            Order.status.in_(["ROUTED", "PO_SUBMITTED"])
        ).scalar() or 0
        shipped = self.db.query(func.count(Order.id)).filter(Order.status == "SHIPPED").scalar() or 0
        delivered = self.db.query(func.count(Order.id)).filter(
            Order.status.in_(["DELIVERED", "COMPLETED"])
        ).scalar() or 0
        cancelled = self.db.query(func.count(Order.id)).filter(Order.status == "CANCELLED").scalar() or 0

        # Revenue last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        revenue_30d = self.db.query(func.sum(Order.order_total)).filter(
            Order.ordered_at >= thirty_days_ago,
            Order.status.notin_(["CANCELLED", "REFUNDED"])
        ).scalar() or Decimal("0")

        # Today's orders
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.query(func.count(Order.id)).filter(
            Order.created_at >= today_start
        ).scalar() or 0

        # Average order value
        avg_val = Decimal("0")
        if total > 0:
            total_revenue = self.db.query(func.sum(Order.order_total)).filter(
                Order.status.notin_(["CANCELLED", "REFUNDED"])
            ).scalar() or Decimal("0")
            non_cancelled = self.db.query(func.count(Order.id)).filter(
                Order.status.notin_(["CANCELLED", "REFUNDED"])
            ).scalar() or 1
            avg_val = (Decimal(str(total_revenue)) / non_cancelled).quantize(Decimal("0.01"))

        return {
            "total_orders": total,
            "pending_routing": pending,
            "awaiting_shipment": awaiting,
            "shipped": shipped,
            "delivered": delivered,
            "cancelled": cancelled,
            "revenue_30d": revenue_30d,
            "orders_today": today_count,
            "avg_order_value": avg_val,
        }

    # ──────────────────────────────────────────────
    # INTERNAL HELPERS
    # ──────────────────────────────────────────────

    def _get_order(self, order_id: int) -> Order:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        return order

    def _get_adapter(self, marketplace: Marketplace):
        import json
        credentials = {}
        if marketplace.credentials_encrypted:
            try:
                credentials = json.loads(decrypt_credential(marketplace.credentials_encrypted))
            except Exception:
                pass
        from app.adapters.registry import get_marketplace_adapter
        return get_marketplace_adapter(marketplace.adapter_class, credentials=credentials)

    def _add_event(self, order_id: int, event_type: str, details: Dict[str, Any]):
        event = OrderEvent(
            order_id=order_id,
            event_type=event_type,
            details=details,
        )
        self.db.add(event)

    @staticmethod
    def _generate_po_number() -> str:
        """Generates a unique PO number like PO-20260922-A1B2C3."""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"PO-{date_part}-{unique_part}"
