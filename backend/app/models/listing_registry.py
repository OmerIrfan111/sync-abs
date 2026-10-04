from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class ListingRegistry(Base):
    __tablename__ = "listing_registry"

    id = Column(Integer, primary_key=True, index=True)
    normalized_upc = Column(String(50), nullable=False, index=True)
    marketplace = Column(String(100), nullable=False, index=True)
    marketplace_listing_id = Column(String(100), nullable=True, index=True)
    sku = Column(String(100), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    brand = Column(String(255), nullable=True, index=True)
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, WITHDRAWN, ENDED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product")

    __table_args__ = (
        UniqueConstraint("marketplace", "normalized_upc", name="uq_listing_registry_mkt_upc"),
    )
