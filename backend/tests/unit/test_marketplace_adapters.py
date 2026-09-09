from decimal import Decimal
import pytest

from app.adapters.marketplaces.mock_ebay import MockEBayAdapter
from app.adapters.marketplaces.mock_amazon import MockAmazonAdapter
from app.adapters.marketplaces.mock_shopify import MockShopifyAdapter
from app.adapters.registry import get_marketplace_adapter

ALL_MARKETPLACE_CLASSES = [
    MockEBayAdapter,
    MockAmazonAdapter,
    MockShopifyAdapter,
]

@pytest.mark.parametrize("adapter_cls", ALL_MARKETPLACE_CLASSES)
def test_all_marketplaces_listing_lifecycle(adapter_cls):
    adapter = adapter_cls()
    assert adapter.test_connection() is True

    # 1. Create Listing
    sku = "TEST-ADAPTER-SKU"
    res = adapter.create_listing(
        sku=sku,
        title="Cross Channel Test Monitor",
        description="High resolution IPS display",
        price=Decimal("499.99"),
        quantity=15
    )
    assert "external_listing_id" in res
    assert res["status"] == "ACTIVE"
    ext_id = res["external_listing_id"]

    # 2. Update Inventory
    success_inv = adapter.update_inventory(ext_id, sku, 10)
    assert success_inv is True

    # 3. Update Price
    success_price = adapter.update_price(ext_id, sku, Decimal("549.99"))
    assert success_price is True

    # 4. Withdraw Listing
    success_delist = adapter.withdraw_listing(ext_id)
    assert success_delist is True

    # 5. Fetch Listing State
    details = adapter.get_listing(ext_id)
    assert details["external_listing_id"] == ext_id
    assert details["quantity"] == 0

@pytest.mark.parametrize("adapter_cls", ALL_MARKETPLACE_CLASSES)
def test_all_marketplaces_simulated_failures(adapter_cls):
    auth_fail_adapter = adapter_cls(config={"simulate_auth_failure": True})
    with pytest.raises(PermissionError):
        auth_fail_adapter.test_connection()

    conn_fail_adapter = adapter_cls(config={"simulate_connection_failure": True})
    with pytest.raises(ConnectionError):
        conn_fail_adapter.test_connection()

def test_amazon_rate_limiting_simulation():
    rate_limited_adapter = MockAmazonAdapter(config={"simulate_rate_limit": True})
    with pytest.raises(ConnectionError, match="Rate Limit Encountered"):
        rate_limited_adapter.test_connection()

def test_marketplace_registry_factory():
    ad1 = get_marketplace_adapter("MockEBayAdapter")
    assert isinstance(ad1, MockEBayAdapter)

    ad2 = get_marketplace_adapter("MockAmazonAdapter")
    assert isinstance(ad2, MockAmazonAdapter)

    ad3 = get_marketplace_adapter("MockShopifyAdapter")
    assert isinstance(ad3, MockShopifyAdapter)

