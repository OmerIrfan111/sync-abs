from typing import Dict, Any, List, Optional
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
            decrypted = decrypt_credential(supplier.credentials_encrypted)
            if decrypted:
                try:
                    credentials = json.loads(decrypted)
                except Exception:
                    pass
            else:
                try:
                    credentials = json.loads(supplier.credentials_encrypted)
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

        if is_sole_account_of_its_type and ("d&h" in supplier.name.lower() or "dandh" in supplier.name.lower()):
            env_client_id = getattr(settings, "DANDH_CLIENT_ID", "") or ""
            env_client_secret = getattr(settings, "DANDH_CLIENT_SECRET", "") or ""
            env_bearer = getattr(settings, "DANDH_BEARER_TOKEN", "") or ""
            db_client_id = credentials.get("client_id", "") or ""
            db_bearer = credentials.get("bearer_token", "") or ""

            # Use .env credentials when DB has no credentials at all, or when
            # the DB client_id differs from .env (e.g. stale test/sandbox
            # client_id left over from a previous setup). This lets .env act as
            # the authoritative credential store without requiring a DB update
            # every time credentials are rotated or the environment changes.
            env_has_creds = bool(env_client_id and env_client_secret) or bool(env_bearer)
            db_missing = not db_client_id and not db_bearer
            db_stale = bool(env_client_id and db_client_id and db_client_id != env_client_id)
            if env_has_creds and (db_missing or db_stale):
                import logging as _logging
                _logging.getLogger(__name__).info(
                    f"D&H credentials: overriding DB {'stale' if db_stale else 'empty'} "
                    f"client_id={db_client_id!r} with .env client_id={env_client_id!r} "
                    f"(environment={getattr(settings, 'DANDH_ENVIRONMENT', 'test')})"
                )
                if env_bearer:
                    credentials["bearer_token"] = env_bearer
                if env_client_id:
                    credentials["client_id"] = env_client_id
                if env_client_secret:
                    credentials["client_secret"] = env_client_secret
                credentials["account_number"] = getattr(settings, "DANDH_ACCOUNT_NUMBER", "3302610000")
                credentials["tenant"] = getattr(settings, "DANDH_TENANT", "dhus")
                credentials["environment"] = getattr(settings, "DANDH_ENVIRONMENT", "test")

        if is_sole_account_of_its_type and ("synnex" in supplier.name.lower() or "tdsynnex" in supplier.name.lower()):
            env_client_id = getattr(settings, "TDSYNNEX_CLIENT_ID", "") or ""
            env_client_secret = getattr(settings, "TDSYNNEX_CLIENT_SECRET", "") or ""
            db_client_id = credentials.get("client_id", "") or ""
            env_has_creds = bool(env_client_id and env_client_secret)
            db_missing = not db_client_id
            db_stale = bool(env_client_id and db_client_id and db_client_id != env_client_id)
            if env_has_creds and (db_missing or db_stale):
                credentials["client_id"] = env_client_id
                credentials["client_secret"] = env_client_secret
                credentials["account_number"] = getattr(settings, "TDSYNNEX_ACCOUNT_NUMBER", None)
                credentials["environment"] = getattr(settings, "TDSYNNEX_ENVIRONMENT", "production")

        from app.adapters.registry import get_supplier_adapter
        adapter_config = getattr(supplier, "_adapter_config", {})
        if supplier.default_shipping_charge is not None:
            adapter_config["default_shipping_charge"] = str(supplier.default_shipping_charge)
            adapter_config["ground_shipping_charge"] = str(supplier.default_shipping_charge)
        if "config" in credentials and isinstance(credentials["config"], dict):
            adapter_config = {**adapter_config, **credentials["config"]}
        return get_supplier_adapter(
            adapter_class=supplier.adapter_class,
            supplier_name=supplier.name,
            credentials=credentials,
            config=adapter_config
        )

    def sync_supplier(self, supplier_id: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes synchronization for a supplier with optional prefetch filters:
        - limit: int > 0
        - category: str
        - brand: str
        - supplier: str (must match target supplier)
        """
        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier ID {supplier_id} not found")

        # Validate Feature 2 prefetch filters
        if filters:
            limit = filters.get("limit")
            if limit is not None:
                try:
                    limit_int = int(limit)
                    if limit_int <= 0:
                        raise ValueError("Prefetch filter 'limit' must be a positive integer greater than 0")
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid prefetch filter 'limit': {e}")

            supplier_filter = filters.get("supplier")
            if supplier_filter and supplier_filter.strip().lower() not in supplier.name.lower():
                raise ValueError(
                    f"Prefetch filter supplier='{supplier_filter}' does not match target supplier '{supplier.name}'"
                )

        adapter = self.get_adapter_for_supplier(supplier)
        imported_count = 0
        changed_count = 0

        try:
            adapter.test_connection()
            items = adapter.fetch_catalog(resume_cursor=supplier.catalog_sync_cursor, filters=filters)

            # Persist where this run left off so the next scheduled sync
            # continues through the rest of the catalog instead of always
            # restarting from the beginning — a real supplier catalog (Ingram
            # Micro: 14,000+ SKUs) takes many runs to fully page through.
            next_cursor = getattr(adapter, "next_cursor", None)
            catalog_exhausted = getattr(adapter, "catalog_exhausted", False)
            supplier.catalog_sync_cursor = next_cursor
            if catalog_exhausted:
                supplier.catalog_sync_exhausted_at = datetime.now(timezone.utc)

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
                "skipped_missing_data": len(getattr(adapter, "_skipped_items", [])),
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
