from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Marketplace(Base, TimestampMixin):
    __tablename__ = "marketplaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    adapter_class = Column(String(255), nullable=False)
    credentials_encrypted = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    listings = relationship("Listing", back_populates="marketplace", cascade="all, delete-orphan")
    pricing_rules = relationship("PricingRule", back_populates="marketplace", cascade="all, delete-orphan")
