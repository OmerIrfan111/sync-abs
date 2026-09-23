from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal

class MarketplaceAdapter(ABC):
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        self.credentials = credentials or {}
        self.config = config or {}

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify marketplace API credentials and connectivity."""
        pass

    @abstractmethod
    def create_listing(self, sku: str, title: str, description: str, price: Decimal, quantity: int, image_urls: Optional[list] = None) -> Dict[str, Any]:
        """
        Create and publish a new marketplace listing.
        Returns a dict containing external_listing_id, status, and metadata.
        """
        pass

    @abstractmethod
    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        """Update live stock quantity for the listing."""
        pass

    @abstractmethod
    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        """Update live selling price for the listing."""
        pass

    @abstractmethod
    def withdraw_listing(self, external_listing_id: str) -> bool:
        """Withdraw/delist an active offer from the marketplace."""
        pass

    def reactivate_listing(self, external_listing_id: str, sku: Optional[str] = None) -> bool:
        """Reactivate/republish a withdrawn/draft listing on the marketplace."""
        return True

    def update_product_details(self, external_listing_id: str, title: Optional[str] = None, description: Optional[str] = None) -> bool:
        """Update live listing title/description on the marketplace if supported."""
        return True

    @abstractmethod
    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        """Retrieve current marketplace listing details."""
        pass

    # ── V2: Order Management Methods ──

    def fetch_orders(self, since_datetime=None) -> List[Dict[str, Any]]:
        """
        Fetch new/updated orders from the marketplace since given timestamp.
        Returns a list of order dicts, each containing:
        - order_id: str (marketplace order reference)
        - buyer_username: str
        - buyer_name: str
        - shipping_address: dict
        - order_total: Decimal
        - marketplace_fees: Decimal
        - currency: str
        - ordered_at: datetime
        - items: list of dicts with sku, title, quantity, unit_price, item_id
        """
        return []

    def update_tracking(self, marketplace_order_id: str, tracking_number: str, carrier: str) -> bool:
        """Push shipment tracking information to the marketplace for a specific order."""
        return True

    def acknowledge_order(self, marketplace_order_id: str) -> bool:
        """Mark an order as acknowledged/accepted on the marketplace."""
        return True


