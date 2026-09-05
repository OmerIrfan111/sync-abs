from typing import Dict, Any, Optional
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter

class VoiceCommAdapter(MockSupplierAdapter):
    """
    Dedicated VoiceComm Mobile Accessories Integration Adapter.
    Simulates VoiceComm REST API for wireless accessories, chargers, cases, and audio gear.
    """
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(supplier_name="VoiceComm", credentials=credentials, config=config)
