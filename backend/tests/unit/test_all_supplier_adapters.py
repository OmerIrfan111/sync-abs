from decimal import Decimal
import pytest

from app.adapters.suppliers.ingram_micro import IngramMicroAdapter
from app.adapters.suppliers.d_and_h import DAndHAdapter
from app.adapters.registry import get_supplier_adapter

ALL_SUPPLIER_CLASSES = [
    IngramMicroAdapter,
    DAndHAdapter,
]

@pytest.mark.parametrize("adapter_cls", ALL_SUPPLIER_CLASSES)
def test_all_suppliers_catalog_and_connection(adapter_cls):
    adapter = adapter_cls()
    assert adapter.test_connection() is True

    catalog = adapter.fetch_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) > 0

    item = catalog[0]
    assert item.supplier_sku is not None
    assert item.title is not None
    assert item.cost > Decimal("0.00")
    assert item.quantity >= 0
    assert item.availability_status in ["ACTIVE", "INACTIVE"]

@pytest.mark.parametrize("adapter_cls", ALL_SUPPLIER_CLASSES)
def test_all_suppliers_inventory_and_pricing(adapter_cls):
    adapter = adapter_cls()
    catalog = adapter.fetch_catalog()
    skus = [p.supplier_sku for p in catalog]

    inv = adapter.fetch_inventory(skus)
    assert isinstance(inv, dict)
    for sku in skus:
        assert sku in inv
        assert isinstance(inv[sku], int)

    prices = adapter.fetch_price_changes()
    assert isinstance(prices, dict)
    for sku in skus:
        assert sku in prices
        assert prices[sku] > Decimal("0.00")

@pytest.mark.parametrize("adapter_cls", ALL_SUPPLIER_CLASSES)
def test_all_suppliers_simulated_failures(adapter_cls):
    auth_fail_adapter = adapter_cls(config={"simulate_auth_failure": True})
    with pytest.raises(PermissionError):
        auth_fail_adapter.test_connection()

    conn_fail_adapter = adapter_cls(config={"simulate_connection_failure": True})
    with pytest.raises(ConnectionError):
        conn_fail_adapter.test_connection()

def test_supplier_registry_factory():
    ad1 = get_supplier_adapter("IngramMicroAdapter")
    assert isinstance(ad1, IngramMicroAdapter)
    assert ad1.supplier_name == "Ingram Micro"

    ad2 = get_supplier_adapter("DAndHAdapter")
    assert isinstance(ad2, DAndHAdapter)
    assert ad2.supplier_name == "D&H"

