import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.adapters.suppliers.td_synnex import TDSynnexAdapter
from app.adapters.registry import get_supplier_adapter


def test_td_synnex_adapter_init_from_credentials():
    creds = {
        "client_id": "sk-test-client-id",
        "client_secret": "sk-test-client-secret",
        "environment": "production"
    }
    adapter = TDSynnexAdapter(credentials=creds)
    assert adapter.is_live() is True
    assert adapter.client_id == "sk-test-client-id"
    assert adapter.client_secret == "sk-test-client-secret"
    assert adapter.environment == "production"
    assert adapter.supplier_name == "TD SYNNEX"


def test_td_synnex_adapter_missing_credentials():
    adapter = TDSynnexAdapter(credentials={})
    # If settings don't have TD SYNNEX creds in test environment:
    adapter.client_id = ""
    adapter.client_secret = ""
    assert adapter.is_live() is False
    with pytest.raises(ValueError, match="requires client_id"):
        adapter.get_access_token()


def test_td_synnex_registry_resolution():
    adapter = get_supplier_adapter(
        "TDSynnexAdapter",
        supplier_name="TD SYNNEX",
        credentials={"client_id": "test_id", "client_secret": "test_secret"}
    )
    assert isinstance(adapter, TDSynnexAdapter)
    assert adapter.client_id == "test_id"


def test_td_synnex_product_normalization():
    adapter = TDSynnexAdapter(credentials={"client_id": "k1", "client_secret": "k2"})
    raw_item = {
        "tdSynnexPartNumber": "TD-CBL-100",
        "manufacturerPartNumber": "AX-CBL-10FT",
        "upcCode": "012345678905",
        "eanCode": "0012345678905",
        "productDescription": "CAT6 Ethernet Patch Cable 10ft Blue",
        "vendorName": "Axiom",
        "category": "Cables & Connectivity",
        "pricing": {
            "customerPrice": 14.50,
            "msrp": 24.99
        },
        "inventory": {
            "totalQuantityAvailable": 120
        },
        "images": [
            "https://cdn.tdsynnex.com/images/TD-CBL-100.jpg"
        ],
        "weight": "0.5",
        "weightUnit": "lbs"
    }

    norm = adapter._normalize_product(raw_item)
    assert norm is not None
    assert norm.supplier_sku == "TD-CBL-100"
    assert norm.mpn == "AX-CBL-10FT"
    assert norm.upc == "012345678905"
    assert norm.title == "CAT6 Ethernet Patch Cable 10ft Blue"
    assert norm.brand == "Axiom"
    assert norm.category == "Cables & Connectivity"
    assert norm.cost == Decimal("14.50")
    assert norm.quantity == 120
    assert norm.stock_status == "IN_STOCK"
    assert len(norm.images) == 1
    assert norm.shipping_info.get("weight") == "0.5"


def test_td_synnex_pagination_exhaustion():
    adapter = TDSynnexAdapter(credentials={"client_id": "k1", "client_secret": "k2"})
    sample_raw_20 = {
        "PriceAvailabilityList": [
            {
                "synnexSKU": f"TD-SKU-{i}",
                "mfgPN": f"MPN-{i}",
                "price": 10.0,
                "totalQuantity": 5,
                "description": f"Item {i}",
            }
            for i in range(20)
        ]
    }

    with patch.object(adapter, "_request", return_value=sample_raw_20):
        # 20 candidate MPNs requested with limit 50 -> page size is 50, candidate count < limit -> exhausted
        prods = adapter.fetch_catalog(resume_cursor="1", filters={"limit": 50, "skus": [f"MPN-{i}" for i in range(20)]})
        assert len(prods) == 20
        assert adapter.catalog_exhausted is True
        assert adapter.next_cursor is None

    sample_raw_50 = {
        "PriceAvailabilityList": [
            {
                "synnexSKU": f"TD-SKU-{i}",
                "mfgPN": f"MPN-{i}",
                "price": 10.0,
                "totalQuantity": 5,
                "description": f"Item {i}",
            }
            for i in range(50)
        ]
    }
    with patch.object(adapter, "_request", return_value=sample_raw_50):
        # 50 candidate MPNs requested with limit 50 -> page size full -> next cursor is "2"
        prods = adapter.fetch_catalog(resume_cursor="1", filters={"limit": 50, "skus": [f"MPN-{i}" for i in range(50)]})
        assert len(prods) == 50
        assert adapter.catalog_exhausted is False
        assert adapter.next_cursor == "2"


def test_td_synnex_ground_shipping_estimate():
    adapter = TDSynnexAdapter(config={"ground_shipping_charge": "9.99"})
    ship = adapter.get_ground_shipping_estimate("TD-123")
    assert ship == Decimal("9.99")

    # Also supports default_shipping_charge from database/Rules page
    adapter_default = TDSynnexAdapter(config={"default_shipping_charge": "12.50"})
    assert adapter_default.get_ground_shipping_estimate("TD-456") == Decimal("12.50")


def test_td_synnex_submit_order_and_tracking():
    adapter = TDSynnexAdapter(credentials={"client_id": "test_id", "client_secret": "test_sec"})
    mock_order_res = {
        "orderNumber": "TDS-987654",
        "status": "SUBMITTED",
        "message": "Order accepted"
    }

    with patch.object(adapter, "_request", return_value=mock_order_res):
        res = adapter.submit_order(
            customer_purchase_order="PO-1001",
            line_items=[{"itemId": "TD-SKU-1", "orderQuantity": 2}],
            delivery_address={"street": "123 Main St", "city": "Dallas", "postalCode": "75001"}
        )
        assert res["orderNumber"] == "TDS-987654"
        assert res["status"] == "SUBMITTED"

    mock_tracking_res = {
        "trackingNumber": "1Z9999999999999999",
        "carrier": "UPS",
        "shippedDate": "2026-10-04T00:00:00Z"
    }
    with patch.object(adapter, "_request", return_value=mock_tracking_res):
        tracking = adapter.check_shipment_status("TDS-987654")
        assert tracking is not None
        assert tracking["tracking_number"] == "1Z9999999999999999"
        assert tracking["carrier"] == "UPS"

