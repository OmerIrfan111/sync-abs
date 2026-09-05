from typing import Dict, Any, Optional
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter

class IngramMicroAdapter(MockSupplierAdapter):
    """
    Dedicated Ingram Micro B2B Integration Adapter.
    Simulates Ingram Micro standard XML / REST product catalog, real-time pricing & stock availability.
    """
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(supplier_name="Ingram Micro", credentials=credentials, config=config)
