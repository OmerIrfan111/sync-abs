from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class OrderEvent(Base):
    """
    Immutable audit trail for every order state change.
    Tracks the complete lifecycle of an order from ingestion to delivery.
    """
    __tablename__ = "order_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    # Event types: ORDER_RECEIVED, SUPPLIER_ROUTED, PO_CREATED, PO_SUBMITTED,
    #              TRACKING_UPDATED, SHIPPED, DELIVERED, CANCELLED, ERROR, NOTE
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    order = relationship("Order", back_populates="events")
