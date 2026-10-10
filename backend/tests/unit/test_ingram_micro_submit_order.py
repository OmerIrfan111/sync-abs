import json
from unittest.mock import patch
import pytest

from app.adapters.suppliers.ingram_micro import IngramMicroAdapter


def _live_adapter():
    adapter = IngramMicroAdapter(credentials={
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "customer_number": "20-222222",
        "environment": "production",
    })
    return adapter


def _patch_reseller_settings(monkeypatch, complete=True):
    import app.adapters.suppliers.ingram_micro as mod
    for name, value in [
        ("RESELLER_COMPANY_NAME", "ABS Incorporated"),
        ("RESELLER_CONTACT_NAME", "Omer Irfan"),
        ("RESELLER_ADDRESS_LINE1", "123 Commerce St"),
        ("RESELLER_ADDRESS_LINE2", ""),
        ("RESELLER_CITY", "Dallas"),
        ("RESELLER_STATE", "TX"),
        ("RESELLER_POSTAL_CODE", "75201"),
        ("RESELLER_COUNTRY_CODE", "US"),
        ("RESELLER_PHONE", "2145550100"),
        ("RESELLER_EMAIL", "orders@absinc.example"),
    ]:
        monkeypatch.setattr(
            "app.core.config.settings." + name,
            value if complete else None,
        )


def test_submit_order_raises_when_reseller_profile_incomplete(monkeypatch):
    """
    Real bug found 2026-10-09: Ingram's Order Create v7 requires a real
    resellerInfo object on every order (confirmed against Ingram's own API
    reference). If this business's own RESELLER_* profile isn't configured,
    submit_order must refuse rather than send an incomplete/fabricated
    payload that Ingram would likely reject anyway.
    """
    adapter = _live_adapter()
    _patch_reseller_settings(monkeypatch, complete=False)

    with pytest.raises(ValueError) as exc:
        adapter.submit_order(
            customer_purchase_order="PO-1",
            line_items=[{"itemId": "ABC123", "orderQuantity": 1}],
            delivery_address={"street": "1 Main St", "city": "LA", "region": "CA", "postalCode": "90001", "country": "US"},
        )
    assert "reseller" in str(exc.value).lower()


def test_submit_order_payload_includes_real_reseller_and_end_user_info(monkeypatch):
    """
    Verifies the actual real Order Create v7 payload shape against Ingram's
    official API reference (resellerInfo/endUserInfo/shipToInfo/lines),
    pasted directly from Ingram's docs on 2026-10-09 — not guessed.
    """
    adapter = _live_adapter()
    _patch_reseller_settings(monkeypatch, complete=True)

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps({
                "confirmationNumber": "US-I-T-24032926562341102332",
                "message": "accepted",
            }).encode("utf-8")

    def fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    with patch.object(adapter, "get_access_token", return_value="fake-token"), \
         patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = adapter.submit_order(
            customer_purchase_order="PO-TEST-1",
            line_items=[{"itemId": "ABC123", "orderQuantity": 2}],
            delivery_address={
                "attention": "Jane Buyer",
                "street": "456 Oak Ave",
                "city": "Austin",
                "region": "TX",
                "postalCode": "78701",
                "country": "US",
                "phone": "5125550199",
                "email": "jane@buyer.example",
            },
        )

    body = captured["body"]
    assert body["customerOrderNumber"] == "PO-TEST-1"

    reseller = body["resellerInfo"]
    assert reseller["companyName"] == "ABS Incorporated"
    assert reseller["addressLine1"] == "123 Commerce St"
    assert reseller["city"] == "Dallas"
    assert reseller["email"] == "orders@absinc.example"

    end_user = body["endUserInfo"]
    assert end_user["contact"] == "Jane Buyer"
    assert end_user["addressLine1"] == "456 Oak Ave"
    assert end_user["city"] == "Austin"
    assert end_user["phoneNumber"] == "5125550199"
    assert end_user["email"] == "jane@buyer.example"

    ship_to = body["shipToInfo"]
    assert ship_to["contact"] == "Jane Buyer"
    assert ship_to["postalCode"] == "78701"

    assert body["lines"] == [{"ingramPartNumber": "ABC123", "quantity": 2}]
    assert result["confirmationNumber"] == "US-I-T-24032926562341102332"
    assert result["id"] == "US-I-T-24032926562341102332"


def test_submit_order_raises_without_live_credentials():
    adapter = IngramMicroAdapter(credentials={})
    # Force not-live regardless of real env credentials configured in this
    # deployment's .env (the constructor otherwise falls back to them).
    adapter.client_id = ""
    adapter.client_secret = ""
    with pytest.raises(ConnectionError):
        adapter.submit_order(
            customer_purchase_order="PO-1",
            line_items=[{"itemId": "X", "orderQuantity": 1}],
            delivery_address={},
        )
