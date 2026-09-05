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
from app.adapters.marketplaces.mock_ebay import MockEBayAdapter
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

    def publish_product_to_marketplace(
        self,
        product_id: int,
        marketplace_id: int,
        custom_price: Optional[Decimal] = None,
        custom_qty: Optional[int] = None
    ) -> Listing:
        """
        Publishes a canonical product to a selected marketplace channel.
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found")

        marketplace = self.db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
        if not marketplace:
            raise ValueError(f"Marketplace {marketplace_id} not found")

        # Check existing listing
        listing = self.db.query(Listing).filter(
            Listing.product_id == product_id,
            Listing.marketplace_id == marketplace_id
        ).first()

        from app.services.pricing_service import PricingService
        from app.services.inventory_service import InventoryService
        from app.services.supplier_selection_service import SupplierSelectionService

        pricing_service = PricingService(self.db)
        inventory_service = InventoryService(self.db)
        selection_service = SupplierSelectionService(self.db)

        best_sp = selection_service.select_best_supplier(product)
        supplier_cost = best_sp.cost if best_sp else Decimal("0.00")
        supplier_stock = best_sp.qty_available if best_sp else sum(sp.qty_available for sp in product.supplier_products)

        # Calculate initial listed quantity applying safety buffer & zero floor (Spec Section 14)
        if custom_qty is not None:
            quantity = max(0, custom_qty)
            oos_action = "SET_QUANTITY_ZERO"
        else:
            quantity, oos_action = inventory_service.calculate_marketplace_quantity(
                supplier_quantity=supplier_stock,
                product_id=product.id
            )

        # Calculate price using PricingEngine (Spec Section 16)
        if custom_price is not None:
            price = custom_price
        else:
            price = pricing_service.calculate_price(
                cost=supplier_cost,
                product_id=product.id,
                marketplace_id=marketplace.id
            )

        target_status = inventory_service.determine_listing_status(quantity, oos_action)

        adapter = self.get_adapter_for_marketplace(marketplace)

        try:
            adapter_result = adapter.create_listing(
                sku=product.sku,
                title=product.title,
                description=product.description or product.title,
                price=price,
                quantity=quantity,
                image_urls=product.images or []
            )

            now = datetime.now(timezone.utc)
            if not listing:
                listing = Listing(
                    product_id=product.id,
                    marketplace_id=marketplace.id,
                    external_listing_id=adapter_result["external_listing_id"],
                    status=target_status,
                    selling_price=price,
                    listed_qty=quantity,
                    last_updated_at=now
                )
                self.db.add(listing)
            else:
                listing.external_listing_id = adapter_result["external_listing_id"]
                listing.status = target_status
                listing.selling_price = price
                listing.listed_qty = quantity
                listing.last_updated_at = now

            self.db.commit()
            self.db.refresh(listing)

            # Audit log
            sync_log = SyncLog(
                product_id=product.id,
                field_changed=f"published_to_{marketplace.name.lower()}",
                old_value=None,
                new_value=f"Listing ID: {listing.external_listing_id}, Price: ${price}, Qty: {quantity}"
            )
            self.db.add(sync_log)
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
                    if new_status in ["PAUSED", "WITHDRAWN"] and listing.status == "ACTIVE":
                        if listing.external_listing_id:
                            try:
                                adapter.withdraw_listing(listing.external_listing_id)
                            except Exception:
                                pass
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
                    adapter.update_inventory(listing.external_listing_id, product.sku, active_qty)
                    adapter.update_price(listing.external_listing_id, product.sku, price)
                except Exception:
                    pass

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
