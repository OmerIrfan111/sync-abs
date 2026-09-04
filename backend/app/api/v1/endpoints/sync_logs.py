from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.sync_log import SyncLog
from app.models.product import Product
from app.models.supplier import Supplier
from app.schemas.sync import SyncLogResponse, PaginatedSyncLogsResponse

router = APIRouter()

@router.get("", response_model=PaginatedSyncLogsResponse)
def get_sync_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
    field_changed: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(SyncLog)
    if product_id:
        query = query.filter(SyncLog.product_id == product_id)
    if supplier_id:
        query = query.filter(SyncLog.supplier_id == supplier_id)
    if field_changed:
        query = query.filter(SyncLog.field_changed == field_changed)

    total = query.count()
    skip = (page - 1) * page_size
    logs = query.order_by(desc(SyncLog.synced_at)).offset(skip).limit(page_size).all()

    items = []
    for log in logs:
        prod = db.query(Product).filter(Product.id == log.product_id).first() if log.product_id else None
        sup = db.query(Supplier).filter(Supplier.id == log.supplier_id).first() if log.supplier_id else None
        items.append(SyncLogResponse(
            id=log.id,
            product_id=log.product_id,
            product_sku=prod.sku if prod else None,
            supplier_id=log.supplier_id,
            supplier_name=sup.name if sup else None,
            field_changed=log.field_changed,
            old_value=log.old_value,
            new_value=log.new_value,
            synced_at=log.synced_at
        ))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedSyncLogsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
