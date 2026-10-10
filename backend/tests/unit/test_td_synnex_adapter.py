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


def test_td_synnex_ground_shipping_estimate_uses_live_quote_when_available():
    adapter = TDSynnexAdapter(
        credentials={"client_id": "test_id", "client_secret": "test_sec"},
        config={"default_shipping_charge": "99.00"},
    )
    live_response = {
        "FreightQuoteResponse": {
            "Shipment": [
                {
                    "AvailableShipMethods": [
                        {"Code": "UPG", "Freight": 6.79},
                        {"Code": "UPS2", "Freight": 15.50},
                    ]
                }
            ]
        }
    }
    with patch.object(adapter, "_request", return_value=live_response):
        ship = adapter.get_ground_shipping_estimate("TD-123", destination_zip="99201")
    # Picks the cheapest live ship method, not the configured flat-rate fallback
    assert ship == Decimal("6.79")


def test_td_synnex_ground_shipping_estimate_ignores_non_customer_methods():
    """
    Real TD SYNNEX response observed in production: alongside real carrier
    rates, it included a "LABS" (LAB SHIP - PAPER TRAIL ONLY) internal code
    at $0.00 Freight, which a naive min() would wrongly pick as "the cheapest
    shipping option" when it isn't a real customer-facing method at all.
    Also verifies ground service is preferred over cheaper non-ground options.
    """
    adapter = TDSynnexAdapter(
        credentials={"client_id": "test_id", "client_secret": "test_sec"},
        config={"default_shipping_charge": "99.00"},
    )
    live_response = {
        "FreightQuoteResponse": {
            "Shipment": [
                {
                    "AvailableShipMethods": [
                        {"Code": "LABS", "ShipMethodDescription": "LAB SHIP - PAPER TRAIL ONLY", "Freight": 0.0},
                        {"Code": "FG", "ShipMethodDescription": "FedEx Ground", "Freight": 13.10},
                        {"Code": "UP", "ShipMethodDescription": "UPS Ground", "Freight": 13.25},
                        {"Code": "F2", "ShipMethodDescription": "FedEx 2 Day", "Freight": 29.38},
                    ]
                }
            ]
        }
    }
    with patch.object(adapter, "_request", return_value=live_response):
        ship = adapter.get_ground_shipping_estimate("2058146", destination_zip="99201")
    assert ship == Decimal("13.10")


def test_td_synnex_ground_shipping_estimate_falls_back_on_live_error():
    adapter = TDSynnexAdapter(
        credentials={"client_id": "test_id", "client_secret": "test_sec"},
        config={"default_shipping_charge": "12.50"},
    )
    with patch.object(adapter, "_request", side_effect=RuntimeError("timeout")):
        ship = adapter.get_ground_shipping_estimate("TD-123", destination_zip="99201")
    assert ship == Decimal("12.50")


def test_td_synnex_ground_shipping_estimate_falls_back_on_business_error():
    adapter = TDSynnexAdapter(
        credentials={"client_id": "test_id", "client_secret": "test_sec"},
        config={"default_shipping_charge": "12.50"},
    )
    business_error_response = {
        "FreightQuoteResponse": {
            "ErrorMessage": "InvalidSynnexSKU",
            "ErrorDetail": "SKU not found"
        }
    }
    with patch.object(adapter, "_request", return_value=business_error_response):
        ship = adapter.get_ground_shipping_estimate("TD-123", destination_zip="99201")
    assert ship == Decimal("12.50")


def test_td_synnex_submit_order_and_tracking():
    """
    Real schema (confirmed against TD SYNNEX's own API reference, 2026-10-09):
    the order confirmation lives under OrderResponse.Items.Item[], each with
    its own real OrderNumber — not a flat top-level orderNumber/status as
    this test originally assumed before that doc was available. See also
    test_td_synnex_submit_order.py for dedicated payload-shape coverage.
    """
    adapter = TDSynnexAdapter(credentials={"client_id": "test_id", "client_secret": "test_sec"})
    mock_order_res = {
        "OrderResponse": {
            "PONumber": "PO-1001",
            "Code": "accepted",
            "SynnexReferenceNumber": "REF-1001",
            "Items": {
                "Item": [
                    {"lineNumber": 1, "SKU": "TD-SKU-1", "OrderQuantity": 2, "Code": "accepted", "OrderNumber": 987654},
                ]
            },
        },
        "errorMessage": None,
    }

    with patch.object(adapter, "_request", return_value=mock_order_res):
        res = adapter.submit_order(
            customer_purchase_order="PO-1001",
            line_items=[{"itemId": "TD-SKU-1", "orderQuantity": 2, "unitPrice": "10.00"}],
            delivery_address={"street": "123 Main St", "city": "Dallas", "postalCode": "75001"}
        )
        assert res["orderNumber"] == "987654"
        assert res["status"] == "accepted"

    # Real GetOrderStatus schema (confirmed 2026-10-09): tracking lives at
    # lines[].subLines[].tracking[], never at the top level.
    mock_tracking_res = [
        {
            "orderNumber": "987654",
            "lines": [
                {
                    "lineNumber": "1",
                    "subLines": [
                        {
                            "shipDate": "10/04/2026 00:00:00",
                            "tracking": [
                                {"trackingNumber": "1Z9999999999999999", "shippingMethod": "UPSN"},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    with patch.object(adapter, "_request", return_value=mock_tracking_res):
        tracking = adapter.check_shipment_status("TDS-987654")
        assert tracking is not None
        assert tracking["tracking_number"] == "1Z9999999999999999"
        assert tracking["carrier"] == "UPSN"


def test_td_synnex_tracking_from_lines():
    """
    Real schema (confirmed 2026-10-09): tracking numbers are nested at
    lines[].subLines[].tracking[], not directly on the line — a prior
    version of this adapter only checked a flat line.trackingNumber field,
    which doesn't exist in the real response, so it would never have found
    real tracking data.
    """
    adapter = TDSynnexAdapter(credentials={"client_id": "test_id", "client_secret": "test_sec"})
    mock_order_status_lines = [
        {
            "orderNumber": "12345",
            "lines": [
                {
                    "lineNumber": "1",
                    "subLines": [
                        {
                            "shipDate": "10/04/2026 12:00:00",
                            "tracking": [
                                {"trackingNumber": "1Z8888888888888888", "shippingMethod": "FDEG"},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    with patch.object(adapter, "_request", return_value=mock_order_status_lines):
        tracking = adapter.check_shipment_status("12345")
        assert tracking is not None
        assert tracking["tracking_number"] == "1Z8888888888888888"
        assert tracking["carrier"] == "FDEG"
        assert tracking["shipped_at"] == "10/04/2026 12:00:00"


def test_td_synnex_tracking_never_fabricates_carrier_when_unknown():
    """
    Real incident class fixed 2026-10-09: this adapter used to default the
    carrier to a fabricated "UPS" when no real carrier/method was found.
    Never fabricate — if shippingMethod is genuinely absent, surface an
    empty string, not a guess.
    """
    adapter = TDSynnexAdapter(credentials={"client_id": "test_id", "client_secret": "test_sec"})
    mock_res = [
        {
            "orderNumber": "55555",
            "lines": [
                {"subLines": [{"tracking": [{"trackingNumber": "TRK-NO-METHOD"}]}]}
            ],
        }
    ]
    with patch.object(adapter, "_request", return_value=mock_res):
        tracking = adapter.check_shipment_status("55555")
    assert tracking["tracking_number"] == "TRK-NO-METHOD"
    assert tracking["carrier"] == ""


def test_td_synnex_tracking_returns_none_on_not_found_error():
    adapter = TDSynnexAdapter(credentials={"client_id": "test_id", "client_secret": "test_sec"})
    with patch.object(adapter, "_request", return_value=[{"errorMessage": "not found!"}]):
        tracking = adapter.check_shipment_status("99999")
    assert tracking is None


def test_td_synnex_fetch_inventory_batch():
    adapter = TDSynnexAdapter(credentials={"client_id": "test_id", "client_secret": "test_sec"})
    mock_availability = {
        "PriceAvailabilityList": [
            {"synnexSKU": "123456", "mfgPN": "PART-A", "totalQuantity": 42},
            {"synnexSKU": "789012", "mfgPN": "PART-B", "totalQuantity": 0},
        ]
    }
    with patch.object(adapter, "_request", return_value=mock_availability):
        inv = adapter.fetch_inventory(["123456", "PART-B"])
        assert inv["123456"] == 42
        assert inv["PART-A"] == 42
        assert inv["789012"] == 0
        assert inv["PART-B"] == 0


