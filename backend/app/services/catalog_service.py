import logging
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, false, desc, func
from app.models.product import Product
from app.models.supplier_product import SupplierProduct
from app.models.supplier import Supplier
from app.models.sync_log import SyncLog
from app.models.warehouse import Warehouse, WarehouseStock
from app.models.listing import Listing
from app.schemas.supplier import NormalizedProduct
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, SupplierProductInfo

from app.core.image_status import real_images

logger = logging.getLogger(__name__)


def _safe_lookup(provider, brand, mpn, gtin):
    """Returns ((match, restricted), error). error is set only for transient failures."""
    from app.adapters.suppliers.icecat_provider import IcecatContentError
    try:
        return provider.lookup_with_status(brand, mpn, gtin), None
    except IcecatContentError as exc:
        return (None, False), exc

# Ingram Micro reports non-physical SKUs (software licenses, support/renewal
# contracts) with a quantity that's a multiple of this sentinel instead of a
# real stock count — confirmed empirically: every such value in real catalog
# data is an exact multiple of 9,999,999 (9999999, 19999998, 29999997, ...),
# and 97%+ of matching rows have no UPC (consistent with non-physical items).
UNLIMITED_STOCK_SENTINEL = 9999999


def _is_unlimited_stock(qty: int) -> bool:
    return qty > 0 and qty % UNLIMITED_STOCK_SENTINEL == 0

# D&H branch codes, per their Customer Order Management API docs. Unknown
# codes (new branches, other suppliers) fall back to using the code itself
# as the display name rather than guessing at a real-world location.
KNOWN_WAREHOUSE_NAMES: Dict[str, str] = {
    "BR01": "Mid-Atlantic",
    "BR03": "Toronto",
    "BR04": "West Coast",
    "BR05": "Midwest",
    "BR06": "Atlanta",
    "BR08": "Vancouver",
}

class CatalogService:
    # Caps real image-search+verification calls (network-bound: a Bing scrape
    # plus a HEAD request per candidate) per CatalogService instance, which
    # lives for one sync_supplier() run. Without a cap, syncing hundreds of
    # brand-new products in one run could blow the sync's time budget on
    # image lookups alone. Real images accumulate incrementally across
    # successive scheduled runs instead — same pattern as this project's
    # resumable catalog pagination.
    IMAGE_MATCH_BUDGET_PER_SYNC = 15

    def __init__(self, db: Session):
        self.db = db
        self._image_match_budget_remaining = self.IMAGE_MATCH_BUDGET_PER_SYNC

    def find_matching_product(self, item: NormalizedProduct, supplier_id: Optional[int] = None) -> Optional[Product]:
        """
        Product Matching Engine (Spec Section 12):
        Matches incoming items by UPC, EAN, MPN, or SKU against existing products.

        Real incident (2026-10-08): Ingram Micro returns "9999999999999" as a
        placeholder UPC for tray/OEM CPU parts with no individual barcode —
        a value that fails real GS1 check-digit validation. Matching on it
        raw collapsed every such item sharing that same fake value into one
        Product row. Only a UPC/EAN that actually passes validation is
        trusted as a match key now; an invalid one is simply ignored, same
        as if it were absent.

        Also real: MPN describes the chip, not the specific listing — the
        same MPN (e.g. a Ryzen 7800X3D) legitimately appears across several
        genuinely distinct real Ingram listings (different tray/bulk/program
        tiers, different real supplier_sku, different real cost). MPN
        matching is intended for CROSS-supplier aggregation (the same real
        product carried by Ingram and D&H, say), not for collapsing several
        different same-supplier listings into one — that silently discarded
        real distinct cost/sku data every time it happened. So an MPN match
        is only trusted when the candidate product has no OTHER supplier_sku
        already on file for this same supplier; if it does, that's a
        genuinely different real listing and must not be merged onto it.
        """
        from app.core.upc_utils import validate_check_digit

        def _is_real_upc(code: Optional[str]) -> bool:
            if not code or not str(code).isdigit():
                return False
            return validate_check_digit(str(code))

        match_conditions = []
        if _is_real_upc(item.upc):
            match_conditions.append(Product.upc == item.upc)
        if _is_real_upc(item.ean):
            match_conditions.append(Product.ean == item.ean)
        if item.supplier_sku:
            match_conditions.append(Product.sku == item.supplier_sku)

        candidate = self.db.query(Product).filter(or_(*match_conditions)).first() if match_conditions else None
        if candidate:
            return candidate

        if item.mpn:
            mpn_candidates = self.db.query(Product).filter(Product.mpn == item.mpn).all()
            for cand in mpn_candidates:
                if supplier_id is None:
                    return cand
                existing_sp = (
                    self.db.query(SupplierProduct)
                    .filter(SupplierProduct.product_id == cand.id, SupplierProduct.supplier_id == supplier_id)
                    .first()
                )
                if existing_sp is None or existing_sp.supplier_sku == item.supplier_sku:
                    return cand
            return None

        return None

    def upsert_supplier_product(self, supplier: Supplier, item: NormalizedProduct) -> Tuple[Product, SupplierProduct, List[SyncLog]]:
        """
        Normalizes and links supplier products to central catalog, performing change detection (Spec Section 19).
        """
        logs: List[SyncLog] = []
        product = self.find_matching_product(item, supplier_id=supplier.id)

        # 1. If product doesn't exist yet, create canonical product
        if not product:
            product = Product(
                sku=item.supplier_sku,
                upc=item.upc,
                ean=item.ean,
                mpn=item.mpn,
                title=item.title,
                brand=item.brand,
                description=item.description,
                category=item.category,
                # Only real photos are ever stored. Adapters pad item.images
                # with generic stock photos for display; persisting those made
                # unrelated pictures (a graphics card on a wall mount) look
                # like the product's real photo.
                images=real_images(item.images),
                specs_json=item.specs,
                is_enabled=True
            )
            self.db.add(product)
            self.db.flush()
            logs.append(SyncLog(
                product_id=product.id,
                supplier_id=supplier.id,
                field_changed="product_created",
                old_value=None,
                new_value=product.sku
            ))

            # Real photo: a supplier-provided image is already trusted as-is;
            # otherwise try manufacturer content (exact GTIN / Brand+MPN, no
            # search quota). Bounded and best-effort: anything not resolved
            # here is picked up by image_backfill_task, so a slow or failing
            # lookup never blocks or fails the sync.
            if real_images(item.images):
                specs = dict(product.specs_json or {})
                specs["image_status"] = "supplier"
                product.specs_json = specs
            elif self._image_match_budget_remaining > 0:
                self._image_match_budget_remaining -= 1
                try:
                    from app.services.image_matching_service import ImageMatchingService
                    ImageMatchingService(db=self.db).resolve_from_content(product, save_db=False)
                except Exception as img_exc:
                    logger.warning(f"Content image lookup skipped for new product {product.sku}: {img_exc}")
        else:
            # Root cause of "wrong photo everywhere" (found 2026-11-18): this
            # used to run `product.images = item.images` on EVERY sync, and
            # D&H/Ingram's item.images are always three generic stock photos,
            # so each 5-minute sync overwrote whatever real photo the product
            # had (manufacturer, verified, or staff-chosen). Now: never write
            # a placeholder, never replace or reorder an existing real photo,
            # and only append a genuinely new supplier-provided photo.
            current = real_images(product.images)
            incoming = [u for u in real_images(item.images) if u not in current]
            if incoming or len(current) != len(product.images or []):
                product.images = current + incoming
                if incoming and not current:
                    specs = dict(product.specs_json or {})
                    specs["image_status"] = "supplier"
                    product.specs_json = specs

        # 2. Check existing supplier product link
        supplier_prod = self.db.query(SupplierProduct).filter(
            SupplierProduct.product_id == product.id,
            SupplierProduct.supplier_id == supplier.id
        ).first()

        now = datetime.now(timezone.utc)

        if not supplier_prod:
            base_shipping = supplier.default_shipping_charge
            supplier_prod = SupplierProduct(
                product_id=product.id,
                supplier_id=supplier.id,
                supplier_sku=item.supplier_sku,
                cost=item.cost,
                qty_available=item.quantity,
                stock_status=item.stock_status,
                availability_status=item.availability_status,
                shipping_info=item.shipping_info,
                base_shipping_charge=base_shipping,
                shipping_source="default" if base_shipping is not None else None,
                shipping_status="valid" if base_shipping is not None else "valid",
                shipping_updated_at=now if base_shipping is not None else None,
                last_seen_at=now
            )
            self.db.add(supplier_prod)
            self.db.flush()  # populate supplier_prod.id for warehouse_stock FK below
            logs.append(SyncLog(
                product_id=product.id,
                supplier_id=supplier.id,
                field_changed="supplier_linked",
                old_value=None,
                new_value=f"Cost: {item.cost}, Qty: {item.quantity}"
            ))
        else:
            # Change detection (Spec Section 19)
            if supplier_prod.cost != item.cost:
                logs.append(SyncLog(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    field_changed="cost",
                    old_value=str(supplier_prod.cost),
                    new_value=str(item.cost)
                ))
                supplier_prod.cost = item.cost

            if supplier_prod.qty_available != item.quantity:
                logs.append(SyncLog(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    field_changed="qty_available",
                    old_value=str(supplier_prod.qty_available),
                    new_value=str(item.quantity)
                ))
                supplier_prod.qty_available = item.quantity

            if supplier_prod.stock_status != item.stock_status:
                logs.append(SyncLog(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    field_changed="stock_status",
                    old_value=supplier_prod.stock_status,
                    new_value=item.stock_status
                ))
                supplier_prod.stock_status = item.stock_status

            if supplier_prod.base_shipping_charge is None and supplier.default_shipping_charge is not None:
                supplier_prod.base_shipping_charge = supplier.default_shipping_charge
                supplier_prod.shipping_source = "default"
                supplier_prod.shipping_status = "valid"
                supplier_prod.shipping_updated_at = now

            supplier_prod.last_seen_at = now
            supplier_prod.shipping_info = item.shipping_info
            supplier_prod.availability_status = item.availability_status

        branch_inventory = (item.shipping_info or {}).get("branch_inventory")
        if branch_inventory:
            self._sync_warehouse_stock(supplier, supplier_prod, branch_inventory)

        for log in logs:
            self.db.add(log)

        self.db.commit()
        self.db.refresh(product)
        self.db.refresh(supplier_prod)
        return product, supplier_prod, logs

    def _sync_warehouse_stock(
        self,
        supplier: Supplier,
        supplier_prod: SupplierProduct,
        branch_inventory: List[Dict[str, Any]],
    ) -> None:
        """
        Upserts per-warehouse stock rows from a supplier's branch-level
        inventory breakdown (currently: D&H's priceAndAvailability response).
        The aggregate SupplierProduct.qty_available is untouched — this is
        purely additive detail for suppliers that report it.
        """
        for branch in branch_inventory:
            code = str(branch.get("branch") or "").strip()
            if not code:
                continue

            warehouse = self.db.query(Warehouse).filter(
                Warehouse.supplier_id == supplier.id,
                Warehouse.code == code,
            ).first()
            if not warehouse:
                warehouse = Warehouse(
                    supplier_id=supplier.id,
                    code=code,
                    name=KNOWN_WAREHOUSE_NAMES.get(code, code),
                )
                self.db.add(warehouse)
                self.db.flush()

            stock = self.db.query(WarehouseStock).filter(
                WarehouseStock.supplier_product_id == supplier_prod.id,
                WarehouseStock.warehouse_id == warehouse.id,
            ).first()

            qty = branch.get("availableQuantity")
            replenish_date = branch.get("stockReplenishDate")
            parsed_replenish = None
            if replenish_date:
                try:
                    parsed_replenish = datetime.fromisoformat(str(replenish_date).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    parsed_replenish = None

            if not stock:
                stock = WarehouseStock(
                    supplier_product_id=supplier_prod.id,
                    warehouse_id=warehouse.id,
                    qty_available=max(0, int(qty or 0)),
                    stock_replenish_date=parsed_replenish,
                )
                self.db.add(stock)
            else:
                stock.qty_available = max(0, int(qty or 0))
                stock.stock_replenish_date = parsed_replenish

    def backfill_product_images(self, limit: int = 300, workers: int = 6) -> Dict[str, int]:
        """
        Replaces generic stock-photo placeholders with the manufacturer's real
        photo (Icecat, exact GTIN / Brand+MPN lookup, no search quota).

        Selection fixes two real defects of the previous version, which
        scraped Bing for the 30 oldest-updated products each run:
        - Verified products kept the oldest updated_at, so they piled up at
          the front of the "oldest 120" window, which was then filtered to
          nothing: the backfill eventually stopped making any progress.
        - Failures were never remembered, so the same products were
          re-queried forever, burning the search quota.
        Now the database itself excludes products that already have a real
        photo or were definitively checked within IMAGE_RECHECK_DAYS, and
        in-stock products are served first. A transient error (network, rate
        limit) is not recorded as a miss, so it is simply retried next run.
        """
        from concurrent.futures import ThreadPoolExecutor
        from datetime import timedelta
        from sqlalchemy import case, exists
        from app.adapters.suppliers.icecat_provider import IcecatContentProvider
        from app.core.image_status import REAL_IMAGE_STATUSES, IMAGE_RECHECK_DAYS
        from app.services.image_matching_service import ImageMatchingService

        status_col = Product.specs_json["image_status"].as_string()
        checked_col = Product.specs_json["image_content_checked_at"].as_string()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=IMAGE_RECHECK_DAYS)).isoformat()
        content_status_col = Product.specs_json["image_content_status"].as_string()
        key_used_col = Product.specs_json["image_content_key_used"].as_string()
        from app.core.config import settings as _settings
        retry_now_with_key = (
            and_(content_status_col == "requires_full_icecat", or_(key_used_col.is_(None), key_used_col != "true"))
            if _settings.ICECAT_APP_KEY else false()
        )
        in_stock = exists().where(
            SupplierProduct.product_id == Product.id,
            SupplierProduct.qty_available > 0,
            SupplierProduct.availability_status == "ACTIVE",
        )

        candidates = (
            self.db.query(Product)
            .filter(
                Product.is_enabled == True,
                or_(Product.upc.isnot(None), Product.ean.isnot(None), Product.mpn.isnot(None)),
                or_(status_col.is_(None), status_col.notin_(REAL_IMAGE_STATUSES)),
                or_(checked_col.is_(None), checked_col < cutoff, retry_now_with_key),
            )
            .order_by(case((in_stock, 0), else_=1), Product.id)
            .limit(limit)
            .all()
        )

        provider = IcecatContentProvider()

        # Network lookups run in parallel from plain values; ORM writes stay
        # on this thread/session.
        snapshot = [(p, p.brand, p.mpn, p.upc or p.ean) for p in candidates]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(
                lambda t: _safe_lookup(provider, t[1], t[2], t[3]), snapshot
            ))

        service = ImageMatchingService(db=self.db)
        matched = no_match = errors = 0
        restricted_count = 0
        for (product, *_), ((match, restricted), err) in zip(snapshot, outcomes):
            if err is not None:
                errors += 1
            elif match:
                service.apply_content_match(product, match, save_db=False)
                matched += 1
            else:
                service.record_content_miss(product, restricted=restricted, save_db=False)
                no_match += 1
                restricted_count += 1 if restricted else 0
        self.db.commit()

        return {
            "attempted": len(candidates), "matched": matched, "no_match": no_match,
            "needs_full_icecat": restricted_count, "errors": errors,
        }

    def backfill_walmart_match_status(self, limit: int = 20) -> Dict[str, int]:
        """
        Bounded background check of which enabled products can actually be
        listed on Walmart via MP_ITEM_MATCH (real GTIN-exists-in-Walmart's-
        catalog check via LiveWalmartAdapter.search_walmart_catalog_by_gtin),
        so the catalog can be filtered by real matchability instead of
        finding out per-product only when someone tries to list it.

        Bounded per call (one real Walmart API call per product) so this
        can run as a small frequent background task rather than one slow
        unbounded sweep — mirrors backfill_product_images' budget pattern.
        """
        from app.models.marketplace import Marketplace
        from app.services.listing_service import ListingService
        from datetime import datetime, timezone

        wm = self.db.query(Marketplace).filter(Marketplace.name.ilike("%walmart%")).first()
        if not wm:
            return {"attempted": 0, "matchable": 0, "not_matchable": 0}

        adapter = ListingService(self.db).get_adapter_for_marketplace(wm)
        if not hasattr(adapter, "search_walmart_catalog_by_gtin"):
            return {"attempted": 0, "matchable": 0, "not_matchable": 0}

        candidates = (
            self.db.query(Product)
            .filter(
                Product.is_enabled == True,
                or_(Product.upc.isnot(None), Product.ean.isnot(None)),
            )
            .order_by(Product.updated_at.asc())
            .limit(limit * 4)
            .all()
        )

        attempted = 0
        matchable = 0
        not_matchable = 0
        for product in candidates:
            if attempted >= limit:
                break
            specs = product.specs_json or {}
            if specs.get("walmart_match_status"):
                continue
            attempted += 1
            try:
                items = adapter.search_walmart_catalog_by_gtin(product.upc or product.ean)
                specs = dict(product.specs_json or {})
                specs["walmart_match_status"] = "matchable" if items else "not_matchable"
                specs["walmart_match_checked_at"] = datetime.now(timezone.utc).isoformat()
                product.specs_json = specs
                if items:
                    matchable += 1
                else:
                    not_matchable += 1
            except Exception as exc:
                logger.warning(f"Walmart match check failed for product {product.sku}: {exc}")

        self.db.commit()
        return {"attempted": attempted, "matchable": matchable, "not_matchable": not_matchable}

    def get_products(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        supplier_id: Optional[int] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        in_stock: Optional[bool] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        marketplace_id: Optional[int] = None,
        walmart_match_status: Optional[str] = None,
    ) -> Tuple[List[ProductResponse], int]:
        query = self.db.query(Product)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Product.sku.ilike(pattern),
                    Product.upc.ilike(pattern),
                    Product.ean.ilike(pattern),
                    Product.mpn.ilike(pattern),
                    Product.title.ilike(pattern),
                    Product.brand.ilike(pattern)
                )
            )

        if brand:
            query = query.filter(Product.brand == brand)
        if category:
            query = query.filter(Product.category == category)

        if supplier_id:
            query = query.join(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id)

        if in_stock is True:
            in_stock_subquery = self.db.query(SupplierProduct.product_id).filter(SupplierProduct.qty_available > 0).distinct().subquery()
            query = query.filter(Product.id.in_(in_stock_subquery))
        elif in_stock is False:
            in_stock_subquery = self.db.query(SupplierProduct.product_id).filter(SupplierProduct.qty_available > 0).distinct().subquery()
            query = query.filter(~Product.id.in_(in_stock_subquery))

        # Price range filters against each product's lowest supplier cost,
        # since Product itself carries no direct sell price.
        if min_price is not None:
            price_floor_subquery = (
                self.db.query(SupplierProduct.product_id)
                .group_by(SupplierProduct.product_id)
                .having(func.min(SupplierProduct.cost) >= min_price)
                .subquery()
            )
            query = query.filter(Product.id.in_(price_floor_subquery))
        if max_price is not None:
            price_ceiling_subquery = (
                self.db.query(SupplierProduct.product_id)
                .group_by(SupplierProduct.product_id)
                .having(func.min(SupplierProduct.cost) <= max_price)
                .subquery()
            )
            query = query.filter(Product.id.in_(price_ceiling_subquery))

        if marketplace_id:
            listed_subquery = (
                self.db.query(Listing.product_id)
                .filter(Listing.marketplace_id == marketplace_id)
                .distinct()
                .subquery()
            )
            query = query.filter(Product.id.in_(listed_subquery))

        if walmart_match_status:
            # specs_json is a plain JSON column (not JSONB), so the SQLAlchemy
            # JSON comparator is .as_string(), not JSONB's .astext.
            if walmart_match_status == "unchecked":
                query = query.filter(
                    Product.specs_json["walmart_match_status"].as_string().is_(None)
                )
            else:
                query = query.filter(
                    Product.specs_json["walmart_match_status"].as_string() == walmart_match_status
                )

        total = query.count()
        products = query.order_by(desc(Product.updated_at)).offset(skip).limit(limit).all()

        results = []
        for p in products:
            sp_infos = []
            total_stock = 0
            costs = []
            for sp in p.supplier_products:
                unlimited = _is_unlimited_stock(sp.qty_available)
                sp_infos.append(SupplierProductInfo(
                    id=sp.id,
                    supplier_id=sp.supplier_id,
                    supplier_name=sp.supplier.name if sp.supplier else None,
                    supplier_sku=sp.supplier_sku,
                    cost=sp.cost,
                    qty_available=sp.qty_available,
                    is_unlimited_stock=unlimited,
                    stock_status=sp.stock_status,
                    availability_status=sp.availability_status,
                    shipping_info=sp.shipping_info or {},
                    base_shipping_charge=sp.base_shipping_charge,
                    shipping_source=sp.shipping_source,
                    shipping_status=sp.shipping_status,
                    shipping_updated_at=sp.shipping_updated_at,
                    last_seen_at=sp.last_seen_at
                ))
                # Sentinel quantities are excluded from the real physical
                # total — summing them in would make total_stock nonsensical
                # (tens of millions of "units" for a support contract).
                if not unlimited:
                    total_stock += sp.qty_available
                costs.append(sp.cost)

            has_unlimited = any(info.is_unlimited_stock for info in sp_infos)
            # Prioritize in-stock suppliers for lowest_cost, so the seller sees what they will actually pay
            in_stock_costs = [sp.cost for sp in p.supplier_products if sp.qty_available > 0 or sp.stock_status == "IN_STOCK"]
            effective_lowest_cost = min(in_stock_costs) if in_stock_costs else (min(costs) if costs else None)

            results.append(ProductResponse(
                id=p.id,
                sku=p.sku,
                upc=p.upc,
                ean=p.ean,
                mpn=p.mpn,
                title=p.title,
                brand=p.brand,
                description=p.description,
                category=p.category,
                images=p.images or [],
                specs_json=p.specs_json or {},
                is_enabled=p.is_enabled,
                created_at=p.created_at,
                updated_at=p.updated_at,
                supplier_products=sp_infos,
                total_stock=total_stock,
                is_unlimited_stock=has_unlimited,
                lowest_cost=effective_lowest_cost
            ))

        return results, total

    def get_product_by_id(self, product_id: int) -> Optional[ProductResponse]:
        p = self.db.query(Product).filter(Product.id == product_id).first()
        if not p:
            return None

        sp_infos = []
        total_stock = 0
        costs = []
        for sp in p.supplier_products:
            unlimited = _is_unlimited_stock(sp.qty_available)
            sp_infos.append(SupplierProductInfo(
                id=sp.id,
                supplier_id=sp.supplier_id,
                supplier_name=sp.supplier.name if sp.supplier else None,
                supplier_sku=sp.supplier_sku,
                cost=sp.cost,
                qty_available=sp.qty_available,
                is_unlimited_stock=unlimited,
                stock_status=sp.stock_status,
                availability_status=sp.availability_status,
                shipping_info=sp.shipping_info or {},
                base_shipping_charge=sp.base_shipping_charge,
                shipping_source=sp.shipping_source,
                shipping_status=sp.shipping_status,
                shipping_updated_at=sp.shipping_updated_at,
                last_seen_at=sp.last_seen_at
            ))
            if not unlimited:
                total_stock += sp.qty_available
            costs.append(sp.cost)

        has_unlimited = any(info.is_unlimited_stock for info in sp_infos)
        in_stock_costs = [sp.cost for sp in p.supplier_products if sp.qty_available > 0 or sp.stock_status == "IN_STOCK"]
        effective_lowest_cost = min(in_stock_costs) if in_stock_costs else (min(costs) if costs else None)

        return ProductResponse(
            id=p.id,
            sku=p.sku,
            upc=p.upc,
            ean=p.ean,
            mpn=p.mpn,
            title=p.title,
            brand=p.brand,
            description=p.description,
            category=p.category,
            images=p.images or [],
            specs_json=p.specs_json or {},
            is_enabled=p.is_enabled,
            created_at=p.created_at,
            updated_at=p.updated_at,
            supplier_products=sp_infos,
            total_stock=total_stock,
            is_unlimited_stock=has_unlimited,
            lowest_cost=effective_lowest_cost
        )
