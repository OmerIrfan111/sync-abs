from typing import Dict, Type, Optional, Any
import logging

from app.adapters.suppliers.base import SupplierAdapter
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter
from app.adapters.suppliers.ingram_micro import IngramMicroAdapter
from app.adapters.suppliers.d_and_h import DAndHAdapter
from app.adapters.suppliers.td_synnex import TDSynnexAdapter
from app.adapters.suppliers.ma_labs import MaLabsAdapter
from app.adapters.suppliers.voicecomm import VoiceCommAdapter

from app.adapters.marketplaces.base import MarketplaceAdapter
from app.adapters.marketplaces.mock_ebay import MockEBayAdapter
from app.adapters.marketplaces.mock_amazon import MockAmazonAdapter
from app.adapters.marketplaces.mock_shopify import MockShopifyAdapter
from app.adapters.marketplaces.mock_walmart import MockWalmartAdapter
from app.adapters.marketplaces.mock_newegg import MockNeweggAdapter

logger = logging.getLogger(__name__)

SUPPLIER_ADAPTERS: Dict[str, Type[SupplierAdapter]] = {
    "MockSupplierAdapter": MockSupplierAdapter,
    "IngramMicroAdapter": IngramMicroAdapter,
    "DAndHAdapter": DAndHAdapter,
    "TDSynnexAdapter": TDSynnexAdapter,
    "MaLabsAdapter": MaLabsAdapter,
    "VoiceCommAdapter": VoiceCommAdapter,
}

MARKETPLACE_ADAPTERS: Dict[str, Type[MarketplaceAdapter]] = {
    "MockEBayAdapter": MockEBayAdapter,
    "MockAmazonAdapter": MockAmazonAdapter,
    "MockShopifyAdapter": MockShopifyAdapter,
    "MockWalmartAdapter": MockWalmartAdapter,
    "MockNeweggAdapter": MockNeweggAdapter,
    "MockMarketplaceAdapter": MockEBayAdapter,
}

def get_supplier_adapter(
    adapter_class: str,
    supplier_name: Optional[str] = None,
    credentials: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> SupplierAdapter:
    """Factory to instantiate supplier adapter by class name."""
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
    """Factory to instantiate marketplace adapter by class name."""
    cls = MARKETPLACE_ADAPTERS.get(adapter_class, MockEBayAdapter)
    return cls(credentials=credentials, config=config)
