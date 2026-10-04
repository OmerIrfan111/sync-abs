from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ProductShippingHistory(Base):
    __tablename__ = "product_shipping_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_product_id = Column(Integer, ForeignKey("supplier_products.id", ondelete="SET NULL"), nullable=True, index=True)
    shipping_charge = Column(Numeric(10, 2), nullable=False)
    source = Column(String(50), nullable=False)  # "live", "history"
    destination_zip = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product")
    supplier = relationship("Supplier")
    supplier_product = relationship("SupplierProduct")
