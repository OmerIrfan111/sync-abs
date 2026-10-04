import pytest
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter
from app.services.sync_service import SyncService
from app.models.supplier import Supplier


def test_prefetch_filters_in_adapter():
    """
    Feature 2: Test prefetch filtering on limit, category, and brand in supplier adapter.
    """
    adapter = MockSupplierAdapter(supplier_name="Mock Tech Supplies")

    # 1. Unfiltered returns all 5 items
    all_items = adapter.fetch_catalog()
    assert len(all_items) == 5

    # 2. Limit filter = 3
    limited_items = adapter.fetch_catalog(filters={"limit": 3})
    assert len(limited_items) == 3

    # 3. Category filter = "Monitors"
    monitor_items = adapter.fetch_catalog(filters={"category": "Monitors"})
    assert len(monitor_items) >= 1
    for it in monitor_items:
        assert "monitor" in (it.category or "").lower()

    # 4. Brand filter = "Logitech"
    logi_items = adapter.fetch_catalog(filters={"brand": "Logitech"})
    assert len(logi_items) >= 1
    for it in logi_items:
        assert (it.brand or "").lower() == "logitech"

    # 5. Combined filters: category="Computer Accessories" AND limit=1
    combo_items = adapter.fetch_catalog(filters={"category": "Computer Accessories", "limit": 1})
    assert len(combo_items) == 1
    assert "accessories" in (combo_items[0].category or "").lower()

    # 6. Supplier name filter mismatch returns empty
    mismatch = adapter.fetch_catalog(filters={"supplier": "Ingram Micro"})
    assert len(mismatch) == 0


def test_prefetch_filters_validation_in_sync_service(db_session):
    """
    Feature 2: Input validation in SyncService rejects invalid filters with clear errors.
    """
    supplier = Supplier(name="Test Filter Supplier", adapter_class="MockSupplierAdapter", is_active=True)
    db_session.add(supplier)
    db_session.commit()

    service = SyncService(db_session)

    # 1. Negative limit
    with pytest.raises(ValueError) as exc:
        service.sync_supplier(supplier.id, filters={"limit": -5})
    assert "greater than 0" in str(exc.value)

    # 2. Zero limit
    with pytest.raises(ValueError) as exc:
        service.sync_supplier(supplier.id, filters={"limit": 0})
    assert "greater than 0" in str(exc.value)

    # 3. Non-numeric limit
    with pytest.raises(ValueError) as exc:
        service.sync_supplier(supplier.id, filters={"limit": "abc"})
    assert "Invalid prefetch filter" in str(exc.value)

    # 4. Mismatched supplier filter
    with pytest.raises(ValueError) as exc:
        service.sync_supplier(supplier.id, filters={"supplier": "Different Supplier"})
    assert "does not match target supplier" in str(exc.value)
