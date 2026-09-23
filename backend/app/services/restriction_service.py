from typing import Optional
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_restriction import ProductRestriction


class RestrictionService:
    """
    Checks whether a product is blocked (or pending approval) from being
    published to a given marketplace (Phase 4: product restriction
    management). A specific product_id restriction always takes precedence
    over a category/brand-wide one.
    """

    def __init__(self, db: Session):
        self.db = db

    def find_blocking_restriction(self, product: Product, marketplace_id: int) -> Optional[ProductRestriction]:
        marketplace_scope = or_(
            ProductRestriction.marketplace_id.is_(None),
            ProductRestriction.marketplace_id == marketplace_id,
        )

        # 1. Product-specific restriction takes precedence
        specific = self.db.query(ProductRestriction).filter(
            ProductRestriction.product_id == product.id,
            marketplace_scope,
        ).first()
        if specific and self._is_blocking(specific):
            return specific

        # 2. Category/brand-wide restriction
        category_or_brand_conditions = []
        if product.category:
            category_or_brand_conditions.append(ProductRestriction.category == product.category)
        if product.brand:
            category_or_brand_conditions.append(ProductRestriction.brand == product.brand)

        if category_or_brand_conditions:
            general = self.db.query(ProductRestriction).filter(
                ProductRestriction.product_id.is_(None),
                or_(*category_or_brand_conditions),
                marketplace_scope,
            ).first()
            if general and self._is_blocking(general):
                return general

        return None

    @staticmethod
    def _is_blocking(restriction: ProductRestriction) -> bool:
        if restriction.restriction_type == "BLOCKED":
            return True
        if restriction.restriction_type == "REQUIRES_APPROVAL" and not restriction.approved_at:
            return True
        return False
