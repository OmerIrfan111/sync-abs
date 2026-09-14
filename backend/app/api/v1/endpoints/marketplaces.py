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

    if not m.credentials_encrypted and not m.adapter_class.startswith("Mock"):
        raise HTTPException(
            status_code=400,
            detail=f"No API credentials configured for {m.name}. Please click 'Connect Store', enter your credentials, and save before testing."
        )

    credentials = {}
    try:
        decrypted = decrypt_credential(m.credentials_encrypted)
        if decrypted:
            credentials = json.loads(decrypted)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decrypt credentials: {str(e)}")

    if not m.adapter_class.startswith("Mock") and (not credentials or not any(str(v).strip() for v in credentials.values() if v is not None)):
        raise HTTPException(
            status_code=400,
            detail=f"Credentials for {m.name} are empty. Please enter your valid keys or tokens."
        )

    adapter = get_marketplace_adapter(m.adapter_class, credentials=credentials)
    try:
        success = adapter.test_connection()
        return {
            "success": success,
            "marketplace": m.name,
            "adapter": m.adapter_class,
            "message": f"Real connection to {m.name} verified successfully!"
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{m.name} Connection Error: {str(exc)}")


@router.post("/ebay/exchange-code")
def exchange_ebay_code(payload: dict, db: Session = Depends(get_db)):
    """
    Exchanges an eBay OAuth authorization code for an 18-month refresh token and access token,
    saving both to the eBay marketplace credentials.
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")

    ebay = db.query(Marketplace).filter(Marketplace.id == 1).first()
    if not ebay:
        raise HTTPException(status_code=404, detail="eBay marketplace not found")

    creds = {}
    if ebay.credentials_encrypted:
        try:
            creds = json.loads(decrypt_credential(ebay.credentials_encrypted))
        except Exception:
            pass

    app_id = creds.get("app_id")
    cert_id = creds.get("cert_id")
    ru_name = creds.get("ru_name", "")

    if not app_id or not cert_id:
        raise HTTPException(status_code=400, detail="eBay App ID and Cert ID must be configured in store settings.")

    import urllib.request, urllib.parse, urllib.error, base64
    auth_str = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code.strip(),
        "redirect_uri": ru_name
    }).encode()

    req = urllib.request.Request(
        "https://api.ebay.com/identity/v1/oauth2/token",
        data=data,
        headers={
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode())
            access_token = res.get("access_token")
            refresh_token = res.get("refresh_token")
            if not access_token:
                raise RuntimeError("eBay did not return an access token")

            creds["user_token"] = access_token
            if refresh_token:
                creds["refresh_token"] = refresh_token
            creds["ru_name"] = ru_name

            ebay.credentials_encrypted = encrypt_credential(json.dumps(creds))
            db.commit()

            return {
                "success": True,
                "message": "eBay OAuth tokens exchanged and saved successfully! Refresh token active for 18 months.",
                "has_refresh_token": bool(refresh_token)
            }
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=400, detail=f"eBay OAuth exchange failed ({err.code}): {err_body}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

