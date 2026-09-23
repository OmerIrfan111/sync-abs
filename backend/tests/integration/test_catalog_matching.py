import pytest
from decimal import Decimal
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.supplier_product import SupplierProduct
from app.models.sync_log import SyncLog
from app.services.catalog_service import CatalogService
from app.services.sync_service import SyncService
from app.schemas.supplier import NormalizedProduct
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter

def test_product_matching_across_suppliers(db_session):
    # Setup two suppliers
    sup1 = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    sup2 = Supplier(name="D&H", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add_all([sup1, sup2])
    db_session.commit()

    service = CatalogService(db_session)

    # Supplier 1 imports Logitech Keyboard
    prod1_data = NormalizedProduct(
        supplier_sku="ING-LOGI-MXKEYS",
        upc="097855149367",
        title="Logitech MX Keys Wireless Keyboard",
        cost=Decimal("50.00"),
        quantity=20,
        stock_status="IN_STOCK",
        availability_status="ACTIVE"
    )
    product1, sp1, logs1 = service.upsert_supplier_product(sup1, prod1_data)
    assert product1.id is not None
    assert sp1.cost == Decimal("50.00")
    assert sp1.qty_available == 20

    # Supplier 2 imports same keyboard with matching UPC but different SKU & cost
    prod2_data = NormalizedProduct(
        supplier_sku="DH-LOGI-MXKEYS",
        upc="097855149367",
        title="Logitech MX Keys Wireless Keyboard (Graphite)",
        cost=Decimal("52.00"),
        quantity=50,
        stock_status="IN_STOCK",
        availability_status="ACTIVE"
    )
    product2, sp2, logs2 = service.upsert_supplier_product(sup2, prod2_data)

    # CRITICAL: They must link to the EXACT SAME Product ID (Section 12 Product Matching)
    assert product1.id == product2.id

    # Check that product has both suppliers linked
    linked_suppliers = db_session.query(SupplierProduct).filter(SupplierProduct.product_id == product1.id).all()
    assert len(linked_suppliers) == 2

def test_change_detection_and_sync_log(db_session):
    sup = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(sup)
    db_session.commit()

    service = CatalogService(db_session)

    initial_item = NormalizedProduct(
        supplier_sku="ING-TEST-001",
        upc="840080500111",
        title="Enterprise 4K UltraHD Pro Monitor",
        cost=Decimal("500.00"),
        quantity=20,
        stock_status="IN_STOCK",
        availability_status="ACTIVE"
    )
    product, sp, logs = service.upsert_supplier_product(sup, initial_item)
    assert sp.cost == Decimal("500.00")
    assert sp.qty_available == 20

    # Simulate price update ($500 -> $520) and stock decrease (20 -> 8)
    updated_item = NormalizedProduct(
        supplier_sku="ING-TEST-001",
        upc="840080500111",
        title="Enterprise 4K UltraHD Pro Monitor",
        cost=Decimal("520.00"),
        quantity=8,
        stock_status="IN_STOCK",
        availability_status="ACTIVE"
    )
    product, sp, logs = service.upsert_supplier_product(sup, updated_item)

    # Verify updated values in DB
    assert sp.cost == Decimal("520.00")
    assert sp.qty_available == 8

    # Verify SyncLog records changes
    sync_logs = db_session.query(SyncLog).filter(SyncLog.product_id == product.id).all()
    fields_changed = [l.field_changed for l in sync_logs]
    assert "cost" in fields_changed
    assert "qty_available" in fields_changed

    cost_log = next(l for l in sync_logs if l.field_changed == "cost")
    assert cost_log.old_value == "500.00"
    assert cost_log.new_value == "520.00"

    qty_log = next(l for l in sync_logs if l.field_changed == "qty_available")
    assert qty_log.old_value == "20"
    assert qty_log.new_value == "8"

def test_upsert_supplier_product_populates_warehouse_stock(db_session):
    """
    Suppliers whose real API reports per-warehouse breakdown (D&H's
    priceAndAvailability response) should get real Warehouse/WarehouseStock
    rows, without disturbing the existing aggregate qty_available contract
    that pricing/inventory rules already rely on.
    """
    from app.models.warehouse import Warehouse, WarehouseStock

    sup = Supplier(name="D&H", adapter_class="DAndHAdapter", is_active=True)
    db_session.add(sup)
    db_session.commit()

    service = CatalogService(db_session)
    item = NormalizedProduct(
        supplier_sku="AXG99626",
        title="15FT CAT6 550mhz Cable",
        cost=Decimal("11.32"),
        quantity=30,
        availability_status="ACTIVE",
        shipping_info={
            "weight_lbs": 1.0,
            "branch_inventory": [
                {"branch": "BR01", "availableQuantity": 20, "stockReplenishDate": None},
                {"branch": "BR06", "availableQuantity": 10, "stockReplenishDate": None},
            ],
        },
    )
    product, supplier_prod, _ = service.upsert_supplier_product(sup, item)

    warehouses = db_session.query(Warehouse).filter(Warehouse.supplier_id == sup.id).all()
    assert {w.code for w in warehouses} == {"BR01", "BR06"}
    assert next(w.name for w in warehouses if w.code == "BR01") == "Mid-Atlantic"

    stock_rows = db_session.query(WarehouseStock).filter(
        WarehouseStock.supplier_product_id == supplier_prod.id
    ).all()
    assert len(stock_rows) == 2
    assert sum(s.qty_available for s in stock_rows) == 30

    # Re-sync with updated branch quantities should update, not duplicate
    item2 = item.model_copy(update={"shipping_info": {
        "branch_inventory": [
            {"branch": "BR01", "availableQuantity": 5, "stockReplenishDate": None},
            {"branch": "BR06", "availableQuantity": 10, "stockReplenishDate": None},
        ],
    }})
    service.upsert_supplier_product(sup, item2)

    stock_rows_after = db_session.query(WarehouseStock).filter(
        WarehouseStock.supplier_product_id == supplier_prod.id
    ).all()
    assert len(stock_rows_after) == 2
    br01_stock = next(s for s in stock_rows_after if s.warehouse.code == "BR01")
    assert br01_stock.qty_available == 5


def test_sync_service_full_run(db_session):
    sup = Supplier(name="VoiceComm", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(sup)
    db_session.commit()

    sync_service = SyncService(db_session)
    result = sync_service.sync_supplier(sup.id)

    assert result["status"] == "SUCCESSFULLY_SYNCHRONIZED"
    assert result["products_imported"] >= 1
    assert sup.last_synced_at is not None


def test_sync_service_isolates_one_malformed_item(monkeypatch):
    """
    A single bad item (DB error, unexpected data shape, etc.) must not abort
    the rest of the batch. The sync should still succeed, import the good
    items, and log a MISSING_DATA error for the bad one.

    Uses its own standalone engine/session (not the shared db_session
    fixture): this test exercises a real session.rollback() mid-sync, which
    needs a genuinely-committed prior transaction to recover correctly from
    (exactly like production). The shared fixture wraps the whole test in one
    outer, never-really-committed transaction, so a rollback() there would
    wipe out this test's own setup data too — a fixture artifact, not a
    production behavior.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SQLASession
    from app.core.database import Base
    from app.models.error_log import ErrorLog

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db_session = SQLASession(bind=engine)

    sup = Supplier(name="Ingram Micro", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(sup)
    db_session.commit()

    good_item_1 = NormalizedProduct(
        supplier_sku="GOOD-001", title="Good Item One",
        cost=Decimal("10.00"), quantity=5, availability_status="ACTIVE",
    )
    bad_item = NormalizedProduct(
        supplier_sku="BAD-001", title="Bad Item",
        cost=Decimal("10.00"), quantity=5, availability_status="ACTIVE",
    )
    good_item_2 = NormalizedProduct(
        supplier_sku="GOOD-002", title="Good Item Two",
        cost=Decimal("20.00"), quantity=3, availability_status="ACTIVE",
    )

    from app.adapters.suppliers.mock_supplier import MockSupplierAdapter as MSA
    monkeypatch.setattr(MSA, "fetch_catalog", lambda self, **kw: [good_item_1, bad_item, good_item_2])

    original_upsert = CatalogService.upsert_supplier_product

    def flaky_upsert(self, supplier, item):
        if item.supplier_sku == "BAD-001":
            raise RuntimeError("Simulated DB constraint violation")
        return original_upsert(self, supplier, item)

    monkeypatch.setattr(CatalogService, "upsert_supplier_product", flaky_upsert)

    sync_service = SyncService(db_session)
    result = sync_service.sync_supplier(sup.id)

    assert result["status"] == "SUCCESSFULLY_SYNCHRONIZED"
    assert result["products_imported"] == 2

    imported_skus = {p.sku for p in db_session.query(Product).all()}
    assert "GOOD-001" in imported_skus
    assert "GOOD-002" in imported_skus
    assert "BAD-001" not in imported_skus

    error = db_session.query(ErrorLog).filter(
        ErrorLog.error_type == "MISSING_DATA",
        ErrorLog.supplier_id == sup.id,
    ).first()
    assert error is not None
    assert "BAD-001" in error.message

    db_session.close()
    Base.metadata.drop_all(bind=engine)
