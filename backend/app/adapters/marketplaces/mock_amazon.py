import uuid
import time
from decimal import Decimal
from typing import Dict, Any, Optional
from app.adapters.marketplaces.base import MarketplaceAdapter

# In-memory mock Amazon datastore
MOCK_AMAZON_LISTINGS: Dict[str, Dict[str, Any]] = {}

class MockAmazonAdapter(MarketplaceAdapter):
    """
    High-fidelity Mock Amazon Selling Partner API (SP-API) Adapter.
    Simulates:
    1. LWA OAuth 2.0 Token Authentication
    2. PUT/POST /listings/2021-08-01/items/{sellerId}/{sku}
    3. PATCH /listings/2021-08-01/items/{sellerId}/{sku} (Fulfillment stock & Price)
    4. Rate-limiting token bucket simulation (HTTP 429) & gateway timeout (HTTP 504)
    5. Listing closure / withdrawal
    """

    def test_connection(self) -> bool:
        if self.config.get("simulate_auth_failure"):
            raise PermissionError("Amazon SP-API LWA Error: Invalid Client Secret or Refresh Token (HTTP 401)")
        if self.config.get("simulate_rate_limit"):
            raise ConnectionError("Amazon SP-API Error: Quota exceeded - Rate Limit Encountered (HTTP 429)")
        if self.config.get("simulate_connection_failure"):
            raise ConnectionError("Amazon SP-API Endpoint Unreachable: Gateway Timeout (HTTP 504)")
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

        asin = f"B0{uuid.uuid4().hex[:8].upper()}"
        external_listing_id = f"amzn_{asin}_{sku}"

        record = {
            "external_listing_id": external_listing_id,
            "asin": asin,
            "sku": sku,
            "title": title,
            "description": description,
            "price": Decimal(str(price)),
            "quantity": quantity,
            "status": "ACTIVE",
            "marketplace": "Amazon US",
            "published_at": time.time()
        }
        MOCK_AMAZON_LISTINGS[external_listing_id] = record
        return record

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_AMAZON_LISTINGS:
            MOCK_AMAZON_LISTINGS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal("0.00"),
                "quantity": quantity,
                "status": "ACTIVE"
            }
        MOCK_AMAZON_LISTINGS[external_listing_id]["quantity"] = quantity
        return True

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_AMAZON_LISTINGS:
            MOCK_AMAZON_LISTINGS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal(str(price)),
                "quantity": 0,
                "status": "ACTIVE"
            }
        MOCK_AMAZON_LISTINGS[external_listing_id]["price"] = Decimal(str(price))
        return True

    def withdraw_listing(self, external_listing_id: str) -> bool:
        self.test_connection()
        if external_listing_id in MOCK_AMAZON_LISTINGS:
            MOCK_AMAZON_LISTINGS[external_listing_id]["status"] = "WITHDRAWN"
            MOCK_AMAZON_LISTINGS[external_listing_id]["quantity"] = 0
        return True

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        self.test_connection()
        if external_listing_id not in MOCK_AMAZON_LISTINGS:
            raise KeyError(f"Listing ID {external_listing_id} not found on Amazon")
        return MOCK_AMAZON_LISTINGS[external_listing_id]
