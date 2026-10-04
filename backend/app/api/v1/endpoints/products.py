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
        marketplace_id=marketplace_id
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
    from app.adapters.suppliers.image_search_provider import get_image_search_provider

    TRUSTED_SUPPLIER_DOMAINS = (
        "officedepot.com", "media.officedepot.com",
        "static.storeautomator.com", "storeautomator.com",
        "cdwg.com", "cdn.cdwg.com",
        "ingram.com", "assets.ingrammicro.com",
    )
    stored = product.images or []
    supplier_images = [
        img for img in stored
        if img and any(d in img.lower() for d in TRUSTED_SUPPLIER_DOMAINS) and _validate_url(img)
    ]

    provider = get_image_search_provider()
    web_candidates = []
    query_used = ""

    if q and q.strip():
        query_used = q.strip()
        if hasattr(provider, "search_web_images"):
            web_candidates = provider.search_web_images(query_used, max_results=12)
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
            web_candidates = provider.search_web_images(fallback_query, max_results=10)

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

    return {
        "product_id": product_id,
        "query_used": query_used,
        "suggestions": ordered_urls[:15],
        "candidates": [
            {
                "image_url": c.image_url,
                "title": c.title,
                "source": c.source,
                "snippet": c.snippet
            }
            for c in web_candidates[:15]
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

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return None