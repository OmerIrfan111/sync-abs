import json
from unittest.mock import patch

from app.adapters.suppliers.ingram_micro import IngramMicroAdapter


def _live_adapter():
    return IngramMicroAdapter(credentials={
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "customer_number": "20-222222",
        "environment": "production",
    })


def test_check_shipment_status_resolves_real_tracking_via_two_step_lookup():
    """
    Verifies the real two-step Ingram Micro v7 lookup this adapter's own
    docstring claims is confirmed: Search Orders v7 (confirmationNumber ->
    ingramOrderNumber) then Get Order Details v7 for the real nested
    tracking path lines[].shipmentDetails[].carrierDetails[].trackingDetails
    (a single object in V7, not an array — confirmed from Ingram's real
    "What's New in V7" changelog pasted earlier this session).
    """
    adapter = _live_adapter()

    search_response = {
        "orders": [
            {
                "ingramOrderNumber": "20-T777Y",
                "ingramOrderDate": "2026-10-05T01:11:43+00:00",
                "orderStatus": "DELIVERED",
                "eta": "",
                "subOrders": [],
            }
        ]
    }
    details_response = {
        "lines": [
            {
                "shipmentDetails": [
                    {
                        "shippedDateTime": "2026-10-06T00:00:00Z",
                        "carrierDetails": [
                            {
                                "carrierName": "UPS",
                                "shippedDate": "2026-10-06T00:00:00Z",
                                "deliveredDate": "2026-10-08T00:00:00Z",
                                "trackingDetails": {
                                    "trackingNumber": "1Z123456789",
                                    "trackingUrl": "https://ups.com/track/1Z123456789",
                                },
                            }
                        ],
                    }
                ]
            }
        ]
    }

    call_count = {"n": 0}

    class FakeResponse:
        def __init__(self, body):
            self.body = body
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps(self.body).encode("utf-8")

    def fake_urlopen(req, timeout=25):
        call_count["n"] += 1
        if call_count["n"] == 1:
            assert "orders/search" in req.full_url
            assert "confirmationNumber=US-I-T-123" in req.full_url
            return FakeResponse(search_response)
        else:
            assert "orders/20-T777Y" in req.full_url
            return FakeResponse(details_response)

    with patch.object(adapter, "get_access_token", return_value="fake-token"), \
         patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = adapter.check_shipment_status("US-I-T-123")

    assert result["ingram_order_number"] == "20-T777Y"
    assert result["order_status"] == "DELIVERED"
    assert result["tracking_number"] == "1Z123456789"
    assert result["tracking_url"] == "https://ups.com/track/1Z123456789"
    assert result["carrier"] == "UPS"
    assert result["shipped_at"] == "2026-10-06T00:00:00Z"
    assert result["delivered_at"] == "2026-10-08T00:00:00Z"


def test_check_shipment_status_returns_none_when_not_found():
    adapter = _live_adapter()

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps({"orders": []}).encode("utf-8")

    with patch.object(adapter, "get_access_token", return_value="fake-token"), \
         patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = adapter.check_shipment_status("US-I-T-UNKNOWN")

    assert result is None
