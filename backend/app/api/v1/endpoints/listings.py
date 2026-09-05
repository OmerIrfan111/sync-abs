from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.listing import Listing
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.schemas.listing import (
    ListingPublishRequest,
    ListingUpdate,
    ListingResponse,
    PaginatedListingsResponse
)
from app.services.listing_service import ListingService

router = APIRouter()

@router.get("", response_model=PaginatedListingsResponse)
def list_listings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    marketplace_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Listing)
    if marketplace_id:
        query = query.filter(Listing.marketplace_id == marketplace_id)
    if product_id:
        query = query.filter(Listing.product_id == product_id)
    if status:
        query = query.filter(Listing.status == status)

    total = query.count()
    skip = (page - 1) * page_size
    listings = query.order_by(desc(Listing.updated_at)).offset(skip).limit(page_size).all()

    items = []
    for l in listings:
        items.append(ListingResponse(
            id=l.id,
            product_id=l.product_id,
            product_sku=l.product.sku if l.product else None,
            product_title=l.product.title if l.product else None,
            marketplace_id=l.marketplace_id,
            marketplace_name=l.marketplace.name if l.marketplace else None,
            external_listing_id=l.external_listing_id,
            status=l.status,
            selling_price=l.selling_price,
            listed_qty=l.listed_qty,
            last_updated_at=l.last_updated_at,
            created_at=l.created_at,
            updated_at=l.updated_at
        ))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedListingsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    return ListingResponse(
        id=l.id,
        product_id=l.product_id,
        product_sku=l.product.sku if l.product else None,
        product_title=l.product.title if l.product else None,
        marketplace_id=l.marketplace_id,
        marketplace_name=l.marketplace.name if l.marketplace else None,
        external_listing_id=l.external_listing_id,
        status=l.status,
        selling_price=l.selling_price,
        listed_qty=l.listed_qty,
        last_updated_at=l.last_updated_at,
        created_at=l.created_at,
        updated_at=l.updated_at
    )

@router.post("/publish", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
def publish_listing(payload: ListingPublishRequest, db: Session = Depends(get_db)):
    service = ListingService(db)
    try:
        listing = service.publish_product_to_marketplace(
            product_id=payload.product_id,
            marketplace_id=payload.marketplace_id,
            custom_price=payload.custom_price,
            custom_qty=payload.custom_qty
        )
        return ListingResponse(
            id=listing.id,
            product_id=listing.product_id,
            product_sku=listing.product.sku if listing.product else None,
            product_title=listing.product.title if listing.product else None,
            marketplace_id=listing.marketplace_id,
            marketplace_name=listing.marketplace.name if listing.marketplace else None,
            external_listing_id=listing.external_listing_id,
            status=listing.status,
            selling_price=listing.selling_price,
            listed_qty=listing.listed_qty,
            last_updated_at=listing.last_updated_at,
            created_at=listing.created_at,
            updated_at=listing.updated_at
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(listing_id: int, payload: ListingUpdate, db: Session = Depends(get_db)):
    service = ListingService(db)
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    try:
        updated = service.update_listing_on_marketplace(
            listing_id=listing_id,
            new_price=payload.selling_price,
            new_qty=payload.listed_qty,
            new_status=payload.status
        )
        return ListingResponse(
            id=updated.id,
            product_id=updated.product_id,
            product_sku=updated.product.sku if updated.product else None,
            product_title=updated.product.title if updated.product else None,
            marketplace_id=updated.marketplace_id,
            marketplace_name=updated.marketplace.name if updated.marketplace else None,
            external_listing_id=updated.external_listing_id,
            status=updated.status,
            selling_price=updated.selling_price,
            listed_qty=updated.listed_qty,
            last_updated_at=updated.last_updated_at,
            created_at=updated.created_at,
            updated_at=updated.updated_at
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/{listing_id}/reactivate", response_model=ListingResponse)
def reactivate_listing(listing_id: int, db: Session = Depends(get_db)):
    service = ListingService(db)
    try:
        reactivated = service.reactivate_listing_on_marketplace(listing_id)
        return ListingResponse(
            id=reactivated.id,
            product_id=reactivated.product_id,
            product_sku=reactivated.product.sku if reactivated.product else None,
            product_title=reactivated.product.title if reactivated.product else None,
            marketplace_id=reactivated.marketplace_id,
            marketplace_name=reactivated.marketplace.name if reactivated.marketplace else None,
            external_listing_id=reactivated.external_listing_id,
            status=reactivated.status,
            selling_price=reactivated.selling_price,
            listed_qty=reactivated.listed_qty,
            last_updated_at=reactivated.last_updated_at,
            created_at=reactivated.created_at,
            updated_at=reactivated.updated_at
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/{listing_id}/sync", response_model=ListingResponse)
def sync_listing(listing_id: int, db: Session = Depends(get_db)):
    service = ListingService(db)
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    try:
        if listing.status in ["WITHDRAWN", "PAUSED"]:
            updated = service.reactivate_listing_on_marketplace(listing.id)
        else:
            updated = service.update_listing_on_marketplace(
                listing_id=listing.id,
                new_price=listing.selling_price,
                new_qty=listing.listed_qty
            )
        return ListingResponse(
            id=updated.id,
            product_id=updated.product_id,
            product_sku=updated.product.sku if updated.product else None,
            product_title=updated.product.title if updated.product else None,
            marketplace_id=updated.marketplace_id,
            marketplace_name=updated.marketplace.name if updated.marketplace else None,
            external_listing_id=updated.external_listing_id,
            status=updated.status,
            selling_price=updated.selling_price,
            listed_qty=updated.listed_qty,
            last_updated_at=updated.last_updated_at,
            created_at=updated.created_at,
            updated_at=updated.updated_at
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/{listing_id}/withdraw", response_model=ListingResponse)
def withdraw_listing(listing_id: int, db: Session = Depends(get_db)):
    service = ListingService(db)
    try:
        withdrawn = service.withdraw_listing_from_marketplace(listing_id)
        return ListingResponse(
            id=withdrawn.id,
            product_id=withdrawn.product_id,
            product_sku=withdrawn.product.sku if withdrawn.product else None,
            product_title=withdrawn.product.title if withdrawn.product else None,
            marketplace_id=withdrawn.marketplace_id,
            marketplace_name=withdrawn.marketplace.name if withdrawn.marketplace else None,
            external_listing_id=withdrawn.external_listing_id,
            status=withdrawn.status,
            selling_price=withdrawn.selling_price,
            listed_qty=withdrawn.listed_qty,
            last_updated_at=withdrawn.last_updated_at,
            created_at=withdrawn.created_at,
            updated_at=withdrawn.updated_at
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    db.delete(listing)
    db.commit()
    return None
