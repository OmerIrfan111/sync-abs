from typing import List, Optional
from pydantic import BaseModel


class RevenueTrendPoint(BaseModel):
    date: str
    revenue: float
    profit: float


class SupplierMargin(BaseModel):
    supplier_id: int
    supplier_name: str
    revenue: float
    cost: float
    margin_pct: float


class TopSku(BaseModel):
    sku: str
    title: str
    units_sold: int
    revenue: float
    profit: float


class CategoryPerformance(BaseModel):
    category: str
    units_sold: int
    revenue: float
    profit: float
    margin_pct: float


class PeriodComparison(BaseModel):
    previous_period_days: int
    revenue_change_pct: Optional[float] = None
    profit_change_pct: Optional[float] = None
    order_count_change_pct: Optional[float] = None
    previous_revenue_total: float
    previous_net_profit_total: float
    previous_order_count: int


class AnalyticsSummary(BaseModel):
    period_days: int
    revenue_total: float
    cost_total: float
    fees_total: float
    net_profit_total: float
    gross_margin_pct: float
    order_count: int
    revenue_trend: List[RevenueTrendPoint]
    margin_by_supplier: List[SupplierMargin]
    top_skus: List[TopSku]
    category_performance: List[CategoryPerformance] = []
    comparison: Optional[PeriodComparison] = None


class SupplierScore(BaseModel):
    supplier_id: int
    supplier_name: str
    po_count: int
    avg_fulfillment_days: Optional[float] = None
    cancellation_rate_pct: float
    routed_item_count: int
