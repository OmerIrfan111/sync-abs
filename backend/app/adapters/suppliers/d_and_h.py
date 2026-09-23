import json
import logging
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
from decimal import Decimal
from typing import Dict, Any, Optional, List

from app.adapters.suppliers.base import SupplierAdapter
from app.schemas.supplier import NormalizedProduct
from app.core.config import settings

logger = logging.getLogger(__name__)

class DAndHAdapter(SupplierAdapter):
    """
    Dedicated D&H Distributing B2B REST Integration Adapter.
    Communicates directly with D&H's Axway API Gateway (/catalog/v1/customers/{accountNumber}/items)
    to query real-time product catalogs, pricing, inventory, and order fulfillment.
    Authenticates via OAuth 2.0 client_credentials grant against D&H's Axway auth service
    (per the Catalog API's published OpenAPI security scheme).

    Deliberately does NOT inherit from MockSupplierAdapter (see IngramMicroAdapter
    for why: that inheritance previously let a credential hiccup silently
    fall back to fabricated mock catalog data reported as a successful sync).
    """
    TEST_BASE_URL = "https://test.api.dandh.com/catalog/v1"
    PRODUCTION_BASE_URL = "https://api.dandh.com/catalog/v1"
    TEST_ORDER_MGMT_BASE_URL = "https://test.api.dandh.com/customerOrderManagement/v2"
    PRODUCTION_ORDER_MGMT_BASE_URL = "https://api.dandh.com/customerOrderManagement/v2"
    TEST_TOKEN_URL = "https://test.auth.dandh.com/api/oauth/token"
    PRODUCTION_TOKEN_URL = "https://auth.dandh.com/api/oauth/token"
    OAUTH_SCOPE = "resource.READ"
    PRICE_AVAILABILITY_BATCH_SIZE = 50

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials=credentials, config=config)
        self.supplier_name = "D&H"
        self.credentials = credentials or {}
        
        self.account_number = (
            self.credentials.get("account_number")
            or getattr(settings, "DANDH_ACCOUNT_NUMBER", None)
            or "3302610000"
        ).strip()

        self.client_id = (
            self.credentials.get("client_id")
            or getattr(settings, "DANDH_CLIENT_ID", None)
            or ""
        ).strip()

        self.client_secret = (
            self.credentials.get("client_secret")
            or getattr(settings, "DANDH_CLIENT_SECRET", None)
            or ""
        ).strip()

        self.bearer_token = (
            self.credentials.get("bearer_token")
            or getattr(settings, "DANDH_BEARER_TOKEN", None)
            or ""
        ).strip()

        self.tenant = (
            self.credentials.get("tenant")
            or getattr(settings, "DANDH_TENANT", "dhus")
        ).strip()

        env = (self.credentials.get("environment") or getattr(settings, "DANDH_ENVIRONMENT", "test")).lower()
        self.environment = "production" if env == "production" else "test"
        self.base_url = self.PRODUCTION_BASE_URL if self.environment == "production" else self.TEST_BASE_URL
        self.order_mgmt_base_url = self.PRODUCTION_ORDER_MGMT_BASE_URL if self.environment == "production" else self.TEST_ORDER_MGMT_BASE_URL
        self.token_url = self.PRODUCTION_TOKEN_URL if self.environment == "production" else self.TEST_TOKEN_URL

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

        # Items skipped during the last fetch_catalog() call due to missing
        # real price/availability data. Populated fresh on each call; read by
        # SyncService afterward to log MISSING_DATA errors visible on the
        # dashboard, rather than silently fabricating values.
        self._skipped_items: List[Dict[str, str]] = []

    def is_live(self) -> bool:
        """Returns True if live API credentials (OAuth client credentials or a static bearer token) are present."""
        return bool((self.client_id and self.client_secret) or self.bearer_token) and bool(self.account_number)

    def get_access_token(self) -> str:
        """
        Retrieves or refreshes an OAuth 2.0 access token via the client_credentials grant
        against D&H's Axway auth service. Falls back to a static bearer token if no
        client_id/client_secret are configured (e.g. legacy manual token setup).
        """
        if not self.client_id or not self.client_secret:
            return self.bearer_token

        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        token_data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.OAUTH_SCOPE,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.token_url,
            data=token_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "SyncABS-Dropship-Integration/1.0"
            },
            method="POST"
        )

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._access_token = data.get("access_token")
                expires_in = int(data.get("expires_in", 3600))
                self._token_expires_at = now + expires_in
                logger.info(f"Successfully obtained D&H ({self.environment}) OAuth access token (expires in {expires_in}s)")
                return self._access_token
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error(f"D&H OAuth token request failed [{err.code}]: {err_body}")
            raise ValueError(f"D&H Auth Failed (HTTP {err.code}): {err_body}")
        except Exception as exc:
            logger.error(f"Error requesting D&H OAuth token: {exc}")
            raise ValueError(f"D&H Auth Connection Error: {str(exc)}")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json",
            "dandh-tenant": self.tenant,
            "Authorization": f"Bearer {self.get_access_token()}",
            "User-Agent": "SyncABS-Dropship-Integration/1.0"
        }

    def test_connection(self) -> bool:
        """
        Verifies connectivity to D&H Catalog API by querying 10 items.
        """
        if not self.is_live():
            raise ConnectionError(
                "D&H adapter has no live credentials configured (missing bearer_token/client credentials)."
            )

        url = f"{self.base_url}/customers/{self.account_number}/items?countryOfOrigin=US&pageSize=10"
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=35) as resp:
                if resp.status in (200, 204):
                    logger.info(f"D&H {self.environment} catalog connection test passed successfully.")
                    return True
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error(f"D&H catalog test failed [HTTP {err.code}]: {err_body}")
            raise ValueError(f"D&H API Error (HTTP {err.code}): {err_body}")
        except Exception as exc:
            logger.error(f"D&H connection error: {exc}")
            raise ValueError(f"D&H Connection Error: {str(exc)}")

        return True

    def fetch_price_and_availability(self, item_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetches real-time price and per-warehouse availability for up to 50 item
        IDs at once via the Customer Order Management API. This is the ONLY
        source of truth for D&H stock quantity — the Catalog API has no
        quantity field at all. Returns a dict keyed by itemId; items D&H
        doesn't return data for (discontinued, invalid ID, etc.) are simply
        absent from the result rather than defaulted.
        """
        if not item_ids:
            return {}

        results: Dict[str, Dict[str, Any]] = {}
        ctx = ssl.create_default_context()

        for i in range(0, len(item_ids), self.PRICE_AVAILABILITY_BATCH_SIZE):
            batch = item_ids[i:i + self.PRICE_AVAILABILITY_BATCH_SIZE]
            query_str = urllib.parse.urlencode({"items": ",".join(batch)})
            url = f"{self.order_mgmt_base_url}/customers/{self.account_number}/items/priceAndAvailability/bulk?{query_str}"
            req = urllib.request.Request(url, headers=self._get_headers(), method="GET")

            try:
                with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for entry in (data or []):
                        item_id = entry.get("itemId")
                        if item_id:
                            results[item_id] = entry
            except Exception as exc:
                logger.warning(f"D&H price/availability batch lookup failed for {len(batch)} item(s): {exc}")

        return results

    def fetch_catalog(self, max_products: int = 100) -> List[NormalizedProduct]:
        """
        Fetches live products from D&H Catalog API using scrollId pagination,
        then enriches each page with real price/quantity from the Customer
        Order Management API. Items with no real price/availability data are
        skipped and recorded in self._skipped_items rather than given a
        fabricated cost or a hardcoded quantity.
        """
        if not self.is_live():
            raise ConnectionError(
                "D&H adapter has no live credentials configured (missing bearer_token/client credentials); "
                "refusing to return fabricated catalog data."
            )

        self._skipped_items = []
        products: List[NormalizedProduct] = []
        page_size = 10
        scroll_id: Optional[str] = None
        has_next = True
        ctx = ssl.create_default_context()

        try:
            while len(products) < max_products and has_next:
                params = {
                    "countryOfOrigin": "US",
                    # Note: combining sortOrder with countryOfOrigin causes D&H's
                    # API to time out server-side; omitted since scrollId already
                    # gives deterministic pagination without it.
                    "pageSize": page_size
                }
                if scroll_id:
                    params["scrollId"] = scroll_id

                query_str = urllib.parse.urlencode(params)
                url = f"{self.base_url}/customers/{self.account_number}/items?{query_str}"
                req = urllib.request.Request(url, headers=self._get_headers(), method="GET")

                try:
                    with urllib.request.urlopen(req, context=ctx, timeout=35) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        elements = data.get("elements") or []
                        if not elements:
                            break

                        # Real price + quantity for this page's items, in one batch call.
                        page_item_ids = [
                            str(el.get("itemId") or el.get("vendorItemId") or "").strip()
                            for el in elements
                        ]
                        page_item_ids = [pid for pid in page_item_ids if pid]
                        price_avail = self.fetch_price_and_availability(page_item_ids)

                        for item in elements:
                            sku = str(item.get("itemId") or item.get("vendorItemId") or "").strip()
                            if not sku:
                                continue

                            pa = price_avail.get(sku)
                            if not pa or pa.get("salesPrice") is None or pa.get("totalAvailableQuantity") is None:
                                self._skipped_items.append({
                                    "sku": sku,
                                    "reason": "No real-time price/availability returned by D&H for this item",
                                })
                                continue

                            try:
                                cost = Decimal(str(pa["salesPrice"]))
                                qty = int(pa["totalAvailableQuantity"])
                            except (ValueError, TypeError, ArithmeticError) as parse_err:
                                self._skipped_items.append({
                                    "sku": sku,
                                    "reason": f"Malformed price/availability data: {parse_err}",
                                })
                                continue

                            title = item.get("description") or f"{item.get('vendorName', '')} {sku}".strip()
                            brand = item.get("vendorName") or "D&H"
                            upc = str(item.get("universalProductCode") or "").strip()
                            if upc == "000000000000" or not upc:
                                upc = None
                            mpn = item.get("vendorItemId") or None
                            category = item.get("category") or "Consumer Electronics"
                            sub_category = item.get("subcategory") or ""

                            branch_inventory = pa.get("branchInventory") or []

                            dims = item.get("shippingDimensions") or {}
                            weight = float(dims.get("weight") or 1.0)

                            # Extract real product image from D&H API response
                            supplier_img = (
                                item.get("imageUrl")
                                or item.get("image")
                                or item.get("thumbnailUrl")
                                or item.get("imageLink")
                                or item.get("productImageUrl")
                            )
                            # Check links array if present
                            if not supplier_img:
                                for link in (item.get("links") or []):
                                    if "image" in (link.get("rel") or link.get("type") or "").lower():
                                        supplier_img = link.get("href")
                                        break

                            from app.adapters.suppliers.image_resolver import resolve_product_imagery
                            images = resolve_product_imagery(
                                brand=brand,
                                category=category,
                                subcategory=sub_category,
                                title=title,
                                sku=sku,
                                upc=upc,
                                supplier_image_url=supplier_img
                            )

                            products.append(NormalizedProduct(
                                supplier_sku=sku,
                                upc=upc,
                                ean=None,
                                mpn=mpn,
                                title=title,
                                brand=brand,
                                description=f"{title} ({sub_category})".strip(),
                                category=category,
                                images=images,
                                specs={
                                    "subcategory": sub_category,
                                    "itemType": item.get("itemType", ""),
                                    "itemStatus": item.get("itemStatus", "")
                                },
                                cost=cost,
                                quantity=qty,
                                stock_status="IN_STOCK" if qty > 0 else "OUT_OF_STOCK",
                                shipping_info={
                                    "weight_lbs": weight,
                                    "lead_time_days": 2,
                                    "branch_inventory": branch_inventory,
                                },
                                availability_status="ACTIVE" if item.get("itemStatus", "active") == "active" else "DISCONTINUED"
                            ))

                            if len(products) >= max_products:
                                break

                        has_next = bool(data.get("hasNext", False))
                        scroll_id = data.get("scrollId")
                        if not scroll_id or len(products) >= max_products:
                            break
                except Exception as page_err:
                    logger.warning(f"D&H page query finished or returned: {page_err}")
                    break

            logger.info(f"Retrieved {len(products)} live products from D&H Distributing catalog.")
            return products
        except Exception as exc:
            logger.error(f"D&H live catalog fetch error: {exc}")
            raise ConnectionError(f"D&H Connection Error: {exc}") from exc

    def fetch_inventory(self, skus: Optional[List[str]] = None) -> Dict[str, int]:
        raise NotImplementedError(
            "D&H inventory-only refresh is not implemented; use fetch_catalog(), "
            "which returns live quantities inline. Not currently called by the sync pipeline."
        )

    def fetch_price_changes(self) -> Dict[str, Decimal]:
        raise NotImplementedError(
            "D&H price-only refresh is not implemented; use fetch_catalog(), "
            "which returns live pricing inline. Not currently called by the sync pipeline."
        )
