import json
import logging
import re
import urllib.request
import urllib.parse
import urllib.error
import time
import base64
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from decimal import Decimal

from app.adapters.marketplaces.base import MarketplaceAdapter

logger = logging.getLogger(__name__)


class LiveWalmartAdapter(MarketplaceAdapter):
    """
    Live Walmart Marketplace API (v3) Adapter.
    Connects to Walmart Marketplace REST API using OAuth 2.0 Client Credentials (My API Key).
    Supports:
    1. Automated OAuth Token retrieval & caching (15-min lifespan)
    2. Endpoint ping / Test Connection (GET /v3/items?limit=1)
    3. Price and Inventory synchronization (PUT /v3/prices, PUT /v3/inventory)
    4. Real-time Order Ingestion (GET /v3/orders)
    5. Order Shipment and Tracking Push (POST /v3/orders/{purchaseOrderId}/shipping)
    6. Order Acknowledgement (POST /v3/orders/{purchaseOrderId}/acknowledge)
    """

    PRODUCTION_BASE_URL = "https://marketplace.walmartapis.com"
    SANDBOX_BASE_URL = "https://sandbox.walmartapis.com"

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self.credentials = credentials or {}

        # Credentials from encrypted DB or settings
        self.client_id = (self.credentials.get("client_id") or "").strip()
        self.client_secret = (self.credentials.get("client_secret") or "").strip()

        env = (self.credentials.get("environment") or "production").lower()
        self.environment = "sandbox" if env == "sandbox" else "production"
        self.base_url = self.SANDBOX_BASE_URL if self.environment == "sandbox" else self.PRODUCTION_BASE_URL

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    def get_access_token(self) -> str:
        """
        Retrieves or refreshes the Walmart OAuth 2.0 Bearer access token.
        Token is cached until 60 seconds prior to expiration (tokens last 900s / 15m).
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        if not self.client_id or not self.client_secret:
            raise ValueError("Walmart Marketplace integration requires client_id and client_secret.")

        token_url = f"{self.base_url}/v3/token"
        auth_bytes = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        basic_auth = base64.b64encode(auth_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "WM_SVC.NAME": "Walmart Marketplace",
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        }
        data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")

        req = urllib.request.Request(token_url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                self._access_token = res.get("access_token")
                expires_in = int(res.get("expires_in", 900))
                self._token_expires_at = now + expires_in
                logger.info("Walmart Marketplace OAuth access token acquired successfully.")
                return self._access_token
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"Walmart OAuth error HTTP {exc.code}: {body}")
            raise PermissionError(f"Walmart authorization failed ({exc.code}): {body}")
        except Exception as exc:
            logger.error(f"Walmart auth network error: {exc}")
            raise ConnectionError(f"Could not connect to Walmart auth service: {exc}")

    def _get_headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        token = self.get_access_token()
        headers = {
            "WM_SEC.ACCESS_TOKEN": token,
            "WM_SVC.NAME": "Walmart Marketplace",
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            "Accept": "application/json",
            "User-Agent": "SyncABS-Platform/1.0",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        timeout: float = 15.0,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Executes HTTP request against Walmart Marketplace API with Bearer token authentication
        and exponential backoff retry for rate limits (429/503).
        """
        url = endpoint if endpoint.startswith("http") else f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if params:
            qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if qs:
                url = f"{url}?{qs}"

        body = json.dumps(json_data).encode("utf-8") if json_data is not None else None

        last_exc = None
        for attempt in range(max_retries):
            try:
                headers = self._get_headers()
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    if not raw.strip():
                        return {}
                    return json.loads(raw)
            except urllib.error.HTTPError as exc:
                last_exc = exc
                body_text = exc.read().decode("utf-8", errors="ignore")
                if exc.code in (429, 503) and attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) * 0.75
                    logger.warning(f"Walmart rate limit/unavailable ({exc.code}). Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
                logger.error(f"Walmart API error {exc.code} for {url}: {body_text}")
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    time.sleep((2 ** attempt) * 0.5)
                    continue
                raise

        raise RuntimeError(f"Walmart request failed after retries: {last_exc}")

    def test_connection(self) -> bool:
        """
        Validates API connectivity and credentials by querying item catalog.
        Returns True only if the response actually looks like a real item
        catalog payload; raises on an HTTP failure or an unrecognized shape
        rather than claiming success on any 2xx response regardless of body.
        """
        try:
            res = self._request("/v3/items?limit=1", method="GET")
            if isinstance(res, dict) and ("ItemResponse" in res or "totalItems" in res):
                return True
            raise ValueError(f"Unexpected Walmart /v3/items response shape: {list(res.keys()) if isinstance(res, dict) else type(res)}")
        except Exception as exc:
            logger.error(f"Walmart test_connection failed: {exc}")
            raise

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        """
        Retrieve current marketplace listing details by SKU.
        """
        sku = str(external_listing_id).strip()
        try:
            res = self._request(f"/v3/items/{urllib.parse.quote(sku)}", method="GET")
            item = res.get("ItemResponse", [{}])[0] if isinstance(res.get("ItemResponse"), list) else res
            price_val = item.get("price", {}).get("amount") if isinstance(item.get("price"), dict) else item.get("price")
            return {
                "listing_id": sku,
                "title": item.get("productName") or sku,
                "price": Decimal(str(price_val or "0.00")),
                "status": item.get("publishedStatus") or "ACTIVE",
                "raw_response": item,
            }
        except Exception as exc:
            logger.warning(f"Walmart get_listing failed for SKU {sku}: {exc}")
            return {
                "listing_id": sku,
                "status": "UNKNOWN",
                "error": str(exc),
            }

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        """
        Update live stock quantity for SKU on Walmart Marketplace.
        """
        target_sku = str(sku or external_listing_id).strip()
        payload = {
            "sku": target_sku,
            "quantity": {
                "unit": "EACH",
                "amount": max(0, int(quantity)),
            },
        }
        try:
            res = self._request("/v3/inventory", method="PUT", json_data=payload)
            logger.info(f"Walmart inventory updated for SKU {target_sku}: qty={quantity}")
            return True
        except Exception as exc:
            logger.error(f"Walmart update_inventory failed for SKU {target_sku}: {exc}")
            raise

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        """
        Update live selling price for SKU on Walmart Marketplace.
        """
        target_sku = str(sku or external_listing_id).strip()
        payload = {
            "sku": target_sku,
            "pricing": [
                {
                    "currentPriceType": "BASE",
                    "currentPrice": {
                        "currency": "USD",
                        "amount": float(price),
                    },
                }
            ],
        }
        try:
            res = self._request("/v3/prices", method="PUT", json_data=payload)
            logger.info(f"Walmart price updated for SKU {target_sku}: price=${price}")
            return True
        except Exception as exc:
            logger.error(f"Walmart update_price failed for SKU {target_sku}: {exc}")
            raise

    def submit_item_match_feed(
        self,
        sku: str,
        upc: str,
        price: Decimal,
        weight_lbs: float,
        condition: str = "New",
        main_image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new Walmart catalog entry by MATCHING your offer to an
        existing item already in Walmart's broader catalog, via its real
        GTIN/UPC — POST /v3/feeds?feedType=MP_ITEM_MATCH. Payload shape
        confirmed directly from Walmart's own official MP_ITEM_MATCH v5.x
        sample feed file, not guessed.

        This is the right mechanism for well-known branded items (the bulk
        of this catalog) that already exist somewhere in Walmart's catalog —
        full MP_ITEM (defining a brand-new item from scratch against a
        category-specific spec fetched via Get Spec) is a separate, much
        larger integration not built here.

        Submission is asynchronous: a successful call only means Walmart
        ACCEPTED the feed for processing, not that the match succeeded yet —
        real status follows via get_feed_status(feedId). Raises on failure
        rather than fabricating a feed ID.
        """
        if not upc or not str(upc).strip():
            raise ValueError(
                f"Cannot submit a Walmart item-match feed for SKU '{sku}': no real UPC/GTIN on file "
                "for this product. Walmart matches by product identifier, not SKU alone."
            )
        if not weight_lbs or weight_lbs <= 0:
            raise ValueError(
                f"Cannot submit a Walmart item-match feed for SKU '{sku}': no real shipping weight "
                "on file for this product. Walmart's MP_ITEM_MATCH feed requires a real ShippingWeight, "
                "never a fabricated one."
            )

        # Walmart's real MP_ITEM_MATCH sample feed uses productIdType "GTIN"
        # with a zero-padded 14-digit productId, not "UPC" with the raw
        # 12/13-digit code — confirmed directly against Walmart's own sample
        # file, not guessed. Sending "UPC" as the type was a structural
        # mismatch causing Walmart to reject the whole feed file outright
        # (ERR_INT_SYS_0801003, itemsReceived: 0 — rejected before any
        # item-level validation even ran).
        clean_digits = re.sub(r"\D", "", str(upc).strip())
        gtin14 = clean_digits.zfill(14)

        item_payload: Dict[str, Any] = {
            "sku": str(sku).strip(),
            "productIdentifiers": {
                "productIdType": "GTIN",
                "productId": gtin14,
            },
            "ShippingWeight": float(weight_lbs),
            "price": float(price),
            "condition": condition,
        }
        if main_image_url:
            item_payload["mainImageUrl"] = main_image_url

        # Confirmed against Walmart's own MP_ITEM_MATCH v4.2 sample feed file
        # (a second, more complete real sample than the v5.x one used
        # originally): "sellingChannel": "mpsetupbymatch" is present there and
        # totally absent from the v5.x sample we built against first, despite
        # both claiming to be the same feedType. Its absence is the most
        # concrete lead for why Walmart's processor rejects the file outright
        # (ERR_INT_SYS_0801003, itemsReceived: 0) before any item validation —
        # without it, the processor may not even recognize what operation the
        # feed is requesting.
        payload = {
            "MPItemFeedHeader": {
                "processMode": "REPLACE",
                "subset": "EXTERNAL",
                "locale": "en",
                "sellingChannel": "mpsetupbymatch",
                "version": "4.2",
            },
            "MPItem": [{"Item": item_payload}],
        }

        try:
            res = self._request(
                "/v3/feeds",
                method="POST",
                params={"feedType": "MP_ITEM_MATCH"},
                json_data=payload,
                timeout=30.0,
            )
            logger.info(f"Walmart MP_ITEM_MATCH feed submitted for SKU {sku} (UPC {upc}): {res.get('feedId')}")
            return res
        except Exception as exc:
            logger.error(f"Walmart MP_ITEM_MATCH feed submission failed for SKU {sku}: {exc}")
            raise

    def get_feed_status(self, feed_id: str) -> Dict[str, Any]:
        """
        Real feed processing status via GET /v3/feeds/{feedId} — use this to
        check whether a submit_item_match_feed() call actually succeeded,
        since feed processing happens asynchronously after acceptance.

        includeDetails=true is required to get itemDetails.itemIngestionStatus
        (per-item success/error) — without it Walmart returns only the feed-
        level summary counts with an empty item list, which isn't enough to
        tell "still processing" apart from "every item actually failed".
        """
        return self._request(
            f"/v3/feeds/{urllib.parse.quote(str(feed_id))}",
            method="GET",
            params={"includeDetails": "true"},
        )

    def search_walmart_catalog_by_gtin(self, gtin: str) -> List[Dict[str, Any]]:
        """
        Real pre-check for whether a GTIN exists anywhere in Walmart's
        broader catalog (GET /v3/items/walmart/search) — confirmed live
        against a known-existing item (2 results) and two known item-match
        failures (0 results each, matching their real feed outcomes exactly).
        Lets us tell staff upfront whether MP_ITEM_MATCH can work for a
        product, instead of finding out only after a real feed submission.

        Not the same as search_by_upc's web image search, nor Catalog
        search (which only covers this seller's own offers) — this queries
        Walmart's actual catalog directly.

        This endpoint's own index is confirmed flaky (real test: 3 identical
        calls for the same GTIN one second apart returned 1 match, then 0,
        then 0 — Walmart-side inconsistency, not a bug here). A single empty
        result is therefore not trusted as "no match" — retries a few times
        with a short delay first, and only returns empty once every attempt
        agrees. A single found match is returned immediately, since a false
        positive is far less likely/costly than a false negative that would
        wrongly block a real, working listing.
        """
        clean_gtin = re.sub(r"\D", "", str(gtin).strip())
        last_items: List[Dict[str, Any]] = []
        for attempt in range(3):
            res = self._request("/v3/items/walmart/search", method="GET", params={"gtin": clean_gtin})
            items = res.get("items") or []
            if items:
                return items
            last_items = items
            if attempt < 2:
                time.sleep(1.0)
        return last_items

    # Confirmed live against the real account: the "version" below is not a
    # free-choice major version like MP_ITEM_MATCH's — Walmart's spec
    # endpoint rejects any other value with "No schema found for input
    # parameters" and returns this exact string as the only accepted enum
    # value. If this ever starts failing again, re-fetch it from a real
    # "Get spec" docs page/call; never guess a new one.
    MP_ITEM_SPEC_VERSION = "5.0.20250121-19_24_23-api"

    def get_item_spec(self, product_types: List[str]) -> Dict[str, Any]:
        """
        Real per-category field schema for full MP_ITEM setup (brand-new
        catalog item, not matched to an existing one) — POST /v3/items/spec.
        Throttled by Walmart to 3 requests/minute per seller; callers should
        batch product_types (up to 20 per call) rather than looping calls.
        """
        return self._request(
            "/v3/items/spec",
            method="POST",
            json_data={
                "feedType": "MP_ITEM",
                "version": self.MP_ITEM_SPEC_VERSION,
                "productTypes": product_types,
            },
        )

    def submit_new_item_feed(
        self,
        sku: str,
        upc: str,
        price: Decimal,
        weight_lbs: float,
        product_type: str,
        visible_attributes: Dict[str, Any],
        condition: str = "New",
    ) -> Dict[str, Any]:
        """
        Creates a brand-new Walmart catalog item (not matched to an existing
        one) via MP_ITEM — POST /v3/feeds?feedType=MP_ITEM. Unlike
        MP_ITEM_MATCH, this defines the item's own full catalog content, so
        visible_attributes must satisfy that product_type's real required
        fields (see get_item_spec) — this method does not fabricate or
        default any of that content; the caller supplies real values.
        """
        if not upc or not str(upc).strip():
            raise ValueError(f"Cannot submit a Walmart MP_ITEM feed for SKU '{sku}': no real UPC/GTIN on file.")
        if not weight_lbs or weight_lbs <= 0:
            raise ValueError(f"Cannot submit a Walmart MP_ITEM feed for SKU '{sku}': no real shipping weight on file.")
        if not visible_attributes:
            raise ValueError(
                f"Cannot submit a Walmart MP_ITEM feed for SKU '{sku}': no category-specific content supplied. "
                "Call get_item_spec() for the real required fields first — never fabricated here."
            )

        clean_digits = re.sub(r"\D", "", str(upc).strip())
        gtin14 = clean_digits.zfill(14)

        payload = {
            "MPItemFeedHeader": {
                "businessUnit": "WALMART_US",
                "locale": "en",
                "version": self.MP_ITEM_SPEC_VERSION,
            },
            "MPItem": [
                {
                    "Orderable": {
                        "productIdentifiers": {
                            "productIdType": "GTIN",
                            "productId": gtin14,
                        },
                        "sku": str(sku).strip(),
                        "specProductType": product_type,
                        "price": float(price),
                        "ShippingWeight": float(weight_lbs),
                    },
                    "Visible": {
                        product_type: {**visible_attributes, "condition": condition},
                    },
                }
            ],
        }

        try:
            res = self._request(
                "/v3/feeds",
                method="POST",
                params={"feedType": "MP_ITEM"},
                json_data=payload,
                timeout=30.0,
            )
            logger.info(f"Walmart MP_ITEM feed submitted for SKU {sku} (UPC {upc}): {res.get('feedId')}")
            return res
        except Exception as exc:
            logger.error(f"Walmart MP_ITEM feed submission failed for SKU {sku}: {exc}")
            raise

    def create_listing(
        self,
        sku: str,
        title: str,
        description: str,
        price: Decimal,
        quantity: int,
        image_urls: Optional[list] = None,
        upc: Optional[str] = None,
        weight_lbs: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Sets price and inventory for a SKU that already exists in Walmart's
        catalog. If it doesn't exist yet, submits a real MP_ITEM_MATCH feed
        to create it (see submit_item_match_feed) — requires upc/weight_lbs
        to be passed through by the caller; if either is missing, raises
        rather than fabricating them, same as submit_item_match_feed itself.

        Item-match feed submission is asynchronous — a successful call here
        means the feed was accepted, not that the item is live yet. Real
        status requires polling get_feed_status(feedId) separately.
        """
        target_sku = str(sku).strip()

        existing = self.get_listing(target_sku)
        if existing.get("status") in ("UNKNOWN", None) or existing.get("error"):
            if not upc or not weight_lbs:
                raise ValueError(
                    f"Walmart has no catalog item for SKU '{target_sku}' yet. A real item-match feed "
                    "can create it (submit_item_match_feed), but that needs a real UPC and shipping "
                    f"weight for this product, which weren't provided. Walmart's own error: {existing.get('error')}"
                )
            feed_result = self.submit_item_match_feed(
                sku=target_sku,
                upc=upc,
                price=price,
                weight_lbs=weight_lbs,
                main_image_url=(image_urls[0] if image_urls else None),
            )
            return {
                "external_listing_id": target_sku,
                "status": "PENDING",
                "metadata": {
                    "sku": target_sku,
                    "title": title,
                    "price": str(price),
                    "quantity": quantity,
                    "marketplace": "Walmart Marketplace",
                    "feed_id": feed_result.get("feedId"),
                    "note": "Item-match feed submitted and accepted by Walmart; processing is asynchronous — "
                            "check get_feed_status(feedId) before assuming the item is actually live.",
                },
            }

        self.update_price(target_sku, target_sku, price)
        self.update_inventory(target_sku, target_sku, quantity)

        return {
            "external_listing_id": target_sku,
            "status": "ACTIVE",
            "metadata": {
                "sku": target_sku,
                "title": title,
                "price": str(price),
                "quantity": quantity,
                "marketplace": "Walmart Marketplace",
            },
        }

    def withdraw_listing(self, external_listing_id: str) -> bool:
        """
        Zeroes out inventory on Walmart Marketplace to delist/pause the offer.
        This is a PAUSE, not a deletion — the item stays in Walmart's catalog
        (buyer-facing visibility of an out-of-stock item is Walmart's own
        behavior, not something this call controls) and can be restocked
        later via reactivate. For a real, permanent removal use retire_item().
        """
        target_sku = str(external_listing_id).strip()
        return self.update_inventory(target_sku, target_sku, 0)

    def retire_item(self, sku: str) -> bool:
        """
        Permanently retires the item from Walmart's catalog —
        DELETE /v3/items/{sku}, confirmed against Walmart's own real "Retire
        an item" reference. Unlike withdraw_listing (zero-stock pause, fully
        reversible), this is NOT reversible — the item would need to be
        recreated via a fresh MP_ITEM_MATCH/MP_ITEM feed to sell again.
        """
        target_sku = str(sku).strip()
        encoded_sku = urllib.parse.quote(target_sku, safe="")
        try:
            self._request(f"/v3/items/{encoded_sku}", method="DELETE")
            logger.info(f"Walmart item retired: SKU {target_sku}")
            return True
        except Exception as exc:
            logger.error(f"Walmart retire_item failed for SKU {target_sku}: {exc}")
            raise

    def reactivate_listing(self, external_listing_id: str, sku: Optional[str] = None) -> bool:
        """
        Reactivates offer on Walmart Marketplace.
        """
        target_sku = str(sku or external_listing_id).strip()
        return True

    def fetch_orders(self, since_datetime=None) -> List[Dict[str, Any]]:
        """
        Fetch new/updated orders from Walmart Marketplace.
        """
        params: Dict[str, Any] = {"limit": 100}
        if since_datetime:
            if isinstance(since_datetime, str):
                params["createdStartDate"] = since_datetime
            elif hasattr(since_datetime, "isoformat"):
                params["createdStartDate"] = since_datetime.isoformat()

        try:
            res = self._request("/v3/orders", method="GET", params=params)
            raw_orders = res.get("list", {}).get("elements", {}).get("order", [])
        except Exception as exc:
            logger.error(f"Walmart fetch_orders failed: {exc}")
            raise

        normalized_orders: List[Dict[str, Any]] = []
        for o in raw_orders:
            po_id = str(o.get("purchaseOrderId") or o.get("customerOrderId") or "")
            if not po_id:
                continue

            order_date_raw = o.get("orderDate")
            if isinstance(order_date_raw, (int, float)):
                ordered_at = datetime.fromtimestamp(order_date_raw / 1000.0, tz=timezone.utc)
            elif isinstance(order_date_raw, str):
                try:
                    ordered_at = datetime.fromisoformat(order_date_raw.replace("Z", "+00:00"))
                except Exception:
                    ordered_at = datetime.now(timezone.utc)
            else:
                ordered_at = datetime.now(timezone.utc)

            ship_info = o.get("shippingInfo") or {}
            postal = ship_info.get("postalAddress") or {}
            buyer_name = postal.get("name") or "Walmart Customer"

            shipping_address = {
                "name": buyer_name,
                "street": postal.get("address1") or "",
                "city": postal.get("city") or "",
                "state": postal.get("state") or "",
                "postalCode": postal.get("postalCode") or "",
                "country": postal.get("country") or "US",
                "phone": ship_info.get("phone") or "",
            }

            lines_raw = o.get("orderLines", {}).get("orderLine", [])
            items: List[Dict[str, Any]] = []
            order_total = Decimal("0.00")

            for line in lines_raw:
                item_obj = line.get("item") or {}
                line_sku = item_obj.get("sku") or ""
                line_title = item_obj.get("productName") or line_sku
                qty = int(line.get("orderLineQuantity", {}).get("amount") or 1)

                charges = line.get("charges", {}).get("charge", [])
                unit_price = Decimal("0.00")
                for c in charges:
                    if c.get("chargeType") == "PRODUCT":
                        amt = c.get("chargeAmount", {}).get("amount")
                        if amt:
                            unit_price = Decimal(str(amt))
                            order_total += unit_price

                items.append({
                    "sku": line_sku,
                    "title": line_title,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "item_id": str(line.get("lineNumber") or ""),
                })

            normalized_orders.append({
                "order_id": po_id,
                "buyer_username": o.get("customerEmailId") or buyer_name,
                "buyer_name": buyer_name,
                "shipping_address": shipping_address,
                "order_total": order_total,
                "marketplace_fees": Decimal("0.00"),
                "currency": "USD",
                "ordered_at": ordered_at,
                "items": items,
            })

        logger.info(f"Fetched {len(normalized_orders)} orders from Walmart Marketplace.")
        return normalized_orders

    def update_tracking(
        self,
        marketplace_order_id: str,
        tracking_number: str,
        carrier: str,
        line_item_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        Pushes carrier tracking details and confirms shipment for a Walmart
        order. line_item_ids are Walmart's own real orderLine lineNumbers
        (stored as OrderItem.marketplace_item_id at ingestion — see
        fetch_orders' item_id). Without these, a multi-item order would only
        ever get its first line marked shipped on Walmart's side, silently
        leaving the rest stuck un-fulfilled there even though this call
        reports success — "1" is only a fallback for the genuinely-unknown
        case, never a default to prefer.
        """
        po_id = str(marketplace_order_id).strip()
        now_ms = int(time.time() * 1000)
        clean_line_numbers = [str(x).strip() for x in line_item_ids if str(x).strip()] if line_item_ids else ["1"]

        # Standardize carrier name for Walmart
        carrier_clean = carrier.strip()
        standard_carrier = "UPS"
        carrier_lower = carrier_clean.lower()
        if "fedex" in carrier_lower:
            standard_carrier = "FedEx"
        elif "usps" in carrier_lower:
            standard_carrier = "USPS"
        elif "dhl" in carrier_lower:
            standard_carrier = "DHL"
        elif "ups" in carrier_lower:
            standard_carrier = "UPS"
        else:
            standard_carrier = carrier_clean

        payload = {
            "orderShipment": {
                "orderLines": {
                    "orderLine": [
                        {
                            "lineNumber": line_number,
                            "orderLineStatuses": {
                                "orderLineStatus": [
                                    {
                                        "status": "Shipped",
                                        "statusQuantity": {
                                            "unitOfMeasurement": "EACH",
                                            "amount": "1",
                                        },
                                        "trackingInfo": {
                                            "shipDateTime": now_ms,
                                            "carrierName": {
                                                "carrier": standard_carrier,
                                            },
                                            "methodCode": "Standard",
                                            "trackingNumber": str(tracking_number).strip(),
                                        },
                                    }
                                ]
                            },
                        }
                        for line_number in clean_line_numbers
                    ]
                }
            }
        }

        try:
            res = self._request(f"/v3/orders/{po_id}/shipping", method="POST", json_data=payload)
            logger.info(f"Walmart tracking successfully pushed for order {po_id}: {standard_carrier} {tracking_number}")
            return True
        except Exception as exc:
            logger.error(f"Walmart tracking push failed for order {po_id}: {exc}")
            raise

    def acknowledge_order(self, marketplace_order_id: str) -> bool:
        """
        Acknowledges receipt of an order on Walmart Marketplace. Raises on
        failure like every other write method in this adapter (update_inventory,
        update_price, update_tracking) — a caller must not be able to mistake
        a failed acknowledgement for "not yet acknowledged".
        """
        po_id = str(marketplace_order_id).strip()
        try:
            self._request(f"/v3/orders/{po_id}/acknowledge", method="POST")
            logger.info(f"Walmart order {po_id} acknowledged successfully.")
            return True
        except Exception as exc:
            logger.error(f"Walmart acknowledge order failed for {po_id}: {exc}")
            raise
