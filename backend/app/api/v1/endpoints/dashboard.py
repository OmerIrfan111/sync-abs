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

    # 4. Needs attention: pending errors or inactive products
    pending_errors = db.query(ErrorLog).filter(ErrorLog.status == "PENDING").count()
    needs_attention = pending_errors

    # 5. Suppliers health
    suppliers = db.query(Supplier).all()
    suppliers_health = []
    for s in suppliers:
        p_count = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == s.id).count()
        recent_err = db.query(ErrorLog).filter(
            ErrorLog.supplier_id == s.id,
            ErrorLog.status == "PENDING"
        ).first()
        status_str = "ERROR" if recent_err else ("HEALTHY" if s.is_active else "IDLE")
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
    for m in marketplaces:
        l_count = db.query(Listing).filter(Listing.marketplace_id == m.id).count()
        recent_err = db.query(ErrorLog).filter(
            ErrorLog.marketplace_id == m.id,
            ErrorLog.status == "PENDING"
        ).first()
        status_str = "ERROR" if recent_err else ("HEALTHY" if m.is_active else "IDLE")
        marketplaces_health.append(MarketplaceHealthStatus(
            id=m.id,
            name=m.name,
            is_active=m.is_active,
            status=status_str,
            listing_count=l_count
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
        suppliers_health=suppliers_health,
        marketplaces_health=marketplaces_health,
        recent_errors=recent_errors
    )
