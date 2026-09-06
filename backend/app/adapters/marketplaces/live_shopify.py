import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

from app.adapters.marketplaces.base import MarketplaceAdapter

logger = logging.getLogger(__name__)

class LiveShopifyAdapter(MarketplaceAdapter):
    """
    Live Shopify Admin REST API Adapter.
    Connects directly to real Shopify stores via Shopify Admin REST API.
    Supports Admin Access Tokens (shpat_...), product creation, variant pricing,
    multi-location inventory level synchronization, and drafting/archiving listings.
    """

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self.credentials = credentials or {}
        
        raw_shop = (
            self.credentials.get("shop_url") 
            or self.credentials.get("shop_domain") 
            or self.credentials.get("shop") 
            or ""
        ).strip().lower()

        # Normalize shop domain: remove http/https and trailing slashes
        raw_shop = raw_shop.replace("https://", "").replace("http://", "").rstrip("/")
        if raw_shop and not raw_shop.endswith(".myshopify.com") and "." not in raw_shop:
            raw_shop = f"{raw_shop}.myshopify.com"

        self.shop_domain = raw_shop
        self.access_token = (
            self.credentials.get("access_token") 
            or self.credentials.get("admin_access_token") 
            or self.credentials.get("password") 
            or ""
        ).strip()
        self.api_version = self.credentials.get("api_version") or "2024-01"

        if self.shop_domain:
            self.base_url = f"https://{self.shop_domain}/admin/api/{self.api_version}"
        else:
            self.base_url = ""

        self._location_id: Optional[int] = self.credentials.get("location_id") or 89914146974

    def _get_headers(self) -> Dict[str, str]:
        """Builds authenticated headers for Shopify Admin REST requests."""
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SyncABS/1.0"
        }

    def _request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes an HTTP request to the Shopify Admin REST API."""
        if not self.shop_domain or not self.access_token:
            raise PermissionError("Shopify credentials incomplete: shop_url and access_token (shpat_...) are required.")

        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data).encode("utf-8") if data is not None else None

        req = urllib.request.Request(url, data=body, headers=self._get_headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                resp_data = response.read().decode("utf-8")
                return json.loads(resp_data) if resp_data else {}
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="ignore")
            logger.error(f"Shopify API Error [{err.code}] on {method} {url}: {err_body}")
            if err.code == 401:
                raise PermissionError(f"Shopify Authentication Error (401): Invalid Access Token. Details: {err_body}")
            elif err.code == 404:
                raise ConnectionError(f"Shopify Resource Not Found (404) at {url}. Verify shop domain: {self.shop_domain}")
            elif err.code == 429:
                raise RuntimeError("Shopify API Rate Limit Exceeded (429). Please retry shortly.")
            raise RuntimeError(f"Shopify API HTTP {err.code}: {err_body}")
        except urllib.error.URLError as err:
            logger.error(f"Shopify Network Error: {err.reason}")
            raise ConnectionError(f"Failed to connect to Shopify store '{self.shop_domain}': {err.reason}")

    def test_connection(self) -> bool:
        """
        Validates connection and credentials against Shopify GET /admin/api/2024-01/shop.json.
        """
        result = self._request("/shop.json", method="GET")
        if "shop" in result:
            shop_name = result["shop"].get("name", self.shop_domain)
            logger.info(f"Connected successfully to live Shopify store: {shop_name} ({self.shop_domain})")
            return True
        return False

    def get_location_for_item(self, inventory_item_id: int) -> int:
        """Fetches location ID for the inventory item or uses cached default location."""
        if self._location_id:
            return self._location_id

        try:
            res = self._request(f"/inventory_levels.json?inventory_item_ids={inventory_item_id}", method="GET")
            levels = res.get("inventory_levels", [])
            if levels and "location_id" in levels[0]:
                self._location_id = levels[0]["location_id"]
                return self._location_id
        except Exception:
            pass

        return self._location_id or 89914146974

    def find_product_by_sku(self, sku: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Searches Shopify for an existing product and variant matching the given SKU."""
        try:
            res = self._request("/products.json?limit=50", method="GET")
            for prod in res.get("products", []):
                for var in prod.get("variants", []):
                    if var.get("sku") == sku:
                        return prod, var
        except Exception as e:
            logger.warning(f"Could not search Shopify products by SKU: {e}")
        return None

    def create_listing(
        self,
        sku: str,
        title: str,
        description: str,
        price: Decimal,
        quantity: int,
        image_urls: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Publishes a product to Shopify via POST /admin/api/2024-01/products.json
        or updates existing product with matching SKU, preventing duplicate listings.
        """
        self.test_connection()

        # 1. If product with this SKU already exists on Shopify, update it instead of creating a duplicate!
        existing = self.find_product_by_sku(sku)
        if existing:
            prod, var = existing
            product_id = prod["id"]
            variant_id = var["id"]
            external_listing_id = f"shopify_{product_id}_{variant_id}"
            logger.info(f"Product with SKU {sku} already exists on Shopify ({external_listing_id}). Updating price and inventory.")
            self.update_price(external_listing_id, sku, price)
            self.update_inventory(external_listing_id, sku, quantity)
            return {
                "external_listing_id": external_listing_id,
                "product_id": str(product_id),
                "variant_id": str(variant_id),
                "sku": sku,
                "title": prod.get("title", title),
                "price": Decimal(str(price)),
                "quantity": quantity,
                "status": "ACTIVE",
                "marketplace": "Shopify"
            }

        images_payload = [{"src": url} for url in (image_urls or []) if url]
        formatted_price = str(Decimal(str(price)).quantize(Decimal("0.01")))

        product_payload = {
            "product": {
                "title": title,
                "body_html": description or title,
                "vendor": "Sync ABS",
                "status": "active",
                "variants": [
                    {
                        "sku": sku,
                        "price": formatted_price,
                        "inventory_management": "shopify"
                    }
                ],
                "images": images_payload
            }
        }

        res = self._request("/products.json", method="POST", data=product_payload)
        product = res.get("product", {})
        product_id = product.get("id")
        variants = product.get("variants", [])

        if not variants:
            raise RuntimeError("Shopify did not return product variants upon creation.")

        primary_variant = variants[0]
        variant_id = primary_variant.get("id")
        inventory_item_id = primary_variant.get("inventory_item_id")

        external_listing_id = f"shopify_{product_id}_{variant_id}"

        # Sync inventory if quantity provided and inventory_item_id available
        if inventory_item_id and quantity is not None:
            try:
                # 1. Ensure inventory item has tracking enabled
                self._request(f"/inventory_items/{inventory_item_id}.json", method="PUT", data={
                    "inventory_item": {
                        "id": inventory_item_id,
                        "tracked": True
                    }
                })

                # 2. Set available inventory
                location_id = self.get_location_for_item(inventory_item_id)
                self._request("/inventory_levels/set.json", method="POST", data={
                    "location_id": location_id,
                    "inventory_item_id": inventory_item_id,
                    "available": max(0, quantity)
                })
            except Exception as e:
                logger.warning(f"Could not set initial Shopify inventory level: {e}")

        return {
            "external_listing_id": external_listing_id,
            "product_id": str(product_id),
            "variant_id": str(variant_id),
            "inventory_item_id": str(inventory_item_id) if inventory_item_id else None,
            "sku": sku,
            "title": title,
            "price": Decimal(str(price)),
            "quantity": quantity,
            "status": "ACTIVE",
            "marketplace": "Shopify"
        }

    def _parse_listing_ids(self, external_listing_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Extracts product_id and variant_id from external_listing_id format."""
        if not external_listing_id:
            return None, None
        clean_id = str(external_listing_id).strip()
        if "gid://shopify/Product/" in clean_id:
            return clean_id.split("/")[-1], None
        parts = clean_id.split("_")
        if len(parts) >= 3 and parts[0] in ("shopify", "shpfy"):
            return parts[1], parts[2]
        elif len(parts) == 2 and parts[0] in ("shopify", "shpfy"):
            return parts[1], None
        return clean_id, None

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        """Revises variant price on Shopify via PUT /admin/api/2024-01/variants/{variant_id}.json."""
        product_id, variant_id = self._parse_listing_ids(external_listing_id)
        formatted_price = str(Decimal(str(price)).quantize(Decimal("0.01")))

        if variant_id:
            res = self._request(f"/variants/{variant_id}.json", method="PUT", data={
                "variant": {
                    "id": int(variant_id),
                    "price": formatted_price
                }
            })
            return "variant" in res

        if product_id:
            res = self._request(f"/products/{product_id}.json", method="GET")
            prod = res.get("product", {})
            for var in prod.get("variants", []):
                if var.get("sku") == sku or not sku:
                    v_id = var["id"]
                    self._request(f"/variants/{v_id}.json", method="PUT", data={
                        "variant": {
                            "id": v_id,
                            "price": formatted_price
                        }
                    })
                    return True

        return False

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        """Updates stock quantity on Shopify via /inventory_levels/set.json."""
        product_id, variant_id = self._parse_listing_ids(external_listing_id)
        inventory_item_id = None

        if variant_id:
            res = self._request(f"/variants/{variant_id}.json", method="GET")
            variant = res.get("variant", {})
            inventory_item_id = variant.get("inventory_item_id")
        elif product_id:
            res = self._request(f"/products/{product_id}.json", method="GET")
            prod = res.get("product", {})
            for var in prod.get("variants", []):
                if var.get("sku") == sku or not sku:
                    inventory_item_id = var.get("inventory_item_id")
                    break

        if inventory_item_id:
            # Ensure tracked
            try:
                self._request(f"/inventory_items/{inventory_item_id}.json", method="PUT", data={
                    "inventory_item": {"id": inventory_item_id, "tracked": True}
                })
            except Exception:
                pass

            location_id = self.get_location_for_item(inventory_item_id)
            self._request("/inventory_levels/set.json", method="POST", data={
                "location_id": location_id,
                "inventory_item_id": inventory_item_id,
                "available": max(0, quantity)
            })
            return True

        return False

    def withdraw_listing(self, external_listing_id: str, sku: Optional[str] = None) -> bool:
        """Unpublishes / sets product status to draft on Shopify."""
        product_id, _ = self._parse_listing_ids(external_listing_id)
        if not product_id and sku:
            existing = self.find_product_by_sku(sku)
            if existing:
                product_id = existing[0]["id"]
        if product_id:
            logger.info(f"Setting Shopify product {product_id} to draft (hidden)")
            self._request(f"/products/{product_id}.json", method="PUT", data={
                "product": {
                    "id": int(product_id),
                    "status": "draft"
                }
            })
            return True
        return False

    def reactivate_listing(self, external_listing_id: str, sku: Optional[str] = None) -> bool:
        """Publishes / sets product status back to active on Shopify."""
        product_id, _ = self._parse_listing_ids(external_listing_id)
        if not product_id and sku:
            existing = self.find_product_by_sku(sku)
            if existing:
                product_id = existing[0]["id"]
        if product_id:
            logger.info(f"Setting Shopify product {product_id} to active (unhidden/live)")
            self._request(f"/products/{product_id}.json", method="PUT", data={
                "product": {
                    "id": int(product_id),
                    "status": "active"
                }
            })
            return True
        return False

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        """Fetches product details from Shopify."""
        product_id, _ = self._parse_listing_ids(external_listing_id)
        if product_id:
            res = self._request(f"/products/{product_id}.json", method="GET")
            return res.get("product", {})
        raise KeyError(f"Invalid external listing ID {external_listing_id}")
