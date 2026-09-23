from decimal import Decimal

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.marketplace import Marketplace
from app.services.order_service import OrderService
from app.services.analytics_service import AnalyticsService


def _setup_catalog(db_session):
    product = Product(sku="ING-LOGI-MXKEYS", title="Logitech MX Keys")
    db_session.add(product)
    supplier = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(supplier)
    marketplace = Marketplace(name="eBay Analytics Test", adapter_class="MockEBayAdapter", is_active=True)
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


def test_summary_before_routing_shows_zero_cost(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    order_service = OrderService(db_session)
    order_service.ingest_marketplace_orders(marketplace.id)

    analytics = AnalyticsService(db_session)
    summary = analytics.get_summary(days=30)

    assert summary["order_count"] == 1
    assert summary["cost_total"] == 0.0
    assert summary["revenue_total"] > 0
    # Unrouted items have no supplier_cost yet, so margin_by_supplier stays empty
    assert summary["margin_by_supplier"] == []


def test_summary_after_routing_computes_real_margin(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    order_service = OrderService(db_session)
    order = order_service.ingest_marketplace_orders(marketplace.id)[0]
    order_service.route_order(order.id)

    analytics = AnalyticsService(db_session)
    summary = analytics.get_summary(days=30)

    assert summary["cost_total"] == 89.0
    assert len(summary["margin_by_supplier"]) == 1
    assert summary["margin_by_supplier"][0]["supplier_id"] == supplier.id
    assert len(summary["top_skus"]) == 1
    assert summary["top_skus"][0]["sku"] == "ING-LOGI-MXKEYS"

    net_profit = summary["revenue_total"] - summary["cost_total"] - summary["fees_total"]
    assert abs(summary["net_profit_total"] - net_profit) < 0.01


def test_supplier_scores_reflect_fulfillment_and_cancellations(db_session):
    product, supplier, marketplace = _setup_catalog(db_session)
    order_service = OrderService(db_session)
    order = order_service.ingest_marketplace_orders(marketplace.id)[0]
    order_service.route_order(order.id)
    order_service.create_purchase_orders(order.id)
    order_service.update_tracking(order.id, "1Z999AA10123456784", "UPS")

    analytics = AnalyticsService(db_session)
    scores = analytics.get_supplier_scores(days=90)

    supplier_score = next(s for s in scores if s["supplier_id"] == supplier.id)
    assert supplier_score["po_count"] == 1
    assert supplier_score["avg_fulfillment_days"] is not None
    assert supplier_score["avg_fulfillment_days"] >= 0
    assert supplier_score["cancellation_rate_pct"] == 0.0
    assert supplier_score["routed_item_count"] == 1
