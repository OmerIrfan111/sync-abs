from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class InventoryRule(Base, TimestampMixin):
    __tablename__ = "inventory_rules"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    safety_buffer = Column(Integer, default=0, nullable=False)
    out_of_stock_action = Column(String(50), default="SET_QUANTITY_ZERO", nullable=False) # SET_QUANTITY_ZERO, DISABLE_LISTING, MARK_UNAVAILABLE

    product = relationship("Product", back_populates="inventory_rules")
