from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Order(Base, TimestampMixin):
    """
    Represents a customer order received from a marketplace (eBay, Amazon, Shopify).
    Central record for tracking the full order lifecycle from ingestion to delivery.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id", ondelete="SET NULL"), nullable=True, index=True)
    marketplace_order_id = Column(String(200), nullable=False, unique=True, index=True)
    buyer_username = Column(String(200), nullable=True)
    buyer_name = Column(String(300), nullable=True)
    shipping_address = Column(JSON, default=dict, nullable=False)
    order_total = Column(Numeric(12, 2), nullable=False, default=0)
    marketplace_fees = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(String(50), default="PENDING_ROUTING", nullable=False, index=True)
    # Statuses: PENDING_ROUTING, ROUTED, PO_SUBMITTED, SHIPPED, DELIVERED, COMPLETED, CANCELLED, REFUNDED
    ordered_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    marketplace = relationship("Marketplace")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="order", cascade="all, delete-orphan")
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan", order_by="OrderEvent.created_at.desc()")
