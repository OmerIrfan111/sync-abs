from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from decimal import Decimal
from app.schemas.supplier import NormalizedProduct

class SupplierAdapter(ABC):
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        self.credentials = credentials or {}
        self.config = config or {}

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify API/Feed connectivity and credentials."""
        pass

    @abstractmethod
    def fetch_catalog(self) -> List[NormalizedProduct]:
        """Fetch full or delta catalog from supplier."""
        pass

    @abstractmethod
    def fetch_inventory(self, skus: Optional[List[str]] = None) -> Dict[str, int]:
        """Fetch stock quantities keyed by supplier SKU."""
        pass

    @abstractmethod
    def fetch_price_changes(self) -> Dict[str, Decimal]:
        """Fetch updated costs keyed by supplier SKU."""
        pass
