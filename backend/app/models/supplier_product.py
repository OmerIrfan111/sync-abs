from sqlalchemy import Column, Integer, String, Numeric, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class SupplierProduct(Base, TimestampMixin):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_sku = Column(String(100), nullable=False, index=True)
    cost = Column(Numeric(10, 2), nullable=False)
    qty_available = Column(Integer, default=0, nullable=False)
    stock_status = Column(String(50), default="IN_STOCK", nullable=False) # IN_STOCK, OUT_OF_STOCK, BACKORDER
    availability_status = Column(String(50), default="ACTIVE", nullable=False) # ACTIVE, DISCONTINUED, UNAVAILABLE
    shipping_info = Column(JSON, default=dict, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="supplier_products")
    supplier = relationship("Supplier", back_populates="supplier_products")
