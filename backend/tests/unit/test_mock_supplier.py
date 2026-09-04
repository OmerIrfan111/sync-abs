import pytest
from decimal import Decimal
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter

def test_mock_supplier_catalog_fetch():
    adapter = MockSupplierAdapter(supplier_name="Ingram Micro")
    assert adapter.test_connection() is True

    items = adapter.fetch_catalog()
    assert len(items) >= 2
    logi = next((item for item in items if "MXKEYS" in item.supplier_sku), None)
    assert logi is not None
    assert logi.cost == Decimal("50.00")
    assert logi.quantity == 20
    assert logi.brand == "Logitech"
    assert logi.stock_status == "IN_STOCK"

def test_mock_supplier_inventory_and_prices():
    adapter = MockSupplierAdapter(supplier_name="D&H")
    inv = adapter.fetch_inventory()
    assert "DH-LOGI-MXKEYS" in inv
    assert inv["DH-LOGI-MXKEYS"] == 50

    prices = adapter.fetch_price_changes()
    assert "DH-LOGI-MXKEYS" in prices
    assert prices["DH-LOGI-MXKEYS"] == Decimal("52.00")

def test_mock_supplier_simulated_failures():
    # Auth failure simulation
    auth_failing_adapter = MockSupplierAdapter(
        supplier_name="Ingram Micro",
        config={"simulate_auth_failure": True}
    )
    with pytest.raises(PermissionError):
        auth_failing_adapter.test_connection()

    # Connection failure simulation
    conn_failing_adapter = MockSupplierAdapter(
        supplier_name="Ingram Micro",
        config={"simulate_connection_failure": True}
    )
    with pytest.raises(ConnectionError):
        conn_failing_adapter.fetch_catalog()

def test_mock_supplier_dynamic_state_manipulation():
    supplier = "Ingram Micro"
    sku = "ING-LOGI-MXKEYS"

    # Set new cost and stock
    MockSupplierAdapter.set_mock_product(supplier, sku, cost=Decimal("54.50"), quantity=15)
    adapter = MockSupplierAdapter(supplier_name=supplier)
    prices = adapter.fetch_price_changes()
    inventory = adapter.fetch_inventory([sku])

    assert prices[sku] == Decimal("54.50")
    assert inventory[sku] == 15

    # Test OOS status transition
    MockSupplierAdapter.set_mock_product(supplier, sku, quantity=0)
    items = adapter.fetch_catalog()
    target = next(i for i in items if i.supplier_sku == sku)
    assert target.quantity == 0
    assert target.stock_status == "OUT_OF_STOCK"
