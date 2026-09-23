from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Warehouse(Base, TimestampMixin):
    """
    A physical distribution location belonging to a supplier (e.g. D&H's
    BR01 Mid-Atlantic branch). Suppliers whose API doesn't expose per-location
    breakdown (Ingram Micro's Catalog API returns only an aggregate quantity)
    simply have no Warehouse rows — aggregate-only stock keeps working as-is.
    """
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    supplier = relationship("Supplier")
    stock_records = relationship("WarehouseStock", back_populates="warehouse", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("supplier_id", "code", name="uq_warehouse_supplier_code"),
    )


class WarehouseStock(Base, TimestampMixin):
    """
    Per-warehouse stock quantity for a given supplier's product. The
    aggregate SupplierProduct.qty_available remains the source of truth for
    pricing/inventory rules (spec's existing formulas operate on it
    unchanged); this table adds the location-level detail underneath it,
    for suppliers that report it, without touching that existing contract.
    """
    __tablename__ = "warehouse_stock"

    id = Column(Integer, primary_key=True, index=True)
    supplier_product_id = Column(Integer, ForeignKey("supplier_products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    qty_available = Column(Integer, default=0, nullable=False)
    stock_replenish_date = Column(DateTime, nullable=True)

    supplier_product = relationship("SupplierProduct", back_populates="warehouse_stock")
    warehouse = relationship("Warehouse", back_populates="stock_records")

    __table_args__ = (
        UniqueConstraint("supplier_product_id", "warehouse_id", name="uq_warehouse_stock_product_warehouse"),
    )
