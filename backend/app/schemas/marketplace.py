from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class MarketplaceBase(BaseModel):
    name: str
    adapter_class: str
    is_active: bool = True

class MarketplaceUpdate(BaseModel):
    name: Optional[str] = None
    adapter_class: Optional[str] = None
    is_active: Optional[bool] = None
    credentials: Optional[Dict[str, Any]] = None

class MarketplaceResponse(MarketplaceBase):
    id: int
    has_credentials: bool
    active_listings_count: int
    total_listings_count: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
