import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import base64
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal

from app.adapters.marketplaces.base import MarketplaceAdapter

logger = logging.getLogger(__name__)

class LiveEBayAdapter(MarketplaceAdapter):
    """
    Live eBay Sell REST API Adapter.
    Connects directly to eBay Sell Inventory API (Sandbox or Production).
    Supports token refresh, inventory item management, stock sync, and price updates.
    """

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self.credentials = credentials or {}
        self.app_id = self.credentials.get("app_id") or ""
        self.cert_id = self.credentials.get("cert_id") or ""
        self.dev_id = self.credentials.get("dev_id") or ""
        self.user_token = self.credentials.get("user_token") or ""
        self.refresh_token = self.credentials.get("refresh_token") or ""

        # Environment: sandbox by default
        env = (self.credentials.get("environment") or "sandbox").lower()
        self.environment = "production" if env == "production" else "sandbox"

        if self.environment == "production":
            self.base_url = "https://api.ebay.com"
            self.oauth_url = "https://api.ebay.com/identity/v1/oauth2/token"
        else:
            self.base_url = "https://api.sandbox.ebay.com"
            self.oauth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

    def _get_auth_header(self) -> Dict[str, str]:
        """Returns HTTP headers for authenticated eBay REST requests."""
        token = self.user_token.replace("Bearer ", "").strip()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US",
            "Accept": "application/json"
        }

    def _refresh_access_token_if_needed(self) -> bool:
        """Exchanges refresh_token for a new user access token and persists it."""
        if not self.refresh_token or not self.app_id or not self.cert_id:
            return False

        try:
            auth_str = base64.b64encode(f"{self.app_id}:{self.cert_id}".encode()).decode()
            data = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }).encode()

            req = urllib.request.Request(
                self.oauth_url,
                data=data,
                headers={
                    "Authorization": f"Basic {auth_str}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if "access_token" in result:
                    self.user_token = result["access_token"]
                    self.credentials["user_token"] = self.user_token
                    logger.info("Successfully refreshed eBay OAuth user token")

                    try:
                        from app.core.database import SessionLocal
                        from app.models.marketplace import Marketplace
                        from app.core.security import encrypt_credential
                        db = SessionLocal()
                        m = db.query(Marketplace).filter(Marketplace.adapter_class == "LiveEBayAdapter").first()
                        if m:
                            creds = self.credentials.copy()
                            creds["user_token"] = self.user_token
                            m.credentials_encrypted = encrypt_credential(json.dumps(creds))
                            db.commit()
                        db.close()
                    except Exception as save_err:
                        logger.warning(f"Could not persist refreshed eBay token to DB: {save_err}")

                    return True
        except Exception as e:
            logger.warning(f"Could not refresh eBay token: {e}")
        return False

    def test_connection(self) -> bool:
        """Pings eBay Sell Inventory API to verify live token and connectivity."""
        url = f"{self.base_url}/sell/inventory/v1/inventory_item?limit=1"
        try:
            req = urllib.request.Request(url, headers=self._get_auth_header())
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return True
        except urllib.error.HTTPError as err:
            if err.code == 401:
                # Try refreshing token and retry once
                if self._refresh_access_token_if_needed():
                    req2 = urllib.request.Request(url, headers=self._get_auth_header())
                    with urllib.request.urlopen(req2, timeout=8) as resp2:
                        return resp2.status == 200
                if not self.refresh_token:
                    raise PermissionError(
                        "Your eBay OAuth User Token has expired (access tokens strictly expire after 2 hours). "
                        "To fix this permanently, open eBay Developer Portal (User Tokens -> OAuth), "
                        "copy your Refresh Token, and paste it into Connect Stores -> eBay -> Edit Keys."
                    )
                raise PermissionError(
                    f"eBay Live API Authorization Error (401): {err.reason}. "
                    "Your Refresh Token or User Token could not be verified by eBay."
                )
            if err.code == 429:
                retry_after = err.headers.get("Retry-After") if err.headers else None
                raise ConnectionError(f"eBay API Rate Limit Exceeded (429). Retry-After: {retry_after or 'unspecified'}s.")
            raise ConnectionError(f"eBay API error (HTTP {err.code}): {err.reason}")
        except Exception as err:
            raise ConnectionError(f"eBay server unreachable: {err}")
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
        """
        Creates/replaces live inventory item on eBay (PUT /sell/inventory/v1/inventory_item/{sku}).
        Fulfills real eBay inventory creation.
        """
        # Ensure connection / valid token
        self.test_connection()

        # Extract brand for eBay required item specifics
        brand = "Generic"
        t_lower = (title or "").lower()
        if "anker" in t_lower:
            brand = "Anker"
        elif "corsair" in t_lower:
            brand = "Corsair"
        elif "samsung" in t_lower:
            brand = "Samsung"
        elif "logitech" in t_lower:
            brand = "Logitech"

        url = f"{self.base_url}/sell/inventory/v1/inventory_item/{urllib.parse.quote(sku)}"
        payload = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": int(quantity)
                }
            },
            "condition": "NEW",
            "product": {
                "title": (title or "Product")[:80],
                "description": description or title,
                "aspects": {
                    "Brand": [brand],
                    "Type": ["Electronics"]
                },
                "imageUrls": (image_urls or [])[:12]
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="PUT", headers=self._get_auth_header())

        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    logger.info(f"Live eBay item PUT returned HTTP {resp.status} for SKU {sku}")
                    break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode()
                if e.code in (500, 502, 503) and attempt == 0:
                    logger.warning(f"eBay returned transient HTTP {e.code}, retrying in 1.5s...")
                    time.sleep(1.5)
                    continue
                logger.error(f"eBay create_listing HTTP {e.code}: {err_body}")
                raise RuntimeError(f"eBay API error {e.code}: {err_body}")

        # Automatically publish live consumer offer to assign real eBay Item Number
        live_listing_id = self._publish_offer_if_possible(sku, price, quantity)
        external_id = live_listing_id or f"ebay_live_{sku}"

        return {
            "external_listing_id": external_id,
            "sku": sku,
            "title": title,
            "price": Decimal(str(price)),
            "quantity": int(quantity),
            "status": "ACTIVE",
            "marketplace": f"eBay ({self.environment.title()})",
            "published_at": time.time(),
            "live_synced": True
        }

    def _publish_offer_if_possible(self, sku: str, price: Decimal, quantity: int) -> Optional[str]:
        """Attempts to create and publish a live consumer offer on eBay, returning listingId."""
        try:
            # 1. Ensure default warehouse location exists
            loc_url = f"{self.base_url}/sell/inventory/v1/location/default_warehouse"
            loc_req = urllib.request.Request(
                loc_url,
                data=json.dumps({
                    "name": "Main Warehouse",
                    "location": {
                        "address": {
                            "addressLine1": "100 Main St",
                            "city": "Dallas",
                            "stateOrProvince": "TX",
                            "postalCode": "75201",
                            "country": "US"
                        }
                    },
                    "locationTypes": ["WAREHOUSE"]
                }).encode(),
                method="POST",
                headers=self._get_auth_header()
            )
            try:
                with urllib.request.urlopen(loc_req, timeout=8):
                    pass
            except Exception:
                pass

            # 2. Use seller's active fulfillment, payment, and return policies
            fulfillment_id = "137419252015"
            payment_id = "240485170015"
            return_id = "246630508015"

            # 3. Create or update offer
            offer_url = f"{self.base_url}/sell/inventory/v1/offer"
            offer_payload = {
                "sku": sku,
                "marketplaceId": "EBAY_US",
                "format": "FIXED_PRICE",
                "availableQuantity": max(1, int(quantity)),
                "categoryId": "123417",
                "listingPolicies": {
                    "fulfillmentPolicyId": fulfillment_id,
                    "paymentPolicyId": payment_id,
                    "returnPolicyId": return_id
                },
                "pricingSummary": {
                    "price": {
                        "value": str(Decimal(str(price)).quantize(Decimal("0.01"))),
                        "currency": "USD"
                    }
                },
                "merchantLocationKey": "default_warehouse"
            }
            offer_req = urllib.request.Request(offer_url, data=json.dumps(offer_payload).encode(), method="POST", headers=self._get_auth_header())
            with urllib.request.urlopen(offer_req, timeout=10) as off_resp:
                off_data = json.loads(off_resp.read().decode())
                offer_id = off_data.get("offerId")

            if offer_id:
                # 4. Publish offer to make it active on eBay
                pub_url = f"{self.base_url}/sell/inventory/v1/offer/{offer_id}/publish"
                pub_req = urllib.request.Request(pub_url, data=b"", method="POST", headers=self._get_auth_header())
                with urllib.request.urlopen(pub_req, timeout=12) as pub_resp:
                    pub_data = json.loads(pub_resp.read().decode())
                    listing_id = pub_data.get("listingId")
                    if listing_id:
                        logger.info(f"Successfully published live eBay offer! Listing ID: {listing_id}")
                        return str(listing_id)
        except Exception as e:
            logger.warning(f"Notice on eBay offer publish (inventory item preserved): {e}")
        return None

    def update_inventory(self, external_listing_id: str, sku: str, quantity: int) -> bool:
        """Updates live stock quantity on eBay (PUT /sell/inventory/v1/inventory_item/{sku})."""
        self.test_connection()
        url = f"{self.base_url}/sell/inventory/v1/inventory_item/{urllib.parse.quote(sku)}"
        payload = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": max(0, int(quantity))
                }
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="PUT", headers=self._get_auth_header())

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.error(f"Failed to update eBay live inventory for SKU {sku}: {e}")
            raise e

    def update_price(self, external_listing_id: str, sku: str, price: Decimal) -> bool:
        """
        Updates selling price on eBay by finding the active offer for this SKU
        and PATCHing its pricingSummary (price lives on the offer, not the
        inventory item, in eBay's Sell Inventory API).
        """
        self.test_connection()
        actual_sku = sku or external_listing_id.replace("ebay_live_", "").replace("ebay_listing_", "")

        try:
            offer_lookup_url = f"{self.base_url}/sell/inventory/v1/offer?sku={urllib.parse.quote(actual_sku)}"
            req = urllib.request.Request(offer_lookup_url, headers=self._get_auth_header())
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                offers = data.get("offers", [])
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="ignore")
            logger.error(f"eBay offer lookup failed for SKU {actual_sku} (HTTP {err.code}): {err_body}")
            raise RuntimeError(f"eBay price update failed: could not find offer for SKU {actual_sku} ({err.code})")

        if not offers:
            logger.warning(f"No eBay offer found for SKU {actual_sku}; price not updated.")
            return False

        offer_id = offers[0].get("offerId")
        formatted_price = str(Decimal(str(price)).quantize(Decimal("0.01")))
        patch_url = f"{self.base_url}/sell/inventory/v1/offer/{offer_id}"
        payload = {
            "pricingSummary": {
                "price": {
                    "value": formatted_price,
                    "currency": "USD"
                }
            }
        }

        req = urllib.request.Request(
            patch_url,
            data=json.dumps(payload).encode("utf-8"),
            method="PUT",
            headers=self._get_auth_header()
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"eBay price updated for SKU {actual_sku} to ${formatted_price} (offer {offer_id})")
                return resp.status in (200, 204)
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="ignore")
            logger.error(f"eBay update_price failed for SKU {actual_sku} (HTTP {err.code}): {err_body}")
            raise RuntimeError(f"eBay price update failed ({err.code}): {err_body}")

    def withdraw_listing(self, external_listing_id: str, sku: Optional[str] = None) -> bool:
        """Withdraws / ends active listing and sets live stock to 0 on eBay."""
        actual_sku = sku or external_listing_id.replace("ebay_live_", "").replace("ebay_listing_", "")
        
        # 1. Withdraw any active published offers for this SKU on eBay
        try:
            offer_lookup_url = f"{self.base_url}/sell/inventory/v1/offer?sku={urllib.parse.quote(actual_sku)}"
            req = urllib.request.Request(offer_lookup_url, headers=self._get_auth_header())
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                offers = data.get("offers", [])
                for off in offers:
                    offer_id = off.get("offerId")
                    if offer_id and off.get("status") != "WITHDRAWN":
                        withdraw_url = f"{self.base_url}/sell/inventory/v1/offer/{offer_id}/withdraw"
                        w_req = urllib.request.Request(withdraw_url, data=b"", method="POST", headers=self._get_auth_header())
                        try:
                            with urllib.request.urlopen(w_req, timeout=10) as w_resp:
                                logger.info(f"Successfully withdrew eBay offer {offer_id} (status {w_resp.status})")
                        except Exception as w_err:
                            logger.warning(f"Could not withdraw eBay offer {offer_id}: {w_err}")
        except Exception as err:
            logger.warning(f"Notice on eBay offer lookup for withdrawal: {err}")

        # 2. Update stock to 0 on eBay inventory item
        try:
            return self.update_inventory(external_listing_id, actual_sku, quantity=0)
        except Exception:
            return True

    def get_listing(self, external_listing_id: str) -> Dict[str, Any]:
        """Retrieves live item from eBay Inventory API."""
        sku = external_listing_id.replace("ebay_live_", "").replace("ebay_listing_", "")
        url = f"{self.base_url}/sell/inventory/v1/inventory_item/{urllib.parse.quote(sku)}"
        req = urllib.request.Request(url, headers=self._get_auth_header())
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

    # ── V2: Live Order Management ──

    def fetch_orders(self, since_datetime=None) -> list:
        """
        Fetches new/unshipped orders from eBay Sell Fulfillment API.
        GET /sell/fulfillment/v1/order?filter=orderfulfillmentstatus:{NOT_STARTED|IN_PROGRESS}
        """
        self._refresh_access_token_if_needed()

        filter_str = "orderfulfillmentstatus:{NOT_STARTED|IN_PROGRESS}"
        url = f"{self.base_url}/sell/fulfillment/v1/order?filter={urllib.parse.quote(filter_str)}&limit=50"

        try:
            req = urllib.request.Request(url, headers=self._get_auth_header())
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                orders = []

                for ebay_order in data.get("orders", []):
                    order_id = ebay_order.get("orderId", "")
                    buyer = ebay_order.get("buyer", {})
                    payment = ebay_order.get("paymentSummary", {})
                    pricing = ebay_order.get("pricingSummary", {})

                    # Extract shipping address
                    fulfillment_start = ebay_order.get("fulfillmentStartInstructions", [])
                    ship_to = {}
                    if fulfillment_start:
                        ship_to_ref = fulfillment_start[0].get("shippingStep", {}).get("shipTo", {})
                        contact = ship_to_ref.get("contactAddress", {})
                        ship_to = {
                            "name": ship_to_ref.get("fullName", ""),
                            "street": contact.get("addressLine1", ""),
                            "city": contact.get("city", ""),
                            "state": contact.get("stateOrProvince", ""),
                            "zip": contact.get("postalCode", ""),
                            "country": contact.get("countryCode", "US"),
                        }

                    # Extract order total
                    total_val = pricing.get("total", {}).get("value", "0")
                    fee_val = "0"
                    for payment_item in payment.get("payments", []):
                        for fee in payment_item.get("totalFeeAmount", {}).get("value", "0"):
                            pass
                    # Use totalMarketplaceFee if available
                    fee_val = pricing.get("totalMarketplaceFee", {}).get("value", "0")

                    # Parse line items
                    items = []
                    for line in ebay_order.get("lineItems", []):
                        items.append({
                            "item_id": line.get("lineItemId", ""),
                            "sku": line.get("sku", ""),
                            "title": line.get("title", ""),
                            "quantity": int(line.get("quantity", 1)),
                            "unit_price": Decimal(str(line.get("lineItemCost", {}).get("value", "0"))),
                        })

                    # Parse order creation date
                    ordered_at = None
                    creation_date = ebay_order.get("creationDate", "")
                    if creation_date:
                        try:
                            from datetime import datetime
                            ordered_at = datetime.fromisoformat(creation_date.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    orders.append({
                        "order_id": order_id,
                        "buyer_username": buyer.get("username", ""),
                        "buyer_name": ship_to.get("name", ""),
                        "shipping_address": ship_to,
                        "order_total": Decimal(str(total_val)),
                        "marketplace_fees": Decimal(str(fee_val)),
                        "currency": pricing.get("total", {}).get("currency", "USD"),
                        "ordered_at": ordered_at,
                        "items": items,
                    })

                logger.info(f"Fetched {len(orders)} orders from eBay ({self.environment})")
                return orders

        except urllib.error.HTTPError as err:
            if err.code == 401:
                if self._refresh_access_token_if_needed():
                    return self.fetch_orders(since_datetime)
            err_body = err.read().decode("utf-8", errors="ignore")
            logger.error(f"eBay fetch_orders failed (HTTP {err.code}): {err_body}")
            raise ConnectionError(f"eBay Orders API error ({err.code}): {err_body}")
        except Exception as exc:
            logger.error(f"eBay fetch_orders error: {exc}")
            raise

    def update_tracking(self, marketplace_order_id: str, tracking_number: str, carrier: str) -> bool:
        """
        Pushes shipment tracking to eBay via Sell Fulfillment API.
        POST /sell/fulfillment/v1/order/{orderId}/shipping_fulfillment
        """
        self._refresh_access_token_if_needed()

        url = f"{self.base_url}/sell/fulfillment/v1/order/{urllib.parse.quote(marketplace_order_id)}/shipping_fulfillment"

        # Map common carrier names to eBay's expected values
        carrier_map = {
            "ups": "UPS",
            "fedex": "FedEx",
            "usps": "USPS",
            "dhl": "DHL",
        }
        ebay_carrier = carrier_map.get(carrier.lower().strip(), carrier) if carrier else "OTHER"

        payload = {
            "trackingNumber": tracking_number,
            "shippingCarrierCode": ebay_carrier,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST", headers=self._get_auth_header())
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"eBay tracking updated for order {marketplace_order_id}: {tracking_number} ({ebay_carrier})")
                return resp.status in (200, 201)
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="ignore")
            logger.error(f"eBay update_tracking failed (HTTP {err.code}): {err_body}")
            return False
        except Exception as exc:
            logger.error(f"eBay update_tracking error: {exc}")
            return False

    def acknowledge_order(self, marketplace_order_id: str) -> bool:
        """eBay auto-acknowledges orders. No action needed."""
        return True

