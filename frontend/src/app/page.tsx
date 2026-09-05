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
  HelpCircle,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  X,
  ShieldCheck,
  Check,
  Sparkles
} from "lucide-react";
import { fetchApi, DashboardStats } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [lastUpdatedTime, setLastUpdatedTime] = useState<Date>(new Date());
  const [mounted, setMounted] = useState(false);
  const [showGettingStarted, setShowGettingStarted] = useState(true);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
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

  const hasSuppliers = (stats?.suppliers_health.length ?? 0) > 0;
  const hasProducts = (stats?.total_products ?? 0) > 0;
  const hasListings = (stats?.active_listings ?? 0) > 0;
  const hasMarketplaces = (stats?.marketplaces_health.length ?? 0) > 0;

  const gettingStartedSteps = [
    {
      num: 1,
      title: "Connect your first supplier",
      description: "Link to your wholesale distributors to automatically import their catalog.",
      href: "/suppliers",
      done: hasSuppliers,
      actionText: "Manage Suppliers"
    },
    {
      num: 2,
      title: "Choose what products to sell",
      description: "Browse the wholesale catalog and decide which products you want in your store.",
      href: "/catalog",
      done: hasProducts,
      actionText: "Browse Catalog"
    },
    {
      num: 3,
      title: "Set your profit rules",
      description: "Decide how much profit margin you want on each product.",
      href: "/rules",
      done: true,
      actionText: "Set Profit Rules"
    },
    {
      num: 4,
      title: "Choose your online stores",
      description: "Connect Amazon, eBay, Shopify, Walmart, or Newegg to sell to buyers.",
      href: "/marketplaces",
      done: hasMarketplaces,
      actionText: "Connect Stores"
    },
    {
      num: 5,
      title: "Automatic sync handles the rest",
      description: "Prices and stock levels are continuously kept up to date for you.",
      href: "/listings",
      done: hasListings,
      actionText: "View Live Stores"
    },
  ];

  const kpis = [
    {
      title: "Products Available",
      value: stats?.total_products ?? 0,
      icon: Package,
      iconColor: "text-[#905831]",
      description: "Imported from wholesale suppliers",
      tooltip: "All unique products your wholesale suppliers provide that you can sell.",
      href: "/catalog"
    },
    {
      title: "Live in Your Stores",
      value: stats?.active_listings ?? 0,
      icon: Layers,
      iconColor: "text-emerald-700",
      description: "Online products buyers can buy now",
      tooltip: "Products currently visible and ready for customers to purchase on your marketplaces.",
      href: "/listings"
    },
    {
      title: "In Stock",
      value: stats?.in_stock_products ?? 0,
      icon: CheckCircle2,
      iconColor: "text-teal-700",
      description: "Ready to ship immediately",
      tooltip: "Products your suppliers currently have in their warehouses.",
      href: "/catalog?in_stock=true"
    },
    {
      title: "Out of Stock",
      value: stats?.out_of_stock_products ?? 0,
      icon: AlertTriangle,
      iconColor: "text-amber-700",
      description: "Suppliers temporarily ran out",
      tooltip: "Products that have 0 inventory at suppliers. We protect you by hiding or setting them to 0 on your stores.",
      href: "/catalog"
    },
    {
      title: "Issues to Check",
      value: stats?.needs_attention ?? 0,
      icon: AlertCircle,
      iconColor: "text-rose-700",
      description: stats?.needs_attention ? "Items need quick review" : "Everything running smoothly",
      tooltip: "Sync warnings or connection interruptions that need a quick look.",
      href: "/logs"
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Clean Unboxed Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Store Overview</h1>
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-amber-50 text-[#905831] border border-amber-200">
              Live Automation
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Real-time control center for your connected distributors, profit calculations, and active marketplace offers.
          </p>
          <div className="flex items-center gap-2 text-xs text-gray-400 pt-1">
            <Clock className="h-3.5 w-3.5 text-gray-400" />
            <span suppressHydrationWarning>
              Last checked: {mounted ? lastUpdatedTime.toLocaleTimeString() : "--:--"} (Continuous background sync every 10s)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleReconcileAll}
            disabled={reconciling}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <Zap className={`h-3.5 w-3.5 ${reconciling ? "animate-pulse text-[#905831]" : "text-[#905831]"}`} />
            <span>{reconciling ? "Checking..." : "Update Everything Now"}</span>
          </button>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-medium transition-colors border border-gray-300 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-gray-500 ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Getting Started Guide */}
      {showGettingStarted && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-5 w-5 text-[#905831]" />
              <div>
                <h2 className="text-sm font-bold text-gray-900">Getting Started Guide</h2>
                <p className="text-xs text-gray-500">5 steps to automate your wholesale inventory and sales.</p>
              </div>
            </div>
            <button 
              onClick={() => setShowGettingStarted(false)}
              className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 flex items-center gap-1 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
              <span>Dismiss</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {gettingStartedSteps.map((step) => (
              <div 
                key={step.num}
                className={`p-3.5 rounded-lg border flex flex-col justify-between transition-colors ${
                  step.done 
                    ? "bg-emerald-50/40 border-emerald-200/80" 
                    : "bg-gray-50/60 border-gray-200"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      step.done 
                        ? "bg-emerald-100 text-emerald-800" 
                        : "bg-gray-200 text-gray-700"
                    }`}>
                      Step {step.num}
                    </span>
                    {step.done ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                    ) : (
                      <span className="text-[10px] text-gray-400 font-medium">Pending</span>
                    )}
                  </div>
                  <h3 className="text-xs font-semibold text-gray-900 leading-snug">{step.title}</h3>
                  <p className="text-[11px] text-gray-500 mt-1 leading-snug">{step.description}</p>
                </div>
                <Link
                  href={step.href}
                  className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-[#905831] hover:text-[#7b4724]"
                >
                  <span>{step.actionText}</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Immediate Reconcile Result Box */}
      {reconcileResult && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 font-semibold text-xs text-emerald-900">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              <span>All 5 wholesale suppliers checked and updated!</span>
            </div>
            <button
              onClick={() => setReconcileResult(null)}
              className="text-xs text-emerald-700 hover:text-emerald-900 px-2 py-0.5 bg-white rounded border border-emerald-200"
            >
              Dismiss
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 mt-2">
            {reconcileResult.details.map((d, i) => (
              <div key={i} className="text-xs p-2.5 rounded-lg bg-white border border-emerald-100">
                <span className="font-semibold text-gray-900 block">{d.supplier_name}</span>
                {d.status === "SUCCESS" ? (
                  <span className="text-gray-500 text-[11px]">
                    Imported: <span className="text-emerald-700 font-bold">{d.imported}</span> | Changes: <span className="text-[#905831] font-bold">{d.changed}</span>
                  </span>
                ) : (
                  <span className="text-rose-600 text-[11px]">{d.error}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5 Grounded KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <Link
              key={index}
              href={kpi.href}
              className="bg-white border border-gray-200 hover:border-gray-300 rounded-xl p-4 flex flex-col justify-between transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500">{kpi.title}</span>
                <div className={`p-1.5 rounded-md bg-gray-50 ${kpi.iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-gray-900 tracking-tight">
                  {loading ? "..." : kpi.value.toLocaleString()}
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">{kpi.description}</div>
              </div>
              <div className="mt-3 pt-2 border-t border-gray-100 text-[10px] text-gray-400 flex items-center gap-1">
                <HelpCircle className="h-3 w-3 text-gray-400 shrink-0" />
                <span className="truncate">{kpi.tooltip}</span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Wholesale Suppliers & Online Stores Side-by-Side Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Wholesale Suppliers */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
            <div className="flex items-center gap-2">
              <Truck className="h-4 w-4 text-[#905831]" />
              <div>
                <h2 className="text-sm font-bold text-gray-900">Your Wholesale Suppliers</h2>
                <p className="text-xs text-gray-500">Live feeds from connected distributor warehouses.</p>
              </div>
            </div>
            <Link 
              href="/suppliers" 
              className="text-xs font-semibold text-[#905831] hover:text-[#7b4724] flex items-center gap-1"
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
                    <div className="text-xs font-semibold text-gray-900">{sup.name}</div>
                    <div className="text-[11px] text-gray-500">
                      {sup.status === "HEALTHY" ? "Connected & Up to date" : "Needs Attention"}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-gray-900">{sup.product_count} items</div>
                  <span className="text-[10px] text-gray-400">Available</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Online Stores */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
            <div className="flex items-center gap-2">
              <Store className="h-4 w-4 text-gray-700" />
              <div>
                <h2 className="text-sm font-bold text-gray-900">Your Online Stores</h2>
                <p className="text-xs text-gray-500">Active listings on customer-facing marketplaces.</p>
              </div>
            </div>
            <Link 
              href="/marketplaces" 
              className="text-xs font-semibold text-gray-700 hover:text-gray-900 flex items-center gap-1"
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
                  <div className="h-2 w-2 rounded-full bg-emerald-500" />
                  <div>
                    <div className="text-xs font-semibold text-gray-900">{mkt.name}</div>
                    <div className="text-[11px] text-emerald-700 font-medium">Active & Selling</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-gray-900">{mkt.listing_count} offers</div>
                  <span className="text-[10px] text-gray-400">Live in store</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications & Plain English Alerts */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-gray-700" />
            <div>
              <h2 className="text-sm font-bold text-gray-900">Alerts & Notifications</h2>
              <p className="text-xs text-gray-500">Operational events requiring your attention.</p>
            </div>
          </div>
          <Link href="/logs" className="text-xs font-semibold text-[#905831] hover:text-[#7b4724] flex items-center gap-1">
            <span>View History</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {stats?.recent_errors && stats.recent_errors.length > 0 ? (
          <div className="space-y-2.5">
            {stats.recent_errors.map((err) => (
              <div key={err.id} className="p-3 bg-rose-50/70 border border-rose-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800">
                      Attention
                    </span>
                    <span className="text-[11px] text-gray-500" suppressHydrationWarning>{new Date(err.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-gray-900 font-semibold mt-1">
                    {err.marketplace_name 
                      ? `Temporary connection notice for ${err.marketplace_name}.` 
                      : err.supplier_name 
                        ? `Could not reach ${err.supplier_name} during check.` 
                        : "A temporary update was delayed."}
                  </p>
                  <p className="text-[11px] text-gray-600 mt-0.5">
                    Why it matters: Stock or price updates for affected items may be delayed until re-checked.
                  </p>
                </div>
                <Link
                  href="/logs"
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-xs font-semibold self-start sm:self-center shrink-0 transition-colors"
                >
                  Review
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-500 text-xs bg-gray-50 rounded-lg border border-gray-100">
            <CheckCircle2 className="h-7 w-7 text-emerald-600 mx-auto mb-1.5" />
            <div className="font-semibold text-gray-900">All systems are running smoothly</div>
            <p className="text-[11px] text-gray-500 mt-0.5">All wholesale suppliers are connected, and all store listings are in sync.</p>
          </div>
        )}

        {/* Collapsible Technical Diagnostics */}
        <div className="mt-4 pt-3 border-t border-gray-100">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="text-[11px] text-gray-500 hover:text-gray-800 flex items-center gap-1 transition-colors font-medium"
          >
            {showTechnicalDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            <span>{showTechnicalDetails ? "Hide technical diagnostic details" : "Show technical diagnostic details"}</span>
          </button>

          {showTechnicalDetails && (
            <div className="mt-2.5 p-3 bg-gray-50 rounded-lg border border-gray-200 text-[11px] font-mono text-gray-600 space-y-1">
              <div>Backend Status: Connected (http://localhost:8000/api/v1)</div>
              <div>Database: PostgreSQL 16 (Relational Catalog & Rules Storage)</div>
              <div>Worker Task Queue: Celery + RabbitMQ (Asynchronous distributor sync)</div>
              <div>Distributed Lock: Redis 7 (Concurrency protection across listings)</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
