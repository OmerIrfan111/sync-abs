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

def test_sync_service_full_run(db_session):
    sup = Supplier(name="VoiceComm", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(sup)
    db_session.commit()

    sync_service = SyncService(db_session)
    result = sync_service.sync_supplier(sup.id)

    assert result["status"] == "SUCCESSFULLY_SYNCHRONIZED"
    assert result["products_imported"] >= 1
    assert sup.last_synced_at is not None
