from typing import Dict, Any, Optional
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter

class TDSynnexAdapter(MockSupplierAdapter):
    """
    Dedicated TD SYNNEX B2B Integration Adapter.
    Simulates TD SYNNEX enterprise IT distribution API, tiered volume pricing, and warehouse feeds.
    """
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(supplier_name="TD SYNNEX", credentials=credentials, config=config)
