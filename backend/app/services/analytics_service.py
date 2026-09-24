from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.supplier_product import SupplierProduct
from app.models.error_log import ErrorLog

NON_REVENUE_STATUSES = ["CANCELLED", "REFUNDED"]


class AnalyticsService:
    """
    Phase V2.1: Profitability analytics and supplier performance scoring.

    Net profit is computed as order_total - supplier_cost - marketplace_fees.
    Shipping cost is intentionally excluded: no marketplace or supplier adapter
    in this system currently reports actual shipping cost per order, so adding
    a shipping_cost term would mean fabricating a number rather than reporting one.
    Supplier cost only reflects items that have been routed (OrderItem.supplier_cost
    is null until routing runs), so profit on not-yet-routed orders is an
    underestimate of cost (and therefore an overestimate of profit) until routed.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        current = self._compute_period(since, now)

        # Period-over-period comparison: the immediately preceding window of
        # equal length, so "up 12% vs last period" means something concrete
        # rather than an arbitrary fixed baseline.
        previous_since = since - timedelta(days=days)
        previous = self._compute_period(previous_since, since)

        def pct_change(curr: float, prev: float) -> Optional[float]:
            if prev == 0:
                return None  # undefined — avoid a misleading "+inf%" or fabricated 0%
            return round((curr - prev) / abs(prev) * 100, 2)

        current["comparison"] = {
            "previous_period_days": days,
            "revenue_change_pct": pct_change(current["revenue_total"], previous["revenue_total"]),
            "profit_change_pct": pct_change(current["net_profit_total"], previous["net_profit_total"]),
            "order_count_change_pct": pct_change(current["order_count"], previous["order_count"]),
            "previous_revenue_total": previous["revenue_total"],
            "previous_net_profit_total": previous["net_profit_total"],
            "previous_order_count": previous["order_count"],
        }
        return current

    def _compute_period(self, start: datetime, end: datetime) -> Dict[str, Any]:
        orders = (
            self.db.query(Order)
            .filter(Order.created_at >= start, Order.created_at < end, Order.status.notin_(NON_REVENUE_STATUSES))
            .all()
        )

        revenue_total = Decimal("0")
        cost_total = Decimal("0")
        fees_total = Decimal("0")
        revenue_by_day: Dict[str, Dict[str, Decimal]] = {}
        margin_by_supplier: Dict[int, Dict[str, Any]] = {}
        sku_stats: Dict[str, Dict[str, Any]] = {}
        category_stats: Dict[str, Dict[str, Any]] = {}

        product_categories: Dict[int, str] = {
            p.id: (p.category or "Uncategorized") for p in self.db.query(Product.id, Product.category).all()
        }

        for order in orders:
            order_cost = Decimal("0")
            for item in order.items:
                item_cost = (item.supplier_cost or Decimal("0")) * item.quantity
                order_cost += item_cost

                if item.supplier_id:
                    entry = margin_by_supplier.setdefault(item.supplier_id, {
                        "supplier_id": item.supplier_id,
                        "revenue": Decimal("0"),
                        "cost": Decimal("0"),
                    })
                    entry["revenue"] += item.unit_price * item.quantity
                    entry["cost"] += item_cost

                sku_key = item.sku or f"item-{item.id}"
                sku_entry = sku_stats.setdefault(sku_key, {
                    "sku": sku_key,
                    "title": item.title or sku_key,
                    "units_sold": 0,
                    "revenue": Decimal("0"),
                    "cost": Decimal("0"),
                })
                sku_entry["units_sold"] += item.quantity
                sku_entry["revenue"] += item.unit_price * item.quantity
                sku_entry["cost"] += item_cost

                category = product_categories.get(item.product_id, "Uncategorized") if item.product_id else "Uncategorized"
                cat_entry = category_stats.setdefault(category, {
                    "category": category,
                    "units_sold": 0,
                    "revenue": Decimal("0"),
                    "cost": Decimal("0"),
                })
                cat_entry["units_sold"] += item.quantity
                cat_entry["revenue"] += item.unit_price * item.quantity
                cat_entry["cost"] += item_cost

            revenue_total += order.order_total
            cost_total += order_cost
            fees_total += order.marketplace_fees or Decimal("0")

            day_key = (order.ordered_at or order.created_at).date().isoformat()
            day_entry = revenue_by_day.setdefault(day_key, {"revenue": Decimal("0"), "profit": Decimal("0")})
            day_entry["revenue"] += order.order_total
            day_entry["profit"] += order.order_total - order_cost - (order.marketplace_fees or Decimal("0"))

        net_profit_total = revenue_total - cost_total - fees_total
        gross_margin_pct = float((net_profit_total / revenue_total * 100)) if revenue_total > 0 else 0.0

        revenue_trend = [
            {
                "date": day,
                "revenue": float(vals["revenue"]),
                "profit": float(vals["profit"]),
            }
            for day, vals in sorted(revenue_by_day.items())
        ]

        suppliers_by_id = {s.id: s.name for s in self.db.query(Supplier).all()}
        margin_table = []
        for supplier_id, vals in margin_by_supplier.items():
            revenue = vals["revenue"]
            cost = vals["cost"]
            margin_pct = float((revenue - cost) / revenue * 100) if revenue > 0 else 0.0
            margin_table.append({
                "supplier_id": supplier_id,
                "supplier_name": suppliers_by_id.get(supplier_id, f"Supplier #{supplier_id}"),
                "revenue": float(revenue),
                "cost": float(cost),
                "margin_pct": round(margin_pct, 2),
            })
        margin_table.sort(key=lambda x: x["revenue"], reverse=True)

        top_skus = []
        for vals in sku_stats.values():
            revenue = vals["revenue"]
            cost = vals["cost"]
            profit = revenue - cost
            top_skus.append({
                "sku": vals["sku"],
                "title": vals["title"],
                "units_sold": vals["units_sold"],
                "revenue": float(revenue),
                "profit": float(profit),
            })
        top_skus.sort(key=lambda x: x["revenue"], reverse=True)
        top_skus = top_skus[:10]

        category_table = []
        for vals in category_stats.values():
            revenue = vals["revenue"]
            cost = vals["cost"]
            margin_pct = float((revenue - cost) / revenue * 100) if revenue > 0 else 0.0
            category_table.append({
                "category": vals["category"],
                "units_sold": vals["units_sold"],
                "revenue": float(revenue),
                "profit": float(revenue - cost),
                "margin_pct": round(margin_pct, 2),
            })
        category_table.sort(key=lambda x: x["revenue"], reverse=True)

        period_days = max(1, (end.date() - start.date()).days)

        return {
            "period_days": period_days,
            "revenue_total": float(revenue_total),
            "cost_total": float(cost_total),
            "fees_total": float(fees_total),
            "category_performance": category_table,
            "net_profit_total": float(net_profit_total),
            "gross_margin_pct": round(gross_margin_pct, 2),
            "order_count": len(orders),
            "revenue_trend": revenue_trend,
            "margin_by_supplier": margin_table,
            "top_skus": top_skus,
        }

    def get_supplier_scores(self, days: int = 90) -> List[Dict[str, Any]]:
        """
        Supplier performance scoring based on data this system actually has:
        - avg_fulfillment_days: mean time from PO creation to shipment.
        - cancellation_rate_pct: % of routed order items for that supplier whose
          parent order ended up CANCELLED.
        - po_count: purchase orders placed with that supplier in the window.
        - catalog_missing_data_rate_pct: % of that supplier's current catalog
          rows that were skipped during the last sync for lacking real
          price/quantity data (a genuine proxy for feed reliability, built
          from ErrorLog rows this system actually writes).

        catalog_missing_data_rate_pct is NOT the "inventory accuracy" metric
        named in the V2.1 roadmap (promised-vs-actual stock at fulfillment
        time) — no adapter reports that, so there is no real signal for it.
        This is a different, honestly-labeled proxy: how often the supplier's
        own feed fails to return usable data at all. Reported separately so
        it's never mistaken for the roadmap's original metric.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        suppliers = self.db.query(Supplier).all()
        scores = []

        for supplier in suppliers:
            pos = (
                self.db.query(PurchaseOrder)
                .filter(PurchaseOrder.supplier_id == supplier.id, PurchaseOrder.created_at >= since)
                .all()
            )
            po_count = len(pos)

            shipped_pos = [po for po in pos if po.shipped_at]
            if shipped_pos:
                avg_fulfillment_days = sum(
                    (po.shipped_at - po.created_at).total_seconds() for po in shipped_pos
                ) / len(shipped_pos) / 86400
            else:
                avg_fulfillment_days = None

            routed_items = (
                self.db.query(OrderItem)
                .join(Order, OrderItem.order_id == Order.id)
                .filter(OrderItem.supplier_id == supplier.id, Order.created_at >= since)
                .all()
            )
            total_routed = len(routed_items)
            cancelled_routed = sum(1 for item in routed_items if item.order.status == "CANCELLED")
            cancellation_rate_pct = (cancelled_routed / total_routed * 100) if total_routed > 0 else 0.0

            missing_data_count = (
                self.db.query(ErrorLog)
                .filter(
                    ErrorLog.supplier_id == supplier.id,
                    ErrorLog.error_type == "MISSING_DATA",
                    ErrorLog.created_at >= since,
                )
                .count()
            )
            catalog_size = (
                self.db.query(SupplierProduct)
                .filter(SupplierProduct.supplier_id == supplier.id)
                .count()
            )
            catalog_missing_data_rate_pct = (
                (missing_data_count / catalog_size * 100) if catalog_size > 0 else None
            )

            scores.append({
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
                "po_count": po_count,
                "avg_fulfillment_days": round(avg_fulfillment_days, 2) if avg_fulfillment_days is not None else None,
                "cancellation_rate_pct": round(cancellation_rate_pct, 2),
                "routed_item_count": total_routed,
                "catalog_missing_data_rate_pct": (
                    round(catalog_missing_data_rate_pct, 2) if catalog_missing_data_rate_pct is not None else None
                ),
            })

        scores.sort(key=lambda x: x["po_count"], reverse=True)
        return scores
