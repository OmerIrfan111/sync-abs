from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.pricing_rule import PricingRule
from app.models.inventory_rule import InventoryRule
from app.models.supplier_priority import SupplierPriority
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.supplier import Supplier
from app.schemas.rules import (
    PricingRuleCreate,
    PricingRuleUpdate,
    PricingRuleResponse,
    InventoryRuleCreate,
    InventoryRuleUpdate,
    InventoryRuleResponse,
    SupplierPriorityCreate,
    SupplierPriorityUpdate,
    SupplierPriorityResponse,
)
from app.services.pricing_service import PricingService
from app.services.inventory_service import InventoryService
from app.services.supplier_selection_service import SupplierSelectionService

router = APIRouter()

# ==========================================
# PRICING RULES
# ==========================================

@router.get("/pricing", response_model=List[PricingRuleResponse])
def get_pricing_rules(
    product_id: Optional[int] = Query(None),
    marketplace_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(PricingRule)
    if product_id is not None:
        query = query.filter(PricingRule.product_id == product_id)
    if marketplace_id is not None:
        query = query.filter(PricingRule.marketplace_id == marketplace_id)

    rules = query.order_by(desc(PricingRule.created_at)).all()
    results = []
    for r in rules:
        results.append(PricingRuleResponse(
            id=r.id,
            product_id=r.product_id,
            product_sku=r.product.sku if r.product else None,
            product_title=r.product.title if r.product else None,
            marketplace_id=r.marketplace_id,
            marketplace_name=r.marketplace.name if r.marketplace else None,
            rule_type=r.rule_type,
            fixed_amount=r.fixed_amount,
            percentage=r.percentage,
            marketplace_fee=r.marketplace_fee,
            desired_margin=r.desired_margin,
            notes=r.notes,
            created_at=r.created_at,
            updated_at=r.updated_at
        ))
    return results

@router.post("/pricing", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED)
def create_pricing_rule(
    payload: PricingRuleCreate,
    db: Session = Depends(get_db)
):
    if payload.product_id:
        prod = db.query(Product).filter(Product.id == payload.product_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail="Product not found")
    if payload.marketplace_id:
        mp = db.query(Marketplace).filter(Marketplace.id == payload.marketplace_id).first()
        if not mp:
            raise HTTPException(status_code=404, detail="Marketplace not found")

    rule = PricingRule(
        product_id=payload.product_id,
        marketplace_id=payload.marketplace_id,
        rule_type=payload.rule_type.upper(),
        fixed_amount=payload.fixed_amount,
        percentage=payload.percentage,
        marketplace_fee=payload.marketplace_fee,
        desired_margin=payload.desired_margin,
        notes=payload.notes
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return PricingRuleResponse(
        id=rule.id,
        product_id=rule.product_id,
        product_sku=rule.product.sku if rule.product else None,
        product_title=rule.product.title if rule.product else None,
        marketplace_id=rule.marketplace_id,
        marketplace_name=rule.marketplace.name if rule.marketplace else None,
        rule_type=rule.rule_type,
        fixed_amount=rule.fixed_amount,
        percentage=rule.percentage,
        marketplace_fee=rule.marketplace_fee,
        desired_margin=rule.desired_margin,
        notes=rule.notes,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )

@router.put("/pricing/{rule_id}", response_model=PricingRuleResponse)
def update_pricing_rule(
    rule_id: int,
    payload: PricingRuleUpdate,
    db: Session = Depends(get_db)
):
    rule = db.query(PricingRule).filter(PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    if payload.rule_type is not None:
        rule.rule_type = payload.rule_type.upper()
    if payload.fixed_amount is not None:
        rule.fixed_amount = payload.fixed_amount
    if payload.percentage is not None:
        rule.percentage = payload.percentage
    if payload.marketplace_fee is not None:
        rule.marketplace_fee = payload.marketplace_fee
    if payload.desired_margin is not None:
        rule.desired_margin = payload.desired_margin
    if payload.notes is not None:
        rule.notes = payload.notes

    db.commit()
    db.refresh(rule)

    return PricingRuleResponse(
        id=rule.id,
        product_id=rule.product_id,
        product_sku=rule.product.sku if rule.product else None,
        product_title=rule.product.title if rule.product else None,
        marketplace_id=rule.marketplace_id,
        marketplace_name=rule.marketplace.name if rule.marketplace else None,
        rule_type=rule.rule_type,
        fixed_amount=rule.fixed_amount,
        percentage=rule.percentage,
        marketplace_fee=rule.marketplace_fee,
        desired_margin=rule.desired_margin,
        notes=rule.notes,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )

@router.delete("/pricing/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pricing_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(PricingRule).filter(PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    db.delete(rule)
    db.commit()
    return None


# ==========================================
# INVENTORY RULES
# ==========================================

@router.get("/inventory", response_model=List[InventoryRuleResponse])
def get_inventory_rules(
    product_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(InventoryRule)
    if product_id is not None:
        query = query.filter(InventoryRule.product_id == product_id)

    rules = query.order_by(desc(InventoryRule.created_at)).all()
    results = []
    for r in rules:
        results.append(InventoryRuleResponse(
            id=r.id,
            product_id=r.product_id,
            product_sku=r.product.sku if r.product else None,
            product_title=r.product.title if r.product else None,
            safety_buffer=r.safety_buffer,
            out_of_stock_action=r.out_of_stock_action,
            created_at=r.created_at,
            updated_at=r.updated_at
        ))
    return results

@router.post("/inventory", response_model=InventoryRuleResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_rule(
    payload: InventoryRuleCreate,
    db: Session = Depends(get_db)
):
    if payload.product_id:
        prod = db.query(Product).filter(Product.id == payload.product_id).first()
        if not prod:
            raise HTTPException(status_code=404, detail="Product not found")

    rule = InventoryRule(
        product_id=payload.product_id,
        safety_buffer=payload.safety_buffer,
        out_of_stock_action=payload.out_of_stock_action.upper()
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return InventoryRuleResponse(
        id=rule.id,
        product_id=rule.product_id,
        product_sku=rule.product.sku if rule.product else None,
        product_title=rule.product.title if rule.product else None,
        safety_buffer=rule.safety_buffer,
        out_of_stock_action=rule.out_of_stock_action,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )

@router.put("/inventory/{rule_id}", response_model=InventoryRuleResponse)
def update_inventory_rule(
    rule_id: int,
    payload: InventoryRuleUpdate,
    db: Session = Depends(get_db)
):
    rule = db.query(InventoryRule).filter(InventoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Inventory rule not found")

    if payload.safety_buffer is not None:
        rule.safety_buffer = payload.safety_buffer
    if payload.out_of_stock_action is not None:
        rule.out_of_stock_action = payload.out_of_stock_action.upper()

    db.commit()
    db.refresh(rule)

    return InventoryRuleResponse(
        id=rule.id,
        product_id=rule.product_id,
        product_sku=rule.product.sku if rule.product else None,
        product_title=rule.product.title if rule.product else None,
        safety_buffer=rule.safety_buffer,
        out_of_stock_action=rule.out_of_stock_action,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )

@router.delete("/inventory/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(InventoryRule).filter(InventoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Inventory rule not found")
    db.delete(rule)
    db.commit()
    return None


# ==========================================
# SUPPLIER PRIORITY RULES
# ==========================================

@router.get("/supplier-priority", response_model=List[SupplierPriorityResponse])
def get_supplier_priorities(
    product_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(SupplierPriority)
    if product_id is not None:
        query = query.filter(SupplierPriority.product_id == product_id)

    priorities = query.order_by(SupplierPriority.priority_rank).all()
    results = []
    for p in priorities:
        results.append(SupplierPriorityResponse(
            id=p.id,
            product_id=p.product_id,
            product_sku=p.product.sku if p.product else None,
            product_title=p.product.title if p.product else None,
            supplier_id=p.supplier_id,
            supplier_name=p.supplier.name if p.supplier else None,
            priority_rank=p.priority_rank,
            selection_rule=p.selection_rule,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))
    return results

@router.post("/supplier-priority", response_model=SupplierPriorityResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_priority(
    payload: SupplierPriorityCreate,
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter(Product.id == payload.product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    supp = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not supp:
        raise HTTPException(status_code=404, detail="Supplier not found")

    priority = SupplierPriority(
        product_id=payload.product_id,
        supplier_id=payload.supplier_id,
        priority_rank=payload.priority_rank,
        selection_rule=payload.selection_rule.upper()
    )
    db.add(priority)
    db.commit()
    db.refresh(priority)

    return SupplierPriorityResponse(
        id=priority.id,
        product_id=priority.product_id,
        product_sku=priority.product.sku if priority.product else None,
        product_title=priority.product.title if priority.product else None,
        supplier_id=priority.supplier_id,
        supplier_name=priority.supplier.name if priority.supplier else None,
        priority_rank=priority.priority_rank,
        selection_rule=priority.selection_rule,
        created_at=priority.created_at,
        updated_at=priority.updated_at
    )

@router.put("/supplier-priority/{priority_id}", response_model=SupplierPriorityResponse)
def update_supplier_priority(
    priority_id: int,
    payload: SupplierPriorityUpdate,
    db: Session = Depends(get_db)
):
    priority = db.query(SupplierPriority).filter(SupplierPriority.id == priority_id).first()
    if not priority:
        raise HTTPException(status_code=404, detail="Supplier priority rule not found")

    if payload.priority_rank is not None:
        priority.priority_rank = payload.priority_rank
    if payload.selection_rule is not None:
        priority.selection_rule = payload.selection_rule.upper()

    db.commit()
    db.refresh(priority)

    return SupplierPriorityResponse(
        id=priority.id,
        product_id=priority.product_id,
        product_sku=priority.product.sku if priority.product else None,
        product_title=priority.product.title if priority.product else None,
        supplier_id=priority.supplier_id,
        supplier_name=priority.supplier.name if priority.supplier else None,
        priority_rank=priority.priority_rank,
        selection_rule=priority.selection_rule,
        created_at=priority.created_at,
        updated_at=priority.updated_at
    )

@router.delete("/supplier-priority/{priority_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier_priority(priority_id: int, db: Session = Depends(get_db)):
    priority = db.query(SupplierPriority).filter(SupplierPriority.id == priority_id).first()
    if not priority:
        raise HTTPException(status_code=404, detail="Supplier priority rule not found")
    db.delete(priority)
    db.commit()
    return None


# ==========================================
# SIMULATION / PREVIEW ENDPOINT
# ==========================================

@router.get("/preview/{product_id}")
def preview_rules_calculation(
    product_id: int,
    marketplace_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Live dry-run calculation showing how supplier selection, safety buffer,
    and pricing rules resolve for a given product.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    pricing_service = PricingService(db)
    inventory_service = InventoryService(db)
    selection_service = SupplierSelectionService(db)

    # 1. Supplier selection
    best_sp = selection_service.select_best_supplier(product)
    supplier_info = None
    if best_sp:
        supplier_info = {
            "supplier_id": best_sp.supplier_id,
            "supplier_name": best_sp.supplier.name if best_sp.supplier else "Unknown",
            "cost": float(best_sp.cost),
            "stock": best_sp.qty_available,
            "lead_time_days": best_sp.shipping_info.get("lead_time_days") if best_sp.shipping_info else None
        }

    supplier_cost = best_sp.cost if best_sp else Decimal("0.00")
    supplier_stock = best_sp.qty_available if best_sp else 0

    # 2. Inventory calculation
    inv_rule = inventory_service.resolve_rule(product.id)
    marketplace_qty, oos_action = inventory_service.calculate_marketplace_quantity(
        supplier_quantity=supplier_stock,
        product_id=product.id
    )
    listing_status = inventory_service.determine_listing_status(marketplace_qty, oos_action)

    # 3. Pricing calculation
    resolved_pricing_rule = pricing_service.resolve_rule(product.id, marketplace_id)
    calculated_price = pricing_service.calculate_price(
        cost=supplier_cost,
        product_id=product.id,
        marketplace_id=marketplace_id
    )

    return {
        "product_id": product.id,
        "product_sku": product.sku,
        "product_title": product.title,
        "selected_supplier": supplier_info,
        "inventory": {
            "raw_supplier_stock": supplier_stock,
            "safety_buffer_applied": inv_rule.safety_buffer if inv_rule else 0,
            "calculated_marketplace_qty": marketplace_qty,
            "out_of_stock_action": oos_action,
            "target_listing_status": listing_status
        },
        "pricing": {
            "supplier_cost": float(supplier_cost),
            "rule_type": resolved_pricing_rule.rule_type if resolved_pricing_rule else "DEFAULT_15_PERCENT",
            "calculated_price": float(calculated_price),
            "fixed_amount": float(resolved_pricing_rule.fixed_amount) if resolved_pricing_rule else 0.0,
            "percentage": float(resolved_pricing_rule.percentage) if resolved_pricing_rule else 15.0,
            "marketplace_fee": float(resolved_pricing_rule.marketplace_fee) if resolved_pricing_rule else 0.0,
            "desired_margin": float(resolved_pricing_rule.desired_margin) if resolved_pricing_rule else 0.0,
        }
    }
