import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.supplier_product import SupplierProduct
from app.models.shipping_history import ProductShippingHistory
from app.models.supplier import Supplier

logger = logging.getLogger(__name__)

class ShippingService:
    def __init__(self, db: Session):
        self.db = db

    def resolve_shipping_charge(
        self,
        supplier_product: SupplierProduct,
        destination_zip: str = "90210",
        force_history_fallback: bool = False,
    ) -> Tuple[Optional[Decimal], str]:
        """
        Feature 1: Resolves base shipping charge for a supplier product.
        1. Attempts to source live ground shipping charge from supplier adapter.
        2. If live charge is unavailable, falls back to the most recent historical shipping charge.
        3. If no historical charge exists, flags product as 'shipping_unknown' and returns (None, 'shipping_unknown').
        4. Stores the result in ProductShippingHistory and updates SupplierProduct with audit fields.
        """
        now = datetime.now(timezone.utc)
        live_charge: Optional[Decimal] = None

        if not force_history_fallback:
            supplier = self.db.query(Supplier).filter(Supplier.id == supplier_product.supplier_id).first()
            if supplier:
                try:
                    from app.services.sync_service import SyncService
                    adapter = SyncService(self.db).get_adapter_for_supplier(supplier)
                    if hasattr(adapter, "get_ground_shipping_estimate"):
                        raw_charge = adapter.get_ground_shipping_estimate(
                            supplier_sku=supplier_product.supplier_sku,
                            destination_zip=destination_zip
                        )
                        if raw_charge is not None:
                            live_charge = Decimal(str(raw_charge))
                except Exception as exc:
                    logger.warning(
                        f"Live shipping rate lookup failed for SKU {supplier_product.supplier_sku} at {supplier.name}: {exc}"
                    )
                    live_charge = None

        if live_charge is not None and live_charge >= Decimal("0.00"):
            # Sourced live from supplier
            history_entry = ProductShippingHistory(
                product_id=supplier_product.product_id,
                supplier_id=supplier_product.supplier_id,
                supplier_product_id=supplier_product.id,
                shipping_charge=live_charge,
                source="live",
                destination_zip=destination_zip,
                created_at=now,
            )
            self.db.add(history_entry)

            supplier_product.base_shipping_charge = live_charge
            supplier_product.shipping_source = "live"
            supplier_product.shipping_status = "valid"
            supplier_product.shipping_updated_at = now
            self.db.commit()
            return live_charge, "live"

        # Fallback to historical shipping record
        recent_history = (
            self.db.query(ProductShippingHistory)
            .filter(
                ProductShippingHistory.product_id == supplier_product.product_id,
                ProductShippingHistory.supplier_id == supplier_product.supplier_id,
            )
            .order_by(desc(ProductShippingHistory.created_at))
            .first()
        )

        if recent_history and recent_history.shipping_charge is not None:
            hist_charge = Decimal(str(recent_history.shipping_charge))
            supplier_product.base_shipping_charge = hist_charge
            supplier_product.shipping_source = "history"
            supplier_product.shipping_status = "valid"
            supplier_product.shipping_updated_at = now
            self.db.commit()
            return hist_charge, "history"

        # Fallback to stored charge on supplier_product if present and not flagged unknown
        if supplier_product.base_shipping_charge is not None and supplier_product.shipping_status != "shipping_unknown":
            stored_charge = Decimal(str(supplier_product.base_shipping_charge))
            history_entry = ProductShippingHistory(
                product_id=supplier_product.product_id,
                supplier_id=supplier_product.supplier_id,
                supplier_product_id=supplier_product.id,
                shipping_charge=stored_charge,
                source="history",
                destination_zip=destination_zip,
                created_at=now,
            )
            self.db.add(history_entry)
            supplier_product.shipping_source = "history"
            supplier_product.shipping_status = "valid"
            supplier_product.shipping_updated_at = now
            self.db.commit()
            return stored_charge, "history"

        # Fallback to supplier default_shipping_charge if configured
        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_product.supplier_id).first()
        if supplier and supplier.default_shipping_charge is not None:
            def_charge = Decimal(str(supplier.default_shipping_charge))
            history_entry = ProductShippingHistory(
                product_id=supplier_product.product_id,
                supplier_id=supplier_product.supplier_id,
                supplier_product_id=supplier_product.id,
                shipping_charge=def_charge,
                source="default",
                destination_zip=destination_zip,
                created_at=now,
            )
            self.db.add(history_entry)
            supplier_product.base_shipping_charge = def_charge
            supplier_product.shipping_source = "default"
            supplier_product.shipping_status = "valid"
            supplier_product.shipping_updated_at = now
            self.db.commit()
            return def_charge, "default"

        # No live or historical charge available -> flag as shipping_unknown
        supplier_product.base_shipping_charge = None
        supplier_product.shipping_source = None
        supplier_product.shipping_status = "shipping_unknown"
        supplier_product.shipping_updated_at = now
        self.db.commit()
        return None, "shipping_unknown"
