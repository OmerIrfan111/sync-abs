from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
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
    # When the current stored credentials (e.g. an eBay 18-month refresh token)
    # will stop working and require the merchant to manually re-authorize.
    # Null means unknown/not tracked (e.g. static tokens, or a token issued
    # before this tracking existed).
    credentials_expires_at = Column(DateTime, nullable=True)

    listings = relationship("Listing", back_populates="marketplace", cascade="all, delete-orphan")
    pricing_rules = relationship("PricingRule", back_populates="marketplace", cascade="all, delete-orphan")
