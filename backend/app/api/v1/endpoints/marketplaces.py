import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_credential, decrypt_credential
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.schemas.marketplace import MarketplaceResponse, MarketplaceUpdate
from app.adapters.registry import get_marketplace_adapter

router = APIRouter()

@router.get("", response_model=List[MarketplaceResponse])
def list_marketplaces(db: Session = Depends(get_db)):
    marketplaces = db.query(Marketplace).order_by(Marketplace.id).all()
    results = []
    for m in marketplaces:
        active_count = db.query(Listing).filter(
            Listing.marketplace_id == m.id,
            Listing.status == "ACTIVE"
        ).count()
        total_count = db.query(Listing).filter(
            Listing.marketplace_id == m.id
        ).count()

        results.append(MarketplaceResponse(
            id=m.id,
            name=m.name,
            adapter_class=m.adapter_class,
            is_active=m.is_active,
            has_credentials=bool(m.credentials_encrypted),
            active_listings_count=active_count,
            total_listings_count=total_count,
            created_at=m.created_at,
            updated_at=m.updated_at
        ))
    return results

@router.get("/{marketplace_id}", response_model=MarketplaceResponse)
def get_marketplace(marketplace_id: int, db: Session = Depends(get_db)):
    m = db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Marketplace channel not found")

    active_count = db.query(Listing).filter(
        Listing.marketplace_id == m.id,
        Listing.status == "ACTIVE"
    ).count()
    total_count = db.query(Listing).filter(
        Listing.marketplace_id == m.id
    ).count()

    return MarketplaceResponse(
        id=m.id,
        name=m.name,
        adapter_class=m.adapter_class,
        is_active=m.is_active,
        has_credentials=bool(m.credentials_encrypted),
        active_listings_count=active_count,
        total_listings_count=total_count,
        created_at=m.created_at,
        updated_at=m.updated_at
    )

@router.put("/{marketplace_id}", response_model=MarketplaceResponse)
def update_marketplace(marketplace_id: int, payload: MarketplaceUpdate, db: Session = Depends(get_db)):
    m = db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Marketplace channel not found")

    if payload.name is not None:
        m.name = payload.name
    if payload.adapter_class is not None:
        m.adapter_class = payload.adapter_class
    if payload.is_active is not None:
        m.is_active = payload.is_active
    if payload.credentials is not None:
        m.credentials_encrypted = encrypt_credential(json.dumps(payload.credentials))

    db.commit()
    db.refresh(m)

    active_count = db.query(Listing).filter(
        Listing.marketplace_id == m.id,
        Listing.status == "ACTIVE"
    ).count()
    total_count = db.query(Listing).filter(
        Listing.marketplace_id == m.id
    ).count()

    return MarketplaceResponse(
        id=m.id,
        name=m.name,
        adapter_class=m.adapter_class,
        is_active=m.is_active,
        has_credentials=bool(m.credentials_encrypted),
        active_listings_count=active_count,
        total_listings_count=total_count,
        created_at=m.created_at,
        updated_at=m.updated_at
    )

@router.post("/{marketplace_id}/test")
def test_marketplace_connection(marketplace_id: int, db: Session = Depends(get_db)):
    m = db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Marketplace channel not found")

    credentials = {}
    if m.credentials_encrypted:
        try:
            decrypted = decrypt_credential(m.credentials_encrypted)
            if decrypted:
                credentials = json.loads(decrypted)
        except Exception:
            pass

    adapter = get_marketplace_adapter(m.adapter_class, credentials=credentials)
    try:
        success = adapter.test_connection()
        return {
            "success": success,
            "marketplace": m.name,
            "adapter": m.adapter_class,
            "message": f"Connection to {m.name} via {m.adapter_class} verified successfully."
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
