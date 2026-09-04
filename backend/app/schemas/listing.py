from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class ListingBase(BaseModel):
    product_id: int
    marketplace_id: int
    selling_price: Decimal = Field(..., ge=0)
    listed_qty: int = Field(0, ge=0)

class ListingCreate(ListingBase):
    pass

class ListingPublishRequest(BaseModel):
    product_id: int
    marketplace_id: int
    custom_price: Optional[Decimal] = None
    custom_qty: Optional[int] = None

class ListingUpdate(BaseModel):
    selling_price: Optional[Decimal] = None
    listed_qty: Optional[int] = None
    status: Optional[str] = None

class ListingResponse(BaseModel):
    id: int
    product_id: int
    product_sku: Optional[str] = None
    product_title: Optional[str] = None
    marketplace_id: int
    marketplace_name: Optional[str] = None
    external_listing_id: Optional[str] = None
    status: str
    selling_price: Decimal
    listed_qty: int
    last_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedListingsResponse(BaseModel):
    items: List[ListingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
