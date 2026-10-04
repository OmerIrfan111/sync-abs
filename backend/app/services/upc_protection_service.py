import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from app.core.upc_utils import normalize_upc
from app.core.product_matcher import calculate_product_similarity, is_same_product
from app.core.config import settings
from app.models.listing_registry import ListingRegistry
from app.models.product import Product
from app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)

@dataclass
class UpcCheckResult:
    status: str  # allowed, uploaded, blocked_upc_conflict, blocked_cross_marketplace_conflict, blocked_duplicate_listing, blocked_batch_duplicate, uploaded_override
    message: str
    normalized_upc: Optional[str] = None
    similarity_score: Optional[float] = None
    conflicting_listing: Optional[Dict[str, Any]] = None
    marketplace: Optional[str] = None
    check_source: str = "local"  # "local", "live", "checked_local_only"

    def is_blocked(self) -> bool:
        return self.status.startswith("blocked_")


class UpcProtectionService:
    def __init__(self, db: Session):
        self.db = db

    def check_product_for_upload(
        self,
        product: Product,
        marketplace_name: str,
        marketplace_adapter: Optional[Any] = None,
        allow_override: bool = False,
        actor_email: Optional[str] = None,
    ) -> UpcCheckResult:
        """
        Executes pre-upload duplicate UPC verification in strict required order:
        1. UPC normalization & check-digit validation
        2. Same marketplace, same UPC, different product -> blocked_upc_conflict
        3. Other marketplace, same UPC, different product -> blocked_cross_marketplace_conflict
        4. Same marketplace, same UPC, same product -> blocked_duplicate_listing
        5. Other marketplace, same UPC, same product -> ALLOWED
        6. Live marketplace lookup fallback handling -> checked_local_only if API fails
        7. Manual admin override support with audit logging
        """
        raw_code = product.upc or product.ean
        if not raw_code:
            # If no UPC exists on product, pass through
            return UpcCheckResult(
                status="allowed",
                message="Product has no UPC code assigned",
                check_source="local"
            )

        norm_upc = normalize_upc(raw_code)
        target_mkt = marketplace_name.strip().lower()

        # 3a. Same marketplace, same UPC check
        same_mkt_listing = (
            self.db.query(ListingRegistry)
            .filter(
                ListingRegistry.normalized_upc == norm_upc,
                ListingRegistry.marketplace == target_mkt,
                ListingRegistry.status == "ACTIVE"
            )
            .first()
        )

        if same_mkt_listing and same_mkt_listing.product_id != product.id:
            same, score = is_same_product(
                product.title, product.brand,
                same_mkt_listing.title, same_mkt_listing.brand
            )
            conflict_details = {
                "id": same_mkt_listing.id,
                "product_id": same_mkt_listing.product_id,
                "title": same_mkt_listing.title,
                "brand": same_mkt_listing.brand,
                "marketplace": same_mkt_listing.marketplace,
                "listing_id": same_mkt_listing.marketplace_listing_id or same_mkt_listing.sku,
            }

            if not same:
                # Same marketplace, same UPC, different product
                msg = (
                    f"UPC {norm_upc} is already listed as '{same_mkt_listing.title}' "
                    f"on {same_mkt_listing.marketplace} (listing/SKU/ID {conflict_details['listing_id'] or same_mkt_listing.id})"
                )
                if allow_override:
                    self._record_override_audit(norm_upc, "blocked_upc_conflict", actor_email, product.id)
                    return UpcCheckResult(status="uploaded_override", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=conflict_details, marketplace=target_mkt)
                return UpcCheckResult(status="blocked_upc_conflict", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=conflict_details, marketplace=target_mkt)
            else:
                # Same marketplace, same UPC, same product (duplicate listing)
                msg = (
                    f"Product with UPC {norm_upc} is already listed on {same_mkt_listing.marketplace} "
                    f"as '{same_mkt_listing.title}' (listing/SKU/ID {conflict_details['listing_id'] or same_mkt_listing.id})"
                )
                if allow_override:
                    self._record_override_audit(norm_upc, "blocked_duplicate_listing", actor_email, product.id)
                    return UpcCheckResult(status="uploaded_override", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=conflict_details, marketplace=target_mkt)
                return UpcCheckResult(status="blocked_duplicate_listing", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=conflict_details, marketplace=target_mkt)

        # 3b. Any other marketplace, same UPC check
        other_mkt_listing = (
            self.db.query(ListingRegistry)
            .filter(
                ListingRegistry.normalized_upc == norm_upc,
                ListingRegistry.marketplace != target_mkt,
                ListingRegistry.status == "ACTIVE"
            )
            .first()
        )

        if other_mkt_listing and other_mkt_listing.product_id != product.id:
            same, score = is_same_product(
                product.title, product.brand,
                other_mkt_listing.title, other_mkt_listing.brand
            )
            conflict_details = {
                "id": other_mkt_listing.id,
                "product_id": other_mkt_listing.product_id,
                "title": other_mkt_listing.title,
                "brand": other_mkt_listing.brand,
                "marketplace": other_mkt_listing.marketplace,
                "listing_id": other_mkt_listing.marketplace_listing_id or other_mkt_listing.sku,
            }

            if not same:
                # Other marketplace, same UPC, different product
                msg = (
                    f"UPC {norm_upc} is already listed as '{other_mkt_listing.title}' "
                    f"on {other_mkt_listing.marketplace} (listing/SKU/ID {conflict_details['listing_id'] or other_mkt_listing.id})"
                )
                if allow_override:
                    self._record_override_audit(norm_upc, "blocked_cross_marketplace_conflict", actor_email, product.id)
                    return UpcCheckResult(status="uploaded_override", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=conflict_details, marketplace=target_mkt)
                return UpcCheckResult(status="blocked_cross_marketplace_conflict", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=conflict_details, marketplace=target_mkt)

        # 4. Live Marketplace Lookup (if adapter supports live lookup by UPC)
        check_source = "local"
        if marketplace_adapter and hasattr(marketplace_adapter, "lookup_catalog_by_upc"):
            try:
                live_item = marketplace_adapter.lookup_catalog_by_upc(norm_upc)
                check_source = "live"
                if live_item:
                    live_title = live_item.get("title", "")
                    live_brand = live_item.get("brand")
                    same, score = is_same_product(product.title, product.brand, live_title, live_brand)
                    live_details = {
                        "marketplace": target_mkt,
                        "title": live_title,
                        "brand": live_brand,
                        "listing_id": live_item.get("listing_id") or live_item.get("asin"),
                    }
                    if not same:
                        msg = f"Live marketplace check: UPC {norm_upc} is already listed as '{live_title}' on {target_mkt} (ID {live_details['listing_id']})"
                        return UpcCheckResult(status="blocked_upc_conflict", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=live_details, marketplace=target_mkt, check_source="live")
                    else:
                        msg = f"Live marketplace check: Product with UPC {norm_upc} already exists on {target_mkt} as '{live_title}'"
                        return UpcCheckResult(status="blocked_duplicate_listing", message=msg, normalized_upc=norm_upc, similarity_score=score, conflicting_listing=live_details, marketplace=target_mkt, check_source="live")
            except Exception as exc:
                logger.warning(f"Live marketplace lookup for UPC {norm_upc} failed/rate-limited: {exc}; falling back to local registry")
                check_source = "checked_local_only"

        return UpcCheckResult(
            status="allowed",
            message=f"UPC {norm_upc} passed all duplicate and conflict checks",
            normalized_upc=norm_upc,
            marketplace=target_mkt,
            check_source=check_source
        )

    def check_batch_for_conflicts(
        self,
        batch_items: List[Dict[str, Any]],
    ) -> Dict[str, UpcCheckResult]:
        """
        Step 5: Batch-level duplicate UPC verification.
        Inside one upload batch, if two different products share a UPC (for same or different marketplaces),
        reject BOTH and report them. Do not silently pick one.
        Returns a dict mapping item key/index to UpcCheckResult.
        """
        results: Dict[str, UpcCheckResult] = {}
        upc_to_items: Dict[str, List[Dict[str, Any]]] = {}

        for item in batch_items:
            key = str(item.get("id") or item.get("sku") or id(item))
            raw_upc = item.get("upc") or item.get("ean")
            if not raw_upc:
                results[key] = UpcCheckResult(status="allowed", message="No UPC present")
                continue
            try:
                norm = normalize_upc(raw_upc)
                item["_normalized_upc"] = norm
                upc_to_items.setdefault(norm, []).append((key, item))
            except Exception as e:
                results[key] = UpcCheckResult(status="blocked_upc_conflict", message=str(e))

        for norm_upc, items_list in upc_to_items.items():
            if len(items_list) > 1:
                # Multiple items share the same UPC in this batch
                # Check if they are different products
                has_conflict = False
                first_key, first_item = items_list[0]
                first_title = first_item.get("title", "")
                first_brand = first_item.get("brand")

                for other_key, other_item in items_list[1:]:
                    other_title = other_item.get("title", "")
                    other_brand = other_item.get("brand")
                    same, score = is_same_product(first_title, first_brand, other_title, other_brand)
                    if not same:
                        has_conflict = True
                        break

                if has_conflict:
                    # Reject BOTH / ALL conflicting items in the batch
                    for k, it in items_list:
                        results[k] = UpcCheckResult(
                            status="blocked_batch_duplicate",
                            message=f"In-batch conflict: UPC {norm_upc} is attached to multiple different products in this upload batch",
                            normalized_upc=norm_upc,
                        )
                else:
                    # Same product in batch: allow if targeting different marketplaces, block if targeting same marketplace twice
                    seen_mkts = set()
                    for k, it in items_list:
                        mkt = (it.get("marketplace") or "").lower()
                        if mkt in seen_mkts:
                            results[k] = UpcCheckResult(
                                status="blocked_batch_duplicate",
                                message=f"In-batch duplicate: identical product with UPC {norm_upc} submitted multiple times for {mkt}",
                                normalized_upc=norm_upc,
                            )
                        else:
                            seen_mkts.add(mkt)
                            results[k] = UpcCheckResult(status="allowed", message="Batch item passed", normalized_upc=norm_upc)
            else:
                k, it = items_list[0]
                results[k] = UpcCheckResult(status="allowed", message="Batch item passed", normalized_upc=norm_upc)

        return results

    def register_listing(
        self,
        product: Product,
        marketplace_name: str,
        marketplace_listing_id: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> ListingRegistry:
        """
        Records an active listing into the ListingRegistry.
        Catches database unique constraint violations to handle race conditions safely.
        """
        raw_code = product.upc or product.ean
        if not raw_code:
            return None

        norm_upc = normalize_upc(raw_code)
        target_mkt = marketplace_name.strip().lower()

        existing = (
            self.db.query(ListingRegistry)
            .filter(
                ListingRegistry.normalized_upc == norm_upc,
                ListingRegistry.marketplace == target_mkt
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if existing:
            existing.product_id = product.id
            existing.title = product.title
            existing.brand = product.brand
            existing.marketplace_listing_id = marketplace_listing_id or existing.marketplace_listing_id
            existing.sku = sku or product.sku or existing.sku
            existing.status = "ACTIVE"
            existing.updated_at = now
            self.db.commit()
            return existing

        registry_entry = ListingRegistry(
            normalized_upc=norm_upc,
            marketplace=target_mkt,
            marketplace_listing_id=marketplace_listing_id,
            sku=sku or product.sku,
            product_id=product.id,
            title=product.title,
            brand=product.brand,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        self.db.add(registry_entry)
        try:
            self.db.commit()
            return registry_entry
        except IntegrityError as exc:
            self.db.rollback()
            logger.error(f"Concurrent upload race condition detected on ({target_mkt}, {norm_upc}): {exc}")
            raise ValueError(
                f"Concurrent upload conflict: UPC {norm_upc} was already registered on {target_mkt} by a simultaneous transaction."
            )

    def _record_override_audit(self, upc: str, original_block_type: str, actor_email: Optional[str], product_id: int):
        actor = actor_email or "admin"
        log = SyncLog(
            product_id=product_id,
            field_changed="upc_override_applied",
            old_value=original_block_type,
            new_value=f"ADMIN OVERRIDE: Allowed UPC {upc} despite {original_block_type} by {actor}"
        )
        self.db.add(log)
        self.db.commit()
