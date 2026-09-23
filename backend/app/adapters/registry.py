from typing import Dict, Type, Optional, Any
import logging

from app.adapters.suppliers.base import SupplierAdapter
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter
from app.adapters.suppliers.ingram_micro import IngramMicroAdapter
from app.adapters.suppliers.d_and_h import DAndHAdapter

from app.adapters.marketplaces.base import MarketplaceAdapter
from app.adapters.marketplaces.mock_ebay import MockEBayAdapter
from app.adapters.marketplaces.live_ebay import LiveEBayAdapter
from app.adapters.marketplaces.mock_amazon import MockAmazonAdapter
from app.adapters.marketplaces.live_amazon import LiveAmazonAdapter
from app.adapters.marketplaces.mock_shopify import MockShopifyAdapter
from app.adapters.marketplaces.live_shopify import LiveShopifyAdapter

logger = logging.getLogger(__name__)

SUPPLIER_ADAPTERS: Dict[str, Type[SupplierAdapter]] = {
    "IngramMicroAdapter": IngramMicroAdapter,
    "DAndHAdapter": DAndHAdapter,
    "MockSupplierAdapter": MockSupplierAdapter,
}

MARKETPLACE_ADAPTERS: Dict[str, Type[MarketplaceAdapter]] = {
    "LiveEBayAdapter": LiveEBayAdapter,
    "MockEBayAdapter": MockEBayAdapter,
    "LiveAmazonAdapter": LiveAmazonAdapter,
    "MockAmazonAdapter": MockAmazonAdapter,
    "LiveShopifyAdapter": LiveShopifyAdapter,
    "MockShopifyAdapter": MockShopifyAdapter,
    # Explicit test-fixture doubles for out-of-scope marketplaces exercised by
    # the multi-channel test suite. Listed explicitly (not a silent catch-all
    # default) so a typo'd or unrecognized adapter_class on a REAL marketplace
    # can never resolve to one of these by accident.
    "MockWalmartAdapter": MockEBayAdapter,
    "MockNeweggAdapter": MockEBayAdapter,
}

def get_supplier_adapter(
    adapter_class: str,
    supplier_name: Optional[str] = None,
    credentials: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> SupplierAdapter:
    """
    Factory to instantiate supplier adapter by class name (Ingram Micro or D&H).

    Deliberately raises on an unrecognized adapter_class instead of falling
    back to MockSupplierAdapter: a silent fallback here previously let a
    misconfigured/mistyped adapter_class on a REAL supplier row silently
    start returning fabricated mock catalog data with no error anywhere in
    the system. Fail loud instead.
    """
    cls = SUPPLIER_ADAPTERS.get(adapter_class)
    if cls is None:
        raise ValueError(
            f"Unrecognized supplier adapter_class '{adapter_class}'. "
            f"Known adapters: {sorted(SUPPLIER_ADAPTERS.keys())}. "
            f"Refusing to silently fall back to mock data for a real supplier."
        )
    if cls is MockSupplierAdapter:
        return MockSupplierAdapter(
            supplier_name=supplier_name or "Ingram Micro",
            credentials=credentials,
            config=config
        )
    return cls(credentials=credentials, config=config)

def get_marketplace_adapter(
    adapter_class: str,
    credentials: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> MarketplaceAdapter:
    """
    Factory to instantiate marketplace adapter by class name (eBay, Amazon, or Shopify).

    Same fail-loud principle as get_supplier_adapter: an unrecognized
    adapter_class raises rather than silently defaulting to a mock, so a
    real marketplace can never silently start pushing to a fake adapter.
    """
    if adapter_class in MARKETPLACE_ADAPTERS:
        return MARKETPLACE_ADAPTERS[adapter_class](credentials=credentials, config=config)

    creds = credentials or {}
    act_lower = adapter_class.lower()

    if "amazon" in act_lower or creds.get("seller_id") or creds.get("lwa_client_id"):
        return LiveAmazonAdapter(credentials=credentials, config=config)

    if "shopify" in act_lower or creds.get("shop_url") or creds.get("shop_domain"):
        return LiveShopifyAdapter(credentials=credentials, config=config)

    if "ebay" in act_lower or creds.get("user_token") or creds.get("cert_id"):
        return LiveEBayAdapter(credentials=credentials, config=config)

    raise ValueError(
        f"Unrecognized marketplace adapter_class '{adapter_class}' and no "
        f"credential shape matched a known live marketplace. "
        f"Known adapters: {sorted(MARKETPLACE_ADAPTERS.keys())}. "
        f"Refusing to silently fall back to a mock adapter for a real marketplace."
    )

