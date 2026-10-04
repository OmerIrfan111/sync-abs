from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel
from app.schemas.sync import ErrorLogResponse

class SupplierHealthStatus(BaseModel):
    id: int
    name: str
    is_active: bool
    status: str # HEALTHY, ERROR, SYNCING, IDLE
    last_synced_at: Optional[datetime] = None
    product_count: int

class MarketplaceHealthStatus(BaseModel):
    id: int
    name: str
    is_active: bool
    status: str
    listing_count: int
    credentials_expires_at: Optional[datetime] = None
    days_until_credentials_expire: Optional[int] = None

class PriceChangeEntry(BaseModel):
    product_id: int
    product_sku: Optional[str] = None
    product_title: Optional[str] = None
    supplier_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime

class DashboardStats(BaseModel):
    total_products: int
    active_listings: int
    in_stock_products: int
    out_of_stock_products: int
    needs_attention: int
    total_orders_today: int = 0
    pending_orders: int = 0
    revenue_30d: Decimal = Decimal("0.00")
    pricing_changes_24h: int = 0
    recent_price_changes: List[PriceChangeEntry] = []
    suppliers_health: List[SupplierHealthStatus]
    marketplaces_health: List[MarketplaceHealthStatus]
    recent_errors: List[ErrorLogResponse]
    credential_warnings: List[str] = []
