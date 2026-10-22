from decimal import Decimal
from unittest.mock import patch

import pytest

from app.adapters.suppliers.ma_labs import MaLabsAdapter
from app.adapters.registry import get_supplier_adapter


def test_ma_labs_adapter_init_from_credentials():
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    assert adapter.is_live() is True
    assert adapter.username == "basit@ibswireless.com"
    assert adapter.supplier_name == "Ma Labs"


def test_ma_labs_adapter_missing_credentials():
    adapter = MaLabsAdapter(credentials={})
    adapter.username = ""
    adapter.password = ""
    assert adapter.is_live() is False
    with pytest.raises(ValueError, match="requires username"):
        adapter._request("https://online.malabs.com/mws/items/")


def test_ma_labs_registry_resolution():
    adapter = get_supplier_adapter(
        "MaLabsAdapter",
        supplier_name="Ma Labs",
        credentials={"username": "basit@ibswireless.com", "password": "secret"},
    )
    assert isinstance(adapter, MaLabsAdapter)
    assert adapter.username == "basit@ibswireless.com"


def test_ma_labs_fetch_catalog_real_response_shape():
    """
    Real captured MWS response (2026-10-22, GET /mws/items/) — exercises the
    adapter against the actual field names Ma Labs returns, not a guess:
    item_no (sku), upc_code, manufacturer_no (mpn), manufacturer (brand),
    product_name (title), price (cost), and inventory as a dict keyed by
    warehouse location code whose values sum to the real total quantity.
    """
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    sample_response = {
        "count": 6799,
        "next": "https://online.malabs.com/mws/items/?limit=10&offset=10",
        "previous": None,
        "results": [
            {
                "list_no": "00003",
                "item_no": "PM9B1256G",
                "upc_code": "",
                "manufacturer_no": "MZVL4256HBJD-00B07",
                "manufacturer": "SAMSUNGOEM",
                "category": "SSD",
                "product_name": "Samsung PM9B1 MZVL4256HBJD-00B07 256 GB M.2 PCIe 4.0 x4 (NVMe) SSD | SKU PM9B1256G",
                "price": 76.22,
                "instant_rebate": "",
                "instant_rebate_item_no": "",
                "weight": 0.24,
                "unit": 160,
                "length": 23.0,
                "width": 17.0,
                "height": 10.0,
                "package": "BULK",
                "specorder": "N",
                "is_domestic_only": "N",
                "inventory": {"": 1},
            },
            {
                "list_no": "00015",
                "item_no": "PM16537T6G",
                "upc_code": "",
                "manufacturer_no": "MZILG7T6HBLA-00A07",
                "manufacturer": "SAMSUNGOEM",
                "category": "SSD",
                "product_name": "Samsung PM1653 MZILG7T6HBLA-00A07 7.68 TB Solid State Drive - 2.5\" Internal - SAS (24Gb/s SAS) | SKU PM16537T6G",
                "price": 6040.95,
                "instant_rebate": "",
                "instant_rebate_item_no": "",
                "weight": 0.54,
                "unit": 48,
                "length": 24.0,
                "width": 17.0,
                "height": 10.0,
                "package": "BULK",
                "specorder": "Y",
                "is_domestic_only": "N",
                "inventory": {"": 56, "L": 0, "M": 0},
            },
        ],
    }

    with patch.object(adapter, "_request", return_value=sample_response):
        products = adapter.fetch_catalog()

    assert len(products) == 2

    p1 = next(p for p in products if p.supplier_sku == "PM9B1256G")
    assert p1.mpn == "MZVL4256HBJD-00B07"
    assert p1.brand == "SAMSUNGOEM"
    assert p1.category == "SSD"
    assert p1.cost == Decimal("76.22")
    assert p1.quantity == 1
    assert p1.stock_status == "IN_STOCK"
    assert p1.upc is None  # real response had an empty upc_code, never fabricated

    p2 = next(p for p in products if p.supplier_sku == "PM16537T6G")
    # Real multi-location inventory dict ({"": 56, "L": 0, "M": 0}) sums to 56
    assert p2.quantity == 56
    assert p2.stock_status == "IN_STOCK"
    assert p2.shipping_info["weight_lbs"] == 0.54
    assert p2.shipping_info["unit_pack_qty"] == 48

    # The real "next" URL is trusted directly as the resume cursor
    assert adapter.next_cursor == "https://online.malabs.com/mws/items/?limit=10&offset=10"
    assert adapter.catalog_exhausted is False


def test_ma_labs_fetch_catalog_exhausted_when_no_next():
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    sample_response = {
        "count": 1,
        "next": None,
        "previous": "https://online.malabs.com/mws/items/?limit=10&offset=0",
        "results": [
            {
                "item_no": "LASTITEM",
                "upc_code": "012345678905",
                "manufacturer_no": "MPN-X",
                "manufacturer": "Acme",
                "category": "Networking",
                "product_name": "Acme Widget",
                "price": 9.99,
                "weight": 0.1,
                "unit": 1,
                "inventory": {"": 0},
            }
        ],
    }
    with patch.object(adapter, "_request", return_value=sample_response):
        products = adapter.fetch_catalog()

    assert len(products) == 1
    assert products[0].quantity == 0
    assert products[0].stock_status == "OUT_OF_STOCK"
    assert products[0].upc == "012345678905"
    assert adapter.next_cursor is None
    assert adapter.catalog_exhausted is True


def test_ma_labs_fetch_catalog_resumes_from_real_next_url():
    """resume_cursor, when it's the exact prior "next" URL, is used directly rather than reconstructed from limit/offset we'd have to guess at."""
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    captured = {}

    def fake_request(url, timeout=15.0):
        captured["url"] = url
        return {"count": 1, "next": None, "previous": None, "results": []}

    with patch.object(adapter, "_request", side_effect=fake_request):
        adapter.fetch_catalog(resume_cursor="https://online.malabs.com/mws/items/?limit=10&offset=20")

    assert captured["url"] == "https://online.malabs.com/mws/items/?limit=10&offset=20"


def test_ma_labs_fetch_inventory_single_sku_lookup():
    """
    Live-confirmed (2026-10-22): /mws/items/{itemno}/ returns a bare JSON
    list ([{...}]), not a single object, unlike the paginated list endpoint
    which wraps results in {"results": [...]}. A prior version of
    fetch_inventory() passed this list straight into _normalize_item()
    (which expects a dict) and raised AttributeError on every real call —
    this reproduces that exact real response shape.
    """
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    raw_list_response = [
        {
            "item_no": "PM16531T9G",
            "upc_code": "",
            "manufacturer_no": "MZILG1T9HCJR-00A07",
            "manufacturer": "SAMSUNGOEM",
            "category": "SSD",
            "product_name": "Samsung Enterprise PM1653 1.92 TB SSD",
            "price": 1900.35,
            "inventory": {"": 57},
        }
    ]
    with patch.object(adapter, "_request", return_value=raw_list_response):
        inv = adapter.fetch_inventory(["PM16531T9G"])
    assert inv["PM16531T9G"] == 57


def test_ma_labs_fetch_inventory_handles_empty_list_response():
    """A SKU with no match returns an empty list from the real API — must not raise, just skip it."""
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    with patch.object(adapter, "_request", return_value=[]):
        inv = adapter.fetch_inventory(["NONEXISTENT-SKU"])
    assert inv == {}


def test_ma_labs_fetch_price_changes():
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    sample_response = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "item_no": "ITEM-1",
                "manufacturer": "Acme",
                "product_name": "Widget",
                "price": 42.5,
                "inventory": {"": 3},
            }
        ],
    }
    with patch.object(adapter, "_request", return_value=sample_response):
        changes = adapter.fetch_price_changes()
    assert changes["ITEM-1"] == Decimal("42.5")


def test_ma_labs_fetch_catalog_emits_confirmed_query_params_only():
    """
    Live-confirmed (2026-10-22): upc, mfrno, and search genuinely filter
    the real API (count drops from the full 6800 when applied). An
    "in_stock" filter was documented but live-tested under every
    reasonable param name/value and never changed the result count —
    so it must never be emitted as a query param, even if a caller passes
    filters={"in_stock": ...}, to avoid silently pretending to filter.
    """
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    captured = {}

    def fake_request(url, timeout=15.0):
        captured["url"] = url
        return {"count": 0, "next": None, "previous": None, "results": []}

    with patch.object(adapter, "_request", side_effect=fake_request):
        adapter.fetch_catalog(filters={
            "upc": "012345678905",
            "mpn": "MZVL4256HBJD-00B07",
            "search": "samsung,ssd",
            "in_stock": True,
        })

    assert "upc=012345678905" in captured["url"]
    assert "mfrno=MZVL4256HBJD-00B07" in captured["url"]
    assert "search=samsung%2Cssd" in captured["url"]
    assert "in_stock" not in captured["url"]
    assert "stock" not in captured["url"]


def test_ma_labs_check_shipment_status_not_implemented():
    """
    No tracking endpoint exists on the real API (confirmed 2026-10-22), so
    this adapter relies on SupplierAdapter's base implementation, which
    honestly returns None rather than fabricating tracking data.
    """
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    assert adapter.check_shipment_status("anything") is None


def test_ma_labs_does_not_fabricate_an_order_api():
    """
    Ma Labs' MWS docs describe no order-submission endpoint, so this
    adapter deliberately has no submit_order() — never a fabricated fake
    success. order_service.py's live-submit allowlist (D&H/Ingram/TD
    SYNNEX only) is what actually keeps a Ma Labs PO from silently trying
    (and failing) a non-existent live call; this just confirms the method
    truly isn't implemented here.
    """
    adapter = MaLabsAdapter(credentials={"username": "basit@ibswireless.com", "password": "secret"})
    assert not hasattr(adapter, "submit_order")
