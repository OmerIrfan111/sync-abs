from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
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

