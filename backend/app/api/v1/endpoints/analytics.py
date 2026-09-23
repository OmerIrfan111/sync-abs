from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsSummary, SupplierScore

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    days: int = Query(30, ge=1, le=365, description="Lookback window in days"),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    return service.get_summary(days=days)


@router.get("/supplier-scores", response_model=list[SupplierScore])
def get_supplier_scores(
    days: int = Query(90, ge=1, le=365, description="Lookback window in days"),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    return service.get_supplier_scores(days=days)
