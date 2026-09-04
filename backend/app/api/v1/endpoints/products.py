from typing import Optional
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
        in_stock=in_stock
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedProductsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

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
