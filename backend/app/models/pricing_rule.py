from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class PricingRule(Base, TimestampMixin):
    __tablename__ = "pricing_rules"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=True, index=True)
    rule_type = Column(String(50), nullable=False) # FIXED_PROFIT, PERCENTAGE_MARKUP, FEE_MARGIN
    fixed_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    marketplace_fee = Column(Numeric(5, 2), default=0.00, nullable=False)
    desired_margin = Column(Numeric(5, 2), default=0.00, nullable=False)
    notes = Column(Text, nullable=True)

    product = relationship("Product", back_populates="pricing_rules")
    marketplace = relationship("Marketplace", back_populates="pricing_rules")
