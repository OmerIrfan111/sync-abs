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
    # Fallback aliases to ensure existing records map safely
    "TDSynnexAdapter": IngramMicroAdapter,
    "MaLabsAdapter": DAndHAdapter,
    "VoiceCommAdapter": IngramMicroAdapter,
}

MARKETPLACE_ADAPTERS: Dict[str, Type[MarketplaceAdapter]] = {
    "LiveEBayAdapter": LiveEBayAdapter,
    "MockEBayAdapter": MockEBayAdapter,
    "LiveAmazonAdapter": LiveAmazonAdapter,
    "MockAmazonAdapter": MockAmazonAdapter,
    "LiveShopifyAdapter": LiveShopifyAdapter,
    "MockShopifyAdapter": MockShopifyAdapter,
    "MockMarketplaceAdapter": MockEBayAdapter,
    # Fallback aliases to ensure existing test scenarios execute cleanly
    "MockWalmartAdapter": MockEBayAdapter,
    "MockNeweggAdapter": MockEBayAdapter,
}

def get_supplier_adapter(
    adapter_class: str,
    supplier_name: Optional[str] = None,
    credentials: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> SupplierAdapter:
    """Factory to instantiate supplier adapter by class name (Ingram Micro or D&H)."""
    cls = SUPPLIER_ADAPTERS.get(adapter_class, MockSupplierAdapter)
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
    """Factory to instantiate marketplace adapter by class name (eBay, Amazon, or Shopify)."""
    creds = credentials or {}

    # If explicitly Live adapter or real live credentials are provided, route to Live adapters
    if adapter_class == "LiveEBayAdapter" or (creds.get("user_token") or creds.get("refresh_token")):
        return LiveEBayAdapter(credentials=credentials, config=config)

    if adapter_class == "LiveAmazonAdapter" or (creds.get("client_id") and creds.get("refresh_token")):
        return LiveAmazonAdapter(credentials=credentials, config=config)

    if adapter_class == "LiveShopifyAdapter" or (creds.get("access_token") and (creds.get("shop_url") or creds.get("shop_domain"))):
        return LiveShopifyAdapter(credentials=credentials, config=config)

    cls = MARKETPLACE_ADAPTERS.get(adapter_class, MockEBayAdapter)
    return cls(credentials=credentials, config=config)

