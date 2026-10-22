import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import base64
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List

from app.adapters.suppliers.base import SupplierAdapter
from app.schemas.supplier import NormalizedProduct
from app.core.config import settings

logger = logging.getLogger(__name__)


class MaLabsAdapter(SupplierAdapter):
    """
    Ma Labs Web Service (MWS) catalog adapter.

    Confirmed from Ma Labs' own MWS reference and a real captured response
    (2026-10-22): HTTP Basic Auth (account email + password), DRF-paginated
    JSON at /mws/items/ (count/next/previous/results), with real item fields
    list_no, item_no, upc_code, manufacturer_no, manufacturer, category,
    product_name, price, weight, unit, length, width, height, package,
    specorder, is_domestic_only, and inventory (a dict keyed by warehouse
    location code -> quantity, e.g. {"": 57} or {"": 0, "L": 0, "M": 0}).

    Catalog/stock/pricing only. Live-confirmed (2026-10-22), not inferred:
    the real MWS API root (GET /mws/) lists exactly one registered
    endpoint ("items"); OPTIONS on /mws/items/ returns Allow: GET, HEAD
    only (no POST/PUT/PATCH/DELETE); and every plausible order/shipment
    path (orders/, po/, purchase-orders/, shipments/, tracking/, etc.)
    returns the exact same generic site error page as a nonsense path,
    not a real endpoint. There is no order-submission or tracking API, so
    this adapter deliberately does not implement submit_order()/
    check_shipment_status(). order_service.py's live-submit path only
    ever routes to D&H, Ingram Micro, or TD SYNNEX by explicit allowlist,
    so a Ma Labs PO correctly falls through to the manual "Mark as
    Submitted" flow rather than silently failing or fabricating a fake
    confirmation.

    Live-confirmed supported list filters: upc, mfrno (manufacturer part
    number), search. An "in_stock" filter was documented but does NOT
    actually work against the real API under any reasonable param
    name/value tried (2026-10-22) — deliberately not implemented; filter
    by stock client-side on the returned quantity instead.
    """

    BASE_URL = "https://online.malabs.com/mws"

    def __init__(self, credentials: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials=credentials, config=config)
        self.supplier_name = "Ma Labs"
        self.credentials = credentials or {}

        self.username = (
            self.credentials.get("username")
            or self.credentials.get("email")
            or getattr(settings, "MALABS_USERNAME", None)
            or ""
        ).strip()

        self.password = (
            self.credentials.get("password")
            or getattr(settings, "MALABS_PASSWORD", None)
            or ""
        ).strip()

        self.next_cursor: Optional[str] = None
        self.catalog_exhausted: bool = False

    def is_live(self) -> bool:
        """Returns True if live MWS credentials are configured."""
        return bool(self.username and self.password)

    def _request(self, url: str, timeout: float = 15.0) -> Dict[str, Any]:
        """GET against MWS with HTTP Basic Auth, confirmed from the real docs."""
        if not self.is_live():
            raise ValueError("Ma Labs integration requires username/email and password.")

        b64_auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode("utf-8")
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Basic {b64_auth}",
                "Accept": "application/json",
                "User-Agent": "Sync-ABS-Platform/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"Ma Labs MWS error {exc.code} for {url}: {body}")
            raise

    def test_connection(self) -> bool:
        """Validates MWS credentials by requesting a single item."""
        if not self.is_live():
            logger.warning("Ma Labs test_connection failed: missing username/password.")
            return False
        try:
            self._request(f"{self.BASE_URL}/items/?limit=1")
            return True
        except Exception as exc:
            logger.error(f"Ma Labs test_connection failed: {exc}")
            return False

    def fetch_catalog(
        self,
        resume_cursor: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[NormalizedProduct]:
        """
        Pages through the real MWS /mws/items/ feed. resume_cursor, when
        present, is the exact "next" URL DRF's own pagination returned last
        time — trusting that URL directly (rather than reconstructing
        limit/offset ourselves) avoids any guessing about MWS's real
        pagination parameters or page-size ceiling.
        """
        if not self.is_live():
            raise ConnectionError("Ma Labs adapter has no live credentials configured.")

        filters = filters or {}

        if resume_cursor and resume_cursor.startswith("http"):
            url = resume_cursor
        else:
            limit = int(filters.get("limit") or 50)
            params: Dict[str, str] = {"limit": str(limit), "offset": "0"}
            if filters.get("upc"):
                params["upc"] = str(filters["upc"])
            if filters.get("mpn") or filters.get("manufacturer_no"):
                params["mfrno"] = str(filters.get("mpn") or filters.get("manufacturer_no"))
            # NOTE: an "in_stock" filter was documented but live-tested
            # (2026-10-22) against the real API under every reasonable
            # param name/value combination (in_stock/instock/stock/
            # available/has_stock x Y/N/true/false/yes/no/1/0) — none of
            # them changed the result count at all (always the full
            # unfiltered 6800). Deliberately not implemented: in-stock
            # filtering must be done client-side on the returned
            # "inventory" field instead of trusting a server param that
            # doesn't actually filter.
            if filters.get("search"):
                params["search"] = str(filters["search"])
            url = f"{self.BASE_URL}/items/?{urllib.parse.urlencode(params)}"

        try:
            res = self._request(url)
        except Exception as exc:
            raise ConnectionError(f"Ma Labs MWS error: {exc}") from exc

        results = res.get("results") or []
        normalized: List[NormalizedProduct] = []
        for item in results:
            norm = self._normalize_item(item)
            if norm:
                normalized.append(norm)

        self.next_cursor = res.get("next") or None
        self.catalog_exhausted = self.next_cursor is None

        logger.info(f"Ma Labs fetched {len(normalized)} products ({'exhausted' if self.catalog_exhausted else 'more pages remain'}).")
        return normalized

    def _normalize_item(self, item: Dict[str, Any]) -> Optional[NormalizedProduct]:
        """Maps a real MWS item record to NormalizedProduct. Never guesses a field name not confirmed in the real response."""
        sku = str(item.get("item_no") or "").strip()
        if not sku:
            return None

        price = item.get("price")
        if price is None:
            return None
        try:
            cost = Decimal(str(price))
        except InvalidOperation:
            return None
        if cost < 0:
            return None

        inventory = item.get("inventory") or {}
        qty = 0
        if isinstance(inventory, dict):
            for v in inventory.values():
                try:
                    qty += max(0, int(v))
                except (TypeError, ValueError):
                    continue

        upc = str(item.get("upc_code") or "").strip() or None
        mpn = str(item.get("manufacturer_no") or "").strip() or None
        brand = str(item.get("manufacturer") or "").strip() or None
        category = str(item.get("category") or "").strip() or None
        title = str(item.get("product_name") or "").strip() or sku

        shipping_info: Dict[str, Any] = {}
        if item.get("weight") is not None:
            shipping_info["weight_lbs"] = item.get("weight")
        if item.get("unit") is not None:
            shipping_info["unit_pack_qty"] = item.get("unit")
        for dim in ("length", "width", "height"):
            if item.get(dim) is not None:
                shipping_info[dim] = item.get(dim)
        if item.get("package"):
            shipping_info["package"] = item.get("package")

        specs: Dict[str, Any] = {
            "list_no": item.get("list_no"),
            "specorder": item.get("specorder"),
            "is_domestic_only": item.get("is_domestic_only"),
            "inventory_by_location": inventory,
        }

        return NormalizedProduct(
            supplier_sku=sku,
            upc=upc,
            mpn=mpn,
            title=title,
            brand=brand,
            category=category,
            specs=specs,
            cost=cost,
            quantity=qty,
            stock_status="IN_STOCK" if qty > 0 else "OUT_OF_STOCK",
            shipping_info=shipping_info,
            availability_status="ACTIVE",
        )

    def fetch_inventory(self, skus: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Fetch stock quantities keyed by supplier SKU (item_no). There's a
        direct /mws/items/{itemno}/ lookup but no documented batch endpoint,
        so explicit SKUs are fetched one at a time; with no SKUs given,
        falls back to a single catalog page.

        Live-confirmed (2026-10-22): unlike the paginated list endpoint,
        /mws/items/{itemno}/ returns a bare JSON list ([{...}]), not a
        single object — passing it straight to _normalize_item() (which
        expects a dict) raised AttributeError on every real call. Fixed to
        unwrap the list first.
        """
        if not self.is_live():
            return {}

        if not skus:
            products = self.fetch_catalog(filters={"limit": 50})
            return {p.supplier_sku: p.quantity for p in products}

        results: Dict[str, int] = {}
        for sku in skus:
            try:
                raw = self._request(f"{self.BASE_URL}/items/{urllib.parse.quote(str(sku))}/")
            except Exception as exc:
                logger.warning(f"Ma Labs inventory lookup failed for {sku}: {exc}")
                continue
            item = raw[0] if isinstance(raw, list) and raw else raw if isinstance(raw, dict) else None
            if not item:
                continue
            norm = self._normalize_item(item)
            if norm:
                results[norm.supplier_sku] = norm.quantity
        return results

    def fetch_price_changes(self) -> Dict[str, Decimal]:
        """Fetches current dealer costs keyed by supplier SKU."""
        if not self.is_live():
            return {}
        try:
            products = self.fetch_catalog(filters={"limit": 50})
            return {p.supplier_sku: p.cost for p in products}
        except Exception as exc:
            logger.warning(f"Ma Labs price changes fetch failed: {exc}")
            return {}
