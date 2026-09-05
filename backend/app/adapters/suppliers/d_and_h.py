from typing import Dict, Any, Optional
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter

class DAndHAdapter(MockSupplierAdapter):
    """
    Dedicated D&H Distributing B2B Integration Adapter.
    Simulates D&H XML / EDI 846 inventory inquiry & catalog feeds for computer and consumer tech.
    """
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(supplier_name="D&H", credentials=credentials, config=config)
