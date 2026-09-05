from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

# --- Pricing Rules ---
class PricingRuleBase(BaseModel):
    product_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    rule_type: str = Field(..., description="FIXED_PROFIT, PERCENTAGE_MARKUP, FEE_MARGIN")
    fixed_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    percentage: Decimal = Field(default=Decimal("0.00"), ge=0)
    marketplace_fee: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    desired_margin: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: Optional[str] = None

class PricingRuleCreate(PricingRuleBase):
    pass

class PricingRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    fixed_amount: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    marketplace_fee: Optional[Decimal] = None
    desired_margin: Optional[Decimal] = None
    notes: Optional[str] = None

class PricingRuleResponse(PricingRuleBase):
    id: int
    product_sku: Optional[str] = None
    product_title: Optional[str] = None
    marketplace_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Inventory Rules ---
class InventoryRuleBase(BaseModel):
    product_id: Optional[int] = None
    safety_buffer: int = Field(default=0, ge=0)
    out_of_stock_action: str = Field(default="SET_QUANTITY_ZERO", description="SET_QUANTITY_ZERO, DISABLE_LISTING, MARK_UNAVAILABLE")

class InventoryRuleCreate(InventoryRuleBase):
    pass

class InventoryRuleUpdate(BaseModel):
    safety_buffer: Optional[int] = None
    out_of_stock_action: Optional[str] = None

class InventoryRuleResponse(InventoryRuleBase):
    id: int
    product_sku: Optional[str] = None
    product_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Supplier Priority Rules ---
class SupplierPriorityBase(BaseModel):
    product_id: int
    supplier_id: int
    priority_rank: int = Field(default=1, ge=1)
    selection_rule: str = Field(default="LOWEST_COST", description="LOWEST_COST, HIGHEST_STOCK, PRIORITY_RANK, SHIPPING_LOCATION")

class SupplierPriorityCreate(SupplierPriorityBase):
    pass

class SupplierPriorityUpdate(BaseModel):
    priority_rank: Optional[int] = None
    selection_rule: Optional[str] = None

class SupplierPriorityResponse(SupplierPriorityBase):
    id: int
    product_sku: Optional[str] = None
    product_title: Optional[str] = None
    supplier_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
