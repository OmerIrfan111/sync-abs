from typing import Dict, Any, Optional
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter

class MaLabsAdapter(MockSupplierAdapter):
    """
    Dedicated Ma Labs Computer Components Integration Adapter.
    Simulates Ma Labs CSV flat-file & FTP inventory/pricing synchronization feeds.
    """
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(supplier_name="Ma Labs", credentials=credentials, config=config)
