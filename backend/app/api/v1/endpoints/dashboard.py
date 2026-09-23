from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
from app.core.database import get_db
from app.models.product import Product
from app.models.supplier_product import SupplierProduct
from app.models.supplier import Supplier
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.models.error_log import ErrorLog
from app.models.order import Order
from app.schemas.dashboard import DashboardStats, SupplierHealthStatus, MarketplaceHealthStatus
from app.schemas.sync import ErrorLogResponse

router = APIRouter()

@router.get("/summary", response_model=DashboardStats)
def get_dashboard_summary(db: Session = Depends(get_db)):
    # 1. Total products
    total_products = db.query(Product).count()

    # 2. Active listings
    active_listings = db.query(Listing).filter(Listing.status == "ACTIVE").count()

    # 3. In stock / out of stock
    # Products with at least one supplier having qty > 0
    in_stock_stmt = (
        select(SupplierProduct.product_id)
        .filter(SupplierProduct.qty_available > 0)
        .distinct()
    )
    in_stock_products = db.query(Product).filter(Product.id.in_(in_stock_stmt)).count()
    out_of_stock_products = max(0, total_products - in_stock_products)

    # 4. Needs attention: pending/failed errors from the last 24h
    # Older unresolved rows reflect past incidents that may have self-recovered
    # on a later sync and shouldn't perpetually flag the dashboard as unhealthy.
    health_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    unresolved_errors = db.query(ErrorLog).filter(
        ErrorLog.status.in_(["PENDING", "FAILED"]),
        ErrorLog.created_at >= health_cutoff,
    ).count()
    needs_attention = unresolved_errors

    # 4b. Order KPIs
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_orders_today = db.query(func.count(Order.id)).filter(Order.created_at >= today_start).scalar() or 0
    pending_orders = db.query(func.count(Order.id)).filter(Order.status == "PENDING_ROUTING").scalar() or 0
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    revenue_30d = db.query(func.sum(Order.order_total)).filter(
        Order.ordered_at >= thirty_days_ago,
        Order.status.notin_(["CANCELLED", "REFUNDED"])
    ).scalar() or Decimal("0")

    # 5. Suppliers health
    # Only a genuine connection failure marks the supplier itself unhealthy.
    # MISSING_DATA / PRICING_ERROR / INVENTORY_MISMATCH are data-quality
    # issues about specific SKUs, not evidence the supplier connection is
    # broken — they still count toward needs_attention above, but shouldn't
    # make a supplier that's actively syncing hundreds of products look
    # "ERROR" and cause alarm fatigue.
    suppliers = db.query(Supplier).all()
    suppliers_health = []
    for s in suppliers:
        p_count = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == s.id).count()
        latest_err = db.query(ErrorLog).filter(
            ErrorLog.supplier_id == s.id,
            ErrorLog.error_type == "SUPPLIER_CONNECTION_ERROR",
            ErrorLog.status.in_(["PENDING", "FAILED"]),
            ErrorLog.created_at >= health_cutoff,
        ).order_by(desc(ErrorLog.created_at)).first()
        # A transient failure earlier in the window shouldn't keep flagging
        # the supplier as broken once a later sync has actually succeeded —
        # only treat it as unhealthy if no successful sync has happened since.
        is_broken = latest_err is not None and (
            s.last_synced_at is None or latest_err.created_at > s.last_synced_at
        )
        status_str = "ERROR" if is_broken else ("HEALTHY" if s.is_active else "IDLE")
        suppliers_health.append(SupplierHealthStatus(
            id=s.id,
            name=s.name,
            is_active=s.is_active,
            status=status_str,
            last_synced_at=s.last_synced_at,
            product_count=p_count
        ))

    # 6. Marketplaces health
    marketplaces = db.query(Marketplace).all()
    marketplaces_health = []
    credential_warnings: List[str] = []
    for m in marketplaces:
        l_count = db.query(Listing).filter(Listing.marketplace_id == m.id).count()
        latest_err = db.query(ErrorLog).filter(
            ErrorLog.marketplace_id == m.id,
            ErrorLog.error_type.in_(["MARKETPLACE_CONNECTION_ERROR", "LISTING_ERROR"]),
            ErrorLog.status.in_(["PENDING", "FAILED"]),
            ErrorLog.created_at >= health_cutoff,
        ).order_by(desc(ErrorLog.created_at)).first()
        # Same self-healing logic as suppliers: a later successful listing
        # sync clears an earlier transient connection error.
        last_activity = db.query(func.max(Listing.last_updated_at)).filter(
            Listing.marketplace_id == m.id
        ).scalar()
        is_broken = latest_err is not None and (
            last_activity is None or latest_err.created_at > last_activity
        )
        status_str = "ERROR" if is_broken else ("HEALTHY" if m.is_active else "IDLE")

        days_left = None
        if m.credentials_expires_at:
            days_left = (m.credentials_expires_at - datetime.now(timezone.utc).replace(tzinfo=None)).days
            if days_left <= 0:
                credential_warnings.append(f"{m.name} credentials have EXPIRED — reauthorize immediately to restore sync.")
                status_str = "ERROR"
            elif days_left <= 30:
                credential_warnings.append(f"{m.name} credentials expire in {days_left} day(s) — reauthorize soon to avoid a sync outage.")

        marketplaces_health.append(MarketplaceHealthStatus(
            id=m.id,
            name=m.name,
            is_active=m.is_active,
            status=status_str,
            listing_count=l_count,
            credentials_expires_at=m.credentials_expires_at,
            days_until_credentials_expire=days_left,
        ))

    # 7. Recent errors
    recent_errors_raw = db.query(ErrorLog).order_by(desc(ErrorLog.created_at)).limit(5).all()
    recent_errors = []
    for log in recent_errors_raw:
        prod = db.query(Product).filter(Product.id == log.product_id).first() if log.product_id else None
        sup = db.query(Supplier).filter(Supplier.id == log.supplier_id).first() if log.supplier_id else None
        mkt = db.query(Marketplace).filter(Marketplace.id == log.marketplace_id).first() if log.marketplace_id else None
        recent_errors.append(ErrorLogResponse(
            id=log.id,
            error_type=log.error_type,
            product_id=log.product_id,
            product_sku=prod.sku if prod else None,
            marketplace_id=log.marketplace_id,
            marketplace_name=mkt.name if mkt else None,
            supplier_id=log.supplier_id,
            supplier_name=sup.name if sup else None,
            message=log.message,
            retry_count=log.retry_count,
            status=log.status,
            resolved_at=log.resolved_at,
            created_at=log.created_at
        ))

    return DashboardStats(
        total_products=total_products,
        active_listings=active_listings,
        in_stock_products=in_stock_products,
        out_of_stock_products=out_of_stock_products,
        needs_attention=needs_attention,
        total_orders_today=total_orders_today,
        pending_orders=pending_orders,
        revenue_30d=revenue_30d,
        suppliers_health=suppliers_health,
        marketplaces_health=marketplaces_health,
        recent_errors=recent_errors,
        credential_warnings=credential_warnings
    )

@router.post("/reconcile-all")
def reconcile_all_suppliers(db: Session = Depends(get_db)):
    """
    Trigger system-wide catalog reconciliation across all active suppliers.
    (Spec Section 20 & 24)
    """
    from app.services.sync_service import SyncService
    sync_service = SyncService(db)
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
    results = []
    for s in suppliers:
        try:
            res = sync_service.sync_supplier(s.id)
            results.append({
                "supplier_id": s.id,
                "supplier_name": s.name,
                "status": "SUCCESS",
                "imported": res.get("products_imported", 0),
                "changed": res.get("changes_detected", 0)
            })
        except Exception as exc:
            results.append({
                "supplier_id": s.id,
                "supplier_name": s.name,
                "status": "ERROR",
                "error": str(exc)
            })

    return {
        "reconciled_suppliers": len(suppliers),
        "details": results,
        "message": "System-wide reconciliation completed successfully."
    }

