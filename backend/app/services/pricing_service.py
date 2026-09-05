from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.pricing_rule import PricingRule

class PricingService:
    def __init__(self, db: Session):
        self.db = db

    def resolve_rule(
        self,
        product_id: Optional[int] = None,
        marketplace_id: Optional[int] = None
    ) -> Optional[PricingRule]:
        """
        Hierarchical Pricing Rule Resolution (Spec Section 7 & 16):
        1. Exact match (product_id AND marketplace_id)
        2. Product-specific (product_id only, marketplace_id is null)
        3. Marketplace-specific (marketplace_id only, product_id is null)
        4. Global rule (both product_id and marketplace_id are null)
        """
        # 1. Product + Marketplace exact match
        if product_id and marketplace_id:
            rule = self.db.query(PricingRule).filter(
                PricingRule.product_id == product_id,
                PricingRule.marketplace_id == marketplace_id
            ).first()
            if rule:
                return rule

        # 2. Product-specific rule
        if product_id:
            rule = self.db.query(PricingRule).filter(
                PricingRule.product_id == product_id,
                PricingRule.marketplace_id.is_(None)
            ).first()
            if rule:
                return rule

        # 3. Marketplace-specific rule
        if marketplace_id:
            rule = self.db.query(PricingRule).filter(
                PricingRule.product_id.is_(None),
                PricingRule.marketplace_id == marketplace_id
            ).first()
            if rule:
                return rule

        # 4. Global rule
        rule = self.db.query(PricingRule).filter(
            PricingRule.product_id.is_(None),
            PricingRule.marketplace_id.is_(None)
        ).first()
        return rule

    def calculate_price(
        self,
        cost: Decimal,
        product_id: Optional[int] = None,
        marketplace_id: Optional[int] = None,
        rule_override: Optional[PricingRule] = None
    ) -> Decimal:
        """
        Computes selling price according to resolved or provided PricingRule.
        Formulas (Spec Section 16):
        - FIXED_PROFIT: cost + fixed_profit
        - PERCENTAGE_MARKUP: cost + (cost * percentage)
        - FEE_MARGIN: accounts for marketplace fee % and desired profit margin %
        Default fallback if no rule exists: 15% markup.
        """
        cost_dec = Decimal(str(cost))
        if cost_dec <= 0:
            return Decimal("0.00")

        rule = rule_override or self.resolve_rule(product_id, marketplace_id)

        if not rule:
            # Default fallback 15% markup
            price = cost_dec * Decimal("1.15")
            return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        rule_type = rule.rule_type.upper()

        if rule_type == "FIXED_PROFIT":
            profit = Decimal(str(rule.fixed_amount or 0))
            price = cost_dec + profit

        elif rule_type == "PERCENTAGE_MARKUP":
            markup_pct = Decimal(str(rule.percentage or 0)) / Decimal("100")
            price = cost_dec + (cost_dec * markup_pct)

        elif rule_type == "FEE_MARGIN":
            fee_pct = Decimal(str(rule.marketplace_fee or 0)) / Decimal("100")
            margin_pct = Decimal(str(rule.desired_margin or 0)) / Decimal("100")

            # Formula: selling_price * (1 - fee_pct) = cost * (1 + margin_pct)
            # selling_price = (cost * (1 + margin_pct)) / (1 - fee_pct)
            denominator = Decimal("1.00") - fee_pct
            if denominator <= Decimal("0.05"):
                # Safety clamp against divide-by-zero or excessive fees >= 100%
                denominator = Decimal("0.85")

            numerator = cost_dec * (Decimal("1.00") + margin_pct)
            price = numerator / denominator

        else:
            price = cost_dec * Decimal("1.15")

        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
