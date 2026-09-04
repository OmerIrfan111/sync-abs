import pytest
from decimal import Decimal
from app.adapters.marketplaces.mock_ebay import MockEBayAdapter

def test_mock_ebay_connection():
    adapter = MockEBayAdapter()
    assert adapter.test_connection() is True

def test_mock_ebay_simulated_failures():
    auth_fail = MockEBayAdapter(config={"simulate_auth_failure": True})
    with pytest.raises(PermissionError):
        auth_fail.test_connection()

    conn_fail = MockEBayAdapter(config={"simulate_connection_failure": True})
    with pytest.raises(ConnectionError):
        conn_fail.test_connection()

def test_mock_ebay_create_listing_lifecycle():
    adapter = MockEBayAdapter()
    sku = "TEST-LOGI-001"
    title = "Logitech MX Keys Wireless Keyboard"
    description = "Premium backlit keyboard"
    price = Decimal("59.99")
    quantity = 25

    listing = adapter.create_listing(
        sku=sku,
        title=title,
        description=description,
        price=price,
        quantity=quantity
    )

    assert "external_listing_id" in listing
    assert listing["external_listing_id"].startswith("ebay_listing_")
    assert listing["status"] == "ACTIVE"
    assert listing["quantity"] == 25
    assert listing["price"] == price

    # Test get listing
    fetched = adapter.get_listing(listing["external_listing_id"])
    assert fetched["sku"] == sku
    assert fetched["quantity"] == 25

def test_mock_ebay_inventory_and_price_revisions():
    adapter = MockEBayAdapter()
    listing = adapter.create_listing(
        sku="TEST-SSD-002",
        title="Samsung T7 SSD",
        description="Fast SSD",
        price=Decimal("99.00"),
        quantity=50
    )
    ext_id = listing["external_listing_id"]

    # Revise inventory
    assert adapter.update_inventory(ext_id, "TEST-SSD-002", quantity=42) is True
    updated = adapter.get_listing(ext_id)
    assert updated["quantity"] == 42

    # Revise price
    assert adapter.update_price(ext_id, "TEST-SSD-002", price=Decimal("109.99")) is True
    updated = adapter.get_listing(ext_id)
    assert updated["price"] == Decimal("109.99")

    # Withdraw listing
    assert adapter.withdraw_listing(ext_id) is True
    updated = adapter.get_listing(ext_id)
    assert updated["status"] == "WITHDRAWN"
    assert updated["quantity"] == 0
