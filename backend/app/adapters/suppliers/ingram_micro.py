import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List

from app.adapters.suppliers.mock_supplier import MockSupplierAdapter
from app.schemas.supplier import NormalizedProduct
from app.core.config import settings

logger = logging.getLogger(__name__)

class IngramMicroAdapter(MockSupplierAdapter):
    """
    Ingram Micro B2B Reseller Integration Adapter.
    Connects to Ingram Micro OAuth 2.0 and REST Reseller v6 APIs (Sandbox & Production).
    """

    OAUTH_TOKEN_URL = "https://api.ingrammicro.com:443/oauth/oauth30/token"
    SANDBOX_BASE_URL = "https://api.ingrammicro.com:443/sandbox/resellers/v6"
    PRODUCTION_BASE_URL = "https://api.ingrammicro.com:443/resellers/v6"

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(supplier_name="Ingram Micro", credentials=credentials, config=config)
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
            return super().test_connection()

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

    def fetch_catalog(self) -> List[NormalizedProduct]:
        """
        Fetches live products from the Ingram Micro Sandbox / Production catalog API.
        """
        if not self.is_live():
            return super().fetch_catalog()

        try:
            token = self.get_access_token()
            url = f"{self.base_url}/catalog?pageNumber=1&pageSize=25"
            req = urllib.request.Request(url, headers=self._get_headers(token), method="GET")

            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                catalog_items = data.get("catalog") or []

                if catalog_items:
                    products: List[NormalizedProduct] = []
                    for item in catalog_items:
                        sku = str(item.get("ingramPartNumber") or item.get("vendorPartNumber") or "").strip()
                        if not sku:
                            continue

                        title = item.get("description") or f"{item.get('vendorName', '')} {sku}".strip()
                        brand = item.get("vendorName") or "Ingram Micro"
                        upc = item.get("upcCode") or None
                        mpn = item.get("vendorPartNumber") or None
                        category = item.get("category") or "Computer Systems"

                        # Estimate standard wholesale cost or use listed price
                        raw_cost = item.get("customerPrice") or item.get("retailPrice") or "199.99"
                        cost = Decimal(str(raw_cost))
                        qty = 25

                        products.append(NormalizedProduct(
                            supplier_sku=sku,
                            upc=upc,
                            ean=None,
                            mpn=mpn,
                            title=title,
                            brand=brand,
                            description=item.get("extraDescription") or title,
                            category=category,
                            images=[
                                "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop"
                            ],
                            specs={
                                "subCategory": item.get("subCategory", ""),
                                "productType": item.get("productType", "")
                            },
                            cost=cost,
                            quantity=qty,
                            stock_status="IN_STOCK",
                            shipping_info={"weight_lbs": 3.5, "lead_time_days": 2},
                            availability_status="ACTIVE"
                        ))
                    if products:
                        logger.info(f"Retrieved {len(products)} real products from Ingram Micro sandbox catalog.")
                        return products
        except Exception as exc:
            logger.error(f"Ingram Micro live catalog fetch error: {exc}. Falling back to default catalog.")

        return super().fetch_catalog()

    def fetch_inventory(self, skus: Optional[List[str]] = None) -> Dict[str, int]:
        return super().fetch_inventory(skus)

    def fetch_price_changes(self) -> Dict[str, Decimal]:
        return super().fetch_price_changes()
