from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class SupplierProductInfo(BaseModel):
    id: int
    supplier_id: int
    supplier_name: Optional[str] = None
    supplier_sku: str
    cost: Decimal
    qty_available: int
    is_unlimited_stock: bool = False
    # True when qty_available is a supplier-side sentinel for "no physical
    # unit limit" (e.g. Ingram Micro reports software licenses/support
    # contracts as multiples of 9,999,999 rather than a real stock count).
    # Confirmed pattern from real catalog data, not a guess — the UI should
    # never display qty_available literally when this is true.
    stock_status: str
    availability_status: str
    shipping_info: Dict[str, Any] = Field(default_factory=dict)
    base_shipping_charge: Optional[Decimal] = None
    shipping_source: Optional[str] = None
    shipping_status: Optional[str] = None
    shipping_updated_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    sku: str = Field(..., max_length=100)
    upc: Optional[str] = Field(None, max_length=50)
    ean: Optional[str] = Field(None, max_length=50)
    mpn: Optional[str] = Field(None, max_length=100)
    title: str = Field(..., max_length=500)
    brand: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=255)
    images: List[str] = Field(default_factory=list)
    specs_json: Dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    upc: Optional[str] = None
    ean: Optional[str] = None
    mpn: Optional[str] = None
    title: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    images: Optional[List[str]] = None
    specs_json: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    supplier_products: List[SupplierProductInfo] = Field(default_factory=list)
    total_stock: Optional[int] = 0
    is_unlimited_stock: bool = False
    lowest_cost: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)

class PaginatedProductsResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
