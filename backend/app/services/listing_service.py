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

        # In Phase 2, we support MockEBayAdapter
        return MockEBayAdapter(credentials=credentials)

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

        # Calculate initial listed quantity (sum across supplier products if not provided)
        if custom_qty is not None:
            quantity = max(0, custom_qty)
        else:
            quantity = sum(sp.qty_available for sp in product.supplier_products)

        # Calculate price (use lowest cost + 15% default markup if not provided)
        if custom_price is not None:
            price = custom_price
        else:
            lowest_cost = min((sp.cost for sp in product.supplier_products), default=Decimal("100.00"))
            price = (lowest_cost * Decimal("1.15")).quantize(Decimal("0.01"))

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
                    status="ACTIVE",
                    selling_price=price,
                    listed_qty=quantity,
                    last_updated_at=now
                )
                self.db.add(listing)
            else:
                listing.external_listing_id = adapter_result["external_listing_id"]
                listing.status = "ACTIVE"
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
        new_qty: Optional[int] = None
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

    def sync_all_listings_for_product(self, product_id: int) -> List[Listing]:
        """
        Propagates supplier stock changes to all active listings for a product.
        (Spec Section 18 & Section 31 QA criteria:
        'Supplier stock changes propagate through Celery to marketplace quantity')
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return []

        active_listings = self.db.query(Listing).filter(
            Listing.product_id == product_id,
            Listing.status == "ACTIVE"
        ).all()

        if not active_listings:
            return []

        # Aggregate total available stock across active suppliers
        total_qty = sum(sp.qty_available for sp in product.supplier_products if sp.availability_status == "ACTIVE")

        # Recalculate price based on lowest cost
        costs = [sp.cost for sp in product.supplier_products if sp.qty_available > 0]
        lowest_cost = min(costs) if costs else (min((sp.cost for sp in product.supplier_products), default=Decimal("0.00")))
        new_price = (lowest_cost * Decimal("1.15")).quantize(Decimal("0.01")) if lowest_cost > 0 else Decimal("0.00")

        updated = []
        for l in active_listings:
            up = self.update_listing_on_marketplace(l.id, new_price=new_price, new_qty=total_qty)
            updated.append(up)
        return updated
