from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SyncLogResponse(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_sku: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    synced_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedSyncLogsResponse(BaseModel):
    items: List[SyncLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class ErrorLogResponse(BaseModel):
    id: int
    error_type: str
    product_id: Optional[int] = None
    product_sku: Optional[str] = None
    marketplace_id: Optional[int] = None
    marketplace_name: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    message: str
    retry_count: int
    status: str
    resolved_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedErrorLogsResponse(BaseModel):
    items: List[ErrorLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class TriggerSyncResponse(BaseModel):
    task_id: str
    message: str
    supplier_id: int
