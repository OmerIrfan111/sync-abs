from sqlalchemy import Column, Integer, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class MarketplaceFeeSchedule(Base, TimestampMixin):
    """
    A per-marketplace default commission percentage (Phase 4: formalized
    marketplace fee calculations). One row per marketplace, category-agnostic
    — real per-category fee tables vary constantly and by seller program, so
    this stores an editable default rather than a precise, unmaintainable
    lookup table. Staff should verify/adjust it against their actual category
    and selling plan; it's a starting point, not an authoritative rate card.
    Used as the fallback fee_percentage when a FEE_MARGIN pricing rule for
    this marketplace doesn't specify its own marketplace_fee.
    """
    __tablename__ = "marketplace_fee_schedules"

    id = Column(Integer, primary_key=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    fee_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)

    marketplace = relationship("Marketplace")
