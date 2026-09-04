from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base

class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String(100), nullable=False, index=True) 
    # e.g. SUPPLIER_CONNECTION_ERROR, MARKETPLACE_CONNECTION_ERROR, LISTING_ERROR, MISSING_DATA, PRICING_ERROR, INVENTORY_MISMATCH
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False, index=True) # PENDING, RETRYING, RESOLVED, FAILED
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
