from typing import List, Optional
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

class DashboardStats(BaseModel):
    total_products: int
    active_listings: int
    in_stock_products: int
    out_of_stock_products: int
    needs_attention: int
    suppliers_health: List[SupplierHealthStatus]
    marketplaces_health: List[MarketplaceHealthStatus]
    recent_errors: List[ErrorLogResponse]
