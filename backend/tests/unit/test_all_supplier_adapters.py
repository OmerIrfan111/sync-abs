import pytest

from app.adapters.suppliers.ingram_micro import IngramMicroAdapter
from app.adapters.suppliers.d_and_h import DAndHAdapter
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter
from app.adapters.registry import get_supplier_adapter

LIVE_SUPPLIER_CLASSES = [
    IngramMicroAdapter,
    DAndHAdapter,
]

LIVE_CREDENTIAL_ENV_VARS = [
    "INGRAM_MICRO_CLIENT_ID", "INGRAM_MICRO_CLIENT_SECRET",
    "DANDH_BEARER_TOKEN", "DANDH_CLIENT_ID", "DANDH_CLIENT_SECRET",
]

@pytest.mark.parametrize("adapter_cls", LIVE_SUPPLIER_CLASSES)
def test_live_adapters_refuse_to_fabricate_data_without_credentials(adapter_cls, monkeypatch):
    """
    A live supplier adapter with no resolvable credentials must raise rather
    than silently return fabricated catalog data. This is a regression test
    for a real incident: IngramMicroAdapter/DAndHAdapter used to inherit from
    MockSupplierAdapter and fall back to its hardcoded mock catalog whenever
    credentials were missing, which let fake "test" products get published to
    a live store as if they were real inventory.

    Explicit empty-string credentials are passed AND the .env-backed settings
    fallback is monkeypatched away, so this doesn't depend on whether real
    credentials happen to be configured in the environment running the tests.
    """
    from app.core.config import settings
    for var in LIVE_CREDENTIAL_ENV_VARS:
        monkeypatch.setattr(settings, var, None, raising=False)

    empty_creds = {"client_id": "", "client_secret": "", "bearer_token": ""}
    adapter = adapter_cls(credentials=empty_creds)
    assert adapter.is_live() is False

    with pytest.raises(ConnectionError):
        adapter.test_connection()

    with pytest.raises(ConnectionError):
        adapter.fetch_catalog()

@pytest.mark.parametrize("adapter_cls", LIVE_SUPPLIER_CLASSES)
def test_live_adapters_do_not_inherit_from_mock(adapter_cls):
    """Structural guard against the same bug reappearing via inheritance."""
    assert not issubclass(adapter_cls, MockSupplierAdapter)

@pytest.mark.parametrize("adapter_cls", LIVE_SUPPLIER_CLASSES)
def test_live_adapters_inventory_and_price_endpoints_are_honest_stubs(adapter_cls):
    """
    Neither adapter implements a standalone inventory/price refresh (the real
    sync pipeline gets both inline from fetch_catalog()). These must raise
    NotImplementedError, not silently return fabricated mock data.
    """
    adapter = adapter_cls()
    with pytest.raises(NotImplementedError):
        adapter.fetch_inventory(["SOME-SKU"])
    with pytest.raises(NotImplementedError):
        adapter.fetch_price_changes()

def test_supplier_registry_factory():
    ad1 = get_supplier_adapter("IngramMicroAdapter")
    assert isinstance(ad1, IngramMicroAdapter)
    assert ad1.supplier_name == "Ingram Micro"

    ad2 = get_supplier_adapter("DAndHAdapter")
    assert isinstance(ad2, DAndHAdapter)
    assert ad2.supplier_name == "D&H"

def test_supplier_registry_rejects_unknown_adapter_class():
    """
    An unrecognized adapter_class must raise, never silently resolve to
    MockSupplierAdapter. This is the other half of the same regression test:
    the registry used to do `SUPPLIER_ADAPTERS.get(adapter_class,
    MockSupplierAdapter)`, so a typo'd or corrupted adapter_class on a REAL
    supplier row would silently start returning fake catalog data.
    """
    with pytest.raises(ValueError):
        get_supplier_adapter("SomeTypoedAdapterName")

def test_mock_supplier_adapter_still_works_directly():
    """MockSupplierAdapter itself remains valid for explicit dev/test use."""
    adapter = MockSupplierAdapter(supplier_name="Ingram Micro")
    assert adapter.test_connection() is True
    catalog = adapter.fetch_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) > 0
