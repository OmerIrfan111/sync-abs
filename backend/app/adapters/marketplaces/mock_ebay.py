import uuid
import time
from decimal import Decimal
from typing import Dict, Any, Optional
from app.adapters.marketplaces.base import MarketplaceAdapter

# In-memory mock eBay datastore across requests
MOCK_EBAY_LISTINGS: Dict[str, Dict[str, Any]] = {}

class MockEBayAdapter(MarketplaceAdapter):
    """
    High-fidelity Mock eBay Sell API adapter fulfilling Spec Section 31 & Section 10.
    Simulates:
    1. PUT /sell/inventory/v1/inventory_item/{sku}
    2. POST /sell/inventory/v1/offer
    3. POST /sell/inventory/v1/offer/{offerId}/publish
    4. Quantity revision & price revision
    5. POST /sell/inventory/v1/offer/{offerId}/withdraw
    """

    def test_connection(self) -> bool:
        if self.config.get("simulate_auth_failure"):
            raise PermissionError("eBay OAuth 2.0 error: Invalid user token or expired refresh token (HTTP 401)")
        if self.config.get("simulate_connection_failure"):
            raise ConnectionError("eBay Sell API gateway unreachable: Gateway Timeout (HTTP 504)")
        return True

    def create_inventory_item(self, sku: str, title: str, description: str, quantity: int, image_urls: Optional[list] = None) -> Dict[str, Any]:
        """Simulates eBay PUT /sell/inventory/v1/inventory_item/{sku}"""
        self.test_connection()
        return {
            "sku": sku,
            "product": {
                "title": title,
                "description": description,
                "imageUrls": image_urls or []
            },
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": quantity
                }
            },
            "statusCode": 204
        }

    def create_offer(self, sku: str, price: Decimal, marketplace_id: str = "EBAY_US") -> str:
        """Simulates eBay POST /sell/inventory/v1/offer"""
        self.test_connection()
        offer_id = f"offer_{uuid.uuid4().hex[:10]}"
        return offer_id

    def publish_offer(self, offer_id: str) -> str:
        """Simulates eBay POST /sell/inventory/v1/offer/{offerId}/publish"""
        self.test_connection()
        listing_id = f"ebay_listing_{uuid.uuid4().hex[:12]}"
        return listing_id

    def create_listing(self, sku: str, title: str, description: str, price: Decimal, quantity: int, image_urls: Optional[list] = None) -> Dict[str, Any]:
        """
        Executes complete eBay Sell API lifecycle:
        create_inventory_item -> create_offer -> publish_offer
        """
        self.test_connection()
        if self.config.get("simulate_latency_ms"):
            time.sleep(self.config["simulate_latency_ms"] / 1000.0)

        # 1. Create inventory item
        self.create_inventory_item(sku, title, description, quantity, image_urls)

        # 2. Create offer
        offer_id = self.create_offer(sku, price)

        # 3. Publish offer to generate live eBay listing ID
        external_listing_id = self.publish_offer(offer_id)

        record = {
            "external_listing_id": external_listing_id,
            "offer_id": offer_id,
            "sku": sku,
            "title": title,
            "price": Decimal(str(price)),
            "quantity": quantity,
            "status": "ACTIVE",
            "marketplace": "eBay US",
            "published_at": time.time()
        }
        MOCK_EBAY_LISTINGS[external_listing_id] = record

        return record

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        """Simulates updating stock in eBay inventory"""
        self.test_connection()
        if external_listing_id not in MOCK_EBAY_LISTINGS:
            # Re-register if state wiped in ephemeral test
            MOCK_EBAY_LISTINGS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal("0.00"),
                "quantity": quantity,
                "status": "ACTIVE"
            }
        MOCK_EBAY_LISTINGS[external_listing_id]["quantity"] = quantity
        return True

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        """Simulates updating selling price in eBay offer"""
        self.test_connection()
        if external_listing_id not in MOCK_EBAY_LISTINGS:
            MOCK_EBAY_LISTINGS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal(str(price)),
                "quantity": 0,
                "status": "ACTIVE"
            }
        MOCK_EBAY_LISTINGS[external_listing_id]["price"] = Decimal(str(price))
        return True

    def withdraw_listing(self, external_listing_id: str) -> bool:
        """Simulates eBay POST /sell/inventory/v1/offer/{offerId}/withdraw"""
        self.test_connection()
        if external_listing_id in MOCK_EBAY_LISTINGS:
            MOCK_EBAY_LISTINGS[external_listing_id]["status"] = "WITHDRAWN"
            MOCK_EBAY_LISTINGS[external_listing_id]["quantity"] = 0
        return True

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        """Retrieves listing status from mock eBay"""
        self.test_connection()
        if external_listing_id not in MOCK_EBAY_LISTINGS:
            raise KeyError(f"Listing ID {external_listing_id} not found on eBay")
        return MOCK_EBAY_LISTINGS[external_listing_id]
