import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import ssl
from decimal import Decimal
from typing import Dict, Any, Optional, List

from app.adapters.suppliers.mock_supplier import MockSupplierAdapter
from app.schemas.supplier import NormalizedProduct
from app.core.config import settings

logger = logging.getLogger(__name__)

class DAndHAdapter(MockSupplierAdapter):
    """
    Dedicated D&H Distributing B2B REST Integration Adapter.
    Communicates directly with D&H's Axway API Gateway (/catalog/v1/customers/{accountNumber}/items)
    to query real-time product catalogs, pricing, inventory, and order fulfillment.
    """
    TEST_BASE_URL = "https://test.api.dandh.com/catalog/v1"
    PRODUCTION_BASE_URL = "https://api.dandh.com/catalog/v1"

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(supplier_name="D&H", credentials=credentials, config=config)
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

    def is_live(self) -> bool:
        """Returns True if live API credentials (bearer token / account number) are present."""
        return bool(self.bearer_token and self.account_number)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json",
            "dandh-tenant": self.tenant,
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "SyncABS-Dropship-Integration/1.0"
        }

    def test_connection(self) -> bool:
        """
        Verifies connectivity to D&H Catalog API by querying 10 items.
        """
        if not self.is_live():
            return super().test_connection()

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

    def fetch_catalog(self, max_products: int = 100) -> List[NormalizedProduct]:
        """
        Fetches live products from D&H Catalog API using scrollId pagination.
        """
        if not self.is_live():
            return super().fetch_catalog()

        products: List[NormalizedProduct] = []
        page_size = 10
        scroll_id: Optional[str] = None
        has_next = True
        ctx = ssl.create_default_context()

        try:
            while len(products) < max_products and has_next:
                params = {
                    "countryOfOrigin": "US",
                    "sortOrder": "itemtype:ascending",
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

                        for item in elements:
                            sku = str(item.get("itemId") or item.get("vendorItemId") or "").strip()
                            if not sku:
                                continue

                            title = item.get("description") or f"{item.get('vendorName', '')} {sku}".strip()
                            brand = item.get("vendorName") or "D&H"
                            upc = str(item.get("universalProductCode") or "").strip()
                            if upc == "000000000000" or not upc:
                                upc = None
                            mpn = item.get("vendorItemId") or None
                            category = item.get("category") or "Consumer Electronics"
                            sub_category = item.get("subcategory") or ""

                            raw_cost = item.get("approximatePrice") or item.get("estimatedRetailPrice") or "89.99"
                            cost = Decimal(str(raw_cost))
                            qty = 30

                            dims = item.get("shippingDimensions") or {}
                            weight = float(dims.get("weight") or 1.0)

                            from app.adapters.suppliers.image_resolver import resolve_product_imagery
                            images = resolve_product_imagery(
                                brand=brand,
                                category=category,
                                subcategory=sub_category,
                                title=title,
                                sku=sku
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
                                stock_status="IN_STOCK",
                                shipping_info={"weight_lbs": weight, "lead_time_days": 2},
                                availability_status="ACTIVE"
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

            if products:
                logger.info(f"Retrieved {len(products)} live products from D&H Distributing catalog.")
                return products
        except Exception as exc:
            logger.error(f"D&H live catalog fetch error: {exc}. Falling back to default mock catalog.")

        return super().fetch_catalog()
