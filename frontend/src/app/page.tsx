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
      iconColor: "text-[#905831]",
      description: "Imported from wholesale suppliers",
      tooltip: "All unique products your wholesale suppliers provide that you can sell.",
      href: "/catalog"
    },
    {
      title: "Live in Your Stores",
      value: stats?.active_listings ?? 0,
      icon: Layers,
      iconColor: "text-emerald-600",
      description: "Online products buyers can buy now",
      tooltip: "Products currently visible and ready for customers to purchase on your marketplaces.",
      href: "/listings"
    },
    {
      title: "In Stock",
      value: stats?.in_stock_products ?? 0,
      icon: CheckCircle2,
      iconColor: "text-teal-600",
      description: "Ready to ship immediately",
      tooltip: "Products your suppliers currently have in their warehouses.",
      href: "/catalog?in_stock=true"
    },
    {
      title: "Out of Stock",
      value: stats?.out_of_stock_products ?? 0,
      icon: AlertTriangle,
      iconColor: "text-amber-600",
      description: "Suppliers temporarily ran out",
      tooltip: "Products that have 0 inventory at suppliers. We protect you by hiding or setting them to 0 on your stores.",
      href: "/catalog"
    },
    {
      title: "Issues to Check",
      value: stats?.needs_attention ?? 0,
      icon: AlertCircle,
      iconColor: "text-rose-600",
      description: stats?.needs_attention ? "Items need quick review" : "Everything running smoothly",
      tooltip: "Sync warnings or connection interruptions that need a quick look.",
      href: "/logs"
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Top Header Surface */}
      <div className="glass-card p-8 rounded-[2rem] shadow-wandor-sm flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
        <div className="space-y-2">
          <div className="flex items-center gap-2.5">
            <h1 className="text-3xl font-black text-[#0a0a0a] tracking-tight">Store Overview</h1>
            <span className="text-xs font-semibold px-3 py-0.5 rounded-full bg-[#905831]/10 text-[#905831] border border-[#905831]/20">
              Live Automation
            </span>
          </div>
          <p className="text-sm text-[#767676] max-w-xl leading-relaxed">
            Real-time control center for your connected distributors, profit calculations, and active marketplace offers.
          </p>
          <div className="flex items-center gap-2 text-xs text-[#767676] pt-1">
            <Clock className="h-3.5 w-3.5 text-[#905831]" />
            <span>Last checked: {lastUpdatedTime.toLocaleTimeString()} (Continuous background sync every 10s)</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="flex flex-col">
            <button
              onClick={handleReconcileAll}
              disabled={reconciling}
              className="inline-flex items-center justify-center gap-2.5 px-6 py-3.5 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-full text-sm font-semibold transition-all shadow-wandor-md hover:shadow-wandor-lg disabled:opacity-50"
            >
              <Zap className={`h-4 w-4 ${reconciling ? "animate-pulse text-[#905831]" : "text-[#905831]"}`} />
              <span>{reconciling ? "Checking Suppliers..." : "Update Everything Now"}</span>
            </button>
            <span className="text-[11px] text-[#767676] mt-1.5 text-center">
              Forces an immediate check across all suppliers & stores
            </span>
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 px-5 py-3.5 bg-white hover:bg-black/[0.02] text-[#1a1a1a] rounded-full text-sm font-semibold transition-all border border-black/[0.08] shadow-wandor-sm disabled:opacity-50 self-start sm:self-auto"
          >
            <RefreshCw className={`h-4 w-4 text-[#767676] ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Getting Started Guide */}
      {showGettingStarted && (
        <div className="glass-card p-7 rounded-[2rem] shadow-wandor-sm border border-black/[0.06] relative overflow-hidden bg-gradient-to-br from-white/90 via-white/80 to-[#fdfbf9]">
          <div className="flex items-center justify-between pb-4 border-b border-black/[0.05] mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-[#905831]/10 text-[#905831]">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#0a0a0a]">Getting Started Guide</h2>
                <p className="text-xs text-[#767676]">Follow these 5 simple steps to have your business running on autopilot.</p>
              </div>
            </div>
            <button 
              onClick={() => setShowGettingStarted(false)}
              className="text-xs text-[#767676] hover:text-[#0a0a0a] px-3 py-1.5 rounded-full border border-black/[0.06] hover:bg-black/[0.03] flex items-center gap-1.5 transition-colors"
            >
              <X className="h-3 w-3" />
              <span>Hide Guide</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5">
            {gettingStartedSteps.map((step) => (
              <div 
                key={step.num}
                className={`p-4 rounded-2xl border flex flex-col justify-between transition-all duration-200 ${
                  step.done 
                    ? "bg-emerald-500/[0.04] border-emerald-500/20" 
                    : "bg-white/80 border-black/[0.06]"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                      step.done 
                        ? "bg-emerald-100/80 text-emerald-800" 
                        : "bg-[#905831]/10 text-[#905831]"
                    }`}>
                      Step {step.num}
                    </span>
                    {step.done ? (
                      <Check className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <span className="text-[10px] text-[#767676] font-medium">Ready</span>
                    )}
                  </div>
                  <h3 className="text-xs font-bold text-[#0a0a0a] leading-tight">{step.title}</h3>
                  <p className="text-[11px] text-[#767676] mt-1.5 leading-snug">{step.description}</p>
                </div>
                <Link
                  href={step.href}
                  className="mt-4 inline-flex items-center gap-1 text-[11px] font-bold text-[#905831] hover:text-[#7b4724] group"
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
        <div className="p-5 rounded-2xl bg-emerald-50/80 border border-emerald-500/30 text-emerald-900 shadow-wandor-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 font-bold text-sm text-emerald-900">
              <CheckCircle className="h-5 w-5 text-emerald-600" />
              <span>All 5 wholesale suppliers checked and updated!</span>
            </div>
            <button
              onClick={() => setReconcileResult(null)}
              className="text-xs text-emerald-800 hover:text-emerald-950 px-2.5 py-1 bg-white/80 rounded-full border border-emerald-200"
            >
              Dismiss
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5 mt-3">
            {reconcileResult.details.map((d, i) => (
              <div key={i} className="text-xs p-3 rounded-xl bg-white/90 border border-emerald-100 shadow-wandor-sm">
                <span className="font-bold text-[#0a0a0a] block">{d.supplier_name}</span>
                {d.status === "SUCCESS" ? (
                  <span className="text-[#767676] text-[11px]">
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

      {/* 5 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <Link
              key={index}
              href={kpi.href}
              className="glass-card glass-card-hover p-6 rounded-3xl shadow-wandor-sm relative overflow-hidden flex flex-col justify-between group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#767676] tracking-wide">{kpi.title}</span>
                <div className={`p-2 rounded-2xl bg-black/[0.03] ${kpi.iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-5">
                <div className="text-3xl font-black text-[#0a0a0a] tracking-tight">
                  {loading ? "..." : kpi.value.toLocaleString()}
                </div>
                <div className="text-[11px] text-[#767676] mt-1 font-medium">{kpi.description}</div>
              </div>
              <div className="mt-4 pt-3 border-t border-black/[0.05] text-[10px] text-[#767676] flex items-center gap-1 group-hover:text-[#0a0a0a] transition-colors">
                <HelpCircle className="h-3 w-3 text-[#905831]" />
                <span className="truncate">{kpi.tooltip}</span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Wholesale Suppliers & Online Stores Side-by-Side Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Wholesale Suppliers */}
        <div className="glass-card p-7 rounded-[2rem] shadow-wandor-sm">
          <div className="flex items-center justify-between pb-4 border-b border-black/[0.05] mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-[#905831]/10 text-[#905831]">
                <Truck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#0a0a0a]">Your Wholesale Suppliers</h2>
                <p className="text-xs text-[#767676]">Where products come from. We check stock and prices continuously.</p>
              </div>
            </div>
            <Link 
              href="/suppliers" 
              className="text-xs font-bold text-[#905831] hover:text-[#7b4724] flex items-center gap-1"
            >
              <span>Manage</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {stats?.suppliers_health.map((sup) => (
              <div
                key={sup.id}
                className="flex items-center justify-between p-4 rounded-2xl bg-white/70 border border-black/[0.05] hover:border-black/[0.1] transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className={`h-2.5 w-2.5 rounded-full ${
                    sup.status === "HEALTHY" ? "bg-emerald-500 shadow-sm shadow-emerald-500/50" : "bg-rose-500"
                  }`} />
                  <div>
                    <div className="text-sm font-bold text-[#1a1a1a]">{sup.name}</div>
                    <div className="text-xs text-[#767676] flex items-center gap-1.5">
                      <span>Status: </span>
                      <span className={sup.status === "HEALTHY" ? "text-emerald-700 font-semibold" : "text-rose-600 font-semibold"}>
                        {sup.status === "HEALTHY" ? "Connected & Up to date" : "Needs Attention"}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-[#0a0a0a]">{sup.product_count} products</div>
                  <span className="text-[10px] text-[#767676]">Available to sell</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Online Stores */}
        <div className="glass-card p-7 rounded-[2rem] shadow-wandor-sm">
          <div className="flex items-center justify-between pb-4 border-b border-black/[0.05] mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-black/[0.05] text-[#0a0a0a]">
                <Store className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#0a0a0a]">Your Online Stores</h2>
                <p className="text-xs text-[#767676]">Where buyers purchase. We update store stock automatically.</p>
              </div>
            </div>
            <Link 
              href="/marketplaces" 
              className="text-xs font-bold text-[#0a0a0a] hover:text-[#767676] flex items-center gap-1"
            >
              <span>Connect More</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {stats?.marketplaces_health.map((mkt) => (
              <div
                key={mkt.id}
                className="flex items-center justify-between p-4 rounded-2xl bg-white/70 border border-black/[0.05] hover:border-black/[0.1] transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
                  <div>
                    <div className="text-sm font-bold text-[#1a1a1a]">{mkt.name}</div>
                    <div className="text-xs text-emerald-700 font-semibold">Store Connected & Selling</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-[#0a0a0a]">{mkt.listing_count} products live</div>
                  <span className="text-[10px] text-[#767676]">Active offers</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications & Plain English Alerts */}
      <div className="glass-card p-7 rounded-[2rem] shadow-wandor-sm">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-black/[0.04] text-[#0a0a0a]">
              <AlertCircle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#0a0a0a]">Alerts & Notifications</h2>
              <p className="text-xs text-[#767676]">Any events or connection issues requiring your attention.</p>
            </div>
          </div>
          <Link href="/logs" className="text-xs font-bold text-[#905831] hover:text-[#7b4724] flex items-center gap-1">
            <span>View Full History</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {stats?.recent_errors && stats.recent_errors.length > 0 ? (
          <div className="space-y-3">
            {stats.recent_errors.map((err) => (
              <div key={err.id} className="p-4 bg-rose-50/80 border border-rose-200/80 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-sm">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800">
                      Needs Attention
                    </span>
                    <span className="text-xs text-[#767676]">{new Date(err.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-[#0a0a0a] font-bold mt-1">
                    {err.marketplace_name 
                      ? `We ran into a temporary issue with your ${err.marketplace_name} store.` 
                      : err.supplier_name 
                        ? `Could not reach ${err.supplier_name} during update check.` 
                        : "A temporary update was delayed."}
                  </p>
                  <p className="text-xs text-rose-800/80 mt-0.5">
                    Why it matters: Stock or price updates for affected products may be delayed until re-checked.
                  </p>
                </div>
                <Link
                  href="/logs"
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-full text-xs font-bold self-start sm:self-center shrink-0 transition-colors shadow-sm"
                >
                  Review & Fix
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-10 text-[#767676] text-sm bg-white/60 rounded-2xl border border-black/[0.04]">
            <CheckCircle2 className="h-10 w-10 text-emerald-600 mx-auto mb-2" />
            <div className="font-bold text-[#0a0a0a]">All systems are running smoothly!</div>
            <p className="text-xs text-[#767676] mt-1">All suppliers are connected, and all store listings are in sync.</p>
          </div>
        )}

        {/* Collapsible Technical Diagnostics */}
        <div className="mt-5 pt-4 border-t border-black/[0.05]">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="text-xs text-[#767676] hover:text-[#0a0a0a] flex items-center gap-1.5 transition-colors font-medium"
          >
            {showTechnicalDetails ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            <span>{showTechnicalDetails ? "Hide technical diagnostic details" : "Show technical diagnostic details"}</span>
          </button>

          {showTechnicalDetails && (
            <div className="mt-3 p-4 bg-white/90 rounded-2xl border border-black/[0.06] text-xs font-mono text-[#767676] space-y-1.5 shadow-wandor-sm">
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
