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

        if supplier.adapter_class == "MockSupplierAdapter":
            return MockSupplierAdapter(supplier_name=supplier.name, credentials=credentials)
        
        # Default to mock adapter with supplier's name
        return MockSupplierAdapter(supplier_name=supplier.name, credentials=credentials)

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

            for item in items:
                _, _, logs = self.catalog_service.upsert_supplier_product(supplier, item)
                imported_count += 1
                if logs:
                    changed_count += len(logs)

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
