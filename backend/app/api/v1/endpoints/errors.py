from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.error_log import ErrorLog
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.marketplace import Marketplace
from app.schemas.sync import ErrorLogResponse, PaginatedErrorLogsResponse

router = APIRouter()

@router.get("", response_model=PaginatedErrorLogsResponse)
def get_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    error_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    marketplace_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ErrorLog)
    if error_type:
        query = query.filter(ErrorLog.error_type == error_type)
    if status:
        query = query.filter(ErrorLog.status == status)
    if supplier_id:
        query = query.filter(ErrorLog.supplier_id == supplier_id)
    if marketplace_id:
        query = query.filter(ErrorLog.marketplace_id == marketplace_id)

    total = query.count()
    skip = (page - 1) * page_size
    logs = query.order_by(desc(ErrorLog.created_at)).offset(skip).limit(page_size).all()

    items = []
    for log in logs:
        prod = db.query(Product).filter(Product.id == log.product_id).first() if log.product_id else None
        sup = db.query(Supplier).filter(Supplier.id == log.supplier_id).first() if log.supplier_id else None
        mkt = db.query(Marketplace).filter(Marketplace.id == log.marketplace_id).first() if log.marketplace_id else None

        items.append(ErrorLogResponse(
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

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedErrorLogsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.post("/{error_id}/resolve", response_model=ErrorLogResponse)
def resolve_error(error_id: int, db: Session = Depends(get_db)):
    error = db.query(ErrorLog).filter(ErrorLog.id == error_id).first()
    if not error:
        raise HTTPException(status_code=404, detail="Error log not found")

    error.status = "RESOLVED"
    error.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(error)

    prod = db.query(Product).filter(Product.id == error.product_id).first() if error.product_id else None
    sup = db.query(Supplier).filter(Supplier.id == error.supplier_id).first() if error.supplier_id else None
    mkt = db.query(Marketplace).filter(Marketplace.id == error.marketplace_id).first() if error.marketplace_id else None

    return ErrorLogResponse(
        id=error.id,
        error_type=error.error_type,
        product_id=error.product_id,
        product_sku=prod.sku if prod else None,
        marketplace_id=error.marketplace_id,
        marketplace_name=mkt.name if mkt else None,
        supplier_id=error.supplier_id,
        supplier_name=sup.name if sup else None,
        message=error.message,
        retry_count=error.retry_count,
        status=error.status,
        resolved_at=error.resolved_at,
        created_at=error.created_at
    )
