from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.inventory_rule import InventoryRule

class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def resolve_rule(self, product_id: Optional[int] = None) -> Optional[InventoryRule]:
        """
        Resolves InventoryRule: product-specific first, then global default.
        """
        if product_id:
            rule = self.db.query(InventoryRule).filter(
                InventoryRule.product_id == product_id
            ).first()
            if rule:
                return rule

        # Global rule (product_id is null)
        rule = self.db.query(InventoryRule).filter(
            InventoryRule.product_id.is_(None)
        ).first()
        return rule

    def calculate_marketplace_quantity(
        self,
        supplier_quantity: int,
        product_id: Optional[int] = None,
        rule_override: Optional[InventoryRule] = None
    ) -> Tuple[int, str]:
        """
        Calculates marketplace quantity and determines status (Spec Section 14 & 15).
        Formula: max(supplier_quantity - safety_buffer, 0)
        Never produces negative numbers.

        Returns: (marketplace_quantity, oos_action)
        """
        rule = rule_override or self.resolve_rule(product_id)
        safety_buffer = rule.safety_buffer if rule else 0
        oos_action = (rule.out_of_stock_action if rule else "SET_QUANTITY_ZERO").upper()

        if supplier_quantity <= 0:
            return 0, oos_action

        # Apply safety buffer with strict zero floor
        calc_qty = supplier_quantity - safety_buffer
        marketplace_qty = max(calc_qty, 0)

        return marketplace_qty, oos_action

    def determine_listing_status(
        self,
        marketplace_qty: int,
        oos_action: str = "SET_QUANTITY_ZERO",
        current_status: str = "ACTIVE"
    ) -> str:
        """
        Computes the target listing status based on stock and configured OOS action.
        - If marketplace_qty > 0: reactivates to 'ACTIVE'
        - If marketplace_qty == 0:
            SET_QUANTITY_ZERO -> status remains 'ACTIVE' (with listed_qty = 0)
            DISABLE_LISTING   -> status becomes 'PAUSED'
            MARK_UNAVAILABLE  -> status becomes 'UNAVAILABLE'
        """
        if marketplace_qty > 0:
            return "ACTIVE"

        if oos_action == "DISABLE_LISTING":
            return "PAUSED"
        elif oos_action == "MARK_UNAVAILABLE":
            return "UNAVAILABLE"
        else: # SET_QUANTITY_ZERO
            return "ACTIVE"
