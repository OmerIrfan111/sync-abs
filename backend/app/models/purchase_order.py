from sqlalchemy import Column, Integer, String, Numeric, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class PurchaseOrder(Base, TimestampMixin):
    """
    Purchase order sent to a supplier to fulfill a customer order.
    One customer order may generate multiple POs if items are sourced from different suppliers.
    """
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    po_number = Column(String(100), unique=True, nullable=False, index=True)
    supplier_order_id = Column(String(200), nullable=True)
    status = Column(String(50), default="DRAFT", nullable=False, index=True)
    # Statuses: DRAFT, SUBMITTED, CONFIRMED, SHIPPED, DELIVERED, CANCELLED
    total_cost = Column(Numeric(12, 2), nullable=False, default=0)
    tracking_number = Column(String(200), nullable=True)
    carrier = Column(String(100), nullable=True)
    shipping_address = Column(JSON, default=dict, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="purchase_orders")
    supplier = relationship("Supplier")
