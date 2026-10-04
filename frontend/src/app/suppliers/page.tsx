"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Truck, 
  RefreshCw, 
  Wifi, 
  AlertCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Filter,
  DollarSign,
  ArrowRight,
  Sparkles
} from "lucide-react";
import { fetchApi, Supplier } from "@/lib/api";

interface PrefetchFilters {
  category: string;
  brand: string;
  limit: string;
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ id: number; message: string; type: "success" | "error" } | null>(null);
  const [expandedSettingsId, setExpandedSettingsId] = useState<number | null>(null);
  const [expandedFilterId, setExpandedFilterId] = useState<number | null>(null);
  const [filteredSyncingId, setFilteredSyncingId] = useState<number | null>(null);

  // Filter form state per supplier
  const [filterForms, setFilterForms] = useState<Record<number, PrefetchFilters>>({});

  const loadSuppliers = async () => {
    try {
      const data = await fetchApi<Supplier[]>("/suppliers");
      // Keep supported wholesale suppliers (Ingram Micro, D&H, TD SYNNEX)
      const supported = data.filter(s => 
        ["ingram", "d&h", "d and h", "dandh", "synnex", "td synnex"].some(k => s.name.toLowerCase().includes(k))
      );
      setSuppliers(supported);
    } catch (err) {
      console.error("Failed to load suppliers:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuppliers();
  }, []);

  const getFilter = (id: number): PrefetchFilters => {
    return filterForms[id] || { category: "", brand: "", limit: "500" };
  };

  const updateFilter = (id: number, key: keyof PrefetchFilters, val: string) => {
    setFilterForms(prev => ({
      ...prev,
      [id]: {
        ...(prev[id] || { category: "", brand: "", limit: "500" }),
        [key]: val
      }
    }));
  };

  const handleTestConnection = async (id: number) => {
    setTestingId(id);
    setFeedback(null);
    try {
      await fetchApi<{ success: boolean; message: string }>(`/suppliers/${id}/test`, {
        method: "POST"
      });
      setFeedback({ id, message: "Connection verified! Distributor API is responsive and ready.", type: "success" });
    } catch (err: any) {
      setFeedback({ id, message: "Could not reach supplier: " + (err.message || "Connection timed out"), type: "error" });
    } finally {
      setTestingId(null);
    }
  };

  const handleSyncNow = async (id: number) => {
    setSyncingId(id);
    setFeedback(null);
    try {
      const res = await fetchApi<any>(`/suppliers/${id}/sync`, {
        method: "POST"
      });
      setFeedback({ 
        id, 
        message: `Stock & prices updated! Processed ${res.products_imported || 0} products (${res.changes_detected || 0} updates applied).`, 
        type: "success" 
      });
      loadSuppliers();
    } catch (err: any) {
      setFeedback({ id, message: "Update check failed: " + err.message, type: "error" });
    } finally {
      setSyncingId(null);
    }
  };

  const handleFilteredSync = async (id: number) => {
    setFilteredSyncingId(id);
    setFeedback(null);
    try {
      const filters = getFilter(id);
      const params = new URLSearchParams();

      if (filters.category.trim()) {
        params.append("category", filters.category.trim());
      }
      if (filters.brand.trim()) {
        params.append("brand", filters.brand.trim());
      }
      if (filters.limit.trim()) {
        const lim = parseInt(filters.limit, 10);
        if (!isNaN(lim) && lim > 0) {
          params.append("limit", String(lim));
        }
      }

      const queryString = params.toString() ? `?${params.toString()}` : "";
      const res = await fetchApi<any>(`/suppliers/${id}/sync${queryString}`, {
        method: "POST"
      });

      const filterSummary = [
        filters.category.trim() ? `Category: "${filters.category.trim()}"` : null,
        filters.brand.trim() ? `Brand: "${filters.brand.trim()}"` : null,
        filters.limit.trim() ? `Limit: ${filters.limit.trim()}` : null,
      ].filter(Boolean).join(", ");

      setFeedback({ 
        id, 
        message: `Filtered sync completed! (${filterSummary || "All items"}) Processed ${res.products_imported || 0} products (${res.changes_detected || 0} updates applied).`, 
        type: "success" 
      });
      loadSuppliers();
    } catch (err: any) {
      setFeedback({ id, message: "Filtered sync failed: " + err.message, type: "error" });
    } finally {
      setFilteredSyncingId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header - Unboxed on canvas */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-brand font-normal text-[#0a0a0a]">Wholesale Suppliers</h1>
          <p className="text-sm text-[#767676] mt-1 max-w-2xl leading-relaxed">
            Connect to distributors who provide products and ship customer orders for you. We check their inventory and wholesale prices continuously.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <Link
            href="/rules"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#0a0a0a] rounded-lg text-xs font-medium transition-all border border-gray-300"
          >
            <DollarSign className="h-3.5 w-3.5 text-[#D9720F]" />
            <span>Manage Base Shipping</span>
          </Link>

          <button
            onClick={loadSuppliers}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#0a0a0a] rounded-lg text-xs font-medium transition-all border border-gray-300"
          >
            <RefreshCw className="h-3.5 w-3.5 text-[#767676]" />
            <span>Refresh List</span>
          </button>
        </div>
      </div>

      {/* Supplier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
        {loading ? (
          <div className="col-span-full py-20 text-center text-[#767676]">
            Loading wholesale supplier connections...
          </div>
        ) : (
          suppliers.map((sup) => {
            const isSyncing = syncingId === sup.id;
            const isTesting = testingId === sup.id;
            const isFilteredSyncing = filteredSyncingId === sup.id;
            const itemFeedback = feedback?.id === sup.id ? feedback : null;
            const isSettingsExpanded = expandedSettingsId === sup.id;
            const isFilterExpanded = expandedFilterId === sup.id;
            const filterState = getFilter(sup.id);

            return (
              <div
                key={sup.id}
                className="bg-white p-6 rounded-lg border border-gray-100 flex flex-col justify-between space-y-4 shadow-sm"
              >
                <div>
                  {/* Top Row: Name & Status */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-lg bg-[#D9720F]/10 text-[#A8560A]">
                        <Truck className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-[#0a0a0a]">{sup.name}</h2>
                        <span className="text-[11px] text-[#767676]">Authorized Distributor</span>
                      </div>
                    </div>
                    {itemFeedback?.type === "error" ? (
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider flex items-center gap-1.5 bg-rose-50 text-rose-800 border border-rose-200">
                        <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
                        <span>Feed Error</span>
                      </span>
                    ) : (
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider flex items-center gap-1.5 ${
                        sup.is_active
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                          : "bg-gray-100 text-gray-600 border border-gray-200"
                      }`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${sup.is_active ? "bg-emerald-500" : "bg-gray-400"}`} />
                        <span>{sup.is_active ? "Catalog Active" : "Paused"}</span>
                      </span>
                    )}
                  </div>

                  {/* Metrics: 3 Columns (Products, Base Shipping, Last Update) */}
                  <div className="grid grid-cols-3 gap-2.5 my-3.5">
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <span className="text-[11px] text-[#767676] block">Products</span>
                      <span className="text-lg font-bold text-[#0a0a0a]">{sup.product_count}</span>
                      <span className="text-[10px] text-[#767676] block mt-0.5">In catalog</span>
                    </div>

                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <span className="text-[11px] text-[#767676] block">Base Shipping</span>
                      <span className="text-base font-bold text-[#0a0a0a]">
                        {sup.default_shipping_charge != null ? `$${Number(sup.default_shipping_charge).toFixed(2)}` : "None"}
                      </span>
                      <span className="text-[10px] text-emerald-700 font-medium block mt-0.5">
                        {sup.default_shipping_charge != null ? "Active on sync" : "Defaults to $0"}
                      </span>
                    </div>

                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <span className="text-[11px] text-[#767676] block">Last Sync</span>
                      <span className="text-xs font-semibold text-[#0a0a0a] block truncate mt-1" suppressHydrationWarning>
                        {sup.last_synced_at ? new Date(sup.last_synced_at).toLocaleTimeString() : "Pending"}
                      </span>
                      <span className="text-[10px] text-emerald-700 font-semibold block mt-0.5">Auto-active</span>
                    </div>
                  </div>

                  {/* Feedback Notification */}
                  {itemFeedback && (
                    <div className={`p-3 rounded-lg text-xs mb-3 flex items-start gap-2 ${
                      itemFeedback.type === "success"
                        ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
                        : "bg-rose-50 text-rose-900 border border-rose-200"
                    }`}>
                      {itemFeedback.type === "success" ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 mt-0.5" />
                      ) : (
                        <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
                      )}
                      <span>{itemFeedback.message}</span>
                    </div>
                  )}

                  {/* Prefetch Filter Form Section */}
                  <div className="mt-3 p-3.5 bg-gray-50/80 rounded-lg border border-gray-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Filter className="h-3.5 w-3.5 text-[#D9720F]" />
                        <span className="text-xs font-semibold text-[#0a0a0a]">Prefetch Filter Sync</span>
                      </div>
                      <button
                        onClick={() => setExpandedFilterId(isFilterExpanded ? null : sup.id)}
                        className="text-[11px] text-[#767676] hover:text-[#0a0a0a] flex items-center gap-1 font-medium transition-colors"
                      >
                        {isFilterExpanded ? (
                          <>
                            <span>Hide filters</span>
                            <ChevronUp className="h-3 w-3" />
                          </>
                        ) : (
                          <>
                            <span>Set category / brand / limit</span>
                            <ChevronDown className="h-3 w-3" />
                          </>
                        )}
                      </button>
                    </div>

                    {isFilterExpanded ? (
                      <div className="pt-2 border-t border-gray-200 space-y-3">
                        <p className="text-[11px] text-[#767676] leading-relaxed">
                          Narrow which items are pulled from this distributor&apos;s wholesale feed to speed up sync or target specific inventory.
                        </p>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                          {/* Category Field */}
                          <div>
                            <label className="text-[10px] font-semibold text-[#767676] uppercase tracking-wider block mb-1">
                              Category
                            </label>
                            <input
                              type="text"
                              placeholder="e.g. Laptops, Displays"
                              value={filterState.category}
                              onChange={(e) => updateFilter(sup.id, "category", e.target.value)}
                              className="w-full px-2.5 py-1.5 bg-white border border-gray-300 rounded-md text-xs text-[#0a0a0a] placeholder:text-gray-400 focus:outline-none focus:border-[#0a0a0a] focus:ring-1 focus:ring-[#0a0a0a]"
                            />
                          </div>

                          {/* Brand Field */}
                          <div>
                            <label className="text-[10px] font-semibold text-[#767676] uppercase tracking-wider block mb-1">
                              Brand
                            </label>
                            <input
                              type="text"
                              placeholder="e.g. Dell, HP, Lenovo"
                              value={filterState.brand}
                              onChange={(e) => updateFilter(sup.id, "brand", e.target.value)}
                              className="w-full px-2.5 py-1.5 bg-white border border-gray-300 rounded-md text-xs text-[#0a0a0a] placeholder:text-gray-400 focus:outline-none focus:border-[#0a0a0a] focus:ring-1 focus:ring-[#0a0a0a]"
                            />
                          </div>

                          {/* Limit Field */}
                          <div>
                            <label className="text-[10px] font-semibold text-[#767676] uppercase tracking-wider block mb-1">
                              Max Items (Limit)
                            </label>
                            <input
                              type="number"
                              min="1"
                              max="10000"
                              placeholder="500"
                              value={filterState.limit}
                              onChange={(e) => updateFilter(sup.id, "limit", e.target.value)}
                              className="w-full px-2.5 py-1.5 bg-white border border-gray-300 rounded-md text-xs text-[#0a0a0a] placeholder:text-gray-400 focus:outline-none focus:border-[#0a0a0a] focus:ring-1 focus:ring-[#0a0a0a]"
                            />
                          </div>
                        </div>

                        {/* Filtered Sync Button */}
                        <div className="flex items-center justify-between pt-1">
                          <span className="text-[10px] text-[#767676]">
                            Targeted prefetch query
                          </span>
                          <button
                            onClick={() => handleFilteredSync(sup.id)}
                            disabled={isFilteredSyncing || isSyncing}
                            className="px-3.5 py-1.5 bg-[#A8560A] hover:bg-[#8F4706] text-white rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-sm"
                          >
                            <Filter className={`h-3.5 w-3.5 ${isFilteredSyncing ? "animate-spin" : ""}`} />
                            <span>{isFilteredSyncing ? "Prefetching..." : "Filtered Sync"}</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between text-[11px] text-[#767676]">
                        <span>Standard sync fetches full catalog pages</span>
                        <button
                          onClick={() => setExpandedFilterId(sup.id)}
                          className="text-[#A8560A] hover:underline font-medium"
                        >
                          Configure filters
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Primary Actions */}
                <div className="space-y-2.5 pt-3.5 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSyncNow(sup.id)}
                      disabled={isTesting || isSyncing || isFilteredSyncing}
                      className="flex-1 px-3 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 text-[#D9720F] ${isSyncing ? "animate-spin" : ""}`} />
                      <span>{isSyncing ? "Checking..." : "Full Sync Now"}</span>
                    </button>

                    <button
                      onClick={() => handleTestConnection(sup.id)}
                      disabled={isTesting || isSyncing || isFilteredSyncing}
                      className="px-3 py-2 bg-white hover:bg-gray-50 text-[#0a0a0a] rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all border border-gray-300 disabled:opacity-50"
                      title="Test API Connection"
                    >
                      <Wifi className={`h-3.5 w-3.5 text-[#767676] ${isTesting ? "animate-pulse text-[#A8560A]" : ""}`} />
                      <span>{isTesting ? "Testing..." : "Test"}</span>
                    </button>
                  </div>

                  {/* Collapsible Connection Settings */}
                  <div className="pt-0.5">
                    <button
                      onClick={() => setExpandedSettingsId(isSettingsExpanded ? null : sup.id)}
                      className="text-[11px] text-[#767676] hover:text-[#0a0a0a] flex items-center gap-1 transition-colors font-medium"
                    >
                      {isSettingsExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      <span>Connection details (Advanced)</span>
                    </button>

                    {isSettingsExpanded && (
                      <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200 text-[11px] font-mono text-[#767676] space-y-1">
                        <div className="flex justify-between">
                          <span>Adapter:</span>
                          <span className="text-[#0a0a0a] font-semibold">{sup.adapter_class}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Environment:</span>
                          <span className="text-emerald-700 font-semibold">
                            {sup.name.toLowerCase().includes("ingram")
                              ? "Production (OAuth 2.0)"
                              : sup.name.toLowerCase().includes("d&h")
                              ? "Production (Axway REST)"
                              : sup.name.toLowerCase().includes("synnex")
                              ? "Production (OAuth 2.0 / StreamOne)"
                              : "REST / Feed"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Base Shipping:</span>
                          <span className="text-[#0a0a0a]">
                            {sup.default_shipping_charge != null ? `$${Number(sup.default_shipping_charge).toFixed(2)}` : "None configured"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Security:</span>
                          <span className="text-[#767676]">AES-128 Fernet Encrypted</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
