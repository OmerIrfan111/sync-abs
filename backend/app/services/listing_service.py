import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, timezone
import redis
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.models.listing import Listing
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.supplier_product import SupplierProduct
from app.models.error_log import ErrorLog
from app.models.sync_log import SyncLog

from app.schemas.listing import ListingResponse
from app.core.security import decrypt_credential

logger = logging.getLogger(__name__)

# Redis Client for Distributed Locks
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.get_redis_url(), socket_timeout=3)
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client

@contextmanager
def distributed_lock(lock_key: str, timeout_seconds: int = 10):
    """
    Redis distributed lock for duplicate-update prevention (Spec Section 21).
    Ensures parallel Celery workers do not conflict on the same marketplace listing.
    """
    r = get_redis_client()
    lock_acquired = False
    lock = None
    if r:
        try:
            lock = r.lock(lock_key, timeout=timeout_seconds, blocking_timeout=5)
            lock_acquired = lock.acquire(blocking=True)
        except Exception as e:
            logger.warning(f"Redis lock unavailable, proceeding with local execution: {e}")
            lock_acquired = True
    else:
        lock_acquired = True

    try:
        yield lock_acquired
    finally:
        if lock and lock_acquired:
            try:
                lock.release()
            except Exception:
                pass

class ListingService:
    def __init__(self, db: Session):
        self.db = db

    def get_adapter_for_marketplace(self, marketplace: Marketplace):
        credentials = {}
        if marketplace.credentials_encrypted:
            try:
                decrypted = decrypt_credential(marketplace.credentials_encrypted)
                if decrypted:
                    credentials = json.loads(decrypted)
            except Exception:
                pass

        from app.adapters.registry import get_marketplace_adapter
        return get_marketplace_adapter(marketplace.adapter_class, credentials=credentials)

    def reconcile_marketplace_listings(self, marketplace: Marketplace, adapter) -> int:
        """
        Compares internal Listing records against the marketplace's actual
        live state (Spec Section 20: catalog_reconcile), catching drift from
        changes made directly on the marketplace outside this system.

        Currently only implemented for Shopify, whose Admin REST API makes
        listing every live product straightforward. eBay's and Amazon's
        equivalent "list everything I'm selling" calls need pagination and
        marketplace-specific handling this system doesn't have yet — rather
        than fabricate a reconciliation that doesn't happen, this returns 0
        and the caller reports "not required" for those marketplaces so it's
        clear no real drift-check ran, not that none was needed.
        """
        is_shopify = "shopify" in marketplace.adapter_class.lower() or "shopify" in marketplace.name.lower()
        if not is_shopify:
            return 0

        res = adapter._request("/products.json?limit=50", method="GET")
        shopify_products = res.get("products", [])
        synced_count = 0
        for sp in shopify_products:
            sp_id = sp.get("id")
            sp_status = sp.get("status", "active").upper()
            db_status = "ACTIVE" if sp_status == "ACTIVE" else "WITHDRAWN"
            for v in sp.get("variants", []):
                sku = v.get("sku")
                var_id = v.get("id")
                price = Decimal(str(v.get("price", "0.00")))
                qty = v.get("inventory_quantity", 0)
                ext_id = f"shopify_{sp_id}_{var_id}"

                prod = self.db.query(Product).filter(Product.sku == sku).first()
                if not prod:
                    continue

                listing = self.db.query(Listing).filter(
                    Listing.product_id == prod.id,
                    Listing.marketplace_id == marketplace.id
                ).first()

                if not listing:
                    listing = Listing(
                        product_id=prod.id,
                        marketplace_id=marketplace.id,
                        external_listing_id=ext_id,
                        status=db_status,
                        selling_price=price,
                        listed_qty=qty
                    )
                    self.db.add(listing)
                else:
                    listing.external_listing_id = ext_id
                    listing.status = db_status
                    listing.selling_price = price
                    listing.listed_qty = qty
                synced_count += 1
        self.db.commit()
        return synced_count

    def publish_product_to_marketplace(
        self,
        product_id: int,
        marketplace_id: int,
        custom_price: Optional[Decimal] = None,
        custom_qty: Optional[int] = None,
        custom_title: Optional[str] = None,
        custom_description: Optional[str] = None,
        custom_image_url: Optional[str] = None,
        custom_weight_lbs: Optional[Decimal] = None,
        allow_upc_override: bool = False,
        actor_email: Optional[str] = None,
    ) -> Listing:
        """
        Publishes a canonical product to a selected marketplace channel.
        Allows custom title, description, price, and stock overrides.
        Integrates Feature 1 (shipping charges) and Feature 3 (duplicate UPC protection).
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found")

        marketplace = self.db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
        if not marketplace:
            raise ValueError(f"Marketplace {marketplace_id} not found")

        from app.services.restriction_service import RestrictionService
        blocking = RestrictionService(self.db).find_blocking_restriction(product, marketplace_id)
        if blocking:
            raise ValueError(
                f"Cannot publish '{product.title}' to {marketplace.name}: {blocking.reason} "
                f"(restriction #{blocking.id}, type: {blocking.restriction_type})"
            )

        # Optionally persist title, description, and custom image to canonical product.
        if custom_title and custom_title.strip():
            product.title = custom_title.strip()
        if custom_description and custom_description.strip():
            product.description = custom_description.strip()
        if custom_image_url and custom_image_url.strip():
            existing = list(product.images or [])
            new_url = custom_image_url.strip()
            updated = [new_url] + [u for u in existing if u != new_url]
            product.images = updated
        if (
            (custom_title and custom_title.strip())
            or (custom_description and custom_description.strip())
            or (custom_image_url and custom_image_url.strip())
        ):
            self.db.commit()
            self.db.refresh(product)

        # Check existing listing
        listing = self.db.query(Listing).filter(
            Listing.product_id == product_id,
            Listing.marketplace_id == marketplace_id
        ).first()

        from app.services.pricing_service import PricingService
        from app.services.inventory_service import InventoryService
        from app.services.supplier_selection_service import SupplierSelectionService
        from app.services.shipping_service import ShippingService
        from app.services.upc_protection_service import UpcProtectionService

        pricing_service = PricingService(self.db)
        inventory_service = InventoryService(self.db)
        selection_service = SupplierSelectionService(self.db)
        shipping_service = ShippingService(self.db)
        upc_service = UpcProtectionService(self.db)

        adapter = self.get_adapter_for_marketplace(marketplace)

        # Feature 3: Pre-upload duplicate UPC verification
        upc_check = upc_service.check_product_for_upload(
            product=product,
            marketplace_name=marketplace.name,
            marketplace_adapter=adapter,
            allow_override=allow_upc_override,
            actor_email=actor_email
        )
        if upc_check.is_blocked():
            raise ValueError(upc_check.message)

        best_sp = selection_service.select_best_supplier(product)
        supplier_cost = best_sp.cost if best_sp else Decimal("0.00")
        supplier_stock = best_sp.qty_available if best_sp else sum(sp.qty_available for sp in product.supplier_products)

        # Feature 1: Shipping charge resolution & guard against shipping_unknown
        shipping_charge = None
        if best_sp:
            shipping_charge, shipping_status = shipping_service.resolve_shipping_charge(best_sp)
            if shipping_status == "shipping_unknown" or shipping_charge is None:
                raise ValueError(
                    f"Cannot publish product {product.sku}: shipping charge is unknown ('shipping_unknown'). "
                    "Products must not be published with wrong or unknown shipping costs."
                )

        # Calculate initial listed quantity applying safety buffer & zero floor (Spec Section 14)
        if custom_qty is not None:
            quantity = max(0, custom_qty)
            oos_action = "SET_QUANTITY_ZERO"
        else:
            quantity, oos_action = inventory_service.calculate_marketplace_quantity(
                supplier_quantity=supplier_stock,
                product_id=product.id
            )

        # Calculate price using PricingEngine (Spec Section 16) including base shipping charge
        if custom_price is not None:
            price = custom_price
        else:
            price = pricing_service.calculate_price(
                cost=supplier_cost,
                product_id=product.id,
                marketplace_id=marketplace.id,
                shipping_charge=shipping_charge
            )

        target_status = inventory_service.determine_listing_status(quantity, oos_action)

        # A PENDING listing's async feed hasn't resolved yet (Walmart's
        # MP_ITEM_MATCH can take minutes; reconciliation only catches up
        # every 10 min). Without this guard, re-clicking "Start Selling"
        # before that resolves falls into the update-in-place branch below,
        # 404s (item doesn't exist yet), and falls through to submitting a
        # SECOND real feed for the same product — a real duplicate-
        # submission bug, not hypothetical, found 2026-10-08.
        if listing and listing.status == "PENDING":
            raise ValueError(
                f"'{product.sku}' is still being processed on {marketplace.name} from an earlier "
                "submission. Wait for it to resolve (checked automatically every 10 minutes), or use "
                "\"Check Real Status\" on the Listings page to see progress now. Submitting again "
                "would create a duplicate, conflicting request."
            )

        now = datetime.now(timezone.utc)
        if listing and listing.external_listing_id:
            try:
                adapter.update_price(listing.external_listing_id, product.sku, price)
                adapter.update_inventory(listing.external_listing_id, product.sku, quantity)
                if hasattr(adapter, "update_product_details") and (custom_title or custom_description):
                    try:
                        adapter.update_product_details(
                            listing.external_listing_id,
                            title=custom_title,
                            description=custom_description
                        )
                    except Exception as details_err:
                        logger.warning(f"Could not update details on {marketplace.name}: {details_err}")

                listing.status = target_status
                listing.selling_price = price
                listing.listed_qty = quantity
                listing.last_updated_at = now
                self.db.commit()
                self.db.refresh(listing)

                # Register in ListingRegistry (Feature 3)
                try:
                    upc_service.register_listing(
                        product=product,
                        marketplace_name=marketplace.name,
                        marketplace_listing_id=listing.external_listing_id,
                        sku=product.sku
                    )
                except Exception as reg_err:
                    logger.warning(f"Could not register listing in ListingRegistry: {reg_err}")

                # Audit log
                sync_log = SyncLog(
                    product_id=product.id,
                    field_changed=f"updated_on_{marketplace.name.lower()}",
                    old_value=None,
                    new_value=f"Listing ID: {listing.external_listing_id}, Price: ${price}, Qty: {quantity}"
                )
                self.db.add(sync_log)
                self.db.commit()

                return listing
            except Exception as e:
                logger.warning(f"Could not update existing listing in-place on {marketplace.name}: {e}. Proceeding to create/sync.")

        # Defense-in-depth: the frontend already runs this same check before
        # calling publish, but this guard protects any other caller (direct
        # API use, future integrations) from firing a real MP_ITEM_MATCH
        # feed that's already known to be impossible — Walmart only
        # supports creating an offer by matching an existing catalog item,
        # and we have a real, confirmed way to check that in advance now.
        #
        # Real bug fixed 2026-10-09: this used to fail OPEN in two cases —
        # a product with no UPC/EAN skipped the check entirely (the `and
        # (product.upc or product.ean)` condition was False, so nothing ran
        # at all), and a live-check failure (network blip, Walmart API
        # error) was caught and logged as a warning while still letting the
        # publish proceed "anyway". Both let an unverified/unmatchable
        # product reach a real MP_ITEM_MATCH submission. Walmart publish
        # must only ever proceed on a genuinely CONFIRMED match — fail
        # closed, not open, in every other case.
        if hasattr(adapter, "search_walmart_catalog_by_gtin"):
            if not (product.upc or product.ean):
                raise ValueError(
                    f"'{product.sku}' has no UPC/EAN on file — Walmart item-match requires a real GTIN to "
                    "check against their catalog, so this can't be verified as matchable. Submission was not sent."
                )
            try:
                matches = adapter.search_walmart_catalog_by_gtin(product.upc or product.ean)
            except Exception as exc:
                raise ValueError(
                    f"Could not verify '{product.sku}' against Walmart's catalog ({exc}). Not proceeding "
                    "without a confirmed match — try again, or use \"Check Real Status\" once Walmart is reachable."
                ) from exc

            specs_update = dict(product.specs_json or {})
            specs_update["walmart_match_status"] = "matchable" if matches else "not_matchable"
            specs_update["walmart_match_checked_at"] = now.isoformat()
            product.specs_json = specs_update
            self.db.commit()
            if not matches:
                raise ValueError(
                    f"'{product.sku}' isn't matchable to anything in Walmart's catalog — Walmart only "
                    "supports creating an offer by matching an existing catalog item, and this GTIN "
                    "doesn't have one. Submission was not sent."
                )

        try:
            # Resolve the effective image list: if the user picked a custom image
            # it will already be images[0] after the persist block above; no
            # additional override needed here — just pass the stored images.
            effective_images = product.images or []

            # Real weight from whichever supplier actually reports one (not
            # all do — see each adapter's fetch_catalog comments). Used by
            # marketplaces that require it for new-item creation (currently
            # Walmart's MP_ITEM_MATCH feed); adapters that don't need it
            # simply don't declare the kwarg, caught below.
            real_weight = next(
                (
                    float(sp.shipping_info["weight_lbs"])
                    for sp in product.supplier_products
                    if sp.shipping_info and sp.shipping_info.get("weight_lbs")
                ),
                None,
            )

            # A staff-entered weight (most of the catalog has none — Ingram
            # and TD SYNNEX don't return physical weight at all) overrides
            # and is persisted onto the real supplier record, so it doesn't
            # have to be re-entered on every future publish/reactivate.
            if custom_weight_lbs is not None and float(custom_weight_lbs) > 0:
                real_weight = float(custom_weight_lbs)
                target_sp = best_sp or (product.supplier_products[0] if product.supplier_products else None)
                if target_sp is not None:
                    updated_shipping = dict(target_sp.shipping_info or {})
                    updated_shipping["weight_lbs"] = real_weight
                    target_sp.shipping_info = updated_shipping
                    self.db.commit()
            try:
                adapter_result = adapter.create_listing(
                    sku=product.sku,
                    title=custom_title or product.title,
                    description=custom_description or product.description or product.title,
                    price=price,
                    quantity=quantity,
                    image_urls=effective_images,
                    upc=product.upc,
                    weight_lbs=real_weight,
                )
            except TypeError:
                adapter_result = adapter.create_listing(
                    sku=product.sku,
                    title=custom_title or product.title,
                    description=custom_description or product.description or product.title,
                    price=price,
                    quantity=quantity,
                    image_urls=effective_images
                )

            # target_status (our own real business decision — e.g. PAUSED
            # for out-of-stock) normally wins; every adapter's returned
            # status is just an echoed-back "ACTIVE" formality in the usual
            # synchronous case. The one real exception is an adapter
            # reporting "PENDING" (e.g. Walmart's async item-match feed was
            # accepted but isn't actually live yet) — that must not be
            # silently overwritten with an assumed ACTIVE/target status.
            effective_status = "PENDING" if adapter_result.get("status") == "PENDING" else target_status

            if not listing:
                listing = Listing(
                    product_id=product.id,
                    marketplace_id=marketplace.id,
                    external_listing_id=adapter_result["external_listing_id"],
                    status=effective_status,
                    selling_price=price,
                    listed_qty=quantity,
                    last_updated_at=now
                )
                self.db.add(listing)
            else:
                listing.external_listing_id = adapter_result["external_listing_id"]
                listing.status = effective_status
                listing.selling_price = price
                listing.listed_qty = quantity
                listing.last_updated_at = now

            self.db.commit()
            self.db.refresh(listing)

            # Register in ListingRegistry (Feature 3)
            try:
                upc_service.register_listing(
                    product=product,
                    marketplace_name=marketplace.name,
                    marketplace_listing_id=listing.external_listing_id,
                    sku=product.sku
                )
            except Exception as reg_err:
                logger.warning(f"Could not register listing in ListingRegistry: {reg_err}")

            # Audit log
            sync_log = SyncLog(
                product_id=product.id,
                field_changed=f"published_to_{marketplace.name.lower()}",
                old_value=None,
                new_value=f"Listing ID: {listing.external_listing_id}, Price: ${price}, Qty: {quantity}"
            )
            self.db.add(sync_log)

            # Walmart's item-match feed is async and returns a real feed_id
            # that can be polled for actual processing status — without
            # saving it, a PENDING listing has no way to ever ask Walmart
            # "did this actually finish?" beyond re-checking for a 404.
            feed_id = (adapter_result.get("metadata") or {}).get("feed_id")
            if feed_id:
                self.db.add(SyncLog(
                    product_id=product.id,
                    field_changed=f"{marketplace.name.lower()}_feed_id",
                    old_value=None,
                    new_value=str(feed_id)
                ))
            self.db.commit()

            return listing

        except Exception as exc:
            error_log = ErrorLog(
                error_type="LISTING_ERROR",
                product_id=product.id,
                marketplace_id=marketplace.id,
                message=str(exc),
                retry_count=0,
                status="FAILED"
            )
            self.db.add(error_log)
            self.db.commit()
            raise exc

    def update_listing_on_marketplace(
        self,
        listing_id: int,
        new_price: Optional[Decimal] = None,
        new_qty: Optional[int] = None,
        new_status: Optional[str] = None
    ) -> Listing:
        """
        Updates an existing listing with Redis concurrency protection (Spec Section 21).
        """
        lock_key = f"sync:lock:listing:{listing_id}"
        with distributed_lock(lock_key) as acquired:
            if not acquired:
                raise RuntimeError(f"Could not acquire distributed lock for listing {listing_id}")

            listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            marketplace = listing.marketplace
            adapter = self.get_adapter_for_marketplace(marketplace)

            try:
                now = datetime.now(timezone.utc)

                if new_qty is not None and new_qty != listing.listed_qty:
                    adapter.update_inventory(listing.external_listing_id or "", listing.product.sku, new_qty)
                    self.db.add(SyncLog(
                        product_id=listing.product_id,
                        field_changed=f"{marketplace.name}_quantity_update",
                        old_value=str(listing.listed_qty),
                        new_value=str(new_qty)
                    ))
                    listing.listed_qty = new_qty

                if new_price is not None and new_price != listing.selling_price:
                    adapter.update_price(listing.external_listing_id or "", listing.product.sku, new_price)
                    self.db.add(SyncLog(
                        product_id=listing.product_id,
                        field_changed=f"{marketplace.name}_price_update",
                        old_value=str(listing.selling_price),
                        new_value=str(new_price)
                    ))
                    listing.selling_price = new_price

                if new_status is not None and new_status != listing.status:
                    # A failed withdraw/reactivate call must not fall through to
                    # the status write below — that would record this listing as
                    # WITHDRAWN/ACTIVE in our own DB while the real marketplace
                    # state never changed. Let it propagate to the outer except,
                    # which logs an ErrorLog and re-raises instead of committing.
                    if new_status in ["PAUSED", "WITHDRAWN"] and listing.status == "ACTIVE":
                        if listing.external_listing_id:
                            try:
                                adapter.withdraw_listing(listing.external_listing_id, listing.product.sku if listing.product else None)
                            except TypeError:
                                adapter.withdraw_listing(listing.external_listing_id)
                    elif new_status == "ACTIVE" and listing.status in ["PAUSED", "WITHDRAWN"]:
                        if listing.external_listing_id:
                            try:
                                adapter.reactivate_listing(listing.external_listing_id, listing.product.sku if listing.product else None)
                            except TypeError:
                                adapter.reactivate_listing(listing.external_listing_id)

                    self.db.add(SyncLog(
                        product_id=listing.product_id,
                        field_changed=f"{marketplace.name}_status_update",
                        old_value=listing.status,
                        new_value=new_status
                    ))
                    listing.status = new_status

                listing.last_updated_at = now
                self.db.commit()
                self.db.refresh(listing)
                return listing

            except Exception as exc:
                error_log = ErrorLog(
                    error_type="MARKETPLACE_CONNECTION_ERROR",
                    product_id=listing.product_id,
                    marketplace_id=listing.marketplace_id,
                    message=str(exc),
                    retry_count=0,
                    status="FAILED"
                )
                self.db.add(error_log)
                self.db.commit()
                raise exc

    def withdraw_listing_from_marketplace(self, listing_id: int) -> Listing:
        """Withdraws/pauses an active marketplace listing."""
        lock_key = f"sync:lock:listing:{listing_id}"
        with distributed_lock(lock_key) as acquired:
            listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            adapter = self.get_adapter_for_marketplace(listing.marketplace)
            if listing.external_listing_id:
                try:
                    adapter.withdraw_listing(listing.external_listing_id, listing.product.sku if listing.product else None)
                except TypeError:
                    adapter.withdraw_listing(listing.external_listing_id)

            listing.status = "WITHDRAWN"
            listing.listed_qty = 0
            listing.last_updated_at = datetime.now(timezone.utc)

            self.db.add(SyncLog(
                product_id=listing.product_id,
                field_changed=f"{listing.marketplace.name}_withdrawn",
                old_value="ACTIVE",
                new_value="WITHDRAWN"
            ))
            self.db.commit()
            self.db.refresh(listing)
            return listing

    def retire_or_withdraw_listing(self, listing: Listing) -> str:
        """
        Best-effort real marketplace cleanup for a listing that's about to be
        deleted from our own database — retires it for real where the
        adapter supports that (Walmart), otherwise falls back to a zero-stock
        withdraw. Never raises: a cleanup failure must not block the local
        delete, but the caller gets a note explaining what happened so it
        can be surfaced instead of silently losing track of a still-live
        marketplace item (real incident, 2026-10-07: product 00TF99 stayed
        live on Walmart with zero local record after a delete that skipped
        this).
        """
        if not listing.external_listing_id:
            return "no external listing id on file, nothing to clean up on the marketplace"
        try:
            marketplace = listing.marketplace
            adapter = self.get_adapter_for_marketplace(marketplace) if marketplace else None
            if adapter is not None and hasattr(adapter, "retire_item"):
                adapter.retire_item(listing.external_listing_id)
                return "retired"
            else:
                self.withdraw_listing_from_marketplace(listing.id)
                return "zeroed (no real delete supported by this marketplace)"
        except Exception as exc:
            return f"marketplace cleanup failed, removed locally only: {exc}"

    def reactivate_listing_on_marketplace(self, listing_id: int) -> Listing:
        """Reactivates / unhides a withdrawn or paused marketplace listing."""
        lock_key = f"sync:lock:listing:{listing_id}"
        with distributed_lock(lock_key) as acquired:
            listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            product = listing.product
            from app.services.inventory_service import InventoryService
            from app.services.pricing_service import PricingService
            from app.services.supplier_selection_service import SupplierSelectionService

            selection_service = SupplierSelectionService(self.db)
            inventory_service = InventoryService(self.db)
            pricing_service = PricingService(self.db)

            best_sp = selection_service.select_best_supplier(product)
            supplier_stock = best_sp.qty_available if best_sp else sum(sp.qty_available for sp in product.supplier_products)
            supplier_cost = best_sp.cost if best_sp else Decimal("0.00")

            calculated_qty, _ = inventory_service.calculate_marketplace_quantity(
                supplier_quantity=supplier_stock,
                product_id=product.id
            )
            # If calculated_qty is 0 but product has stock, default to at least 1 or stock
            active_qty = calculated_qty if calculated_qty > 0 else (supplier_stock if supplier_stock > 0 else 1)

            price = listing.selling_price if listing.selling_price > 0 else pricing_service.calculate_price(
                cost=supplier_cost,
                product_id=product.id,
                marketplace_id=listing.marketplace_id
            )

            adapter = self.get_adapter_for_marketplace(listing.marketplace)
            if listing.external_listing_id:
                try:
                    try:
                        adapter.reactivate_listing(listing.external_listing_id, product.sku)
                    except TypeError:
                        adapter.reactivate_listing(listing.external_listing_id)
                    adapter.update_inventory(listing.external_listing_id, product.sku, active_qty)
                    adapter.update_price(listing.external_listing_id, product.sku, price)
                except Exception as e:
                    # A failed marketplace call must not be followed by marking
                    # this listing ACTIVE in our own DB below — that would be
                    # the same fake-success drift already fixed for Walmart.
                    error_log = ErrorLog(
                        error_type="MARKETPLACE_CONNECTION_ERROR",
                        product_id=product.id,
                        marketplace_id=listing.marketplace_id,
                        message=str(e),
                        retry_count=0,
                        status="FAILED"
                    )
                    self.db.add(error_log)
                    self.db.commit()
                    raise

            old_status = listing.status
            listing.status = "ACTIVE"
            listing.listed_qty = active_qty
            listing.selling_price = price
            listing.last_updated_at = datetime.now(timezone.utc)

            self.db.add(SyncLog(
                product_id=listing.product_id,
                field_changed=f"{listing.marketplace.name}_reactivated",
                old_value=old_status,
                new_value="ACTIVE"
            ))
            self.db.commit()
            self.db.refresh(listing)
            return listing

    def sync_all_listings_for_product(self, product_id: int) -> List[Listing]:
        """
        Propagates supplier stock changes to all listings for a product,
        applying multi-supplier selection, pricing formulas, and safety buffers.
        (Spec Section 13, 14, 15, 16, 18, 29 & Section 31 QA criteria)
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return []

        listings = self.db.query(Listing).filter(
            Listing.product_id == product_id,
            Listing.status.in_(["ACTIVE", "PAUSED", "UNAVAILABLE", "OUT_OF_STOCK"])
        ).all()

        if not listings:
            return []

        from app.services.pricing_service import PricingService
        from app.services.inventory_service import InventoryService
        from app.services.supplier_selection_service import SupplierSelectionService

        pricing_service = PricingService(self.db)
        inventory_service = InventoryService(self.db)
        selection_service = SupplierSelectionService(self.db)

        # Multi-supplier selection
        best_sp = selection_service.select_best_supplier(product)
        if best_sp:
            supplier_cost = best_sp.cost
            supplier_stock = best_sp.qty_available
        else:
            active_sps = [sp for sp in product.supplier_products if sp.availability_status == "ACTIVE"]
            supplier_cost = min((sp.cost for sp in active_sps), default=Decimal("0.00")) if active_sps else Decimal("0.00")
            supplier_stock = 0

        # Safety buffer and marketplace quantity
        target_qty, oos_action = inventory_service.calculate_marketplace_quantity(
            supplier_quantity=supplier_stock,
            product_id=product.id
        )

        updated = []
        for l in listings:
            target_price = pricing_service.calculate_price(
                cost=supplier_cost,
                product_id=product.id,
                marketplace_id=l.marketplace_id
            )
            target_status = inventory_service.determine_listing_status(
                marketplace_qty=target_qty,
                oos_action=oos_action,
                current_status=l.status
            )

            up = self.update_listing_on_marketplace(
                l.id,
                new_price=target_price,
                new_qty=target_qty,
                new_status=target_status
            )
            updated.append(up)
        return updated

    def reconcile_pending_async_listings(self) -> Dict[str, int]:
        """
        Polls real processing status for marketplaces whose item creation is
        asynchronous (currently Walmart's MP_ITEM_MATCH feed) — without this,
        a PENDING listing stays PENDING forever unless someone manually
        clicks "Check Real Status"; this is what actually keeps it current.
        Uses the feed_id saved at publish time (see publish_product_to_marketplace)
        to ask the real marketplace what happened, same mechanism as the
        manual /listings/{id}/real-status endpoint.
        """
        pending_listings = (
            self.db.query(Listing)
            .filter(Listing.status == "PENDING")
            .all()
        )

        updated_active = 0
        updated_failed = 0
        still_pending = 0

        for listing in pending_listings:
            marketplace = listing.marketplace
            if not marketplace:
                continue
            adapter = self.get_adapter_for_marketplace(marketplace)
            if not hasattr(adapter, "get_feed_status"):
                continue

            feed_log = (
                self.db.query(SyncLog)
                .filter(
                    SyncLog.product_id == listing.product_id,
                    SyncLog.field_changed == f"{marketplace.name.lower()}_feed_id",
                )
                .order_by(desc(SyncLog.synced_at))
                .first()
            )
            if not feed_log:
                continue

            try:
                feed_result = adapter.get_feed_status(feed_log.new_value)
            except Exception as exc:
                logger.warning(f"Could not poll feed status for listing {listing.id}: {exc}")
                continue

            item_statuses = (
                (feed_result.get("itemDetails") or {}).get("itemIngestionStatus") or []
            )
            if feed_result.get("feedStatus") == "ERROR":
                listing.status = "ERROR"
                updated_failed += 1
            elif item_statuses and all(
                s.get("ingestionStatus") not in ("SUCCESS", None) for s in item_statuses
            ) and all(s.get("ingestionErrors") for s in item_statuses):
                listing.status = "ERROR"
                updated_failed += 1
            elif feed_result.get("feedStatus") == "PROCESSED" and feed_result.get("itemsSucceeded", 0) > 0:
                listing.status = "ACTIVE"
                updated_active += 1
                # MP_ITEM_MATCH has no quantity field at all — Walmart creates
                # the matched item with 0 stock by default, so it's live but
                # not actually purchasable until a real inventory push
                # happens. This is the first moment we know the item exists
                # on Walmart's side (confirmed via SUCCESS ingestion), so
                # it's the right time to push the real stock we already
                # intended to list it with.
                if hasattr(adapter, "update_inventory") and listing.listed_qty:
                    try:
                        adapter.update_inventory(
                            listing.external_listing_id, listing.external_listing_id, listing.listed_qty
                        )
                    except Exception as exc:
                        logger.warning(
                            f"Listing {listing.id} went ACTIVE but real inventory push failed: {exc}"
                        )
            else:
                still_pending += 1

        self.db.commit()
        return {"active": updated_active, "failed": updated_failed, "still_pending": still_pending}
