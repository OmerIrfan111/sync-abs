const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

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

