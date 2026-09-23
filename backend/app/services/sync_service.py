from typing import Dict, Any, List
from datetime import datetime, timezone
import json
from sqlalchemy.orm import Session
from app.models.supplier import Supplier
from app.models.error_log import ErrorLog
from app.adapters.suppliers.mock_supplier import MockSupplierAdapter
from app.services.catalog_service import CatalogService
from app.core.security import decrypt_credential

class SyncService:
    def __init__(self, db: Session):
        self.db = db
        self.catalog_service = CatalogService(db)

    def get_adapter_for_supplier(self, supplier: Supplier):
        credentials = {}
        if supplier.credentials_encrypted:
            try:
                decrypted = decrypt_credential(supplier.credentials_encrypted)
                if decrypted:
                    credentials = json.loads(decrypted)
            except Exception:
                pass

        from app.core.config import settings

        # .env credentials are a single-account convenience fallback for the
        # original default setup. If more than one Supplier row shares the
        # same adapter_class (Phase 3: multiple supplier accounts), applying
        # this fallback to all of them would silently make every unconfigured
        # "second account" secretly reuse the first account's real
        # credentials — masking that it was never actually set up on its own.
        # In that case, require each account to have its own explicit
        # credentials_encrypted instead of guessing which one gets the .env.
        sibling_count = self.db.query(Supplier).filter(
            Supplier.adapter_class == supplier.adapter_class
        ).count()
        is_sole_account_of_its_type = sibling_count <= 1

        if is_sole_account_of_its_type and "ingram" in supplier.name.lower() and not credentials.get("client_id"):
            if getattr(settings, "INGRAM_MICRO_CLIENT_ID", None):
                credentials["client_id"] = settings.INGRAM_MICRO_CLIENT_ID
                credentials["client_secret"] = settings.INGRAM_MICRO_CLIENT_SECRET
                credentials["customer_number"] = getattr(settings, "INGRAM_MICRO_CUSTOMER_NUMBER", "21-186632")
                credentials["environment"] = getattr(settings, "INGRAM_MICRO_ENVIRONMENT", "production")

        if is_sole_account_of_its_type and ("d&h" in supplier.name.lower() or "dandh" in supplier.name.lower()) and not credentials.get("bearer_token"):
            if getattr(settings, "DANDH_BEARER_TOKEN", None):
                credentials["bearer_token"] = settings.DANDH_BEARER_TOKEN
                credentials["account_number"] = getattr(settings, "DANDH_ACCOUNT_NUMBER", "3302610000")
                credentials["client_id"] = getattr(settings, "DANDH_CLIENT_ID", "")
                credentials["client_secret"] = getattr(settings, "DANDH_CLIENT_SECRET", "")
                credentials["tenant"] = getattr(settings, "DANDH_TENANT", "dhus")
                credentials["environment"] = getattr(settings, "DANDH_ENVIRONMENT", "test")

        from app.adapters.registry import get_supplier_adapter
        return get_supplier_adapter(
            adapter_class=supplier.adapter_class,
            supplier_name=supplier.name,
            credentials=credentials
        )

    def sync_supplier(self, supplier_id: int) -> Dict[str, Any]:
        """
        Executes full synchronization for a supplier:
        1. Tests connection
        2. Fetches supplier catalog items
        3. Upserts and matches products into central catalog
        4. Detects field-level changes and records SyncLog
        5. Logs any errors to ErrorLog
        """
        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier ID {supplier_id} not found")

        adapter = self.get_adapter_for_supplier(supplier)
        imported_count = 0
        changed_count = 0

        try:
            adapter.test_connection()
            items = adapter.fetch_catalog()

            # Adapters record items they deliberately excluded (missing real
            # price/quantity data) rather than fabricating values for them.
            # Surface those as MISSING_DATA errors so staff see them, instead
            # of the item silently vanishing from the sync.
            for skipped in getattr(adapter, "_skipped_items", []):
                self.db.add(ErrorLog(
                    error_type="MISSING_DATA",
                    supplier_id=supplier.id,
                    message=f"SKU {skipped.get('sku', '?')}: {skipped.get('reason', 'missing required data')}",
                    status="PENDING",
                ))

            changed_product_ids = set()
            for item in items:
                # One malformed item (unexpected nulls, DB constraint violation,
                # etc.) must not abort the rest of a 250-item batch. A SAVEPOINT
                # isolates just this item's failed writes on rollback, without
                # expiring or invalidating unrelated session state (e.g. a
                # plain session.rollback() here would expire `supplier` and
                # crash the next line/iteration).
                try:
                    prod, _, logs = self.catalog_service.upsert_supplier_product(supplier, item)
                    imported_count += 1
                    if logs:
                        changed_count += len(logs)
                        changed_product_ids.add(prod.id)
                except Exception as item_err:
                    # rollback() expires every ORM object in the session, so
                    # `supplier` (loaded earlier via SELECT, already durably
                    # committed before this task ran) needs a fresh fetch by
                    # its plain id before it's touched again.
                    self.db.rollback()
                    supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
                    self.db.add(ErrorLog(
                        error_type="MISSING_DATA",
                        supplier_id=supplier_id,
                        message=f"SKU {getattr(item, 'supplier_sku', '?')}: catalog upsert failed: {item_err}",
                        status="PENDING",
                    ))
                    self.db.commit()

            # Automatically propagate stock & price changes to connected marketplaces (Spec Section 18 & 31)
            from app.services.listing_service import ListingService
            listing_service = ListingService(self.db)
            for pid in changed_product_ids:
                try:
                    listing_service.sync_all_listings_for_product(pid)
                except Exception as sync_err:
                    self.db.add(ErrorLog(
                        error_type="MARKETPLACE_CONNECTION_ERROR",
                        product_id=pid,
                        message=f"Automatic propagation failed: {str(sync_err)}",
                        status="PENDING"
                    ))

            supplier.last_synced_at = datetime.now(timezone.utc)
            self.db.commit()

            return {
                "status": "SUCCESSFULLY_SYNCHRONIZED",
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
                "products_imported": imported_count,
                "changes_detected": changed_count,
                "synced_at": supplier.last_synced_at.isoformat()
            }

        except Exception as exc:
            error_log = ErrorLog(
                error_type="SUPPLIER_CONNECTION_ERROR",
                supplier_id=supplier.id,
                message=str(exc),
                retry_count=0,
                status="FAILED"
            )
            self.db.add(error_log)
            self.db.commit()
            raise exc
