import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List

from app.adapters.suppliers.base import SupplierAdapter
from app.schemas.supplier import NormalizedProduct
from app.core.config import settings

logger = logging.getLogger(__name__)

class IngramMicroAdapter(SupplierAdapter):
    """
    Ingram Micro B2B Reseller Integration Adapter.
    Connects to Ingram Micro OAuth 2.0 and REST Reseller v6 APIs (Sandbox & Production).

    Deliberately does NOT inherit from MockSupplierAdapter. It previously did,
    using it as a "not live" fallback — which meant any credential hiccup
    (missing config, a decrypt failure, a transient auth error) silently
    returned fabricated mock catalog data reported as a successful sync, with
    no error anywhere. Real fake products from that bug ended up published on
    a live store. Now every non-live/failure path raises instead.
    """

    OAUTH_TOKEN_URL = "https://api.ingrammicro.com:443/oauth/oauth30/token"
    SANDBOX_BASE_URL = "https://api.ingrammicro.com:443/sandbox/resellers/v6"
    PRODUCTION_BASE_URL = "https://api.ingrammicro.com:443/resellers/v6"

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials=credentials, config=config)
        self.supplier_name = "Ingram Micro"
        self.credentials = credentials or {}

        # Extract credentials with fallback to environment settings
        self.client_id = (
            self.credentials.get("client_id")
            or getattr(settings, "INGRAM_MICRO_CLIENT_ID", None)
            or ""
        ).strip()
        self.client_secret = (
            self.credentials.get("client_secret")
            or getattr(settings, "INGRAM_MICRO_CLIENT_SECRET", None)
            or ""
        ).strip()
        self.customer_number = (
            self.credentials.get("customer_number")
            or getattr(settings, "INGRAM_MICRO_CUSTOMER_NUMBER", None)
            or "21-186632"
        ).strip()
        self.country_code = (self.credentials.get("country_code") or "US").strip().upper()
        
        env = (self.credentials.get("environment") or getattr(settings, "INGRAM_MICRO_ENVIRONMENT", "sandbox")).lower()
        self.environment = "production" if env == "production" else "sandbox"
        self.base_url = self.PRODUCTION_BASE_URL if self.environment == "production" else self.SANDBOX_BASE_URL

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

        # Items skipped during the last fetch_catalog() call because Ingram
        # didn't return real price/availability data for them. Read by
        # SyncService afterward to log MISSING_DATA errors visible on the
        # dashboard, rather than silently fabricating a category-average price.
        self._skipped_items: List[Dict[str, str]] = []

    def is_live(self) -> bool:
        """Returns True if live API credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def get_access_token(self) -> str:
        """
        Retrieves or refreshes OAuth 2.0 Bearer access token from Ingram Micro identity service.
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        if not self.client_id or not self.client_secret:
            raise ValueError("Ingram Micro integration requires client_id and client_secret.")

        token_data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }).encode("utf-8")

        req = urllib.request.Request(
            self.OAUTH_TOKEN_URL,
            data=token_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "SyncABS-Dropship-Integration/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._access_token = data.get("access_token")
                expires_in = int(data.get("expires_in", 3600))
                self._token_expires_at = now + expires_in
                logger.info(f"Successfully obtained Ingram Micro access token (expires in {expires_in}s)")
                return self._access_token
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error(f"Ingram Micro token request failed [{err.code}]: {err_body}")
            raise ValueError(f"Ingram Micro Auth Failed (HTTP {err.code}): {err_body}")
        except Exception as exc:
            logger.error(f"Error requesting Ingram Micro token: {exc}")
            raise ValueError(f"Ingram Micro Auth Connection Error: {str(exc)}")

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Build standard Ingram Micro v6 REST request headers with <= 32 char correlation ID."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "IM-CustomerNumber": self.customer_number,
            "IM-CountryCode": self.country_code,
            "IM-CorrelationID": uuid.uuid4().hex[:32]
        }

    def test_connection(self) -> bool:
        """
        Verifies connectivity by authenticating against Ingram Micro OAuth and querying catalog endpoint.
        """
        if not self.is_live():
            raise ConnectionError(
                "Ingram Micro adapter has no live credentials configured "
                "(missing client_id/client_secret)."
            )

        # Step 1: Request an OAuth token
        token = self.get_access_token()
        if not token:
            raise ValueError("Failed to obtain Ingram Micro access token.")

        # Step 2: Validate live catalog API access
        url = f"{self.base_url}/catalog?pageNumber=1&pageSize=1"
        req = urllib.request.Request(url, headers=self._get_headers(token), method="GET")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 204):
                    logger.info("Ingram Micro Sandbox connection test passed successfully.")
                    return True
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error(f"Ingram Micro catalog test returned HTTP {err.code}: {err_body}")
            raise ValueError(f"Ingram Micro Catalog API error ({err.code}): {err_body}")

        return True

    def fetch_price_and_availability(self, skus: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Batch queries live wholesale pricing and warehouse inventory from Ingram Micro.
        """
        if not self.is_live() or not skus:
            return {}

        results: Dict[str, Dict[str, Any]] = {}
        try:
            token = self.get_access_token()
            url = f"{self.base_url}/catalog/priceandavailability?includePricing=true&includeAvailability=true"
            body = json.dumps({
                "products": [{"ingramPartNumber": s} for s in skus[:50]]
            }).encode("utf-8")

            req = urllib.request.Request(url, data=body, headers=self._get_headers(token), method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data:
                    part_no = item.get("ingramPartNumber")
                    if part_no:
                        results[part_no] = item
        except Exception as exc:
            logger.warning(f"Error fetching batch price & availability: {exc}")

        return results

    def fetch_catalog(self, max_products: int = 250) -> List[NormalizedProduct]:
        """
        Fetches live products from the Ingram Micro Sandbox / Production catalog API with pagination,
        real-time wholesale pricing, live physical warehouse stock, and distinct product imagery.
        """
        if not self.is_live():
            raise ConnectionError(
                "Ingram Micro adapter has no live credentials configured "
                "(missing client_id/client_secret); refusing to return fabricated catalog data."
            )

        from app.adapters.suppliers.image_resolver import resolve_product_imagery

        self._skipped_items = []
        products: List[NormalizedProduct] = []
        page = 1
        page_size = 50

        try:
            token = self.get_access_token()
            headers = self._get_headers(token)

            while len(products) < max_products and page <= 10:
                url = f"{self.base_url}/catalog?pageNumber={page}&pageSize={page_size}&includeProductAttributes=true"
                req = urllib.request.Request(url, headers=headers, method="GET")

                try:
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        catalog_items = data.get("catalog") or []
                        if not catalog_items:
                            break

                        # Batch fetch live wholesale cost and warehouse stock
                        page_skus = [it.get("ingramPartNumber") for it in catalog_items if it.get("ingramPartNumber")]
                        pa_map = self.fetch_price_and_availability(page_skus)

                        for item in catalog_items:
                            sku = str(item.get("ingramPartNumber") or item.get("vendorPartNumber") or "").strip()
                            if not sku:
                                continue

                            title = item.get("description") or f"{item.get('vendorName', '')} {sku}".strip()
                            brand = item.get("vendorName") or "Ingram Micro"
                            upc = item.get("upcCode") or None
                            mpn = item.get("vendorPartNumber") or None
                            category = item.get("category") or "Computer Systems"
                            sub_cat = item.get("subCategory") or ""

                            # Real pricing & stock from live P&A endpoint
                            pa_item = pa_map.get(sku) or {}
                            pa_pricing = pa_item.get("pricing") or {}
                            pa_avail = pa_item.get("availability") or {}

                            raw_cost = (
                                pa_pricing.get("customerPrice")
                                or pa_pricing.get("retailPrice")
                                or item.get("customerPrice")
                                or item.get("retailPrice")
                            )
                            if not raw_cost or Decimal(str(raw_cost)) <= 0:
                                self._skipped_items.append({
                                    "sku": sku,
                                    "reason": "No real-time price returned by Ingram Micro for this item",
                                })
                                continue

                            cost = Decimal(str(raw_cost))
                            qty = pa_avail.get("totalAvailability")
                            if qty is None:
                                self._skipped_items.append({
                                    "sku": sku,
                                    "reason": "No real-time availability returned by Ingram Micro for this item",
                                })
                                continue
                            qty = max(0, int(qty))

                            stock_status = "IN_STOCK" if qty > 0 else "OUT_OF_STOCK"

                            # Extract real product image from Ingram API response
                            supplier_img = None
                            product_attrs = item.get("links") or []
                            for link in product_attrs:
                                if link.get("type") in ("image", "Image") or "image" in (link.get("topic") or "").lower():
                                    supplier_img = link.get("href")
                                    break
                            if not supplier_img:
                                # Check alternative image fields in the response
                                supplier_img = (
                                    item.get("imageUrl")
                                    or item.get("productImage")
                                    or item.get("image")
                                    or item.get("thumbnailUrl")
                                )
                            # Also check price & availability response for image
                            if not supplier_img and pa_item:
                                supplier_img = (
                                    pa_item.get("imageUrl")
                                    or pa_item.get("productImage")
                                )

                            images = resolve_product_imagery(
                                brand=brand,
                                category=category,
                                subcategory=sub_cat,
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
                                description=item.get("extraDescription") or title,
                                category=category,
                                images=images,
                                specs={
                                    "subCategory": sub_cat,
                                    "productType": item.get("productType", "")
                                },
                                cost=cost,
                                quantity=qty,
                                stock_status=stock_status,
                                shipping_info={"weight_lbs": 3.5, "lead_time_days": 2},
                                availability_status="ACTIVE"
                            ))

                            if len(products) >= max_products:
                                break

                        page += 1
                except Exception as page_err:
                    logger.warning(f"Error fetching catalog page {page}: {page_err}")
                    break

            logger.info(f"Retrieved {len(products)} live products across {page-1} pages from Ingram Micro {self.environment} catalog.")
            return products
        except Exception as exc:
            logger.error(f"Ingram Micro live catalog fetch error: {exc}")
            raise ConnectionError(f"Ingram Micro Connection Error: {exc}") from exc

    def fetch_inventory(self, skus: Optional[List[str]] = None) -> Dict[str, int]:
        raise NotImplementedError(
            "Ingram Micro inventory-only refresh is not implemented; use fetch_catalog(), "
            "which returns live quantities inline. Not currently called by the sync pipeline."
        )

    def fetch_price_changes(self) -> Dict[str, Decimal]:
        raise NotImplementedError(
            "Ingram Micro price-only refresh is not implemented; use fetch_catalog(), "
            "which returns live pricing inline. Not currently called by the sync pipeline."
        )
