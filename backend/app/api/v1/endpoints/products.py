from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.product import Product
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, PaginatedProductsResponse
)
from app.services.catalog_service import CatalogService

router = APIRouter()

@router.get("", response_model=PaginatedProductsResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search by SKU, UPC, EAN, MPN, Brand, or Title"),
    supplier_id: Optional[int] = Query(None),
    brand: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    in_stock: Optional[bool] = Query(None),
    min_price: Optional[Decimal] = Query(None, description="Minimum lowest-supplier-cost"),
    max_price: Optional[Decimal] = Query(None, description="Maximum lowest-supplier-cost"),
    marketplace_id: Optional[int] = Query(None, description="Only products currently listed on this marketplace"),
    walmart_match_status: Optional[str] = Query(None, description="matchable | not_matchable | unchecked"),
    db: Session = Depends(get_db)
):
    service = CatalogService(db)
    skip = (page - 1) * page_size
    items, total = service.get_products(
        skip=skip,
        limit=page_size,
        search=q,
        supplier_id=supplier_id,
        brand=brand,
        category=category,
        in_stock=in_stock,
        min_price=min_price,
        max_price=max_price,
        marketplace_id=marketplace_id,
        walmart_match_status=walmart_match_status,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedProductsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/filters/options")
def get_filter_options(db: Session = Depends(get_db)):
    """Return distinct non-empty brands and categories for catalog filtering."""
    brands = [b[0] for b in db.query(Product.brand).filter(Product.brand.isnot(None), Product.brand != "").distinct().order_by(Product.brand).all()]
    categories = [c[0] for c in db.query(Product.category).filter(Product.category.isnot(None), Product.category != "").distinct().order_by(Product.category).all()]
    return {
        "brands": brands,
        "categories": categories
    }

class SetProductImagePayload(BaseModel):
    image_url: str = Field(..., min_length=5, description="Direct URL of the product photo")

@router.get("/{product_id}/image-suggestions")
def get_product_image_suggestions(
    product_id: int,
    q: Optional[str] = Query(None, description="Optional custom query for web image search"),
    db: Session = Depends(get_db)
):
    """
    Returns high-resolution product image candidates for the photo-picker UI.
    Searches web images via Bing by UPC / Brand / MPN / Title so the real product photo
    is retrieved for B2B & consumer products.
    Also falls back to supplier CDN images and category-curated options.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    from app.adapters.suppliers.image_resolver import resolve_product_imagery, _validate_url
    from app.adapters.suppliers.image_search_provider import get_image_search_provider, TRUSTED_SUPPLIER_DOMAINS

    stored = product.images or []
    supplier_images = [
        img for img in stored
        if img and any(d in img.lower() for d in TRUSTED_SUPPLIER_DOMAINS) and _validate_url(img)
    ]

    provider = get_image_search_provider()
    web_candidates = []
    query_used = ""

    # A configured Google provider now raises on a transient network failure
    # (fixed to stop defeating ImageMatchingService's retry wrapper
    # elsewhere) — but this is an interactive picker request, not a retried
    # batch job, so here a failed web search should degrade to the category
    # fallbacks below rather than 500 the whole endpoint.
    try:
        if q and q.strip():
            query_used = q.strip()
            if hasattr(provider, "search_web_images"):
                web_candidates = provider.search_web_images(query_used, max_results=35)
            else:
                web_candidates = provider.search_by_upc(query_used)
        else:
            # Construct intelligent search query for this product
            norm_upc = product.upc or product.ean
            if hasattr(provider, "search_by_upc"):
                web_candidates = provider.search_by_upc(
                    upc=norm_upc or "",
                    title=product.title,
                    brand=product.brand,
                    mpn=product.mpn
                )
                query_used = f"{norm_upc or ''} {product.brand or ''} {product.mpn or ''}".strip()
            elif hasattr(provider, "search_web_images"):
                fallback_query = f"{product.brand or ''} {product.mpn or product.title[:40]}".strip()
                query_used = fallback_query
                web_candidates = provider.search_web_images(fallback_query, max_results=35)
    except Exception:
        web_candidates = []

    # The manual query box (q) does a single raw Bing scrape of exactly what
    # was typed — unlike the automatic UPC pipeline, it has no multi-tier
    # merge to fall back on, so a bare UPC (collision-prone) or a generic
    # free-text query returns whatever Bing ranks first, unfiltered. Applying
    # the same trusted-supplier-CDN-first sort here (stable, doesn't reorder
    # within either group) at least surfaces a real supplier photo above
    # generic/unrelated web results when one exists, same as the automatic
    # pipeline already does.
    web_candidates = sorted(
        web_candidates,
        key=lambda c: 0 if any(d in c.image_url.lower() for d in TRUSTED_SUPPLIER_DOMAINS) else 1
    )

    category_fallbacks = resolve_product_imagery(
        brand=product.brand,
        category=product.category,
        subcategory=None,
        title=product.title,
        sku=product.sku,
        upc=None,
        supplier_image_url=supplier_images[0] if supplier_images else None,
    )

    ordered_urls = []
    seen = set()

    def add_url(u: Optional[str]):
        if u and isinstance(u, str) and u.startswith(("http://", "https://")) and u not in seen:
            seen.add(u)
            ordered_urls.append(u)

    # 1. Real supplier CDN images first
    for img in supplier_images:
        add_url(img)

    # 2. Web search candidate images
    for c in web_candidates:
        add_url(c.image_url)

    # 3. If any existing stored images were not generic fallbacks, include them
    for img in stored:
        if img and not any(f in img for f in ("unsplash.com", "placeholder", "noimage")):
            add_url(img)

    # 4. Fallback images
    for img in category_fallbacks:
        add_url(img)

    # Raised from 15 alongside the max_results caps above (2026-10-10) — no
    # reason to truncate what was already fetched down to a third of it.
    return {
        "product_id": product_id,
        "query_used": query_used,
        "suggestions": ordered_urls[:40],
        "candidates": [
            {
                "image_url": c.image_url,
                "title": c.title,
                "source": c.source,
                "snippet": c.snippet
            }
            for c in web_candidates[:40]
        ]
    }


@router.post("/{product_id}/set-image", response_model=ProductResponse)
def set_product_image(
    product_id: int,
    payload: SetProductImagePayload,
    db: Session = Depends(get_db)
):
    """
    Sets the primary image of a product, updating the database permanently.
    This changes the image seen across the catalog, listings, and exports.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_url = payload.image_url.strip()
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid image URL; must start with http:// or https://")

    # Put this image at position 0
    existing = list(product.images or [])
    updated = [new_url] + [u for u in existing if u != new_url]
    product.images = updated

    # Mark as verified in specs_json
    from datetime import datetime, timezone
    specs = dict(product.specs_json or {})
    specs["image_status"] = "verified"
    specs["chosen_image_url"] = new_url
    specs["image_verified_at"] = datetime.now(timezone.utc).isoformat()
    product.specs_json = specs

    db.commit()
    db.refresh(product)

    service = CatalogService(db)
    return service.get_product_by_id(product.id)


@router.post("/{product_id}/lookup-weight")
def lookup_product_weight(product_id: int, db: Session = Depends(get_db)):
    """
    Best-effort shipping weight lookup by UPC/EAN for products whose supplier
    doesn't report one (Ingram Micro, TD SYNNEX). Staff-triggered only — see
    WeightLookupService docstring for why this must not be run in bulk.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    from app.services.weight_lookup_service import WeightLookupService
    result = WeightLookupService().lookup_weight_by_upc(
        upc=product.upc or product.ean or "",
        title=product.title,
        brand=product.brand,
    )
    if result.status != "found":
        raise HTTPException(status_code=404, detail=result.reason or "No verified weight found.")

    return {
        "weight_lbs": result.weight_lbs,
        "confidence": result.confidence,
        "source_title": result.source_title,
    }


@router.get("/{product_id}/walmart-match-check")
def check_walmart_catalog_match(product_id: int, db: Session = Depends(get_db)):
    """
    Real pre-check for whether this product's GTIN exists anywhere in
    Walmart's catalog, before attempting a real MP_ITEM_MATCH feed
    submission. See LiveWalmartAdapter.search_walmart_catalog_by_gtin.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    upc = product.upc or product.ean
    if not upc:
        raise HTTPException(status_code=400, detail="This product has no UPC/EAN on file to check.")

    from app.models.marketplace import Marketplace
    from app.services.listing_service import ListingService

    wm = db.query(Marketplace).filter(Marketplace.name.ilike("%walmart%")).first()
    if not wm:
        raise HTTPException(status_code=400, detail="No Walmart marketplace configured.")

    adapter = ListingService(db).get_adapter_for_marketplace(wm)
    if not hasattr(adapter, "search_walmart_catalog_by_gtin"):
        raise HTTPException(status_code=400, detail="This marketplace adapter doesn't support a catalog pre-check.")

    try:
        items = adapter.search_walmart_catalog_by_gtin(upc)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Walmart to check: {exc}")

    from datetime import datetime, timezone
    specs = dict(product.specs_json or {})
    specs["walmart_match_status"] = "matchable" if items else "not_matchable"
    specs["walmart_match_checked_at"] = datetime.now(timezone.utc).isoformat()
    product.specs_json = specs
    db.commit()

    return {
        "matchable": len(items) > 0,
        "matches_found": len(items),
        "sample": items[0] if items else None,
    }


def _get_walmart_adapter(db: Session):
    from app.models.marketplace import Marketplace
    from app.services.listing_service import ListingService

    wm = db.query(Marketplace).filter(Marketplace.name.ilike("%walmart%")).first()
    if not wm:
        raise HTTPException(status_code=400, detail="No Walmart marketplace configured.")
    return ListingService(db).get_adapter_for_marketplace(wm)


@router.get("/walmart-item-spec")
def get_walmart_item_spec(
    product_type: str = Query(..., description="Real Walmart category name, e.g. 'Network Switches'"),
    db: Session = Depends(get_db),
):
    """
    Real per-category required-field schema for full MP_ITEM setup (used
    when a product has no existing Walmart catalog match — see
    LiveWalmartAdapter.get_item_spec). Throttled by Walmart to 3
    requests/minute per seller; the frontend should cache this per category,
    not call it on every keystroke.
    """
    adapter = _get_walmart_adapter(db)
    if not hasattr(adapter, "get_item_spec"):
        raise HTTPException(status_code=400, detail="This marketplace adapter doesn't support item spec lookup.")

    try:
        res = adapter.get_item_spec([product_type])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Walmart to fetch spec: {exc}")

    try:
        visible_schema = (
            res["schema"]["properties"]["MPItem"]["items"]["properties"]["Visible"]["properties"][product_type]
        )
    except (KeyError, TypeError):
        raise HTTPException(status_code=404, detail=f"'{product_type}' is not a real Walmart product type.")

    return {
        "product_type": product_type,
        "required": visible_schema.get("required", []),
        "properties": visible_schema.get("properties", {}),
    }


class WalmartNewItemPayload(BaseModel):
    product_type: str
    price: Decimal = Field(gt=0, description="Real selling price; must be positive")
    weight_lbs: float = Field(gt=0, description="Real shipping weight; must be positive")
    condition: str = "New"
    visible_attributes: dict


@router.post("/{product_id}/walmart-create-new-item")
def create_walmart_new_item(product_id: int, payload: WalmartNewItemPayload, db: Session = Depends(get_db)):
    """
    Submits a real MP_ITEM feed to create a brand-new Walmart catalog item
    for a product with no existing catalog match (item-match isn't
    possible — see /walmart-match-check). visible_attributes must satisfy
    the real required fields from /walmart-item-spec; nothing here is
    fabricated or defaulted on the caller's behalf.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not (product.upc or product.ean):
        raise HTTPException(status_code=400, detail="Product has no UPC/EAN on file.")

    adapter = _get_walmart_adapter(db)
    if not hasattr(adapter, "submit_new_item_feed"):
        raise HTTPException(status_code=400, detail="This marketplace adapter doesn't support full item setup.")

    try:
        res = adapter.submit_new_item_feed(
            sku=product.sku,
            upc=product.upc or product.ean,
            price=payload.price,
            weight_lbs=payload.weight_lbs,
            product_type=payload.product_type,
            visible_attributes=payload.visible_attributes,
            condition=payload.condition,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Walmart submission failed: {exc}")

    return {"feed_id": res.get("feedId")}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    service = CatalogService(db)
    product = service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{payload.sku}' already exists"
        )

    product = Product(
        sku=payload.sku,
        upc=payload.upc,
        ean=payload.ean,
        mpn=payload.mpn,
        title=payload.title,
        brand=payload.brand,
        description=payload.description,
        category=payload.category,
        images=payload.images,
        specs_json=payload.specs_json,
        is_enabled=payload.is_enabled
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    service = CatalogService(db)
    return service.get_product_by_id(product.id)

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)

    service = CatalogService(db)
    return service.get_product_by_id(product.id)

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Deletes a product and, via DB cascade, every Listing row attached to it.
    Real incident class this must not repeat: deleting a product that still
    has an ACTIVE/PENDING marketplace listing used to just cascade-delete
    the Listing locally with no attempt to retire/withdraw it on the real
    marketplace first — leaving the item live and purchasable with no local
    record left to manage it (the same bug class fixed for DELETE
    /listings/{id} after the real 00TF99 incident, 2026-10-07). Every
    listing is cleaned up on its marketplace (best-effort, never blocks the
    delete) before the product itself is removed.
    """
    from app.services.listing_service import ListingService

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    service = ListingService(db)
    cleanup_results = []
    for listing in list(product.listings):
        note = service.retire_or_withdraw_listing(listing)
        cleanup_results.append({
            "marketplace": listing.marketplace.name if listing.marketplace else None,
            "cleanup": note,
        })

    db.delete(product)
    db.commit()
    return {"success": True, "message": "Product deleted", "marketplace_cleanup": cleanup_results}