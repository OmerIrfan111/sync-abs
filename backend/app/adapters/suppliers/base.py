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
    def fetch_catalog(self, resume_cursor: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> List[NormalizedProduct]:
        """
        Fetch full or delta catalog from supplier. resume_cursor is an opaque
        pagination token (its meaning is adapter-specific — a page number, a
        scroll id, etc.) returned from a prior call via self.next_cursor, so a
        real multi-thousand-SKU catalog can be paged through across several
        sync runs instead of always restarting from the beginning. Adapters
        that don't paginate (e.g. mock/small feeds) simply ignore it.
        Implementations should set self.next_cursor and self.catalog_exhausted
        before returning so the caller can persist where to resume next time.
        """
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

    # ── Feature 1: Base Ground Shipping Estimate ──

    def get_ground_shipping_estimate(self, supplier_sku: str, destination_zip: str = "90210") -> Optional[Decimal]:
        """
        Retrieves live standard ground shipping charge for a product from the supplier.
        Returns a Decimal shipping cost or None if the supplier does not provide live shipping quotes.
        """
        if self.config.get("simulate_shipping_unknown"):
            return None
        if "ground_shipping_charge" in self.config:
            val = self.config["ground_shipping_charge"]
            return Decimal(str(val)) if val is not None else None
        return None

