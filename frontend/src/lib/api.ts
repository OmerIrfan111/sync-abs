import { getToken, clearAuth } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const token = getToken();
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 401) {
    clearAuth();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    let errorDetail = "API request failed";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch (_) {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  const text = await response.text();
  if (!text || !text.trim()) {
    return {} as T;
  }

  try {
    return JSON.parse(text);
  } catch (_) {
    return {} as T;
  }
}

export interface Listing {
  id: number;
  product_id: number;
  product_sku?: string;
  product_title?: string;
  marketplace_id: number;
  marketplace_name?: string;
  external_listing_id?: string;
  status: string;
  selling_price: number;
  listed_qty: number;
  last_updated_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  sku: string;
  upc?: string;
  ean?: string;
  mpn?: string;
  title: string;
  brand?: string;
  description?: string;
  category?: string;
  images: string[];
  specs_json: Record<string, any>;
  is_enabled: boolean;
  total_stock: number;
  lowest_cost?: number;
  supplier_products: {
    id: number;
    supplier_id: number;
    supplier_name: string;
    supplier_sku: string;
    cost: number;
    qty_available: number;
    stock_status: string;
    availability_status: string;
    shipping_info: Record<string, any>;
    last_seen_at?: string;
  }[];
  created_at: string;
  updated_at: string;
}

export interface Supplier {
  id: number;
  name: string;
  adapter_class: string;
  is_active: boolean;
  last_synced_at?: string;
  product_count: number;
}

export interface Marketplace {
  id: number;
  name: string;
  adapter_class: string;
  is_active: boolean;
  has_credentials: boolean;
  active_listings_count: number;
  total_listings_count: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_products: number;
  active_listings: number;
  in_stock_products: number;
  out_of_stock_products: number;
  needs_attention: number;
  total_orders_today: number;
  pending_orders: number;
  revenue_30d: number;
  suppliers_health: {
    id: number;
    name: string;
    is_active: boolean;
    status: string;
    last_synced_at?: string;
    product_count: number;
  }[];
  marketplaces_health: {
    id: number;
    name: string;
    is_active: boolean;
    status: string;
    listing_count: number;
    credentials_expires_at?: string | null;
    days_until_credentials_expire?: number | null;
  }[];
  recent_errors: {
    id: number;
    error_type: string;
    product_sku?: string;
    supplier_name?: string;
    marketplace_name?: string;
    message: string;
    retry_count: number;
    status: string;
    created_at: string;
  }[];
  credential_warnings: string[];
}

export interface PricingRule {
  id: number;
  product_id?: number | null;
  product_sku?: string | null;
  product_title?: string | null;
  marketplace_id?: number | null;
  marketplace_name?: string | null;
  rule_type: string;
  fixed_amount: number;
  percentage: number;
  marketplace_fee: number;
  desired_margin: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface InventoryRule {
  id: number;
  product_id?: number | null;
  product_sku?: string | null;
  product_title?: string | null;
  safety_buffer: number;
  out_of_stock_action: string;
  created_at: string;
  updated_at: string;
}

export interface SupplierPriority {
  id: number;
  product_id: number;
  product_sku?: string | null;
  product_title?: string | null;
  supplier_id: number;
  supplier_name?: string | null;
  priority_rank: number;
  selection_rule: string;
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  id: number;
  order_id: number;
  product_id?: number | null;
  listing_id?: number | null;
  marketplace_item_id?: string | null;
  sku?: string | null;
  title?: string | null;
  quantity: number;
  unit_price: number;
  supplier_cost?: number | null;
  supplier_id?: number | null;
  supplier_name?: string | null;
  status: string;
  routing_note?: string | null;
}

export interface PurchaseOrder {
  id: number;
  order_id: number;
  supplier_id?: number | null;
  supplier_name?: string | null;
  po_number: string;
  supplier_order_id?: string | null;
  status: string;
  total_cost: number;
  tracking_number?: string | null;
  carrier?: string | null;
  submitted_at?: string | null;
  shipped_at?: string | null;
  created_at?: string | null;
}

export interface OrderEvent {
  id: number;
  order_id: number;
  event_type: string;
  details: Record<string, any>;
  created_at?: string | null;
}

export interface Order {
  id: number;
  marketplace_id?: number | null;
  marketplace_name?: string | null;
  marketplace_order_id: string;
  buyer_username?: string | null;
  buyer_name?: string | null;
  shipping_address: Record<string, any>;
  order_total: number;
  marketplace_fees: number;
  currency: string;
  status: string;
  ordered_at?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  notes?: string | null;
  items_count: number;
  created_at?: string | null;
}

export interface OrderDetail extends Order {
  items: OrderItem[];
  purchase_orders: PurchaseOrder[];
  events: OrderEvent[];
}

export interface OrderStats {
  total_orders: number;
  pending_routing: number;
  awaiting_shipment: number;
  shipped: number;
  delivered: number;
  cancelled: number;
  revenue_30d: number;
  orders_today: number;
  avg_order_value: number;
}

export interface RevenueTrendPoint {
  date: string;
  revenue: number;
  profit: number;
}

export interface SupplierMargin {
  supplier_id: number;
  supplier_name: string;
  revenue: number;
  cost: number;
  margin_pct: number;
}

export interface TopSku {
  sku: string;
  title: string;
  units_sold: number;
  revenue: number;
  profit: number;
}

export interface CategoryPerformance {
  category: string;
  units_sold: number;
  revenue: number;
  profit: number;
  margin_pct: number;
}

export interface PeriodComparison {
  previous_period_days: number;
  revenue_change_pct: number | null;
  profit_change_pct: number | null;
  order_count_change_pct: number | null;
  previous_revenue_total: number;
  previous_net_profit_total: number;
  previous_order_count: number;
}

export interface AnalyticsSummary {
  period_days: number;
  revenue_total: number;
  cost_total: number;
  fees_total: number;
  net_profit_total: number;
  gross_margin_pct: number;
  order_count: number;
  revenue_trend: RevenueTrendPoint[];
  margin_by_supplier: SupplierMargin[];
  top_skus: TopSku[];
  category_performance: CategoryPerformance[];
  comparison: PeriodComparison | null;
}

export interface SupplierScore {
  supplier_id: number;
  supplier_name: string;
  po_count: number;
  avg_fulfillment_days: number | null;
  cancellation_rate_pct: number;
  routed_item_count: number;
  catalog_missing_data_rate_pct: number | null;
}

export interface RulePreview {
  product_id: number;
  product_sku: string;
  product_title: string;
  selected_supplier: {
    supplier_id: number;
    supplier_name: string;
    cost: number;
    stock: number;
    lead_time_days?: number | null;
  } | null;
  inventory: {
    raw_supplier_stock: number;
    safety_buffer_applied: number;
    calculated_marketplace_qty: number;
    out_of_stock_action: string;
    target_listing_status: string;
  };
  pricing: {
    supplier_cost: number;
    rule_type: string;
    calculated_price: number;
    fixed_amount: number;
    percentage: number;
    marketplace_fee: number;
    desired_margin: number;
  };
}

