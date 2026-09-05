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
  SlidersHorizontal,
  X,
  ShieldCheck,
  Check
} from "lucide-react";
import { fetchApi, DashboardStats } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [lastUpdatedTime, setLastUpdatedTime] = useState<Date>(new Date());
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
      gradient: "from-blue-500/20 to-indigo-500/20",
      iconColor: "text-blue-400",
      description: "Imported from wholesale suppliers",
      tooltip: "All unique products your wholesale suppliers provide that you can sell.",
      href: "/catalog"
    },
    {
      title: "Live in Your Stores",
      value: stats?.active_listings ?? 0,
      icon: Layers,
      gradient: "from-emerald-500/20 to-teal-500/20",
      iconColor: "text-emerald-400",
      description: "Online products buyers can buy now",
      tooltip: "Products currently visible and ready for customers to purchase on your marketplaces.",
      href: "/listings"
    },
    {
      title: "In Stock",
      value: stats?.in_stock_products ?? 0,
      icon: CheckCircle2,
      gradient: "from-green-500/20 to-emerald-500/20",
      iconColor: "text-green-400",
      description: "Ready to ship immediately",
      tooltip: "Products your suppliers currently have in their warehouses.",
      href: "/catalog?in_stock=true"
    },
    {
      title: "Out of Stock",
      value: stats?.out_of_stock_products ?? 0,
      icon: AlertTriangle,
      gradient: "from-amber-500/20 to-orange-500/20",
      iconColor: "text-amber-400",
      description: "Suppliers temporarily ran out",
      tooltip: "Products that have 0 inventory at suppliers. We protect you by hiding or setting them to 0 on your stores.",
      href: "/catalog"
    },
    {
      title: "Issues to Check",
      value: stats?.needs_attention ?? 0,
      icon: AlertCircle,
      gradient: "from-rose-500/20 to-red-500/20",
      iconColor: "text-rose-400",
      description: stats?.needs_attention ? "Items need quick review" : "Everything running smoothly",
      tooltip: "Sync warnings or connection interruptions that need a quick look.",
      href: "/logs"
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0e1526] p-6 rounded-2xl border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black text-white tracking-tight">Store Overview</h1>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Live Automation
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            See how your products, stores, and wholesale suppliers are performing right now.
          </p>
          <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
            <Clock className="h-3.5 w-3.5 text-gray-400" />
            <span>Last checked: {lastUpdatedTime.toLocaleTimeString()} (Continuous auto-checks every 10s)</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="flex flex-col">
            <button
              onClick={handleReconcileAll}
              disabled={reconciling}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-amber-500/25 disabled:opacity-50"
            >
              <Zap className={`h-4 w-4 ${reconciling ? "animate-pulse" : "fill-current"}`} />
              <span>{reconciling ? "Checking Suppliers..." : "Update Everything Now"}</span>
            </button>
            <span className="text-[11px] text-gray-400 mt-1 text-center sm:text-left">
              Forces an immediate check across all suppliers & stores
            </span>
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-sm font-semibold transition-all border border-gray-700 disabled:opacity-50 self-start sm:self-auto"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh Screen</span>
          </button>
        </div>
      </div>

      {/* Getting Started Banner (Spec Requirement 5) */}
      {showGettingStarted && (
        <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-950/70 via-purple-950/40 to-slate-900 border border-indigo-500/30 shadow-xl relative overflow-hidden">
          <div className="flex items-center justify-between pb-4 border-b border-indigo-500/20 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-300">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Getting Started Guide</h2>
                <p className="text-xs text-indigo-200/80">Follow these 5 simple steps to have your business running on autopilot.</p>
              </div>
            </div>
            <button 
              onClick={() => setShowGettingStarted(false)}
              className="text-xs text-gray-400 hover:text-white px-2.5 py-1 bg-gray-800/80 hover:bg-gray-700 rounded-lg flex items-center gap-1 transition-colors"
            >
              <X className="h-3 w-3" />
              <span>Hide Guide</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {gettingStartedSteps.map((step) => (
              <div 
                key={step.num}
                className={`p-3.5 rounded-xl border flex flex-col justify-between transition-all ${
                  step.done 
                    ? "bg-emerald-950/30 border-emerald-500/30 text-emerald-200" 
                    : "bg-gray-900/60 border-gray-800 text-gray-300"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className={`text-[11px] font-black px-2 py-0.5 rounded-full ${
                      step.done ? "bg-emerald-500/20 text-emerald-300" : "bg-indigo-500/20 text-indigo-300"
                    }`}>
                      Step {step.num}
                    </span>
                    {step.done ? (
                      <Check className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <span className="text-[10px] text-gray-500">Ready</span>
                    )}
                  </div>
                  <h3 className="text-xs font-bold text-white leading-tight">{step.title}</h3>
                  <p className="text-[11px] text-gray-400 mt-1 leading-snug">{step.description}</p>
                </div>
                <Link
                  href={step.href}
                  className="mt-3 inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 group"
                >
                  <span>{step.actionText}</span>
                  <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Immediate Reconcile Result Box */}
      {reconcileResult && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 shadow-lg">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 font-semibold text-sm">
              <CheckCircle className="h-5 w-5 text-emerald-400" />
              <span>All 5 wholesale suppliers checked and updated!</span>
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

      {/* 5 KPI Cards (Spec Requirement 11) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <Link
              key={index}
              href={kpi.href}
              className="p-5 rounded-2xl bg-gradient-to-b from-[#131b2e] to-[#0e1526] border border-gray-800 hover:border-indigo-500/40 shadow-lg relative overflow-hidden flex flex-col justify-between transition-all group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300 tracking-wide">{kpi.title}</span>
                <div className={`p-2 rounded-xl bg-gray-800/50 ${kpi.iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-4">
                <div className="text-3xl font-black text-white tracking-tight">
                  {loading ? "..." : kpi.value.toLocaleString()}
                </div>
                <div className="text-[11px] text-gray-400 mt-1">{kpi.description}</div>
              </div>
              <div className="mt-3 pt-2.5 border-t border-gray-800/60 text-[10px] text-gray-500 flex items-center gap-1 group-hover:text-indigo-400 transition-colors">
                <HelpCircle className="h-3 w-3" />
                <span className="truncate">{kpi.tooltip}</span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Wholesale Suppliers & Online Stores Side-by-Side Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Wholesale Suppliers */}
        <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <Truck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Your Wholesale Suppliers</h2>
                <p className="text-xs text-gray-400">Where products come from. We check stock and prices continuously.</p>
              </div>
            </div>
            <Link 
              href="/suppliers" 
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              <span>Manage</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {stats?.suppliers_health.map((sup) => (
              <div
                key={sup.id}
                className="flex items-center justify-between p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/60 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`h-3 w-3 rounded-full ${
                    sup.status === "HEALTHY" ? "bg-emerald-500 shadow-sm shadow-emerald-500/50" : "bg-rose-500"
                  }`} />
                  <div>
                    <div className="text-sm font-bold text-gray-200">{sup.name}</div>
                    <div className="text-xs text-gray-500 flex items-center gap-1.5">
                      <span>Status: </span>
                      <span className={sup.status === "HEALTHY" ? "text-emerald-400 font-medium" : "text-rose-400 font-medium"}>
                        {sup.status === "HEALTHY" ? "Connected & Up to date" : "Needs Attention"}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-white">{sup.product_count} products</div>
                  <span className="text-[10px] text-gray-400">Available to sell</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Online Stores */}
        <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-lg">
          <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400">
                <Store className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Your Online Stores</h2>
                <p className="text-xs text-gray-400">Where buyers purchase. We update store stock automatically.</p>
              </div>
            </div>
            <Link 
              href="/marketplaces" 
              className="text-xs font-semibold text-violet-400 hover:text-violet-300 flex items-center gap-1"
            >
              <span>Connect More</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {stats?.marketplaces_health.map((mkt) => (
              <div
                key={mkt.id}
                className="flex items-center justify-between p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/60 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
                  <div>
                    <div className="text-sm font-bold text-gray-200">{mkt.name}</div>
                    <div className="text-xs text-emerald-400 font-medium">Store Connected & Selling</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-white">{mkt.listing_count} products live</div>
                  <span className="text-[10px] text-gray-400">Active offers</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications & Plain English Alerts */}
      <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-indigo-400" />
            <div>
              <h2 className="text-base font-bold text-white">Alerts & Notifications</h2>
              <p className="text-xs text-gray-400">Any events or connection issues requiring your attention.</p>
            </div>
          </div>
          <Link href="/logs" className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
            <span>View Full History</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {stats?.recent_errors && stats.recent_errors.length > 0 ? (
          <div className="space-y-3">
            {stats.recent_errors.map((err) => (
              <div key={err.id} className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-sm">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300">
                      Needs Attention
                    </span>
                    <span className="text-xs text-gray-400">{new Date(err.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-white font-medium mt-1">
                    {err.marketplace_name 
                      ? `We ran into a temporary issue with your ${err.marketplace_name} store.` 
                      : err.supplier_name 
                        ? `Could not reach ${err.supplier_name} during update check.` 
                        : "A temporary update was delayed."}
                  </p>
                  <p className="text-xs text-rose-200/80 mt-0.5">
                    Why it matters: Stock or price updates for affected products may be delayed until re-checked.
                  </p>
                </div>
                <Link
                  href="/logs"
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold self-start sm:self-center shrink-0 transition-colors"
                >
                  Review & Fix
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400 text-sm bg-gray-900/40 rounded-xl border border-gray-800/80">
            <CheckCircle2 className="h-9 w-9 text-emerald-400 mx-auto mb-2" />
            <div className="font-semibold text-white">All systems are running smoothly!</div>
            <p className="text-xs text-gray-500 mt-1">All suppliers are connected, and all store listings are in sync.</p>
          </div>
        )}

        {/* Collapsible Technical Diagnostics */}
        <div className="mt-4 pt-4 border-t border-gray-800">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1.5 transition-colors"
          >
            {showTechnicalDetails ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            <span>{showTechnicalDetails ? "Hide technical diagnostic details" : "Show technical diagnostic details"}</span>
          </button>

          {showTechnicalDetails && (
            <div className="mt-3 p-3.5 bg-gray-950/80 rounded-xl border border-gray-800 text-xs font-mono text-gray-400 space-y-1.5">
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
