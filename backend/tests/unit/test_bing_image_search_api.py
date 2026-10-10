"""
Tests for BingImageSearchAPIProvider — the official, non-scraped Bing Image
Search API added 2026-10-10 after live-confirming that the scraped
BingWebImageSearchProvider is subject to an anti-scraping countermeasure:
the identical query sent 3 times returned 3 different, unrelated results
each time (real test, not simulated), while the same query in a real
browser returned consistent, correct results every time.
"""
import json
from unittest.mock import patch

from app.adapters.suppliers.image_search_provider import BingImageSearchAPIProvider


def _provider():
    return BingImageSearchAPIProvider(api_key="test-key", endpoint="https://api.bing.microsoft.com/v7.0/images/search")


def test_search_web_images_returns_real_shaped_results():
    provider = _provider()
    mock_response = {
        "value": [
            {
                "contentUrl": "https://example.com/hp-battery-808450-002.jpg",
                "name": "Replacement battery for HP ZO04XL 15.2V 64Wh",
                "hostPageUrl": "https://www.laptopbattery.com/hp-808450-002",
            },
            {
                "contentUrl": "https://example.com/unrelated.jpg",
                "name": "Completely unrelated stock photo",
                "hostPageUrl": "https://example.com/stock",
            },
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps(mock_response).encode("utf-8")

    captured = {}

    def fake_urlopen(req, timeout=8.0):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        results = provider.search_web_images("HP BATTERY 808450-002 ZL04XL", max_results=10)

    assert len(results) == 1
    assert results[0].image_url == "https://example.com/hp-battery-808450-002.jpg"
    assert "Ocp-Apim-Subscription-Key" in captured["headers"] or "Ocp-apim-subscription-key" in captured["headers"]
    assert "api.bing.microsoft.com" in captured["url"]


def test_search_web_images_returns_empty_without_api_key():
    provider = BingImageSearchAPIProvider(api_key=None)
    assert provider.search_web_images("anything") == []


def test_search_by_upc_raises_on_transient_failure():
    import pytest
    provider = _provider()
    with patch("urllib.request.urlopen", side_effect=ConnectionError("timeout")):
        with pytest.raises(ConnectionError):
            provider.search_by_upc("012345678905", brand="HP")


def test_search_by_upc_returns_empty_without_api_key():
    provider = BingImageSearchAPIProvider(api_key=None)
    assert provider.search_by_upc("012345678905") == []


def test_get_image_search_provider_resolves_bing_api():
    from app.adapters.suppliers.image_search_provider import get_image_search_provider
    provider = get_image_search_provider("bing_api")
    assert isinstance(provider, BingImageSearchAPIProvider)
