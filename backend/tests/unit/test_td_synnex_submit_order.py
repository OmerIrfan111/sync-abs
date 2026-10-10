from unittest.mock import patch
import pytest

from app.adapters.suppliers.td_synnex import TDSynnexAdapter


def _live_adapter():
    return TDSynnexAdapter(credentials={
        "client_id": "test-key",
        "client_secret": "test-secret",
        "account_number": "813367",
        "environment": "production",
    })


def test_submit_order_payload_matches_real_td_synnex_schema():
    """
    Verifies the real SubmitPO request shape, pasted directly from TD
    SYNNEX's own Partner API reference on 2026-10-09 — PascalCase field
    names nested under OrderRequest, items under Items.Item[] (not a flat
    "lines" array), and DropShipFlag/UnitPrice both present. A prior
    version of this adapter used completely different field names/casing
    and never sent UnitPrice at all, which real SubmitPO requires on every
    line — would have failed 100% of real submissions, never caught because
    this was never exercised with real credentials.
    """
    adapter = _live_adapter()
    captured = {}

    def fake_request(url, method="GET", params=None, json_data=None, **kwargs):
        captured["url"] = url
        captured["body"] = json_data
        return {
            "version": "3.1",
            "OrderResponse": {
                "PONumber": "PO-TEST-1",
                "Code": "accepted",
                "SynnexReferenceNumber": "REF-9988",
                "Items": {
                    "Item": [
                        {
                            "lineNumber": 1, "SKU": "108725", "OrderQuantity": 2,
                            "Code": "accepted", "OrderNumber": 16351210, "OrderType": "SO",
                        }
                    ]
                },
                "ErrorMessage": None,
            },
            "errorMessage": None,
        }

    with patch.object(adapter, "_request", side_effect=fake_request):
        result = adapter.submit_order(
            customer_purchase_order="PO-TEST-1",
            line_items=[{"itemId": "108725", "orderQuantity": 2, "unitPrice": "7.47"}],
            delivery_address={
                "deliveryName": "Jane Buyer", "street": "123 Main St",
                "city": "Fremont", "region": "CA", "postalCode": "94539", "country": "US",
            },
        )

    body = captured["body"]
    assert body["version"] == "3.1"
    order_request = body["OrderRequest"]
    assert order_request["PONumber"] == "PO-TEST-1"
    assert order_request["DropShipFlag"] == "Y"

    ship_to = order_request["Shipment"]["ShipTo"]
    assert ship_to["AddressName1"] == "Jane Buyer"
    assert ship_to["AddressLine1"] == "123 Main St"
    assert ship_to["City"] == "Fremont"
    assert ship_to["State"] == "CA"
    assert ship_to["ZipCode"] == "94539"

    items = order_request["Items"]["Item"]
    assert items == [{"lineNumber": 1, "SKU": "108725", "UnitPrice": "7.47", "OrderQuantity": "2"}]

    assert result["id"] == "16351210"
    assert result["orderNumber"] == "16351210"
    assert result["synnexReferenceNumber"] == "REF-9988"
    assert result["status"] == "accepted"


def test_submit_order_raises_when_line_missing_unit_price():
    """Real schema requires UnitPrice on every line — must refuse, not fabricate or omit."""
    adapter = _live_adapter()
    with pytest.raises(ValueError) as exc:
        adapter.submit_order(
            customer_purchase_order="PO-2",
            line_items=[{"itemId": "108725", "orderQuantity": 1}],
            delivery_address={},
        )
    assert "unitprice" in str(exc.value).lower()


def test_submit_order_raises_on_rejected_line():
    adapter = _live_adapter()

    def fake_request(url, method="GET", params=None, json_data=None, **kwargs):
        return {
            "OrderResponse": {
                "Code": "rejected",
                "Items": {"Item": [{"lineNumber": 1, "Code": "rejected", "Reason": "InvalidSynnexSKU"}]},
            },
            "errorMessage": None,
        }

    with patch.object(adapter, "_request", side_effect=fake_request):
        with pytest.raises(RuntimeError) as exc:
            adapter.submit_order(
                customer_purchase_order="PO-3",
                line_items=[{"itemId": "BAD-SKU", "orderQuantity": 1, "unitPrice": "1.00"}],
                delivery_address={},
            )
    assert "rejected" in str(exc.value).lower()


def test_submit_order_raises_without_live_credentials():
    adapter = TDSynnexAdapter(credentials={})
    adapter.client_id = ""
    adapter.client_secret = ""
    with pytest.raises(ConnectionError):
        adapter.submit_order(
            customer_purchase_order="PO-4",
            line_items=[{"itemId": "X", "orderQuantity": 1, "unitPrice": "1.00"}],
            delivery_address={},
        )
