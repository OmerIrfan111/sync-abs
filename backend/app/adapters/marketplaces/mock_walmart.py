import uuid
import time
from decimal import Decimal
from typing import Dict, Any, Optional
from app.adapters.marketplaces.base import MarketplaceAdapter

# In-memory mock Walmart datastore
MOCK_WALMART_ITEMS: Dict[str, Dict[str, Any]] = {}

class MockWalmartAdapter(MarketplaceAdapter):
    """
    High-fidelity Mock Walmart Marketplace API Adapter.
    Simulates:
    1. Client ID / Client Secret authentication with WM_SEC.ACCESS_TOKEN token header
    2. POST /v3/feeds?feedType=item (Item ingest feed simulation)
    3. PUT /v3/inventory?sku={sku}
    4. PUT /v3/price
    5. Retiring / unpublishing listings
    """

    def test_connection(self) -> bool:
        if self.config.get("simulate_auth_failure"):
            raise PermissionError("Walmart API Error: Invalid Client ID or Client Secret (HTTP 401)")
        if self.config.get("simulate_connection_failure"):
            raise ConnectionError("Walmart Gateway Error: Connection Reset by Peer (HTTP 502)")
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

        wmt_item_id = f"WMT_{uuid.uuid4().hex[:10].upper()}"
        external_listing_id = f"wmt_{wmt_item_id}_{sku}"

        record = {
            "external_listing_id": external_listing_id,
            "wmt_item_id": wmt_item_id,
            "sku": sku,
            "title": title,
            "description": description,
            "price": Decimal(str(price)),
            "quantity": quantity,
            "status": "ACTIVE",
            "marketplace": "Walmart Marketplace",
            "published_at": time.time()
        }
        MOCK_WALMART_ITEMS[external_listing_id] = record
        return record

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_WALMART_ITEMS:
            MOCK_WALMART_ITEMS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal("0.00"),
                "quantity": quantity,
                "status": "ACTIVE"
            }
        MOCK_WALMART_ITEMS[external_listing_id]["quantity"] = quantity
        return True

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_WALMART_ITEMS:
            MOCK_WALMART_ITEMS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal(str(price)),
                "quantity": 0,
                "status": "ACTIVE"
            }
        MOCK_WALMART_ITEMS[external_listing_id]["price"] = Decimal(str(price))
        return True

    def withdraw_listing(self, external_listing_id: str) -> bool:
        self.test_connection()
        if external_listing_id in MOCK_WALMART_ITEMS:
            MOCK_WALMART_ITEMS[external_listing_id]["status"] = "RETIRED"
            MOCK_WALMART_ITEMS[external_listing_id]["quantity"] = 0
        return True

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        self.test_connection()
        if external_listing_id not in MOCK_WALMART_ITEMS:
            raise KeyError(f"Listing ID {external_listing_id} not found on Walmart")
        return MOCK_WALMART_ITEMS[external_listing_id]
