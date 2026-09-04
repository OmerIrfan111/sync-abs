from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Listing(Base, TimestampMixin):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=False, index=True)
    external_listing_id = Column(String(100), nullable=True, index=True)
    status = Column(String(50), default="PENDING", nullable=False) # PENDING, ACTIVE, PAUSED, WITHDRAWN, ERROR
    selling_price = Column(Numeric(10, 2), nullable=False)
    listed_qty = Column(Integer, default=0, nullable=False)
    last_updated_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="listings")
    marketplace = relationship("Marketplace", back_populates="listings")
