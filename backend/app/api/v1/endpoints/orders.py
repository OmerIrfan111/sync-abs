import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.database import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.purchase_order import PurchaseOrder
from app.models.order_event import OrderEvent
from app.models.marketplace import Marketplace
from app.services.order_service import OrderService
from app.schemas.order import (
    OrderResponse,
    OrderDetailResponse,
    OrderItemResponse,
    PurchaseOrderResponse,
    OrderEventResponse,
    OrderStatsResponse,
    TrackingUpdate,
    PurchaseOrderSubmit,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _order_to_response(order: Order) -> OrderResponse:
    """Converts an Order model to an OrderResponse schema."""
    return OrderResponse(
        id=order.id,
        marketplace_id=order.marketplace_id,
        marketplace_name=order.marketplace.name if order.marketplace else None,
        marketplace_order_id=order.marketplace_order_id,
        buyer_username=order.buyer_username,
        buyer_name=order.buyer_name,
        shipping_address=order.shipping_address or {},
        order_total=order.order_total,
        marketplace_fees=order.marketplace_fees,
        currency=order.currency,
        status=order.status,
        ordered_at=order.ordered_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        notes=order.notes,
        items_count=len(order.items) if order.items else 0,
        created_at=order.created_at,
    )


def _order_to_detail(order: Order) -> OrderDetailResponse:
    """Converts an Order model to a full detail response including items, POs, events."""
    items = []
    for item in (order.items or []):
        items.append(OrderItemResponse(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            listing_id=item.listing_id,
            marketplace_item_id=item.marketplace_item_id,
            sku=item.sku,
            title=item.title,
            quantity=item.quantity,
            unit_price=item.unit_price,
            supplier_cost=item.supplier_cost,
            supplier_id=item.supplier_id,
            supplier_name=item.supplier.name if item.supplier else None,
            status=item.status,
        ))

    pos = []
    for po in (order.purchase_orders or []):
        pos.append(PurchaseOrderResponse(
            id=po.id,
            order_id=po.order_id,
            supplier_id=po.supplier_id,
            supplier_name=po.supplier.name if po.supplier else None,
            po_number=po.po_number,
            supplier_order_id=po.supplier_order_id,
            status=po.status,
            total_cost=po.total_cost,
            tracking_number=po.tracking_number,
            carrier=po.carrier,
            submitted_at=po.submitted_at,
            shipped_at=po.shipped_at,
            created_at=po.created_at,
        ))

    events = []
    for ev in (order.events or []):
        events.append(OrderEventResponse(
            id=ev.id,
            order_id=ev.order_id,
            event_type=ev.event_type,
            details=ev.details or {},
            created_at=ev.created_at,
        ))

    base = _order_to_response(order)
    return OrderDetailResponse(
        **base.model_dump(),
        items=items,
        purchase_orders=pos,
        events=events,
    )


# ──────────────────────────────────────────────
# GET /orders  —  List all orders
# ──────────────────────────────────────────────

@router.get("")
def list_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    marketplace_id: Optional[int] = Query(None, description="Filter by marketplace"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Order).options(
        joinedload(Order.marketplace),
        joinedload(Order.items),
    )

    if status:
        query = query.filter(Order.status == status.upper())
    if marketplace_id:
        query = query.filter(Order.marketplace_id == marketplace_id)

    total = query.count()
    orders = query.order_by(desc(Order.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "orders": [_order_to_response(o) for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ──────────────────────────────────────────────
# GET /orders/stats  —  Order statistics
# ──────────────────────────────────────────────

@router.get("/stats")
def order_stats(db: Session = Depends(get_db)):
    service = OrderService(db)
    stats = service.get_stats()
    return OrderStatsResponse(**stats)


# ──────────────────────────────────────────────
# GET /orders/{id}  —  Order detail
# ──────────────────────────────────────────────

@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).options(
        joinedload(Order.marketplace),
        joinedload(Order.items).joinedload(OrderItem.supplier),
        joinedload(Order.purchase_orders).joinedload(PurchaseOrder.supplier),
        joinedload(Order.events),
    ).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return _order_to_detail(order)


# ──────────────────────────────────────────────
# POST /orders/sync  —  Trigger manual order ingestion
# ──────────────────────────────────────────────

@router.post("/sync")
def sync_orders(db: Session = Depends(get_db)):
    """Manually trigger order ingestion from all active marketplaces."""
    service = OrderService(db)
    marketplaces = db.query(Marketplace).filter(Marketplace.is_active == True).all()

    total_ingested = 0
    results = []
    for mp in marketplaces:
        try:
            new_orders = service.ingest_marketplace_orders(mp.id)
            total_ingested += len(new_orders)
            results.append({
                "marketplace": mp.name,
                "new_orders": len(new_orders),
                "status": "success"
            })
        except Exception as exc:
            results.append({
                "marketplace": mp.name,
                "new_orders": 0,
                "status": f"error: {str(exc)}"
            })

    return {
        "total_new_orders": total_ingested,
        "marketplaces": results,
    }


# ──────────────────────────────────────────────
# POST /orders/{id}/route  —  Route order to suppliers
# ──────────────────────────────────────────────

@router.post("/{order_id}/route")
def route_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.route_order(order_id)
        return {"success": True, "status": order.status, "message": f"Order #{order_id} routed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# POST /orders/{id}/create-po  —  Create purchase orders
# ──────────────────────────────────────────────

@router.post("/{order_id}/create-po")
def create_purchase_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        pos = service.create_purchase_orders(order_id)
        return {
            "success": True,
            "purchase_orders": [
                {"po_number": po.po_number, "supplier_id": po.supplier_id, "total_cost": str(po.total_cost)}
                for po in pos
            ],
            "message": f"Created {len(pos)} purchase order(s) for Order #{order_id}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# PUT /purchase-orders/{id}/submit  —  Record real supplier order confirmation
# ──────────────────────────────────────────────

@router.put("/purchase-orders/{po_id}/submit")
def submit_purchase_order(po_id: int, payload: PurchaseOrderSubmit, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        po = service.submit_purchase_order(po_id, payload.supplier_order_id)
        return {
            "success": True,
            "status": po.status,
            "supplier_order_id": po.supplier_order_id,
            "message": f"PO {po.po_number} marked as submitted to supplier",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# PUT /orders/{id}/tracking  —  Update tracking
# ──────────────────────────────────────────────

@router.put("/{order_id}/tracking")
def update_tracking(order_id: int, payload: TrackingUpdate, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.update_tracking(order_id, payload.tracking_number, payload.carrier)
        return {
            "success": True,
            "status": order.status,
            "tracking_number": payload.tracking_number,
            "message": f"Tracking updated and pushed to marketplace for Order #{order_id}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# PUT /orders/{id}/cancel  —  Cancel order
# ──────────────────────────────────────────────

@router.put("/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    try:
        order = service.cancel_order(order_id)
        return {"success": True, "status": order.status, "message": f"Order #{order_id} cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
