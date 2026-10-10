import json
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.adapters.marketplaces.live_walmart import LiveWalmartAdapter
from app.adapters.registry import get_marketplace_adapter


def test_walmart_adapter_init():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret",
        "environment": "production"
    })
    assert adapter.client_id == "test-uuid-id"
    assert adapter.client_secret == "test-secret"
    assert adapter.environment == "production"
    assert adapter.base_url == "https://marketplace.walmartapis.com"


def test_walmart_registry_resolution():
    adapter = get_marketplace_adapter("LiveWalmartAdapter", credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    assert isinstance(adapter, LiveWalmartAdapter)
    assert adapter.client_id == "test-uuid-id"


def test_walmart_get_access_token():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "access_token": "wm_test_token_12345",
        "token_type": "Bearer",
        "expires_in": 900
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        token = adapter.get_access_token()
        assert token == "wm_test_token_12345"
        # Second call uses cached token without network request
        assert adapter.get_access_token() == "wm_test_token_12345"


def test_walmart_test_connection():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })

    with patch.object(adapter, "_request", return_value={"totalItems": 67, "ItemResponse": []}):
        assert adapter.test_connection() is True


def test_walmart_retire_item_calls_real_delete_endpoint():
    """
    Real doc confirmed (Walmart's own "Retire an item" reference):
    DELETE /v3/items/{sku}. Distinct from withdraw_listing (zero-stock
    pause, reversible) — this is permanent removal from Walmart's catalog.
    """
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", return_value={}) as mock_req:
        res = adapter.retire_item("SKU-123")
        assert res is True
        mock_req.assert_called_once_with("/v3/items/SKU-123", method="DELETE")


def test_walmart_retire_item_encodes_special_characters():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", return_value={}) as mock_req:
        adapter.retire_item("SKU/with#special:chars")
        mock_req.assert_called_once_with("/v3/items/SKU%2Fwith%23special%3Achars", method="DELETE")


def test_walmart_retire_item_raises_on_failure():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", side_effect=RuntimeError("500 server error")):
        with pytest.raises(RuntimeError):
            adapter.retire_item("SKU-123")


def test_walmart_update_inventory_and_price():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })

    with patch.object(adapter, "_request", return_value={"status": "OK"}) as mock_req:
        res_inv = adapter.update_inventory("SKU-123", "SKU-123", 15)
        assert res_inv is True
        mock_req.assert_called_with("/v3/inventory", method="PUT", json_data={
            "sku": "SKU-123",
            "quantity": {"unit": "EACH", "amount": 15}
        })

    with patch.object(adapter, "_request", return_value={"status": "OK"}) as mock_req:
        res_price = adapter.update_price("SKU-123", "SKU-123", Decimal("29.99"))
        assert res_price is True
        mock_req.assert_called_with("/v3/prices", method="PUT", json_data={
            "sku": "SKU-123",
            "pricing": [
                {
                    "currentPriceType": "BASE",
                    "currentPrice": {"currency": "USD", "amount": 29.99}
                }
            ]
        })


def test_walmart_item_match_feed_payload_matches_real_sample():
    """
    Payload shape locked in against Walmart's own real MP_ITEM_MATCH sample
    feed files: productIdType must be "GTIN" (not "UPC") with a zero-padded
    14-digit productId (from the v5.x sample), and the header must include
    "sellingChannel": "mpsetupbymatch" / "processMode" / "subset" (from the
    v4.2 sample — fields totally absent from the v5.x sample we built against
    first). Missing these caused Walmart to reject the whole feed file
    outright (ERR_INT_SYS_0801003, itemsReceived: 0) before any item-level
    validation even ran, which is why every real submission went nowhere.
    """
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })

    with patch.object(adapter, "_request", return_value={"feedId": "FEED123"}) as mock_req:
        adapter.submit_item_match_feed(
            sku="5TM469",
            upc="051128788530",
            price=Decimal("30.00"),
            weight_lbs=1.5,
            main_image_url="https://example.com/photo.jpg",
        )
        mock_req.assert_called_once_with(
            "/v3/feeds",
            method="POST",
            params={"feedType": "MP_ITEM_MATCH"},
            json_data={
                "MPItemFeedHeader": {
                    "processMode": "REPLACE",
                    "subset": "EXTERNAL",
                    "locale": "en",
                    "sellingChannel": "mpsetupbymatch",
                    "version": "4.2",
                },
                "MPItem": [{"Item": {
                    "sku": "5TM469",
                    "productIdentifiers": {
                        "productIdType": "GTIN",
                        "productId": "00051128788530",
                    },
                    "ShippingWeight": 1.5,
                    "price": 30.00,
                    "condition": "New",
                    "mainImageUrl": "https://example.com/photo.jpg",
                }}],
            },
            timeout=30.0,
        )


def test_walmart_search_catalog_by_gtin_found():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", return_value={"items": [{"itemId": "123", "description": "Real match"}]}) as mock_req:
        items = adapter.search_walmart_catalog_by_gtin("804467484164")
        assert len(items) == 1
        mock_req.assert_called_once_with(
            "/v3/items/walmart/search", method="GET", params={"gtin": "804467484164"}
        )


def test_walmart_search_catalog_by_gtin_not_found():
    """
    Real-world confirmed: this endpoint's own index is flaky (3 identical
    calls for the same GTIN returned 1 match, then 0, then 0). A single
    empty result must not be trusted — retried 3x before concluding "no
    match", so this test patches time.sleep to keep it fast and asserts the
    real retry count.
    """
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", return_value={"items": []}) as mock_req, \
         patch("time.sleep"):
        items = adapter.search_walmart_catalog_by_gtin("767041063264")
        assert items == []
        assert mock_req.call_count == 3


def test_walmart_search_catalog_by_gtin_retries_until_found():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(
        adapter, "_request",
        side_effect=[{"items": []}, {"items": [{"itemId": "292245307"}]}]
    ) as mock_req, patch("time.sleep"):
        items = adapter.search_walmart_catalog_by_gtin("841280153570")
        assert len(items) == 1
        assert mock_req.call_count == 2


def test_walmart_get_item_spec_payload():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", return_value={"schema": {}}) as mock_req:
        adapter.get_item_spec(["Network Switches", "Network Cables"])
        mock_req.assert_called_once_with(
            "/v3/items/spec",
            method="POST",
            json_data={
                "feedType": "MP_ITEM",
                "version": "5.0.20250121-19_24_23-api",
                "productTypes": ["Network Switches", "Network Cables"],
            },
        )


def test_walmart_submit_new_item_feed_payload():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", return_value={"feedId": "FEED999"}) as mock_req:
        adapter.submit_new_item_feed(
            sku="TEST-SW-01",
            upc="051128788530",
            price=Decimal("150.00"),
            weight_lbs=3.5,
            product_type="Network Switches",
            visible_attributes={
                "productName": "8-Port Gigabit PoE Switch",
                "brand": "Axiom",
                "shortDescription": "Managed 8-port gigabit switch with PoE.",
            },
        )
        mock_req.assert_called_once_with(
            "/v3/feeds",
            method="POST",
            params={"feedType": "MP_ITEM"},
            json_data={
                "MPItemFeedHeader": {
                    "businessUnit": "WALMART_US",
                    "locale": "en",
                    "version": "5.0.20250121-19_24_23-api",
                },
                "MPItem": [{
                    "Orderable": {
                        "productIdentifiers": {
                            "productIdType": "GTIN",
                            "productId": "00051128788530",
                        },
                        "sku": "TEST-SW-01",
                        "specProductType": "Network Switches",
                        "price": 150.00,
                        "ShippingWeight": 3.5,
                    },
                    "Visible": {
                        "Network Switches": {
                            "productName": "8-Port Gigabit PoE Switch",
                            "brand": "Axiom",
                            "shortDescription": "Managed 8-port gigabit switch with PoE.",
                            "condition": "New",
                        },
                    },
                }],
            },
            timeout=30.0,
        )


def test_walmart_submit_new_item_feed_requires_visible_attributes():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    import pytest
    with pytest.raises(ValueError, match="no category-specific content"):
        adapter.submit_new_item_feed(
            sku="TEST-SW-02", upc="051128788530", price=Decimal("1"),
            weight_lbs=1.0, product_type="Network Switches", visible_attributes={},
        )


def test_walmart_fetch_orders_normalization():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })

    mock_raw_orders = {
        "list": {
            "elements": {
                "order": [
                    {
                        "purchaseOrderId": "PO-WM-999",
                        "customerOrderId": "CO-WM-888",
                        "customerEmailId": "buyer@relay.walmart.com",
                        "orderDate": 1791151559000,
                        "shippingInfo": {
                            "phone": "555-123-4567",
                            "postalAddress": {
                                "name": "Jane Doe",
                                "address1": "456 Elm St",
                                "city": "Austin",
                                "state": "TX",
                                "postalCode": "78701",
                                "country": "USA"
                            }
                        },
                        "orderLines": {
                            "orderLine": [
                                {
                                    "lineNumber": "1",
                                    "item": {"sku": "WM-SKU-1", "productName": "Widget Pro"},
                                    "orderLineQuantity": {"amount": "2"},
                                    "charges": {
                                        "charge": [
                                            {"chargeType": "PRODUCT", "chargeAmount": {"amount": 59.98}}
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }

    with patch.object(adapter, "_request", return_value=mock_raw_orders):
        orders = adapter.fetch_orders()
        assert len(orders) == 1
        o = orders[0]
        assert o["order_id"] == "PO-WM-999"
        assert o["buyer_name"] == "Jane Doe"
        assert o["order_total"] == Decimal("59.98")
        assert len(o["items"]) == 1
        assert o["items"][0]["sku"] == "WM-SKU-1"
        assert o["items"][0]["quantity"] == 2


def test_walmart_update_tracking():
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })

    with patch.object(adapter, "_request", return_value={"status": "OK"}) as mock_req:
        res = adapter.update_tracking("PO-WM-999", "1Z9999999999999999", "UPS")
        assert res is True
        assert mock_req.call_args[0][0] == "/v3/orders/PO-WM-999/shipping"
        # No real line numbers supplied -> honest fallback to "1", not silently wrong
        lines = mock_req.call_args[1]["json_data"]["orderShipment"]["orderLines"]["orderLine"]
        assert [l["lineNumber"] for l in lines] == ["1"]


def test_walmart_update_tracking_multi_item_order_marks_every_real_line():
    """
    Real bug found 2026-10-08: hardcoded lineNumber "1" meant a multi-item
    Walmart order only ever got its first line marked shipped on Walmart's
    side, even though the call reported success and the whole order was
    marked SHIPPED locally. Fixed by threading real per-line identifiers
    (Walmart's own orderLine lineNumbers, captured at order ingestion) through.
    """
    adapter = LiveWalmartAdapter(credentials={
        "client_id": "test-uuid-id",
        "client_secret": "test-secret"
    })
    with patch.object(adapter, "_request", return_value={"status": "OK"}) as mock_req:
        adapter.update_tracking(
            "PO-WM-888", "1Z8888888888888888", "FedEx", line_item_ids=["1", "2", "3"]
        )
        lines = mock_req.call_args[1]["json_data"]["orderShipment"]["orderLines"]["orderLine"]
        assert [l["lineNumber"] for l in lines] == ["1", "2", "3"]
        for line in lines:
            assert line["orderLineStatuses"]["orderLineStatus"][0]["trackingInfo"]["carrierName"]["carrier"] == "FedEx"
