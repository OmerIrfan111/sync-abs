"use client";

import React, { useEffect, useState } from "react";
import { 
  Package, 
  Layers, 
  CheckCircle2, 
  AlertTriangle, 
  Activity,
  ArrowUpRight,
  RefreshCw,
  Clock,
  Truck,
  Store,
  Zap,
  CheckCircle,
  AlertCircle
} from "lucide-react";
import { fetchApi, DashboardStats } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [reconcileResult, setReconcileResult] = useState<{
    message: string;
    details: Array<{
      supplier_name: string;
      status: string;
      imported?: number;
      changed?: number;
      error?: string;
    }>;
  } | null>(null);

  const loadStats = async () => {
    try {
      const data = await fetchApi<DashboardStats>("/dashboard/summary");
      setStats(data);
    } catch (err) {
      console.error("Failed to load dashboard statistics:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 10000); // 10s auto-refresh
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadStats();
  };

  const handleReconcileAll = async () => {
    setReconciling(true);
    setReconcileResult(null);
    try {
      const result = await fetchApi<any>("/dashboard/reconcile-all", {
        method: "POST",
      });
      setReconcileResult(result);
      await loadStats();
    } catch (err: any) {
      alert("System reconcile failed: " + err.message);
    } finally {
      setReconciling(false);
    }
  };

  const kpis = [
    {
      title: "Total Catalog Products",
      value: stats?.total_products ?? 0,
      icon: Package,
      gradient: "from-blue-500/20 to-indigo-500/20",
      iconColor: "text-blue-400",
      description: "Canonical products across all suppliers"
    },
    {
      title: "Active Listings",
      value: stats?.active_listings ?? 0,
      icon: Layers,
      gradient: "from-emerald-500/20 to-teal-500/20",
      iconColor: "text-emerald-400",
      description: "Live offers on connected marketplaces"
    },
    {
      title: "In Stock Items",
      value: stats?.in_stock_products ?? 0,
      icon: CheckCircle2,
      gradient: "from-green-500/20 to-emerald-500/20",
      iconColor: "text-green-400",
      description: "Available from at least one supplier"
    },
    {
      title: "Out of Stock Items",
      value: stats?.out_of_stock_products ?? 0,
      icon: AlertTriangle,
      gradient: "from-amber-500/20 to-orange-500/20",
      iconColor: "text-amber-400",
      description: "Zero quantity across all distributors"
    },
    {
      title: "Needs Attention",
      value: stats?.needs_attention ?? 0,
      icon: Activity,
      gradient: "from-rose-500/20 to-red-500/20",
      iconColor: "text-rose-400",
      description: "Pending sync failures or price exceptions"
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">System Operations Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time synchronization metrics across wholesale suppliers and ecommerce marketplaces.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReconcileAll}
            disabled={reconciling}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white rounded-xl text-sm font-semibold transition-all shadow-md shadow-amber-600/20 disabled:opacity-50"
          >
            <Zap className={`h-4 w-4 ${reconciling ? "animate-pulse" : "fill-current"}`} />
            <span>{reconciling ? "Reconciling All..." : "Run System Reconcile"}</span>
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh Metrics</span>
          </button>
        </div>
      </div>

      {/* Reconciliation Result Banner */}
      {reconcileResult && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 font-semibold">
              <CheckCircle className="h-5 w-5 text-emerald-400" />
              <span>{reconcileResult.message}</span>
            </div>
            <button
              onClick={() => setReconcileResult(null)}
              className="text-xs text-gray-400 hover:text-white px-2 py-1 bg-gray-800/60 rounded"
            >
              Dismiss
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 mt-2">
            {reconcileResult.details.map((d, i) => (
              <div key={i} className="text-xs p-2.5 rounded-lg bg-gray-950/60 border border-emerald-500/20">
                <span className="font-bold text-white block">{d.supplier_name}</span>
                {d.status === "SUCCESS" ? (
                  <span className="text-gray-400 text-[11px]">
                    Imported: <span className="text-emerald-400 font-semibold">{d.imported}</span> | Changes: <span className="text-indigo-400 font-semibold">{d.changed}</span>
                  </span>
                ) : (
                  <span className="text-rose-400 text-[11px]">{d.error}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5 KPI Cards (Spec Section 24) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <div
              key={index}
              className="p-5 rounded-2xl bg-gradient-to-b from-[#131b2e] to-[#0e1526] border border-gray-800/80 shadow-lg relative overflow-hidden flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{kpi.title}</span>
                <div className={`p-2 rounded-xl bg-gray-800/50 ${kpi.iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-4">
                <div className="text-3xl font-black text-white tracking-tight">
                  {loading ? "..." : kpi.value.toLocaleString()}
                </div>
                <div className="text-[11px] text-gray-500 mt-1.5">{kpi.description}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Supplier & Marketplace Health Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Suppliers Status */}
        <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <Truck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Wholesale Suppliers Health</h2>
                <p className="text-xs text-gray-400">Connection state & product inventory imports</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {stats?.suppliers_health.map((sup) => (
              <div
                key={sup.id}
                className="flex items-center justify-between p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/60"
              >
                <div className="flex items-center gap-3">
                  <div className={`h-2.5 w-2.5 rounded-full ${
                    sup.status === "HEALTHY" ? "bg-emerald-500" : sup.status === "ERROR" ? "bg-rose-500" : "bg-gray-500"
                  }`} />
                  <div>
                    <div className="text-sm font-semibold text-gray-200">{sup.name}</div>
                    <div className="text-xs text-gray-500 flex items-center gap-1.5">
                      <Clock className="h-3 w-3" />
                      <span>Last sync: {sup.last_synced_at ? new Date(sup.last_synced_at).toLocaleTimeString() : "Pending"}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-white">{sup.product_count} products</div>
                  <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                    sup.status === "HEALTHY"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  }`}>
                    {sup.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Marketplaces Status */}
        <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400">
                <Store className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Connected Marketplaces</h2>
                <p className="text-xs text-gray-400">Sales channels & live listing distribution</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {stats?.marketplaces_health.map((mkt) => (
              <div
                key={mkt.id}
                className="flex items-center justify-between p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/60"
              >
                <div className="flex items-center gap-3">
                  <div className={`h-2.5 w-2.5 rounded-full ${
                    mkt.status === "HEALTHY" ? "bg-emerald-500" : "bg-gray-500"
                  }`} />
                  <div>
                    <div className="text-sm font-semibold text-gray-200">{mkt.name}</div>
                    <div className="text-xs text-gray-500">Channel Integration</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-white">{mkt.listing_count} listings</div>
                  <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    Ready
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity & Errors */}
      <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-lg">
        <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-indigo-400" />
          <span>Recent Issues & Exceptions</span>
        </h2>
        {stats?.recent_errors && stats.recent_errors.length > 0 ? (
          <div className="space-y-2.5">
            {stats.recent_errors.map((err) => (
              <div key={err.id} className="p-3.5 bg-gray-900/60 border border-gray-800 rounded-xl flex items-center justify-between text-sm">
                <div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 mr-2">
                    {err.error_type}
                  </span>
                  <span className="text-gray-300 font-medium">{err.message}</span>
                </div>
                <span className="text-xs text-gray-500">{new Date(err.created_at).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500 text-sm">
            <CheckCircle2 className="h-8 w-8 text-emerald-500/50 mx-auto mb-2" />
            No active synchronization errors. Platform is running optimally.
          </div>
        )}
      </div>
    </div>
  );
}
