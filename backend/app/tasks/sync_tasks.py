import logging
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.supplier import Supplier
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_supplier_task(self, supplier_id: int):
    """
    Celery task to sync a single supplier asynchronously.
    """
    db = SessionLocal()
    try:
        service = SyncService(db)
        result = service.sync_supplier(supplier_id)
        logger.info(f"Supplier sync finished for ID {supplier_id}: {result}")
        return result
    except Exception as exc:
        logger.error(f"Error syncing supplier {supplier_id}: {exc}")
        # Exponential backoff retry
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)
    finally:
        db.close()

@celery_app.task
def sync_all_suppliers_task():
    """
    Periodic task to trigger synchronization for all active suppliers.
    """
    db = SessionLocal()
    try:
        active_suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
        task_ids = []
        for s in active_suppliers:
            t = sync_supplier_task.delay(s.id)
            task_ids.append(t.id)
        return {"queued_tasks": len(task_ids), "task_ids": task_ids}
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def marketplace_push_task(self, product_id: int):
    """
    Celery task: Push updated inventory and price to all active marketplace listings.
    (Spec Section 20 & 31: marketplace_push Calculate quantity and price, update marketplace, retry failures).
    """
    from app.services.listing_service import ListingService
    db = SessionLocal()
    try:
        service = ListingService(db)
        updated_listings = service.sync_all_listings_for_product(product_id)
        logger.info(f"Marketplace push succeeded for Product {product_id}. Updated listings: {len(updated_listings)}")
        return {
            "status": "SUCCESS",
            "product_id": product_id,
            "updated_count": len(updated_listings)
        }
    except Exception as exc:
        logger.error(f"Marketplace push failed for Product {product_id}: {exc}")
        # Exponential backoff retry
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 15)
    finally:
        db.close()

@celery_app.task
def out_of_stock_monitor_task():
    """
    Safety-net sweep (Spec Section 20): re-applies out-of-stock/reactivation
    logic to every product with at least one non-withdrawn listing. Most OOS
    transitions already happen reactively when a supplier sync detects a
    quantity change (via sync_all_listings_for_product), but this catches
    anything that reactive path could miss — a stale listing whose quantity
    drifted without a detected change event, a manual DB edit, etc.
    """
    from app.models.listing import Listing
    from app.services.listing_service import ListingService

    db = SessionLocal()
    try:
        product_ids = [
            row[0] for row in db.query(Listing.product_id).filter(
                Listing.status.in_(["ACTIVE", "PAUSED", "UNAVAILABLE", "OUT_OF_STOCK"])
            ).distinct().all()
        ]
        service = ListingService(db)
        checked = 0
        for product_id in product_ids:
            try:
                service.sync_all_listings_for_product(product_id)
                checked += 1
            except Exception as exc:
                logger.error(f"Out-of-stock sweep failed for product {product_id}: {exc}")
        logger.info(f"Out-of-stock monitor swept {checked} product(s) with active listings")
        return {"status": "checked", "products_checked": checked}
    finally:
        db.close()

@celery_app.task
def catalog_reconcile_task():
    """
    Daily reconciliation (Spec Section 20): compares internal listing state
    against each active marketplace's actual live state, catching drift
    (price/status changes made directly on the marketplace, listings that
    disappeared, etc.) that wouldn't otherwise be detected.
    """
    from app.models.marketplace import Marketplace
    from app.services.listing_service import ListingService

    db = SessionLocal()
    try:
        service = ListingService(db)
        marketplaces = db.query(Marketplace).filter(Marketplace.is_active == True).all()
        results = []
        for mp in marketplaces:
            try:
                adapter = service.get_adapter_for_marketplace(mp)
                synced_count = service.reconcile_marketplace_listings(mp, adapter)
                results.append({"marketplace": mp.name, "status": "SUCCESS", "synced_count": synced_count})
            except Exception as exc:
                logger.error(f"Catalog reconciliation failed for {mp.name}: {exc}")
                results.append({"marketplace": mp.name, "status": "ERROR", "error": str(exc)})
        logger.info(f"Catalog reconciliation complete for {len(marketplaces)} marketplace(s)")
        return {"status": "reconciled", "results": results}
    finally:
        db.close()

@celery_app.task
def order_ingestion_task():
    """
    Periodic task: polls all active marketplaces for new orders and ingests them.
    """
    from app.models.marketplace import Marketplace
    from app.services.order_service import OrderService

    db = SessionLocal()
    try:
        service = OrderService(db)
        marketplaces = db.query(Marketplace).filter(Marketplace.is_active == True).all()
        total_ingested = 0
        for mp in marketplaces:
            try:
                new_orders = service.ingest_marketplace_orders(mp.id)
                total_ingested += len(new_orders)
            except Exception as exc:
                logger.error(f"Order ingestion failed for marketplace {mp.name}: {exc}")
        logger.info(f"Order ingestion task complete: {total_ingested} new order(s) ingested")
        return {"total_new_orders": total_ingested}
    finally:
        db.close()

@celery_app.task
def tracking_sync_task():
    """
    Periodic task: checks purchase orders pending shipment and syncs any
    available tracking numbers back to the originating marketplace.
    """
    from app.models.purchase_order import PurchaseOrder
    from app.services.order_service import OrderService

    db = SessionLocal()
    try:
        service = OrderService(db)
        pending_pos = db.query(PurchaseOrder).filter(
            PurchaseOrder.status.in_(["SUBMITTED", "CONFIRMED"]),
            PurchaseOrder.tracking_number.isnot(None),
        ).all()

        synced = 0
        for po in pending_pos:
            try:
                service.update_tracking(po.order_id, po.tracking_number, po.carrier)
                synced += 1
            except Exception as exc:
                logger.error(f"Tracking sync failed for PO {po.po_number}: {exc}")

        logger.info(f"Tracking sync task complete: {synced} PO(s) synced")
        return {"synced_count": synced}
    finally:
        db.close()
