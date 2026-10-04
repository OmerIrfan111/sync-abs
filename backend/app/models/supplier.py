from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric
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
    default_shipping_charge = Column(Numeric(10, 2), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    catalog_sync_cursor = Column(Text, nullable=True)
    # Resume point for paginated catalog fetches (a page number for Ingram
    # Micro, a scrollId for D&H). A real supplier catalog can have thousands
    # of SKUs — far more than fit in one sync run's time budget — so each run
    # picks up where the last one left off instead of always re-fetching the
    # same first page and calling that "synced". Null means "start over from
    # the beginning" (used both on first sync and once a full pass completes).
    catalog_sync_exhausted_at = Column(DateTime, nullable=True)

    supplier_products = relationship("SupplierProduct", back_populates="supplier", cascade="all, delete-orphan")
    priorities = relationship("SupplierPriority", back_populates="supplier", cascade="all, delete-orphan")
