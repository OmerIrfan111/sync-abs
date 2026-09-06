import json
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import urllib.error

from app.adapters.marketplaces.live_shopify import LiveShopifyAdapter

def test_shopify_initialization_and_domain_cleaning():
    adapter = LiveShopifyAdapter(credentials={
        "shop_url": "https://test-store.myshopify.com/",
        "access_token": "shpat_test123456"
    })
    assert adapter.shop_domain == "test-store.myshopify.com"
    assert adapter.access_token == "shpat_test123456"
    assert adapter.base_url == "https://test-store.myshopify.com/admin/api/2024-01"

def test_shopify_test_connection_success():
    adapter = LiveShopifyAdapter(credentials={
        "shop_url": "test-store.myshopify.com",
        "access_token": "shpat_test123456"
    })

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"shop": {"name": "Test Store", "id": 12345}}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert adapter.test_connection() is True

def test_shopify_test_connection_auth_error():
    adapter = LiveShopifyAdapter(credentials={
        "shop_url": "test-store.myshopify.com",
        "access_token": "shpat_invalid"
    })

    err = urllib.error.HTTPError(
        url="https://test-store.myshopify.com/admin/api/2024-01/shop.json",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=MagicMock(read=lambda: b'{"errors":"Invalid API key or access token"}')
    )

    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(PermissionError) as exc_info:
            adapter.test_connection()
        assert "401" in str(exc_info.value)

def test_shopify_create_listing():
    adapter = LiveShopifyAdapter(credentials={
        "shop_url": "test-store.myshopify.com",
        "access_token": "shpat_test123456"
    })

    shop_resp = MagicMock()
    shop_resp.read.return_value = json.dumps({"shop": {"name": "Test Store"}}).encode("utf-8")
    shop_resp.__enter__.return_value = shop_resp

    locations_resp = MagicMock()
    locations_resp.read.return_value = json.dumps({
        "locations": [{"id": 998877, "name": "Warehouse", "primary": True}]
    }).encode("utf-8")
    locations_resp.__enter__.return_value = locations_resp

    product_resp = MagicMock()
    product_resp.read.return_value = json.dumps({
        "product": {
            "id": 112233,
            "title": "USB Cable",
            "variants": [
                {"id": 445566, "sku": "SKU-USB", "price": "19.99", "inventory_item_id": 778899}
            ]
        }
    }).encode("utf-8")
    product_resp.__enter__.return_value = product_resp

    inv_set_resp = MagicMock()
    inv_set_resp.read.return_value = json.dumps({"inventory_level": {"available": 50}}).encode("utf-8")
    inv_set_resp.__enter__.return_value = inv_set_resp

    with patch("urllib.request.urlopen", side_effect=[shop_resp, product_resp, locations_resp, inv_set_resp]):
        result = adapter.create_listing(
            sku="SKU-USB",
            title="USB Cable",
            description="High speed cable",
            price=Decimal("19.99"),
            quantity=50
        )

    assert result["external_listing_id"] == "shopify_112233_445566"
    assert result["product_id"] == "112233"
    assert result["variant_id"] == "445566"
    assert result["price"] == Decimal("19.99")
    assert result["quantity"] == 50
    assert result["status"] == "ACTIVE"

def test_shopify_update_price():
    adapter = LiveShopifyAdapter(credentials={
        "shop_url": "test-store.myshopify.com",
        "access_token": "shpat_test123456"
    })

    variant_resp = MagicMock()
    variant_resp.read.return_value = json.dumps({
        "variant": {"id": 445566, "price": "24.99"}
    }).encode("utf-8")
    variant_resp.__enter__.return_value = variant_resp

    with patch("urllib.request.urlopen", return_value=variant_resp):
        success = adapter.update_price("shopify_112233_445566", "SKU-USB", Decimal("24.99"))
        assert success is True

def test_shopify_withdraw_listing():
    adapter = LiveShopifyAdapter(credentials={
        "shop_url": "test-store.myshopify.com",
        "access_token": "shpat_test123456"
    })

    draft_resp = MagicMock()
    draft_resp.read.return_value = json.dumps({
        "product": {"id": 112233, "status": "draft"}
    }).encode("utf-8")
    draft_resp.__enter__.return_value = draft_resp

    with patch("urllib.request.urlopen", return_value=draft_resp):
        success = adapter.withdraw_listing("shopify_112233_445566")
        assert success is True
