import uuid
import time
from decimal import Decimal
from typing import Dict, Any, Optional
from app.adapters.marketplaces.base import MarketplaceAdapter

# In-memory mock Newegg datastore
MOCK_NEWEGG_ITEMS: Dict[str, Dict[str, Any]] = {}

class MockNeweggAdapter(MarketplaceAdapter):
    """
    High-fidelity Mock Newegg Marketplace API Adapter.
    Simulates:
    1. Seller ID & Secret Key header authentication
    2. PUT /contentmgmt/item/itemcreationfeed
    3. PUT /contentmgmt/item/inventoryandprice
    4. Deactivation of item listings
    """

    def test_connection(self) -> bool:
        if self.config.get("simulate_auth_failure"):
            raise PermissionError("Newegg API Error: Invalid Seller ID or Secret Key (HTTP 401)")
        if self.config.get("simulate_connection_failure"):
            raise ConnectionError("Newegg API Gateway Timeout (HTTP 504)")
        return True

    def create_listing(
        self,
        sku: str,
        title: str,
        description: str,
        price: Decimal,
        quantity: int,
        image_urls: Optional[list] = None
    ) -> Dict[str, Any]:
        self.test_connection()
        if self.config.get("simulate_latency_ms"):
            time.sleep(self.config["simulate_latency_ms"] / 1000.0)

        newegg_item_number = f"N82E168{uuid.uuid4().hex[:8].upper()}"
        external_listing_id = f"neg_{newegg_item_number}_{sku}"

        record = {
            "external_listing_id": external_listing_id,
            "newegg_item_number": newegg_item_number,
            "sku": sku,
            "title": title,
            "description": description,
            "price": Decimal(str(price)),
            "quantity": quantity,
            "status": "ACTIVE",
            "marketplace": "Newegg",
            "published_at": time.time()
        }
        MOCK_NEWEGG_ITEMS[external_listing_id] = record
        return record

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_NEWEGG_ITEMS:
            MOCK_NEWEGG_ITEMS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal("0.00"),
                "quantity": quantity,
                "status": "ACTIVE"
            }
        MOCK_NEWEGG_ITEMS[external_listing_id]["quantity"] = quantity
        return True

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_NEWEGG_ITEMS:
            MOCK_NEWEGG_ITEMS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal(str(price)),
                "quantity": 0,
                "status": "ACTIVE"
            }
        MOCK_NEWEGG_ITEMS[external_listing_id]["price"] = Decimal(str(price))
        return True

    def withdraw_listing(self, external_listing_id: str) -> bool:
        self.test_connection()
        if external_listing_id in MOCK_NEWEGG_ITEMS:
            MOCK_NEWEGG_ITEMS[external_listing_id]["status"] = "DEACTIVATED"
            MOCK_NEWEGG_ITEMS[external_listing_id]["quantity"] = 0
        return True

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        self.test_connection()
        if external_listing_id not in MOCK_NEWEGG_ITEMS:
            raise KeyError(f"Listing ID {external_listing_id} not found on Newegg")
        return MOCK_NEWEGG_ITEMS[external_listing_id]
