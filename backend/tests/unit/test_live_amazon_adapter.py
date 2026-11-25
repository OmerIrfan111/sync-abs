from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app.adapters.marketplaces.live_amazon import LiveAmazonAdapter


def _adapter():
    adapter = LiveAmazonAdapter(credentials={"seller_id": "SELLER1"})
    patch.object(adapter, "_get_headers", return_value={"x-amz-access-token": "tok"}).start()
    return adapter


def test_update_price_raises_on_real_failure_instead_of_returning_false():
    """
    Real bug fixed 2026-10-22: update_price() used to catch its own HTTP
    failure and return False instead of raising. Every caller in
    listing_service.py (reactivate_listing_on_marketplace,
    sync_all_listings_for_product, etc.) relies entirely on the exception
    propagating to avoid marking a listing ACTIVE/synced after a real
    marketplace call actually failed — eBay/Walmart/Shopify's equivalents
    all raise. A silently swallowed False here would have looked like a
    successful price push everywhere upstream.
    """
    adapter = _adapter()
    with patch("urllib.request.urlopen", side_effect=ConnectionError("timeout")):
        with pytest.raises(ConnectionError):
            adapter.update_price("amzn_x", "SKU1", Decimal("19.99"))


def test_update_inventory_raises_on_real_failure_instead_of_returning_false():
    adapter = _adapter()
    with patch("urllib.request.urlopen", side_effect=ConnectionError("timeout")):
        with pytest.raises(ConnectionError):
            adapter.update_inventory("amzn_x", "SKU1", 5)


def test_update_price_returns_true_on_real_success():
    adapter = _adapter()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert adapter.update_price("amzn_x", "SKU1", Decimal("19.99")) is True


def test_update_inventory_returns_true_on_real_success():
    adapter = _adapter()
    mock_resp = MagicMock()
    mock_resp.status = 204
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert adapter.update_inventory("amzn_x", "SKU1", 5) is True
