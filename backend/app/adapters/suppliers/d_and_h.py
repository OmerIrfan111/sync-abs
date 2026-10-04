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
    # "resource.READ" alone blocks order submission (a write). Confirmed via
    # a real OAuth grant against the production credentials that both
    # "resource.WRITE" and the combined "resource.READ resource.WRITE" are
    # valid scopes (D&H's server returned scope=resource.WRITE for the
    # latter's normalized form) — requesting both in one token means catalog
    # reads and order writes both work without needing separate tokens.
    OAUTH_SCOPE = "resource.READ resource.WRITE"
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
                    logger.info(
                        f"D&H {self.environment} catalog connection test passed "
                        f"(base_url={self.base_url}, account={self.account_number})."
                    )
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

    # Wall-clock budget per sync run, comfortably under the 5-minute schedule
    # interval so successive scheduled runs don't pile up on each other.
    CATALOG_FETCH_TIME_BUDGET_SECONDS = 240

    def fetch_catalog(self, max_products: int = 50000, resume_cursor: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> List[NormalizedProduct]:
        """
        Fetches live products from D&H Catalog API using scrollId pagination.
        Supports Feature 2 prefetch filters: limit, category, brand, supplier.
        """
        filters = filters or {}
        supplier_filter = filters.get("supplier")
        if supplier_filter and supplier_filter.strip().lower() not in "d&h distributing dandh":
            return []

        limit = filters.get("limit")
        if limit is not None:
            max_products = min(max_products, int(limit))

        cat_filter = (filters.get("category") or "").strip().lower()
        brand_filter = (filters.get("brand") or "").strip().lower()

        if not self.is_live():
            raise ConnectionError(
                "D&H adapter has no live credentials configured (missing bearer_token/client credentials); "
                "refusing to return fabricated catalog data."
            )

        self._skipped_items = []
        products: List[NormalizedProduct] = []
        # 100 is the largest pageSize D&H's API reliably serves within a
        # normal request timeout (confirmed against production: 10-200 allowed,
        # must be multiple of 10; 100 returns in <35s per page).
        page_size = 100
        scroll_id: Optional[str] = resume_cursor
        has_next = True
        ctx = ssl.create_default_context()
        deadline = time.time() + self.CATALOG_FETCH_TIME_BUDGET_SECONDS
        self.next_cursor: Optional[str] = None
        self.catalog_exhausted = False
        retried_from_scratch = False
        pages_succeeded = 0
        last_page_error: Optional[Exception] = None
        # Funnel counters (logged at INFO so the sync log shows the full
        # fetch-to-import pipeline in one place).
        _funnel_raw = 0         # items returned by catalog pages
        _funnel_pa_missing = 0  # items with no P&A data returned
        _funnel_parse_err = 0   # items with malformed price/qty
        _funnel_filter_skip = 0 # items filtered by category/brand
        _funnel_accepted = 0    # items that make it into products[]

        try:
            while len(products) < max_products and has_next and time.time() < deadline:
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
                        pages_succeeded += 1
                        elements = data.get("elements") or []
                        if not elements:
                            # Reached the end of the catalog — next run starts
                            # over from the beginning to pick up price/stock changes.
                            self.catalog_exhausted = True
                            self.next_cursor = None
                            break

                        # Real price + quantity for this page's items, in one batch call.
                        page_item_ids = [
                            str(el.get("itemId") or el.get("vendorItemId") or "").strip()
                            for el in elements
                        ]
                        page_item_ids = [pid for pid in page_item_ids if pid]
                        price_avail = self.fetch_price_and_availability(page_item_ids)
                        _funnel_raw += len(elements)

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
                                _funnel_pa_missing += 1
                                continue

                            try:
                                cost = Decimal(str(pa["salesPrice"]))
                                qty = int(pa["totalAvailableQuantity"])
                            except (ValueError, TypeError, ArithmeticError) as parse_err:
                                self._skipped_items.append({
                                    "sku": sku,
                                    "reason": f"Malformed price/availability data: {parse_err}",
                                })
                                _funnel_parse_err += 1
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
                            raw_weight = dims.get("weight")
                            # No silent 1.0lb default: an untagged item has no
                            # weight, not a fabricated "1 pound" one, so real-time
                            # shipping-rate lookups can honestly skip it instead
                            # of quoting a rate against a made-up weight.
                            weight = float(raw_weight) if raw_weight else None

                            # D&H Catalog API (production) does not return any
                            # image URL fields (confirmed: imageUrl, image,
                            # thumbnailUrl, imageLink, productImageUrl, links
                            # are all absent from every catalog item). The
                            # supplier_img path is always None for D&H; the
                            # image_resolver falls back to brand/category stock
                            # photos, which is correct and expected behavior.
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
                            if cat_filter and cat_filter not in (category or "").lower():
                                _funnel_filter_skip += 1
                                continue
                            if brand_filter and brand_filter not in (brand or "").lower():
                                _funnel_filter_skip += 1
                                continue

                            images = resolve_product_imagery(
                                brand=brand,
                                category=category,
                                subcategory=sub_category,
                                title=title,
                                sku=sku,
                                upc=None,           # Never pass UPC - consumer DB returns wrong images for B2B parts
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
                            _funnel_accepted += 1

                            if len(products) >= max_products:
                                break

                        has_next = bool(data.get("hasNext", False))
                        scroll_id = data.get("scrollId")
                        if not scroll_id:
                            # No scroll token to continue with — treat as the
                            # end of what D&H will let us page through.
                            self.catalog_exhausted = True
                            self.next_cursor = None
                            break
                        if len(products) >= max_products:
                            self.next_cursor = scroll_id
                            break
                except urllib.error.HTTPError as page_err:
                    # A resumed scrollId can be expired/rejected by D&H
                    # (their scroll sessions are short-lived server-side).
                    # Restart from the beginning of the catalog once within
                    # this same run rather than failing the whole sync.
                    if scroll_id and not retried_from_scratch:
                        logger.warning(
                            f"D&H rejected resumed scrollId (HTTP {page_err.code}), "
                            "restarting catalog fetch from the beginning: " + str(page_err)
                        )
                        scroll_id = None
                        retried_from_scratch = True
                        continue
                    logger.warning(f"D&H page query failed: {page_err}")
                    last_page_error = page_err
                    self.next_cursor = scroll_id
                    break
                except Exception as page_err:
                    logger.warning(f"D&H page query finished or returned: {page_err}")
                    last_page_error = page_err
                    self.next_cursor = scroll_id
                    break

            # Every page attempt failed and nothing was ever fetched (D&H's API
            # itself erroring, not a legitimate empty catalog) — raise instead
            # of silently reporting a "successful" sync of zero products.
            if pages_succeeded == 0 and last_page_error is not None:
                raise ConnectionError(f"D&H catalog fetch failed on the first page: {last_page_error}") from last_page_error

            # Loop ended without reaching the end of the catalog (time budget
            # or max_products) — resume from here next run.
            if not self.catalog_exhausted and self.next_cursor is None and scroll_id:
                self.next_cursor = scroll_id

            logger.info(
                f"D&H fetch_catalog funnel: "
                f"raw_catalog={_funnel_raw} "
                f"no_pa={_funnel_pa_missing} "
                f"parse_err={_funnel_parse_err} "
                f"filter_skip={_funnel_filter_skip} "
                f"accepted={_funnel_accepted} "
                f"(in_stock={sum(1 for p in products if p.stock_status == 'IN_STOCK')}) "
                f"| cursor={'set' if self.next_cursor else 'none'} exhausted={self.catalog_exhausted} "
                f"env={self.environment}"
            )
            return products
        except Exception as exc:
            logger.error(f"D&H live catalog fetch error: {exc}")
            raise ConnectionError(f"D&H Connection Error: {exc}") from exc

    def submit_order(
        self,
        customer_purchase_order: str,
        line_items: List[Dict[str, Any]],
        delivery_address: Dict[str, Any],
        branch: str = "BR01",
        carrier: str = "FedEx",
        service_type: str = "Ground",
    ) -> Dict[str, Any]:
        """
        Places a REAL purchase order with D&H via POST /salesOrders. This
        spends real money — callers must only invoke this after an explicit,
        human-confirmed action, never on an automated schedule.

        line_items: [{"itemId": "<D&H item id>", "orderQuantity": <int>}, ...]
        delivery_address: {"country","city","street","postalCode","region",
                            "attention","deliveryName"}

        Built directly from D&H's Customer Order Management API 2.0.1 OpenAPI
        spec (POST /customers/{accountNumber}/salesOrders). The published
        example payload only shows {"orderQuantity": 1} per line with no item
        reference; "itemId" is inferred from this same API's own response
        schemas (every other endpoint keys items by "itemId"), not confirmed
        against a real successful order response, so the first real call
        should be verified carefully against D&H's actual response.

        Returns D&H's own response: {"id": <int>, "orderNumber": <int>, ...}.
        "id" is what GET .../salesOrders/{id}/tracking expects afterward.
        """
        if not self.is_live():
            raise ConnectionError(
                "D&H adapter has no live credentials configured; refusing to submit a real order."
            )

        url = f"{self.order_mgmt_base_url}/customers/{self.account_number}/salesOrders"
        payload = {
            "customerPurchaseOrder": customer_purchase_order,
            "shipping": {
                "serviceType": service_type,
                "carrier": carrier,
                "allowPartialShipment": True,
                "allowBackOrder": False,
            },
            "deliveryAddress": {
                "address": {
                    "country": delivery_address.get("country", "US"),
                    "city": delivery_address.get("city", ""),
                    "street": delivery_address.get("street", ""),
                    "postalCode": delivery_address.get("postalCode", ""),
                    "region": delivery_address.get("region", ""),
                },
                "attention": delivery_address.get("attention", ""),
                "deliveryName": delivery_address.get("deliveryName", ""),
            },
            "shipments": [
                {
                    "branch": branch,
                    "lines": [
                        {"itemId": li["itemId"], "orderQuantity": li["orderQuantity"]}
                        for li in line_items
                    ],
                }
            ],
        }

        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                logger.info(
                    f"D&H order placed successfully: PO {customer_purchase_order} -> "
                    f"D&H order id {result.get('id')}, order number {result.get('orderNumber')}"
                )
                return result
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error(f"D&H order submission failed [HTTP {err.code}]: {err_body}")
            raise ValueError(f"D&H Order Submission Failed (HTTP {err.code}): {err_body}")
        except Exception as exc:
            logger.error(f"D&H order submission error: {exc}")
            raise ConnectionError(f"D&H Order Submission Connection Error: {exc}") from exc

    def check_shipment_status(self, supplier_order_id: str) -> Optional[Dict[str, Any]]:
        """
        Polls D&H's real order-tracking endpoint (GET .../salesOrders/{id}/tracking)
        for shipment confirmation on a previously-submitted order. supplier_order_id
        is D&H's own "id" returned by submit_order() (not the customerPurchaseOrder).

        Returns None if not yet shipped or the lookup fails; a dict with
        tracking_number/carrier/shipped_at the first time a real manifest with
        a trackingNumber appears in the response, so staff see real supplier
        tracking automatically instead of typing it in manually.
        """
        if not self.is_live():
            return None

        url = f"{self.order_mgmt_base_url}/customers/{self.account_number}/salesOrders/{supplier_order_id}/tracking"
        req = urllib.request.Request(url, headers=self._get_headers(), method="GET")
        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning(f"D&H shipment status check failed for order {supplier_order_id}: {exc}")
            return None

        for shipment in (data.get("shipments") or []):
            for manifest in (shipment.get("manifests") or []):
                tracking_number = manifest.get("trackingNumber")
                if tracking_number:
                    return {
                        "tracking_number": tracking_number,
                        "carrier": manifest.get("carrier"),
                        "shipped_at": manifest.get("shipmentDate"),
                    }
        return None

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
