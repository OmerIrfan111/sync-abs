"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  RefreshCw,
  Truck,
  Store,
  Zap,
  CheckCircle,
  CheckCircle2,
  AlertCircle,
  ShieldAlert
} from "lucide-react";
import { fetchApi, DashboardStats } from "@/lib/api";
import Donut from "@/components/Donut";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [lastUpdatedTime, setLastUpdatedTime] = useState<Date>(new Date());
  const [mounted, setMounted] = useState(false);
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
      setLastUpdatedTime(new Date());
    } catch (err) {
      console.error("Failed to load dashboard statistics:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    setMounted(true);
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
      alert("System update failed: " + err.message);
    } finally {
      setReconciling(false);
    }
  };

  const manifest = [
    {
      title: "Products",
      value: (stats?.total_products ?? 0).toLocaleString(),
      description: "In wholesale catalog",
      href: "/catalog"
    },
    {
      title: "In Stores",
      value: (stats?.active_listings ?? 0).toLocaleString(),
      description: "Live listings",
      href: "/listings"
    },
    {
      title: "In Stock",
      value: (stats?.in_stock_products ?? 0).toLocaleString(),
      description: "Ready to ship",
      href: "/catalog?in_stock=true"
    },
    {
      title: "Out of Stock",
      value: (stats?.out_of_stock_products ?? 0).toLocaleString(),
      description: "Supplier ran out",
      href: "/catalog"
    },
    {
      title: "Issues",
      value: (stats?.needs_attention ?? 0).toLocaleString(),
      description: stats?.needs_attention ? "Need review" : "All clear",
      href: "/logs",
      alert: !!stats?.needs_attention
    },
    {
      title: "Orders Today",
      value: (stats?.total_orders_today ?? 0).toLocaleString(),
      description: "New this morning",
      href: "/orders"
    },
    {
      title: "Pending Routing",
      value: (stats?.pending_orders ?? 0).toLocaleString(),
      description: "Awaiting supplier",
      href: "/orders?status=PENDING_ROUTING"
    },
    {
      title: "Revenue (30d)",
      value: `$${Number(stats?.revenue_30d ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
      description: "Order revenue",
      href: "/orders",
    },
  ];

  const supplierMix = stats?.suppliers_health.filter((s) => s.product_count > 0) ?? [];
  const maxSupplierCount = Math.max(1, ...supplierMix.map((s) => s.product_count));
  const supplierMixColors = ["#D9720F", "#14B8A6", "#F59E0B", "#EC4899"];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-2xl font-brand font-normal text-[#1C201B]">Store Overview</h1>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleReconcileAll}
            disabled={reconciling}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-[#8B5A2B] hover:bg-[#74491F] text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <Zap className={`h-3.5 w-3.5 ${reconciling ? "animate-pulse" : ""}`} />
            <span>{reconciling ? "Checking..." : "Update Everything Now"}</span>
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#1C201B] rounded-lg text-xs font-medium transition-colors border border-gray-200 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-[#767676] ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Credential Expiry Warnings (e.g. eBay's 18-month refresh token) */}
      {stats?.credential_warnings && stats.credential_warnings.length > 0 && (
        <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 space-y-1.5">
          {stats.credential_warnings.map((warning, i) => (
            <div key={i} className="flex items-center gap-2 text-xs font-semibold text-amber-900">
              <ShieldAlert className="h-4 w-4 text-amber-600 shrink-0" />
              <span>{warning}</span>
              <Link href="/marketplaces" className="ml-auto text-[11px] font-semibold text-amber-800 underline hover:text-amber-900 shrink-0">
                Reauthorize now
              </Link>
            </div>
          ))}
        </div>
      )}

      {/* Immediate Reconcile Result Box */}
      {reconcileResult && (
        <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 font-semibold text-xs text-emerald-900">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              <span>All {reconcileResult.details.length} wholesale suppliers checked and updated!</span>
            </div>
            <button
              onClick={() => setReconcileResult(null)}
              className="text-xs text-emerald-700 hover:text-emerald-900 px-2 py-0.5 bg-white rounded-lg border border-emerald-200"
            >
              Dismiss
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 mt-2">
            {reconcileResult.details.map((d, i) => (
              <div key={i} className="text-xs p-2.5 rounded-lg bg-white border border-emerald-100">
                <span className="font-semibold text-[#1C201B] block">{d.supplier_name}</span>
                {d.status === "SUCCESS" ? (
                  <span className="text-[#767676] text-[11px]">
                    Imported: <span className="text-emerald-700 font-bold">{d.imported}</span> | Changes: <span className="text-[#A8560A] font-bold">{d.changed}</span>
                  </span>
                ) : (
                  <span className="text-rose-600 text-[11px]">{d.error}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Manifest — one bordered ledger, not eight identical boxed tiles */}
      <div className="border border-gray-200 bg-[#FAFAF8] rounded-lg">
        <div className="px-4 py-2 border-b-2 border-[#1C201B] flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-[#767676]">Store Manifest</span>
          <span className="text-[11px] text-[#767676]" suppressHydrationWarning>
            {mounted ? lastUpdatedTime.toLocaleTimeString() : "--:--"}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-gray-200">
          {manifest.map((row, index) => (
            <Link
              key={index}
              href={row.href}
              className="p-4 hover:bg-gray-100/60 transition-colors"
            >
              <div className="text-[11px] font-semibold uppercase tracking-wide text-[#767676]">{row.title}</div>
              <div className={`text-xl font-bold tabular-nums mt-1 ${row.alert ? "text-rose-700" : "text-[#1C201B]"}`}>
                {loading ? "..." : row.value}
              </div>
              <div className="text-[11px] text-[#767676] mt-0.5">{row.description}</div>
            </Link>
          ))}
        </div>
      </div>

      {/* Inventory Health + Supplier Mix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-[#FAFAF8] border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-bold text-[#1C201B] mb-4">Inventory Health</h2>
          <Donut
            centerLabel="Total Products"
            centerValue={(stats?.total_products ?? 0).toLocaleString()}
            segments={[
              { label: "In Stock", value: stats?.in_stock_products ?? 0, color: "#059669" },
              { label: "Out of Stock", value: stats?.out_of_stock_products ?? 0, color: "#E11D48" },
            ]}
          />
        </div>

        <div className="bg-[#FAFAF8] border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-bold text-[#1C201B] mb-4">Catalog by Supplier</h2>
          <div className="space-y-3">
            {supplierMix.length === 0 && (
              <p className="text-xs text-[#767676]">No supplier catalog data yet.</p>
            )}
            {supplierMix.map((s, i) => (
              <div key={s.id}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-semibold text-[#1C201B]">{s.name}</span>
                  <span className="text-[#767676]">{s.product_count.toLocaleString()} items</span>
                </div>
                <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(s.product_count / maxSupplierCount) * 100}%`,
                      backgroundColor: supplierMixColors[i % supplierMixColors.length],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Wholesale Suppliers & Online Stores Side-by-Side Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Wholesale Suppliers */}
        <div className="bg-[#FAFAF8] border border-gray-200 rounded-lg p-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-[#D9720F]/10 text-[#A8560A]">
                <Truck className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#1C201B]">Your Wholesale Suppliers</h2>
                <p className="text-xs text-[#767676]">Live feeds from connected distributor warehouses.</p>
              </div>
            </div>
            <Link
              href="/suppliers"
              className="text-xs font-semibold text-[#A8560A] hover:text-[#A8560A] flex items-center gap-1"
            >
              <span>Manage</span>
            </Link>
          </div>

          <div className="divide-y divide-gray-100">
            {stats?.suppliers_health.map((sup) => (
              <div
                key={sup.id}
                className="flex items-center justify-between py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <div className={`h-2 w-2 rounded-full ${
                    sup.status === "HEALTHY" ? "bg-emerald-500" : "bg-rose-500"
                  }`} />
                  <div>
                    <div className="text-xs font-semibold text-[#1C201B]">{sup.name}</div>
                    <div className="text-[11px] text-[#767676]">
                      {sup.status === "HEALTHY" ? "Connected & Up to date" : "Needs Attention"}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-[#1C201B]">{sup.product_count} items</div>
                  <span className="text-[10px] text-[#767676]">Available</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Online Stores */}
        <div className="bg-[#FAFAF8] border border-gray-200 rounded-lg p-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-teal-50 text-teal-600">
                <Store className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#1C201B]">Your Online Stores</h2>
                <p className="text-xs text-[#767676]">Active listings on customer-facing marketplaces.</p>
              </div>
            </div>
            <Link
              href="/marketplaces"
              className="text-xs font-semibold text-teal-700 hover:text-teal-800 flex items-center gap-1"
            >
              <span>Connect More</span>
            </Link>
          </div>

          <div className="divide-y divide-gray-100">
            {stats?.marketplaces_health.map((mkt) => (
              <div
                key={mkt.id}
                className="flex items-center justify-between py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <div className={`h-2 w-2 rounded-full ${
                    mkt.status === "HEALTHY" ? "bg-emerald-500" : mkt.status === "IDLE" ? "bg-gray-400" : "bg-rose-500"
                  }`} />
                  <div>
                    <div className="text-xs font-semibold text-[#1C201B]">{mkt.name}</div>
                    <div className={`text-[11px] font-medium ${
                      mkt.status === "HEALTHY" ? "text-emerald-700" : mkt.status === "IDLE" ? "text-gray-500" : "text-rose-700"
                    }`}>
                      {mkt.status === "HEALTHY" ? "Active & Selling" : mkt.status === "IDLE" ? "Not active" : "Needs Attention"}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-[#1C201B]">{mkt.listing_count} offers</div>
                  <span className="text-[10px] text-[#767676]">Live in store</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications & Plain English Alerts */}
      <div className="bg-[#FAFAF8] border border-gray-200 rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-rose-50 text-rose-600">
              <AlertCircle className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#1C201B]">Alerts & Notifications</h2>
              <p className="text-xs text-[#767676]">Operational events requiring your attention.</p>
            </div>
          </div>
          <Link href="/logs" className="text-xs font-semibold text-[#A8560A] hover:text-[#A8560A] flex items-center gap-1">
            <span>View History</span>
          </Link>
        </div>

        {stats?.recent_errors && stats.recent_errors.length > 0 ? (
          <div className="space-y-2.5">
            {stats.recent_errors.map((err) => (
              <div key={err.id} className="p-3 bg-rose-50/70 border border-rose-100 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800">
                      Attention
                    </span>
                    <span className="text-[11px] text-[#767676]" suppressHydrationWarning>{new Date(err.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-[#1C201B] font-semibold mt-1">
                    {err.marketplace_name
                      ? `Temporary connection notice for ${err.marketplace_name}.`
                      : err.supplier_name
                        ? `Could not reach ${err.supplier_name} during check.`
                        : "A temporary update was delayed."}
                  </p>
                  <p className="text-[11px] text-[#767676] mt-0.5">
                    Why it matters: Stock or price updates for affected items may be delayed until re-checked.
                  </p>
                </div>
                <Link
                  href="/logs"
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold self-start sm:self-center shrink-0 transition-colors"
                >
                  Review
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-[#767676] text-xs bg-gray-50 rounded-lg border border-gray-100">
            <CheckCircle2 className="h-7 w-7 text-emerald-600 mx-auto mb-1.5" />
            <div className="font-semibold text-[#1C201B]">All systems are running smoothly</div>
            <p className="text-[11px] text-[#767676] mt-0.5">All wholesale suppliers are connected, and all store listings are in sync.</p>
          </div>
        )}
      </div>
    </div>
  );
}
