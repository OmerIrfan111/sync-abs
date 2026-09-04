from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class SupplierPriority(Base, TimestampMixin):
    __tablename__ = "supplier_priorities"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    priority_rank = Column(Integer, default=1, nullable=False)
    selection_rule = Column(String(50), default="LOWEST_COST", nullable=False) # LOWEST_COST, HIGHEST_STOCK, PRIORITY_RANK, SHIPPING_LOCATION

    product = relationship("Product", back_populates="priorities")
    supplier = relationship("Supplier", back_populates="priorities")
