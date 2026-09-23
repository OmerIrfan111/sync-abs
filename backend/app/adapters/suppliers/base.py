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

    # ── V2.2 Phase 2: Supplier Shipping Confirmation (extensibility hook) ──

    def check_shipment_status(self, supplier_order_id: str) -> Optional[Dict[str, Any]]:
        """
        Checks the real supplier's own order-status API for shipment
        confirmation on a previously-submitted purchase order. Returns a dict
        with keys like tracking_number, carrier, shipped_at when the supplier
        reports the order has shipped, or None if not yet shipped / not
        supported by this adapter.

        Optional: adapters that don't have a real order-status endpoint wired
        up (or whose supplier doesn't expose one) simply return None, and
        staff continue recording tracking manually via the Orders UI — this
        never blocks the existing manual workflow.
        """
        return None
