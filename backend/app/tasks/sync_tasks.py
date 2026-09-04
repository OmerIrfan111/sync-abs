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
    """Periodic out of stock task placeholder for Phase 1/3"""
    logger.info("Executing periodic out-of-stock monitor...")
    return {"status": "checked"}

@celery_app.task
def catalog_reconcile_task():
    """Periodic catalog reconciliation placeholder"""
    logger.info("Executing daily catalog reconciliation...")
    return {"status": "reconciled"}
