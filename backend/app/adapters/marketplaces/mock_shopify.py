import uuid
import time
from decimal import Decimal
from typing import Dict, Any, Optional
from app.adapters.marketplaces.base import MarketplaceAdapter

# In-memory mock Shopify datastore
MOCK_SHOPIFY_PRODUCTS: Dict[str, Dict[str, Any]] = {}

class MockShopifyAdapter(MarketplaceAdapter):
    """
    High-fidelity Mock Shopify Admin REST & GraphQL API Adapter.
    Simulates:
    1. X-Shopify-Access-Token header authentication & store domain validation
    2. POST /admin/api/2024-01/products.json
    3. POST /admin/api/2024-01/inventory_levels/set.json
    4. PUT /admin/api/2024-01/variants/{variant_id}.json for price revisions
    5. Archiving / drafting listings
    """

    def test_connection(self) -> bool:
        if self.config.get("simulate_auth_failure"):
            raise PermissionError("Shopify API Error: Invalid X-Shopify-Access-Token or shop URL (HTTP 401)")
        if self.config.get("simulate_connection_failure"):
            raise ConnectionError("Shopify API Gateway Error: Service Unavailable (HTTP 503)")
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

        product_id = f"gid://shopify/Product/{uuid.uuid4().int % 1000000000}"
        variant_id = f"gid://shopify/ProductVariant/{uuid.uuid4().int % 1000000000}"
        external_listing_id = f"shpfy_{product_id.split('/')[-1]}_{sku}"

        record = {
            "external_listing_id": external_listing_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "sku": sku,
            "title": title,
            "description": description,
            "price": Decimal(str(price)),
            "quantity": quantity,
            "status": "ACTIVE",
            "marketplace": "Shopify Store",
            "published_at": time.time()
        }
        MOCK_SHOPIFY_PRODUCTS[external_listing_id] = record
        return record

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_SHOPIFY_PRODUCTS:
            MOCK_SHOPIFY_PRODUCTS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal("0.00"),
                "quantity": quantity,
                "status": "ACTIVE"
            }
        MOCK_SHOPIFY_PRODUCTS[external_listing_id]["quantity"] = quantity
        return True

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        self.test_connection()
        if external_listing_id not in MOCK_SHOPIFY_PRODUCTS:
            MOCK_SHOPIFY_PRODUCTS[external_listing_id] = {
                "external_listing_id": external_listing_id,
                "sku": sku,
                "price": Decimal(str(price)),
                "quantity": 0,
                "status": "ACTIVE"
            }
        MOCK_SHOPIFY_PRODUCTS[external_listing_id]["price"] = Decimal(str(price))
        return True

    def withdraw_listing(self, external_listing_id: str, sku: Optional[str] = None) -> bool:
        self.test_connection()
        if external_listing_id in MOCK_SHOPIFY_PRODUCTS:
            MOCK_SHOPIFY_PRODUCTS[external_listing_id]["status"] = "ARCHIVED"
            MOCK_SHOPIFY_PRODUCTS[external_listing_id]["quantity"] = 0
        return True

    def reactivate_listing(self, external_listing_id: str, sku: Optional[str] = None) -> bool:
        self.test_connection()
        if external_listing_id in MOCK_SHOPIFY_PRODUCTS:
            MOCK_SHOPIFY_PRODUCTS[external_listing_id]["status"] = "ACTIVE"
        return True

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        self.test_connection()
        if external_listing_id not in MOCK_SHOPIFY_PRODUCTS:
            raise KeyError(f"Listing ID {external_listing_id} not found on Shopify")
        return MOCK_SHOPIFY_PRODUCTS[external_listing_id]

    # ── V2: Mock Order Methods ──

    def fetch_orders(self, since_datetime=None) -> list:
        """Returns simulated Shopify orders for testing."""
        from datetime import datetime, timezone
        return [
            {
                "order_id": f"shopify-{uuid.uuid4().hex[:8]}",
                "buyer_username": "shopify_customer",
                "buyer_name": "Shopify Test Customer",
                "shipping_address": {
                    "name": "Shopify Test Customer",
                    "street": "789 Elm Street",
                    "city": "Austin",
                    "state": "TX",
                    "zip": "73301",
                    "country": "US",
                },
                "order_total": Decimal("199.99"),
                "marketplace_fees": Decimal("5.80"),
                "currency": "USD",
                "ordered_at": datetime.now(timezone.utc),
                "items": [
                    {
                        "item_id": f"shopify-item-{uuid.uuid4().hex[:6]}",
                        "sku": "ING-TEST-001",
                        "title": "Enterprise 4K UltraHD Pro Monitor 32-inch",
                        "quantity": 1,
                        "unit_price": Decimal("199.99"),
                    }
                ],
            }
        ]

    def update_tracking(self, marketplace_order_id: str, tracking_number: str, carrier: str) -> bool:
        return True

    def acknowledge_order(self, marketplace_order_id: str) -> bool:
        return True

