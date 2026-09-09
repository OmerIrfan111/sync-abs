from typing import List
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse
from app.services.sync_service import SyncService
from app.core.security import encrypt_credential
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[SupplierResponse])
def get_suppliers(
    db: Session = Depends(get_db),
    # Optional auth dependency; can be public or auth protected
):
    suppliers = db.query(Supplier).all()
    results = []
    for s in suppliers:
        count = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == s.id).count()
        results.append(SupplierResponse(
            id=s.id,
            name=s.name,
            adapter_class=s.adapter_class,
            is_active=s.is_active,
            last_synced_at=s.last_synced_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
            product_count=count
        ))
    return results

@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
):
    existing = db.query(Supplier).filter(Supplier.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supplier with name '{payload.name}' already exists"
        )

    encrypted = None
    if payload.credentials:
        encrypted = encrypt_credential(json.dumps(payload.credentials))

    supplier = Supplier(
        name=payload.name,
        adapter_class=payload.adapter_class,
        credentials_encrypted=encrypted,
        is_active=payload.is_active
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    return SupplierResponse(
        id=supplier.id,
        name=supplier.name,
        adapter_class=supplier.adapter_class,
        is_active=supplier.is_active,
        last_synced_at=supplier.last_synced_at,
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
        product_count=0
    )

@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    count = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier.id).count()
    return SupplierResponse(
        id=supplier.id,
        name=supplier.name,
        adapter_class=supplier.adapter_class,
        is_active=supplier.is_active,
        last_synced_at=supplier.last_synced_at,
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
        product_count=count
    )

@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if payload.name is not None:
        supplier.name = payload.name
    if payload.adapter_class is not None:
        supplier.adapter_class = payload.adapter_class
    if payload.is_active is not None:
        supplier.is_active = payload.is_active
    if payload.credentials is not None:
        supplier.credentials_encrypted = encrypt_credential(json.dumps(payload.credentials))

    db.commit()
    db.refresh(supplier)
    count = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier.id).count()

    return SupplierResponse(
        id=supplier.id,
        name=supplier.name,
        adapter_class=supplier.adapter_class,
        is_active=supplier.is_active,
        last_synced_at=supplier.last_synced_at,
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
        product_count=count
    )

@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    db.delete(supplier)
    db.commit()
    return None

@router.post("/{supplier_id}/test")
def test_supplier_connection(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if not supplier.credentials_encrypted and not supplier.adapter_class.startswith("Mock"):
        raise HTTPException(
            status_code=400,
            detail=f"No account credentials configured for {supplier.name}. Real distributor API/FTP credentials are required to verify live connection."
        )

    service = SyncService(db)
    adapter = service.get_adapter_for_supplier(supplier)
    try:
        success = adapter.test_connection()
        return {"success": success, "message": f"Live connection to {supplier.name} verified successfully."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/{supplier_id}/sync")
def sync_supplier(
    supplier_id: int,
    sync_async: bool = Query(False, description="Whether to queue via Celery or execute immediately"),
    db: Session = Depends(get_db)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if sync_async:
        from app.tasks.sync_tasks import sync_supplier_task
        task = sync_supplier_task.delay(supplier_id)
        return {
            "task_id": task.id,
            "message": f"Sync queued asynchronously for {supplier.name}",
            "supplier_id": supplier.id
        }

    # Synchronous execution for instant frontend response / testing
    service = SyncService(db)
    try:
        result = service.sync_supplier(supplier_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(exc)}")
