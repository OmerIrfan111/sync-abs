import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_credential, decrypt_credential
from app.api.deps import require_role
from app.models.marketplace import Marketplace
from app.models.listing import Listing
from app.schemas.marketplace import MarketplaceResponse, MarketplaceUpdate, MarketplaceCreate
from app.adapters.registry import get_marketplace_adapter

router = APIRouter()

# Real, live adapters only — a new marketplace ACCOUNT (e.g. a second eBay
# store) must be one of these. Deliberately excludes Mock* adapters: those
# exist for tests/dev fixtures, not for a merchant to knowingly create a real
# sales channel against.
CREATABLE_MARKETPLACE_ADAPTERS = {"LiveEBayAdapter", "LiveAmazonAdapter", "LiveShopifyAdapter"}

@router.post("", response_model=MarketplaceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
def create_marketplace(payload: MarketplaceCreate, db: Session = Depends(get_db)):
    """
    Registers a new marketplace ACCOUNT (e.g. a second eBay store). This is
    what makes multi-account support real: without this endpoint, only the
    original pre-seeded eBay/Amazon/Shopify rows could ever exist, and the
    OAuth-exchange fix for multiple accounts had nothing to actually target.
    """
    if payload.adapter_class not in CREATABLE_MARKETPLACE_ADAPTERS:
        raise HTTPException(
            status_code=400,
            detail=f"adapter_class must be one of {sorted(CREATABLE_MARKETPLACE_ADAPTERS)}"
        )
    existing = db.query(Marketplace).filter(Marketplace.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"A marketplace named '{payload.name}' already exists")

    marketplace = Marketplace(
        name=payload.name,
        adapter_class=payload.adapter_class,
        is_active=True,
        credentials_encrypted=None,
    )
    db.add(marketplace)
    db.commit()
    db.refresh(marketplace)

    return MarketplaceResponse(
        id=marketplace.id,
        name=marketplace.name,
        adapter_class=marketplace.adapter_class,
        is_active=marketplace.is_active,
        has_credentials=False,
        active_listings_count=0,
        total_listings_count=0,
        credentials_expires_at=None,
        created_at=marketplace.created_at,
        updated_at=marketplace.updated_at,
    )

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
            credentials_expires_at=m.credentials_expires_at,
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
        credentials_expires_at=m.credentials_expires_at,
        created_at=m.created_at,
        updated_at=m.updated_at
    )

@router.put("/{marketplace_id}", response_model=MarketplaceResponse)
def update_marketplace(marketplace_id: int, payload: MarketplaceUpdate, db: Session = Depends(get_db), _: object = Depends(require_role("admin"))):
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
        credentials_expires_at=m.credentials_expires_at,
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
    saving both to the target eBay marketplace connection's credentials.

    Accepts an optional marketplace_id so multiple eBay store accounts can
    each be authorized independently (Phase 3: multiple seller accounts).
    Falls back to the first LiveEBayAdapter row for backward compatibility
    with single-account setups that don't pass marketplace_id yet.
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")

    marketplace_id = payload.get("marketplace_id")
    if marketplace_id:
        ebay = db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
    else:
        ebay = db.query(Marketplace).filter(Marketplace.adapter_class == "LiveEBayAdapter").order_by(Marketplace.id).first()
    if not ebay:
        raise HTTPException(status_code=404, detail="eBay marketplace connection not found")

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

            # eBay returns the refresh token's actual lifetime in this response
            # (~18 months). Record the real expiry instead of assuming a fixed
            # duration, so the dashboard can warn before it silently breaks.
            refresh_token_expires_in = res.get("refresh_token_expires_in")
            if refresh_token_expires_in:
                from datetime import datetime, timezone, timedelta
                ebay.credentials_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(refresh_token_expires_in))

            db.commit()

            return {
                "success": True,
                "message": "eBay OAuth tokens exchanged and saved successfully! Refresh token active for 18 months.",
                "has_refresh_token": bool(refresh_token),
                "credentials_expires_at": ebay.credentials_expires_at.isoformat() if ebay.credentials_expires_at else None
            }
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=400, detail=f"eBay OAuth exchange failed ({err.code}): {err_body}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ──────────────────────────────────────────────
# Marketplace Fee Schedule (Phase 4)
# ──────────────────────────────────────────────

@router.get("/{marketplace_id}/fee-schedule")
def get_fee_schedule(marketplace_id: int, db: Session = Depends(get_db)):
    from app.models.marketplace_fee_schedule import MarketplaceFeeSchedule

    marketplace = db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
    if not marketplace:
        raise HTTPException(status_code=404, detail="Marketplace not found")

    schedule = db.query(MarketplaceFeeSchedule).filter(
        MarketplaceFeeSchedule.marketplace_id == marketplace_id
    ).first()
    if not schedule:
        return {"marketplace_id": marketplace_id, "marketplace_name": marketplace.name, "fee_percentage": None, "notes": None}

    return {
        "marketplace_id": marketplace_id,
        "marketplace_name": marketplace.name,
        "fee_percentage": schedule.fee_percentage,
        "notes": schedule.notes,
    }


@router.put("/{marketplace_id}/fee-schedule")
def update_fee_schedule(marketplace_id: int, payload: dict, db: Session = Depends(get_db)):
    """
    Sets this marketplace's default commission % used to pre-fill new
    FEE_MARGIN pricing rules. This is an editable default, not a precise
    per-category rate card — staff should set it to whatever actually
    applies to their selling plan/category.
    """
    from app.models.marketplace_fee_schedule import MarketplaceFeeSchedule
    from decimal import Decimal, InvalidOperation

    marketplace = db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()
    if not marketplace:
        raise HTTPException(status_code=404, detail="Marketplace not found")

    fee_percentage = payload.get("fee_percentage")
    if fee_percentage is None:
        raise HTTPException(status_code=400, detail="fee_percentage is required")
    try:
        fee_dec = Decimal(str(fee_percentage))
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="fee_percentage must be a number")
    if fee_dec < 0 or fee_dec > 100:
        raise HTTPException(status_code=400, detail="fee_percentage must be between 0 and 100")

    schedule = db.query(MarketplaceFeeSchedule).filter(
        MarketplaceFeeSchedule.marketplace_id == marketplace_id
    ).first()
    if not schedule:
        schedule = MarketplaceFeeSchedule(marketplace_id=marketplace_id, fee_percentage=fee_dec, notes=payload.get("notes"))
        db.add(schedule)
    else:
        schedule.fee_percentage = fee_dec
        if payload.get("notes") is not None:
            schedule.notes = payload.get("notes")

    db.commit()
    return {"success": True, "marketplace_id": marketplace_id, "fee_percentage": str(schedule.fee_percentage)}

