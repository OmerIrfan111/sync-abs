from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class OrderItem(Base, TimestampMixin):
    """
    Individual line item within a customer order.
    Links the sold listing/product to the routed supplier for fulfillment.
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="SET NULL"), nullable=True, index=True)
    marketplace_item_id = Column(String(200), nullable=True)
    sku = Column(String(100), nullable=True, index=True)
    title = Column(String(500), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    supplier_cost = Column(Numeric(10, 2), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="PENDING", nullable=False)
    # Statuses: PENDING, ROUTED, ORDERED, SHIPPED, UNROUTABLE
    routing_note = Column(String(500), nullable=True)
    # Set only when status=UNROUTABLE, explaining exactly why routing couldn't
    # assign a supplier (e.g. no catalog match, or no supplier has stock) so
    # staff see a real reason instead of an item silently stuck at PENDING.

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    listing = relationship("Listing")
    supplier = relationship("Supplier")
