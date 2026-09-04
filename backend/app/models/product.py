from sqlalchemy import Column, Integer, String, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    upc = Column(String(50), index=True, nullable=True)
    ean = Column(String(50), index=True, nullable=True)
    mpn = Column(String(100), index=True, nullable=True)
    title = Column(String(500), nullable=False)
    brand = Column(String(255), index=True, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(255), index=True, nullable=True)
    images = Column(JSON, default=list, nullable=False)
    specs_json = Column(JSON, default=dict, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)

    supplier_products = relationship("SupplierProduct", back_populates="product", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="product", cascade="all, delete-orphan")
    pricing_rules = relationship("PricingRule", back_populates="product", cascade="all, delete-orphan")
    inventory_rules = relationship("InventoryRule", back_populates="product", cascade="all, delete-orphan")
    priorities = relationship("SupplierPriority", back_populates="product", cascade="all, delete-orphan")
