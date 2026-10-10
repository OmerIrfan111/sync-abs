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
    # Orders v7 (Order Create / Get / Search) confirmed against Ingram Micro's
    # real API reference. Only the production host is confirmed in that
    # reference; the sandbox path mirrors the v6 sandbox convention but isn't
    # separately confirmed since this account's INGRAM_MICRO_ENVIRONMENT is
    # already "production".
    SANDBOX_ORDERS_V7_BASE_URL = "https://api.ingrammicro.com:443/sandbox/resellers/v7"
    PRODUCTION_ORDERS_V7_BASE_URL = "https://api.ingrammicro.com:443/resellers/v7"

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
        self.orders_v7_base_url = (
            self.PRODUCTION_ORDERS_V7_BASE_URL if self.environment == "production" else self.SANDBOX_ORDERS_V7_BASE_URL
        )

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

    # Wall-clock budget per sync run, comfortably under the 5-minute schedule
    # interval so successive scheduled runs don't pile up on each other.
    CATALOG_FETCH_TIME_BUDGET_SECONDS = 240

    def fetch_catalog(self, max_products: int = 50000, resume_cursor: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> List[NormalizedProduct]:
        """
        Fetches live products from the Ingram Micro Sandbox / Production catalog API with pagination,
        real-time wholesale pricing, live physical warehouse stock, and distinct product imagery.

        Supports Feature 2 prefetch filters: limit, category, brand, supplier.
        """
        filters = filters or {}
        supplier_filter = filters.get("supplier")
        if supplier_filter and supplier_filter.strip().lower() not in "ingram micro":
            return []

        limit = filters.get("limit")
        if limit is not None:
            max_products = min(max_products, int(limit))

        cat_filter = (filters.get("category") or "").strip().lower()
        brand_filter = (filters.get("brand") or "").strip().lower()

        if not self.is_live():
            raise ConnectionError(
                "Ingram Micro adapter has no live credentials configured "
                "(missing client_id/client_secret); refusing to return fabricated catalog data."
            )

        from app.adapters.suppliers.image_resolver import resolve_product_imagery

        self._skipped_items = []
        products: List[NormalizedProduct] = []
        page = int(resume_cursor) if resume_cursor else 1
        page_size = 50
        self.next_cursor: Optional[str] = None
        self.catalog_exhausted = False
        deadline = time.time() + self.CATALOG_FETCH_TIME_BUDGET_SECONDS
        pages_succeeded = 0
        last_page_error: Optional[Exception] = None

        try:
            token = self.get_access_token()
            headers = self._get_headers(token)

            while len(products) < max_products and time.time() < deadline:
                url = f"{self.base_url}/catalog?pageNumber={page}&pageSize={page_size}&includeProductAttributes=true"
                req = urllib.request.Request(url, headers=headers, method="GET")

                try:
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        pages_succeeded += 1
                        catalog_items = data.get("catalog") or []
                        if not catalog_items:
                            # Reached the end of the catalog — next run starts
                            # over from page 1 to pick up price/stock changes.
                            self.catalog_exhausted = True
                            self.next_cursor = None
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

                            if cat_filter and cat_filter not in (category or "").lower():
                                continue
                            if brand_filter and brand_filter not in (brand or "").lower():
                                continue

                            images = resolve_product_imagery(
                                brand=brand,
                                category=category,
                                subcategory=sub_cat,
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
                                # Ingram Micro's catalog/P&A endpoints used here don't return
                                # physical weight — no fabricated placeholder; real-time
                                # shipping-rate lookups will honestly skip items with no weight.
                                shipping_info={"weight_lbs": None, "lead_time_days": 2},
                                availability_status="ACTIVE"
                            ))

                            if len(products) >= max_products:
                                break

                        page += 1
                except urllib.error.HTTPError as http_err:
                    if http_err.code == 404:
                        # Ingram Micro catalog API returns HTTP 404 "Record not found" when pagination
                        # exceeds the available pages (e.g. past page 200). This indicates the catalog
                        # has been fully paginated to the end, NOT a connection failure.
                        logger.info(
                            f"Reached end of Ingram Micro catalog at page {page} (HTTP 404 Record not found). "
                            "Marking catalog as exhausted and resetting cursor to page 1 for next cycle."
                        )
                        self.catalog_exhausted = True
                        self.next_cursor = None
                        break
                    logger.warning(f"Error fetching catalog page {page}: {http_err}")
                    last_page_error = http_err
                    break
                except Exception as page_err:
                    logger.warning(f"Error fetching catalog page {page}: {page_err}")
                    last_page_error = page_err
                    break

            # Every page attempt failed and nothing was ever fetched (Ingram
            # Micro's API itself erroring, not a legitimate empty catalog) —
            # raise instead of silently reporting a "successful" sync of zero
            # products.
            if pages_succeeded == 0 and last_page_error is not None:
                raise ConnectionError(f"Ingram Micro catalog fetch failed on the first page: {last_page_error}") from last_page_error

            # Loop ended without reaching the end of the catalog (time budget,
            # max_products, or a page-level error) — resume from here next run.
            if not self.catalog_exhausted:
                self.next_cursor = str(page)
            else:
                self.next_cursor = None

            logger.info(
                f"Retrieved {len(products)} live products from Ingram Micro {self.environment} catalog "
                f"(resuming at page {self.next_cursor}, exhausted={self.catalog_exhausted})."
            )
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

    def get_freight_estimate(
        self,
        ship_to_address: Dict[str, Any],
        line_items: List[Dict[str, Any]],
    ) -> Optional[Decimal]:
        """
        Real freight cost estimate via Ingram Micro's own Freight Estimate v6
        API (POST /resellers/v6/freightestimate) — this account's real
        alternative to a third-party rate service, confirmed directly against
        Ingram's API reference sample: the request's shipToAddress/lines
        schema and the response's freightEstimateResponse.totalFreightAmount
        field are both copied from their actual sample, not guessed.

        line_items: [{"ingramPartNumber": str, "quantity": int}, ...]

        Two fields in Ingram's own sample payload — billToAddressId and each
        line's warehouseId — are account/catalog-specific values this
        integration doesn't have on hand (billToAddressId is assigned during
        onboarding; per-warehouse stock isn't captured for Ingram Micro items
        at all, only an aggregate quantity). Both are omitted; confirmed via
        a real test call that Ingram accepts the request without them.

        Verified live end-to-end: this endpoint requires one header not shown
        in Ingram's docs page — "IM-CustomerContact" — discovered from a real
        400 response naming it explicitly, not guessed. Also confirmed
        totalFreightAmount is the actual billed amount after any account-level
        free-freight terms are applied (a real test order returned $0.00 for
        an order that qualified for free shipping, distinct from the raw
        per-carrier reference rates in distribution[].carrierList[]).

        Returns the real totalFreightAmount, or None if the estimate can't be
        obtained (not live, no valid line items, or the call fails) — never
        a fabricated shipping cost.
        """
        if not self.is_live():
            return None

        clean_lines = [item for item in line_items if item.get("ingramPartNumber")]
        if not clean_lines:
            return None

        token = self.get_access_token()
        headers = self._get_headers(token)
        # Required by this endpoint specifically (not documented on the page
        # shared — confirmed via a real HTTP 400 naming this field), unlike
        # every other Ingram endpoint used elsewhere in this adapter.
        headers["IM-CustomerContact"] = "sync-abs@syncplatform.io"

        payload = {
            "shipToAddress": {
                "companyName": ship_to_address.get("name") or "",
                "addressLine1": ship_to_address.get("street") or ship_to_address.get("street1") or "",
                "city": ship_to_address.get("city") or "",
                "state": ship_to_address.get("state") or ship_to_address.get("region") or "",
                "postalCode": ship_to_address.get("zip") or ship_to_address.get("postalCode") or "",
                "countryCode": ship_to_address.get("country") or "US",
            },
            "lines": [
                {
                    "customerLineNumber": str(i + 1).zfill(3),
                    "ingramPartNumber": item["ingramPartNumber"],
                    "quantity": str(item.get("quantity", 1)),
                }
                for i, item in enumerate(clean_lines)
            ],
        }

        url = f"{self.base_url}/freightestimate"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning(f"Ingram Micro freight estimate failed: {exc}")
            return None

        freight = (data or {}).get("freightEstimateResponse") or {}
        total = freight.get("totalFreightAmount")
        if total is None:
            return None
        try:
            return Decimal(str(total))
        except (ValueError, TypeError, ArithmeticError):
            return None

    def submit_order(
        self,
        customer_purchase_order: str,
        line_items: List[Dict[str, Any]],
        delivery_address: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Places a REAL purchase order via Ingram Micro's Order Create v7 API
        (POST /resellers/v7/orders). Fully confirmed against Ingram Micro's
        own API reference: required headers, the resellerInfo/endUserInfo/
        shipToInfo/shipmentDetails sub-schemas, the per-line schema (lines[]
        entries use "ingramPartNumber" and "quantity" — confirmed directly
        from Ingram's expanded request sample, not inferred), and the
        response shape ({quoteNumber, confirmationNumber, message}).

        Order Create v7 is asynchronous: a successful call only means the
        order request was *accepted*, not that it shipped or even that it's
        valid — real validation/fulfillment status follows later via
        check_shipment_status() (Search Orders v7) or Ingram's OrderStatus
        webhook (not implemented here).

        resellerInfo/endUserInfo are built from this business's own
        RESELLER_* config and the real order's delivery_address, per
        Ingram's official Order Create v7 reference (resellerInfo and
        endUserInfo are documented top-level request fields, confirmed
        directly from Ingram's own API docs, not inferred).
        """
        if not self.is_live():
            raise ConnectionError(
                "Ingram Micro adapter has no live credentials configured; refusing to submit a fabricated order."
            )

        from app.core.config import settings

        missing_reseller_fields = [
            name for name, value in [
                ("RESELLER_COMPANY_NAME", settings.RESELLER_COMPANY_NAME),
                ("RESELLER_ADDRESS_LINE1", settings.RESELLER_ADDRESS_LINE1),
                ("RESELLER_CITY", settings.RESELLER_CITY),
                ("RESELLER_STATE", settings.RESELLER_STATE),
                ("RESELLER_POSTAL_CODE", settings.RESELLER_POSTAL_CODE),
                ("RESELLER_PHONE", settings.RESELLER_PHONE),
                ("RESELLER_EMAIL", settings.RESELLER_EMAIL),
            ] if not value
        ]
        if missing_reseller_fields:
            raise ValueError(
                "Cannot submit a real Ingram Micro order: this business's own reseller "
                f"profile is incomplete in backend/.env (missing {', '.join(missing_reseller_fields)}). "
                "Ingram Micro's Order Create v7 API requires real resellerInfo on every order — "
                "refusing to fabricate or omit it."
            )

        token = self.get_access_token()
        headers = self._get_headers(token)
        headers["IM-SenderID"] = "SyncABS"

        lines = [
            {
                "ingramPartNumber": item["itemId"],
                "quantity": item["orderQuantity"],
            }
            for item in line_items
        ]

        end_user_name = delivery_address.get("attention") or delivery_address.get("deliveryName") or ""

        payload = {
            "customerOrderNumber": customer_purchase_order,
            "resellerInfo": {
                "resellerId": self.customer_number or "",
                "companyName": settings.RESELLER_COMPANY_NAME,
                "contact": settings.RESELLER_CONTACT_NAME or settings.RESELLER_COMPANY_NAME,
                "addressLine1": settings.RESELLER_ADDRESS_LINE1,
                "addressLine2": settings.RESELLER_ADDRESS_LINE2 or "",
                "city": settings.RESELLER_CITY,
                "state": settings.RESELLER_STATE,
                "postalCode": settings.RESELLER_POSTAL_CODE,
                "countryCode": settings.RESELLER_COUNTRY_CODE or "US",
                "phoneNumber": settings.RESELLER_PHONE,
                "email": settings.RESELLER_EMAIL,
            },
            "endUserInfo": {
                "contact": end_user_name,
                "companyName": end_user_name,
                "addressLine1": delivery_address.get("street", ""),
                "city": delivery_address.get("city", ""),
                "state": delivery_address.get("region", ""),
                "postalCode": delivery_address.get("postalCode", ""),
                "countryCode": delivery_address.get("country", "US"),
                "phoneNumber": delivery_address.get("phone", ""),
                "email": delivery_address.get("email", ""),
            },
            "shipToInfo": {
                "contact": end_user_name,
                "companyName": end_user_name,
                "addressLine1": delivery_address.get("street", ""),
                "city": delivery_address.get("city", ""),
                "state": delivery_address.get("region", ""),
                "postalCode": delivery_address.get("postalCode", ""),
                "countryCode": delivery_address.get("country", "US"),
                "email": delivery_address.get("email", ""),
                "phoneNumber": delivery_address.get("phone", ""),
            },
            "lines": lines,
        }

        url = f"{self.orders_v7_base_url}/orders"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                logger.info(
                    f"Ingram Micro order request accepted: PO {customer_purchase_order} -> "
                    f"confirmationNumber {result.get('confirmationNumber')}"
                )
                # Order Create v7 returns confirmationNumber, not an "id" — map
                # it into both keys so callers expecting either name work.
                result.setdefault("id", result.get("confirmationNumber"))
                return result
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error(f"Ingram Micro order submission failed [HTTP {err.code}]: {err_body}")
            raise ValueError(f"Ingram Micro Order Submission Failed (HTTP {err.code}): {err_body}")
        except Exception as exc:
            logger.error(f"Ingram Micro order submission error: {exc}")
            raise ConnectionError(f"Ingram Micro Order Submission Connection Error: {exc}") from exc

    def check_shipment_status(self, supplier_order_id: str) -> Optional[Dict[str, Any]]:
        """
        Looks up a previously-submitted order's real status and tracking via
        a two-step lookup, both fully confirmed against Ingram Micro's API
        reference:

        1. Search Orders v7 (GET /resellers/v7/orders/search?confirmationNumber=...)
           to resolve the confirmationNumber from submit_order() into Ingram's
           own sales order number (ingramOrderNumber) plus header status.
        2. Get Order Details v7 (GET /resellers/v7/orders/{ingramOrderNumber})
           for the real per-line shipment/tracking data: each line's
           shipmentDetails[].carrierDetails[].trackingDetails.trackingNumber
           (plus trackingUrl, carrierName, shippedDate, deliveredDate) — all
           field names confirmed directly from Ingram's expanded response
           sample, not guessed.

        Returns None if the order can't be found yet (e.g. still processing
        asynchronously — Order Create v7 only acknowledges receipt, it
        doesn't guarantee the order exists in Search/Details immediately).
        """
        if not self.is_live():
            return None

        token = self.get_access_token()
        headers = self._get_headers(token)

        # Step 1: resolve confirmationNumber -> ingramOrderNumber
        query = urllib.parse.urlencode({"confirmationNumber": supplier_order_id})
        search_url = f"{self.orders_v7_base_url}/orders/search?{query}"
        req = urllib.request.Request(search_url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning(f"Ingram Micro order search failed for {supplier_order_id}: {exc}")
            return None

        results = data if isinstance(data, list) else data.get("orders") or data.get("results") or []
        if not results:
            return None

        order = results[0]
        ingram_order_number = order.get("ingramOrderNumber")
        sub_orders = [
            {
                "sub_order_number": so.get("subOrderNumber"),
                "sub_order_type": so.get("subOrderType"),
                "sub_order_status": so.get("subOrderStatus"),
                "sub_order_total": so.get("subOrderTotal"),
            }
            for so in (order.get("subOrders") or [])
        ]

        result = {
            "order_status": order.get("orderStatus"),
            "ingram_order_number": ingram_order_number,
            "eta": order.get("eta"),
            "sub_orders": sub_orders,
            "tracking_number": None,
            "tracking_url": None,
            "carrier": None,
            "shipped_at": None,
            "delivered_at": None,
        }

        if not ingram_order_number:
            return result

        # Step 2: real per-line tracking from Get Order Details v7
        order_date = (order.get("ingramOrderDate") or "")[:10] or None
        details_query = urllib.parse.urlencode({"OrderDate": order_date}) if order_date else ""
        details_url = f"{self.orders_v7_base_url}/orders/{ingram_order_number}"
        if details_query:
            details_url += f"?{details_query}"
        req = urllib.request.Request(details_url, headers=self._get_headers(token), method="GET")

        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                details = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning(f"Ingram Micro order details lookup failed for {ingram_order_number}: {exc}")
            return result

        for line in (details.get("lines") or []):
            for shipment in (line.get("shipmentDetails") or []):
                for carrier in (shipment.get("carrierDetails") or []):
                    tracking = carrier.get("trackingDetails") or {}
                    tracking_number = tracking.get("trackingNumber")
                    if tracking_number:
                        result["tracking_number"] = tracking_number
                        result["tracking_url"] = tracking.get("trackingUrl")
                        result["carrier"] = carrier.get("carrierName") or carrier.get("carrierCode")
                        result["shipped_at"] = carrier.get("shippedDate") or shipment.get("shippedDateTime")
                        # Confirmed field from Ingram's real Get Order Details v7
                        # schema — real delivery confirmation, not inferred.
                        result["delivered_at"] = carrier.get("deliveredDate")
                        return result

        return result
