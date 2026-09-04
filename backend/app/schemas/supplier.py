from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class SupplierBase(BaseModel):
    name: str = Field(..., max_length=255)
    adapter_class: str = Field(..., max_length=255)
    is_active: bool = True

class SupplierCreate(SupplierBase):
    credentials: Optional[Dict[str, Any]] = None

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    adapter_class: Optional[str] = None
    is_active: Optional[bool] = None
    credentials: Optional[Dict[str, Any]] = None

class SupplierResponse(SupplierBase):
    id: int
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    product_count: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)

class NormalizedProduct(BaseModel):
    supplier_sku: str
    upc: Optional[str] = None
    ean: Optional[str] = None
    mpn: Optional[str] = None
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    specs: Dict[str, Any] = Field(default_factory=dict)
    cost: Decimal = Field(..., ge=0)
    quantity: int = Field(..., ge=0)
    stock_status: str = "IN_STOCK"
    shipping_info: Dict[str, Any] = Field(default_factory=dict)
    availability_status: str = "ACTIVE"
