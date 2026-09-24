from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from decimal import Decimal
from datetime import datetime


# --- Order Event ---

class OrderEventResponse(BaseModel):
    id: int
    order_id: int
    event_type: str
    details: Dict[str, Any] = {}
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Order Item ---

class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: Optional[int] = None
    listing_id: Optional[int] = None
    marketplace_item_id: Optional[str] = None
    sku: Optional[str] = None
    title: Optional[str] = None
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")
    supplier_cost: Optional[Decimal] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    status: str = "PENDING"
    routing_note: Optional[str] = None

    class Config:
        from_attributes = True


# --- Purchase Order ---

class PurchaseOrderResponse(BaseModel):
    id: int
    order_id: int
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    po_number: str
    supplier_order_id: Optional[str] = None
    status: str = "DRAFT"
    total_cost: Decimal = Decimal("0.00")
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    submitted_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Order ---

class OrderResponse(BaseModel):
    id: int
    marketplace_id: Optional[int] = None
    marketplace_name: Optional[str] = None
    marketplace_order_id: str
    buyer_username: Optional[str] = None
    buyer_name: Optional[str] = None
    shipping_address: Dict[str, Any] = {}
    order_total: Decimal = Decimal("0.00")
    marketplace_fees: Decimal = Decimal("0.00")
    currency: str = "USD"
    status: str = "PENDING_ROUTING"
    ordered_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    items_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    """Extended order response including line items, POs, and event audit trail."""
    items: List[OrderItemResponse] = []
    purchase_orders: List[PurchaseOrderResponse] = []
    events: List[OrderEventResponse] = []


class OrderStatsResponse(BaseModel):
    total_orders: int = 0
    pending_routing: int = 0
    awaiting_shipment: int = 0
    shipped: int = 0
    delivered: int = 0
    cancelled: int = 0
    revenue_30d: Decimal = Decimal("0.00")
    orders_today: int = 0
    avg_order_value: Decimal = Decimal("0.00")


class TrackingUpdate(BaseModel):
    tracking_number: str
    carrier: Optional[str] = None


class PurchaseOrderSubmit(BaseModel):
    supplier_order_id: str
