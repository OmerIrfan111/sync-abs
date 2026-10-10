import json
from unittest.mock import patch

from app.adapters.suppliers.d_and_h import DAndHAdapter


def _live_adapter():
    return DAndHAdapter(credentials={
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "account_number": "3302610000",
        "environment": "production",
    })


def test_submit_order_payload_matches_real_dandh_schema():
    """
    Verifies the real Customer Order Management API 2.0.1 request shape,
    pasted directly from D&H's own Swagger page on 2026-10-09: top-level
    customerPurchaseOrder/shipping/deliveryAddress, and shipments[] each
    with a branch + lines[]. The per-line product key is "item" (matching
    the field name D&H's own order-tracking response uses at the identical
    structural path), not "itemId" as this adapter used before.
    """
    adapter = _live_adapter()
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps({"id": 123456, "orderNumber": 987654}).encode("utf-8")

    def fake_urlopen(req, context=None, timeout=35):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    with patch.object(adapter, "_get_headers", return_value={"Authorization": "Bearer x"}), \
         patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = adapter.submit_order(
            customer_purchase_order="PO-REAL-1",
            line_items=[{"itemId": "DH-ABC123", "orderQuantity": 2}],
            delivery_address={
                "country": "US", "city": "Harrisburg", "street": "123 State St.",
                "postalCode": "17011", "region": "PA",
                "attention": "Jane Buyer", "deliveryName": "Jane Buyer",
            },
            branch="BR02",
        )

    body = captured["body"]
    assert body["customerPurchaseOrder"] == "PO-REAL-1"
    assert body["deliveryAddress"]["address"]["city"] == "Harrisburg"
    assert body["deliveryAddress"]["address"]["postalCode"] == "17011"

    shipments = body["shipments"]
    assert len(shipments) == 1
    assert shipments[0]["branch"] == "BR02"
    assert shipments[0]["lines"] == [{"item": "DH-ABC123", "orderQuantity": 2}]

    assert result["id"] == 123456
    assert result["orderNumber"] == 987654
    # Real enum is lowercase ("ground", not "Ground") — confirmed from the
    # full OAS spec pasted 2026-10-09.
    assert body["shipping"]["serviceType"] == "ground"


def test_submit_order_omits_branch_when_not_provided():
    """
    Real schema: shipments[].branch is OPTIONAL ("D&H will select the best
    warehouse if one is not entered") — confirmed from the full OAS spec.
    When the caller doesn't pass one, it must not appear in the payload at
    all, not default to a guessed branch like the old "BR01" default did.
    """
    adapter = _live_adapter()
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps({"id": 1, "orderNumber": 2}).encode("utf-8")

    def fake_urlopen(req, context=None, timeout=35):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    with patch.object(adapter, "_get_headers", return_value={"Authorization": "Bearer x"}), \
         patch("urllib.request.urlopen", side_effect=fake_urlopen):
        adapter.submit_order(
            customer_purchase_order="PO-REAL-2",
            line_items=[{"itemId": "DH-ABC123", "orderQuantity": 1}],
            delivery_address={"country": "US", "city": "Harrisburg", "street": "1 Main", "postalCode": "17011", "region": "PA"},
        )

    assert "branch" not in captured["body"]["shipments"][0]


def test_check_shipment_status_matches_real_tracking_response_schema():
    """
    Verifies against the real OAS 3.0 spec for GET
    .../salesOrders/{id}/tracking (pasted in full 2026-10-09):
    shipments[].manifests[].trackingNumber/carrier/shipmentDate — this
    adapter's field names and nesting already matched exactly once checked
    against the real spec, confirmed here rather than just claimed.
    """
    adapter = _live_adapter()
    real_shaped_response = {
        "id": 42,
        "orderNumber": 42,
        "orderStatus": "shipped",
        "shipments": [
            {
                "branch": "BR01",
                "manifests": [
                    {
                        "shipMode": "parcel",
                        "carrier": "FedEx",
                        "trackingNumber": "794658392013",
                        "shipmentDate": "2026-10-08T14:00:00Z",
                    }
                ],
            }
        ],
    }

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps(real_shaped_response).encode("utf-8")

    with patch.object(adapter, "_get_headers", return_value={"Authorization": "Bearer x"}), \
         patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = adapter.check_shipment_status("42")

    assert result["tracking_number"] == "794658392013"
    assert result["carrier"] == "FedEx"
    assert result["shipped_at"] == "2026-10-08T14:00:00Z"


def test_check_shipment_status_returns_none_when_no_manifest_yet():
    adapter = _live_adapter()

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps({"id": 1, "shipments": [{"branch": "BR01", "manifests": []}]}).encode("utf-8")

    with patch.object(adapter, "_get_headers", return_value={"Authorization": "Bearer x"}), \
         patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = adapter.check_shipment_status("1")

    assert result is None
