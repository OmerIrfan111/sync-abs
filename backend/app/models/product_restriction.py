from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class ProductRestriction(Base, TimestampMixin):
    """
    Blocks or flags a product (or an entire category/brand) from being
    published to a marketplace — e.g. hazmat items, brand-gated categories
    requiring manufacturer approval, marketplace-specific policy blocks.

    Matching is deliberately broad-to-narrow: a rule can target a specific
    product_id, or a category/brand (applied to any product matching it),
    and can apply to one marketplace_id or all of them (null = all).
    A specific product_id rule always takes precedence when present.
    """
    __tablename__ = "product_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    category = Column(String(255), nullable=True, index=True)
    brand = Column(String(255), nullable=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=True, index=True)
    restriction_type = Column(String(50), nullable=False, default="BLOCKED")
    # BLOCKED: publishing is refused outright.
    # REQUIRES_APPROVAL: publishing is refused until staff clears it (approved_at set).
    reason = Column(Text, nullable=False)
    approved_at = Column(DateTime, nullable=True)  # set when staff clears a REQUIRES_APPROVAL restriction

    product = relationship("Product")
    marketplace = relationship("Marketplace")
