"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Package,
  Layers,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Clock,
  Truck,
  Store,
  Zap,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  ShoppingCart,
  DollarSign,
  ShieldAlert
} from "lucide-react";
import { fetchApi, DashboardStats } from "@/lib/api";
import Donut from "@/components/Donut";

const KPI_STYLES = [
  { icon: Package, chipBg: "bg-[#6C5DD3]/10", chipText: "text-[#6C5DD3]" },
  { icon: Layers, chipBg: "bg-teal-50", chipText: "text-teal-600" },
  { icon: CheckCircle2, chipBg: "bg-emerald-50", chipText: "text-emerald-600" },
  { icon: AlertTriangle, chipBg: "bg-amber-50", chipText: "text-amber-600" },
  { icon: AlertCircle, chipBg: "bg-rose-50", chipText: "text-rose-600" },
];

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

  const kpis = [
    {
      title: "Products Available",
      value: stats?.total_products ?? 0,
      description: "Imported from wholesale suppliers",
      href: "/catalog"
    },
    {
      title: "Live in Your Stores",
      value: stats?.active_listings ?? 0,
      description: "Online products buyers can buy now",
      href: "/listings"
    },
    {
      title: "In Stock",
      value: stats?.in_stock_products ?? 0,
      description: "Ready to ship immediately",
      href: "/catalog?in_stock=true"
    },
    {
      title: "Out of Stock",
      value: stats?.out_of_stock_products ?? 0,
      description: "Suppliers temporarily ran out",
      href: "/catalog"
    },
    {
      title: "Issues to Check",
      value: stats?.needs_attention ?? 0,
      description: stats?.needs_attention ? "Items need quick review" : "Everything running smoothly",
      href: "/logs"
    },
  ];

  const orderKpis = [
    {
      title: "Orders Today",
      value: stats?.total_orders_today ?? 0,
      icon: ShoppingCart,
      chipBg: "bg-[#6C5DD3]/10",
      chipText: "text-[#6C5DD3]",
      description: "New customer orders received today",
      href: "/orders"
    },
    {
      title: "Pending Routing",
      value: stats?.pending_orders ?? 0,
      icon: Clock,
      chipBg: "bg-amber-50",
      chipText: "text-amber-600",
      description: "Orders waiting to be routed to a supplier",
      href: "/orders?status=PENDING_ROUTING"
    },
    {
      title: "Revenue (30 Days)",
      value: `$${Number(stats?.revenue_30d ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      icon: DollarSign,
      chipBg: "bg-emerald-50",
      chipText: "text-emerald-600",
      description: "Order revenue in the last 30 days",
      href: "/orders",
    },
  ];

  const supplierMix = stats?.suppliers_health.filter((s) => s.product_count > 0) ?? [];
  const maxSupplierCount = Math.max(1, ...supplierMix.map((s) => s.product_count));
  const supplierMixColors = ["#6C5DD3", "#14B8A6", "#F59E0B", "#EC4899"];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-[#1B1B2F] tracking-tight">Store Overview</h1>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[#6C5DD3]/10 text-[#6C5DD3] border border-[#6C5DD3]/20">
              Live
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-[#767676] pt-1">
            <Clock className="h-3.5 w-3.5 text-[#767676]" />
            <span suppressHydrationWarning>
              Last checked: {mounted ? lastUpdatedTime.toLocaleTimeString() : "--:--"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleReconcileAll}
            disabled={reconciling}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-[#6C5DD3] hover:bg-[#5b4bd1] text-white rounded-xl text-xs font-semibold transition-colors disabled:opacity-50 shadow-sm shadow-[#6C5DD3]/20"
          >
            <Zap className={`h-3.5 w-3.5 ${reconciling ? "animate-pulse" : ""}`} />
            <span>{reconciling ? "Checking..." : "Update Everything Now"}</span>
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#1B1B2F] rounded-xl text-xs font-medium transition-colors border border-gray-200 disabled:opacity-50 shadow-sm"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-[#767676] ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Credential Expiry Warnings (e.g. eBay's 18-month refresh token) */}
      {stats?.credential_warnings && stats.credential_warnings.length > 0 && (
        <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 space-y-1.5">
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
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900">
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
              <div key={i} className="text-xs p-2.5 rounded-xl bg-white border border-emerald-100">
                <span className="font-semibold text-[#1B1B2F] block">{d.supplier_name}</span>
                {d.status === "SUCCESS" ? (
                  <span className="text-[#767676] text-[11px]">
                    Imported: <span className="text-emerald-700 font-bold">{d.imported}</span> | Changes: <span className="text-[#6C5DD3] font-bold">{d.changed}</span>
                  </span>
                ) : (
                  <span className="text-rose-600 text-[11px]">{d.error}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {kpis.map((kpi, index) => {
          const style = KPI_STYLES[index];
          const Icon = style.icon;
          return (
            <Link
              key={index}
              href={kpi.href}
              className="bg-white border border-gray-100 hover:shadow-md hover:-translate-y-0.5 rounded-2xl p-4 flex flex-col justify-between transition-all shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#767676]">{kpi.title}</span>
                <div className={`p-1.5 rounded-lg ${style.chipBg} ${style.chipText}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-[#1B1B2F] tracking-tight">
                  {loading ? "..." : kpi.value.toLocaleString()}
                </div>
                <div className="text-[11px] text-[#767676] mt-0.5">{kpi.description}</div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Order KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        {orderKpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <Link
              key={index}
              href={kpi.href}
              className="bg-white border border-gray-100 hover:shadow-md hover:-translate-y-0.5 rounded-2xl p-4 flex items-center justify-between transition-all shadow-sm"
            >
              <div>
                <span className="text-xs font-semibold text-[#767676]">{kpi.title}</span>
                <div className="text-2xl font-bold text-[#1B1B2F] tracking-tight mt-1">
                  {loading ? "..." : kpi.value}
                </div>
                <div className="text-[11px] text-[#767676] mt-0.5">{kpi.description}</div>
              </div>
              <div className={`p-2.5 rounded-xl ${kpi.chipBg} ${kpi.chipText}`}>
                <Icon className="h-5 w-5" />
              </div>
            </Link>
          );
        })}
      </div>

      {/* Inventory Health + Supplier Mix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h2 className="text-sm font-bold text-[#1B1B2F] mb-4">Inventory Health</h2>
          <Donut
            centerLabel="Total Products"
            centerValue={(stats?.total_products ?? 0).toLocaleString()}
            segments={[
              { label: "In Stock", value: stats?.in_stock_products ?? 0, color: "#059669" },
              { label: "Out of Stock", value: stats?.out_of_stock_products ?? 0, color: "#E11D48" },
            ]}
          />
        </div>

        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h2 className="text-sm font-bold text-[#1B1B2F] mb-4">Catalog by Supplier</h2>
          <div className="space-y-3">
            {supplierMix.length === 0 && (
              <p className="text-xs text-[#767676]">No supplier catalog data yet.</p>
            )}
            {supplierMix.map((s, i) => (
              <div key={s.id}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-semibold text-[#1B1B2F]">{s.name}</span>
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
        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-[#6C5DD3]/10 text-[#6C5DD3]">
                <Truck className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#1B1B2F]">Your Wholesale Suppliers</h2>
                <p className="text-xs text-[#767676]">Live feeds from connected distributor warehouses.</p>
              </div>
            </div>
            <Link
              href="/suppliers"
              className="text-xs font-semibold text-[#6C5DD3] hover:text-[#5b4bd1] flex items-center gap-1"
            >
              <span>Manage</span>
              <ArrowRight className="h-3 w-3" />
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
                    <div className="text-xs font-semibold text-[#1B1B2F]">{sup.name}</div>
                    <div className="text-[11px] text-[#767676]">
                      {sup.status === "HEALTHY" ? "Connected & Up to date" : "Needs Attention"}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-[#1B1B2F]">{sup.product_count} items</div>
                  <span className="text-[10px] text-[#767676]">Available</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Online Stores */}
        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-teal-50 text-teal-600">
                <Store className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#1B1B2F]">Your Online Stores</h2>
                <p className="text-xs text-[#767676]">Active listings on customer-facing marketplaces.</p>
              </div>
            </div>
            <Link
              href="/marketplaces"
              className="text-xs font-semibold text-teal-700 hover:text-teal-800 flex items-center gap-1"
            >
              <span>Connect More</span>
              <ArrowRight className="h-3 w-3" />
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
                    <div className="text-xs font-semibold text-[#1B1B2F]">{mkt.name}</div>
                    <div className={`text-[11px] font-medium ${
                      mkt.status === "HEALTHY" ? "text-emerald-700" : mkt.status === "IDLE" ? "text-gray-500" : "text-rose-700"
                    }`}>
                      {mkt.status === "HEALTHY" ? "Active & Selling" : mkt.status === "IDLE" ? "Not active" : "Needs Attention"}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-[#1B1B2F]">{mkt.listing_count} offers</div>
                  <span className="text-[10px] text-[#767676]">Live in store</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications & Plain English Alerts */}
      <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-rose-50 text-rose-600">
              <AlertCircle className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#1B1B2F]">Alerts & Notifications</h2>
              <p className="text-xs text-[#767676]">Operational events requiring your attention.</p>
            </div>
          </div>
          <Link href="/logs" className="text-xs font-semibold text-[#6C5DD3] hover:text-[#5b4bd1] flex items-center gap-1">
            <span>View History</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {stats?.recent_errors && stats.recent_errors.length > 0 ? (
          <div className="space-y-2.5">
            {stats.recent_errors.map((err) => (
              <div key={err.id} className="p-3 bg-rose-50/70 border border-rose-100 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-rose-100 text-rose-800">
                      Attention
                    </span>
                    <span className="text-[11px] text-[#767676]" suppressHydrationWarning>{new Date(err.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-[#1B1B2F] font-semibold mt-1">
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
          <div className="text-center py-6 text-[#767676] text-xs bg-gray-50 rounded-xl border border-gray-100">
            <CheckCircle2 className="h-7 w-7 text-emerald-600 mx-auto mb-1.5" />
            <div className="font-semibold text-[#1B1B2F]">All systems are running smoothly</div>
            <p className="text-[11px] text-[#767676] mt-0.5">All wholesale suppliers are connected, and all store listings are in sync.</p>
          </div>
        )}
      </div>
    </div>
  );
}
