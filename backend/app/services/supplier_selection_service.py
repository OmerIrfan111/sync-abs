from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.supplier_product import SupplierProduct
from app.models.supplier_priority import SupplierPriority

class SupplierSelectionService:
    def __init__(self, db: Session):
        self.db = db

    def select_best_supplier(
        self,
        product: Product,
        selection_rule_override: Optional[str] = None
    ) -> Optional[SupplierProduct]:
        """
        Multi-Supplier Selection Engine (Spec Section 13):
        Configurable selection based on availability, lowest cost, supplier priority rank, and shipping location.
        Supported rules:
        - LOWEST_COST (default)
        - HIGHEST_STOCK
        - PRIORITY_RANK
        - SHIPPING_LOCATION
        """
        supplier_products: List[SupplierProduct] = [
            sp for sp in product.supplier_products
            if sp.availability_status == "ACTIVE" and sp.supplier and sp.supplier.is_active
        ]

        if not supplier_products:
            return None

        if len(supplier_products) == 1:
            return supplier_products[0]

        # Determine selection rule from SupplierPriority or fallback to LOWEST_COST
        selection_rule = selection_rule_override
        if not selection_rule:
            configured_priority = self.db.query(SupplierPriority).filter(
                SupplierPriority.product_id == product.id
            ).first()
            if configured_priority and configured_priority.selection_rule:
                selection_rule = configured_priority.selection_rule
            else:
                selection_rule = "LOWEST_COST"

        rule = selection_rule.upper()

        # Separate items with stock vs out of stock
        in_stock = [sp for sp in supplier_products if sp.qty_available > 0]
        candidates = in_stock if in_stock else supplier_products

        if rule == "LOWEST_COST":
            # Minimum cost among available suppliers
            return min(candidates, key=lambda sp: sp.cost)

        elif rule == "HIGHEST_STOCK":
            # Maximum stock available
            return max(candidates, key=lambda sp: sp.qty_available)

        elif rule == "PRIORITY_RANK":
            # Check configured ranks (rank 1 > rank 2)
            priorities = self.db.query(SupplierPriority).filter(
                SupplierPriority.product_id == product.id
            ).all()
            priority_map = {p.supplier_id: p.priority_rank for p in priorities}

            # Sort by rank (lowest integer = highest rank), then cost
            return min(
                candidates,
                key=lambda sp: (priority_map.get(sp.supplier_id, 999), sp.cost)
            )

        elif rule == "SHIPPING_LOCATION":
            # Shortest lead_time_days in shipping_info dict
            def get_lead_time(sp: SupplierProduct) -> int:
                info = sp.shipping_info or {}
                return int(info.get("lead_time_days", 999))

            return min(candidates, key=get_lead_time)

        # Default fallback
        return min(candidates, key=lambda sp: sp.cost)
