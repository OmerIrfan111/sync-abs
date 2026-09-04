from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    adapter_class = Column(String(255), nullable=False)
    credentials_encrypted = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)

    supplier_products = relationship("SupplierProduct", back_populates="supplier", cascade="all, delete-orphan")
    priorities = relationship("SupplierPriority", back_populates="supplier", cascade="all, delete-orphan")
