"use client";

import React, { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Package,
  Truck,
  Clock,
  AlertTriangle,
  BarChart3,
  Tag,
} from "lucide-react";
import { fetchApi, AnalyticsSummary, SupplierScore } from "@/lib/api";
import Gauge from "@/components/Gauge";
import Sparkline from "@/components/Sparkline";

const PERIOD_OPTIONS = [
  { label: "7 Days", value: 7 },
  { label: "30 Days", value: 30 },
  { label: "90 Days", value: 90 },
];

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [scores, setScores] = useState<SupplierScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);

  const loadData = async (days: number) => {
    setLoading(true);
    try {
      const [summaryRes, scoresRes] = await Promise.all([
        fetchApi<AnalyticsSummary>(`/analytics/summary?days=${days}`),
        fetchApi<SupplierScore[]>(`/analytics/supplier-scores?days=${Math.max(days, 90)}`),
      ]);
      setSummary(summaryRes);
      setScores(scoresRes);
    } catch (err) {
      console.error("Failed to load analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(period);
  }, [period]);

  const revenueSeries = summary?.revenue_trend.map((p) => p.revenue) ?? [];
  const profitSeries = summary?.revenue_trend.map((p) => p.profit) ?? [];

  const comparison = summary?.comparison;

  const kpis = [
    {
      title: "Revenue",
      value: `$${(summary?.revenue_total ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      icon: DollarSign,
      iconColor: "text-emerald-700",
      description: `${summary?.order_count ?? 0} order(s) in window`,
      sparkline: revenueSeries,
      sparklineColor: "#059669",
      changePct: comparison?.revenue_change_pct ?? null,
    },
    {
      title: "Net Profit",
      value: `$${(summary?.net_profit_total ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      icon: TrendingUp,
      iconColor: (summary?.net_profit_total ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700",
      description: "Revenue minus supplier cost and marketplace fees",
      sparkline: profitSeries,
      sparklineColor: (summary?.net_profit_total ?? 0) >= 0 ? "#059669" : "#e11d48",
      changePct: comparison?.profit_change_pct ?? null,
    },
    {
      title: "Supplier Cost + Fees",
      value: `$${((summary?.cost_total ?? 0) + (summary?.fees_total ?? 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      icon: Package,
      iconColor: "text-amber-700",
      description: `$${(summary?.cost_total ?? 0).toFixed(2)} cost, $${(summary?.fees_total ?? 0).toFixed(2)} fees`,
      sparkline: null,
      sparklineColor: "#6C5DD3",
      changePct: null,
    },
  ];

  const maxTrendRevenue = Math.max(1, ...(summary?.revenue_trend.map((p) => p.revenue) ?? [1]));

  const maxSkuRevenue = Math.max(1, ...(summary?.top_skus.map((s) => s.revenue) ?? [1]));

  function heatColor(marginPct: number): string {
    if (marginPct < 0) return "bg-rose-50 border-rose-200 text-rose-800";
    if (marginPct < 15) return "bg-amber-50 border-amber-200 text-amber-800";
    return "bg-emerald-50 border-emerald-200 text-emerald-800";
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">
            Net profit, margin by supplier, top-performing SKUs, and supplier fulfillment performance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all shadow-sm ${
                period === opt.value
                  ? "bg-gray-900 text-white"
                  : "bg-white text-gray-500 hover:text-gray-900 border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Data caveat notice */}
      {summary && summary.order_count > 0 && summary.margin_by_supplier.length === 0 && (
        <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
          <span>Orders in this window haven&apos;t been routed to a supplier yet, so supplier cost is $0 and profit is overstated. Route them from the Orders page for accurate margins.</span>
        </div>
      )}

      {/* KPI Cards + Margin Gauge */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <div key={index} className="bg-white border border-gray-100 rounded-2xl shadow-sm p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500">{kpi.title}</span>
                <div className={`p-1.5 rounded-md bg-gray-50 ${kpi.iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="flex items-center gap-2">
                  <div className="text-2xl font-bold text-gray-900 tracking-tight">
                    {loading ? "..." : kpi.value}
                  </div>
                  {kpi.changePct !== null && kpi.changePct !== undefined && (
                    <span
                      className={`inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                        kpi.changePct >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
                      }`}
                      title={`vs. previous ${summary?.comparison?.previous_period_days ?? 0}-day period`}
                    >
                      {kpi.changePct >= 0 ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
                      {Math.abs(kpi.changePct).toFixed(1)}%
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">{kpi.description}</div>
              </div>
              {kpi.sparkline && kpi.sparkline.length > 1 && (
                <div className="mt-2 -mb-1">
                  <Sparkline values={kpi.sparkline} color={kpi.sparklineColor} height={24} />
                </div>
              )}
            </div>
          );
        })}

        {/* Gross Margin Gauge */}
        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-4 flex flex-col items-center justify-center">
          <span className="text-xs font-semibold text-gray-500 self-start mb-1">Gross Margin Health</span>
          <Gauge
            value={summary?.gross_margin_pct ?? 0}
            label="Gross Margin"
            sublabel="Net profit as % of revenue"
          />
        </div>
      </div>

      {/* Revenue Trend */}
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
        <div className="flex items-center gap-2 pb-3 border-b border-gray-100 mb-4">
          <BarChart3 className="h-4 w-4 text-[#6C5DD3]" />
          <div>
            <h2 className="text-sm font-bold text-gray-900">Revenue & Profit Trend</h2>
            <p className="text-xs text-gray-500">Daily revenue (bar) vs. net profit, over the selected window.</p>
          </div>
        </div>

        {!summary || summary.revenue_trend.length === 0 ? (
          <div className="text-center py-10 text-xs text-gray-500">No orders in this window yet.</div>
        ) : (
          <div className="flex items-end gap-1.5 h-40 overflow-x-auto pb-1">
            {summary.revenue_trend.map((point) => {
              const heightPct = Math.max(4, (point.revenue / maxTrendRevenue) * 100);
              const profitPositive = point.profit >= 0;
              return (
                <div key={point.date} className="flex flex-col items-center justify-end h-full min-w-[28px] group relative">
                  <div className="text-[9px] text-gray-400 mb-1 opacity-0 group-hover:opacity-100 transition-opacity absolute -top-5 whitespace-nowrap bg-gray-900 text-white px-1.5 py-0.5 rounded">
                    ${point.revenue.toFixed(2)} / {profitPositive ? "+" : ""}${point.profit.toFixed(2)}
                  </div>
                  <div
                    className={`w-4 rounded-t ${profitPositive ? "bg-[#6C5DD3]" : "bg-rose-400"}`}
                    style={{ height: `${heightPct}%` }}
                  />
                  <span className="text-[9px] text-gray-400 mt-1 rotate-0 whitespace-nowrap">
                    {point.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Margin by Supplier */}
        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
          <div className="flex items-center gap-2 pb-3 border-b border-gray-100 mb-3">
            <Truck className="h-4 w-4 text-[#6C5DD3]" />
            <div>
              <h2 className="text-sm font-bold text-gray-900">Gross Margin by Supplier</h2>
              <p className="text-xs text-gray-500">Revenue vs. cost for routed items, by supplier.</p>
            </div>
          </div>
          {summary?.margin_by_supplier.length === 0 ? (
            <div className="text-center py-8 text-xs text-gray-500">No routed items in this window yet.</div>
          ) : (
            <div className="space-y-2">
              {summary?.margin_by_supplier.map((s) => (
                <div key={s.supplier_id} className="flex items-center justify-between p-2.5 rounded-lg bg-gray-50 border border-gray-100">
                  <div>
                    <div className="text-xs font-semibold text-gray-900">{s.supplier_name}</div>
                    <div className="text-[11px] text-gray-500">${s.revenue.toFixed(2)} revenue, ${s.cost.toFixed(2)} cost</div>
                  </div>
                  <div className={`text-sm font-bold ${s.margin_pct >= 0 ? "text-emerald-700" : "text-rose-600"}`}>
                    {s.margin_pct.toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top SKUs Heatmap */}
        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
          <div className="flex items-center gap-2 pb-3 border-b border-gray-100 mb-3">
            <Package className="h-4 w-4 text-[#6C5DD3]" />
            <div>
              <h2 className="text-sm font-bold text-gray-900">Top-Performing SKUs</h2>
              <p className="text-xs text-gray-500">Tile size = revenue, color = profit margin.</p>
            </div>
          </div>
          {summary?.top_skus.length === 0 ? (
            <div className="text-center py-8 text-xs text-gray-500">No orders in this window yet.</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {summary?.top_skus.map((sku) => {
                const marginPct = sku.revenue > 0 ? (sku.profit / sku.revenue) * 100 : 0;
                const weight = 0.7 + 0.3 * (sku.revenue / maxSkuRevenue);
                return (
                  <div
                    key={sku.sku}
                    title={`${sku.title} — $${sku.revenue.toFixed(2)} revenue, ${marginPct.toFixed(1)}% margin`}
                    className={`rounded-lg border p-2.5 flex flex-col justify-between ${heatColor(marginPct)}`}
                    style={{ minHeight: `${64 * weight}px` }}
                  >
                    <div className="text-[10px] font-mono truncate opacity-80">{sku.sku}</div>
                    <div>
                      <div className="text-xs font-bold">${sku.revenue.toFixed(0)}</div>
                      <div className="text-[10px] font-medium">{marginPct.toFixed(0)}% margin</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Category Performance */}
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
        <div className="flex items-center gap-2 pb-3 border-b border-gray-100 mb-3">
          <Tag className="h-4 w-4 text-[#6C5DD3]" />
          <div>
            <h2 className="text-sm font-bold text-gray-900">Category Performance</h2>
            <p className="text-xs text-gray-500">Revenue and margin by product category, in the selected window.</p>
          </div>
        </div>
        {!summary || summary.category_performance.length === 0 ? (
          <div className="text-center py-8 text-xs text-gray-500">No orders in this window yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-900">
              <thead className="text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
                <tr>
                  <th className="py-2.5 pr-4">Category</th>
                  <th className="py-2.5 pr-4">Units Sold</th>
                  <th className="py-2.5 pr-4">Revenue</th>
                  <th className="py-2.5 pr-4">Profit</th>
                  <th className="py-2.5 pr-4">Margin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {summary.category_performance.map((cat) => (
                  <tr key={cat.category}>
                    <td className="py-2.5 pr-4 font-semibold text-xs">{cat.category}</td>
                    <td className="py-2.5 pr-4 text-xs text-gray-600">{cat.units_sold}</td>
                    <td className="py-2.5 pr-4 text-xs font-semibold text-gray-900">${cat.revenue.toFixed(2)}</td>
                    <td className={`py-2.5 pr-4 text-xs font-semibold ${cat.profit >= 0 ? "text-emerald-700" : "text-rose-600"}`}>
                      ${cat.profit.toFixed(2)}
                    </td>
                    <td className="py-2.5 pr-4 text-xs">{cat.margin_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Supplier Performance Scoring */}
      <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
        <div className="flex items-center gap-2 pb-3 border-b border-gray-100 mb-3">
          <Clock className="h-4 w-4 text-[#6C5DD3]" />
          <div>
            <h2 className="text-sm font-bold text-gray-900">Supplier Fulfillment Performance</h2>
            <p className="text-xs text-gray-500">Based on purchase order fulfillment time and order cancellations.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-900">
            <thead className="text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
              <tr>
                <th className="py-2.5 pr-4">Supplier</th>
                <th className="py-2.5 pr-4">Purchase Orders</th>
                <th className="py-2.5 pr-4">Avg. Fulfillment Time</th>
                <th className="py-2.5 pr-4">Cancellation Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {scores.map((s) => (
                <tr key={s.supplier_id}>
                  <td className="py-2.5 pr-4 font-semibold text-xs">{s.supplier_name}</td>
                  <td className="py-2.5 pr-4 text-xs text-gray-600">{s.po_count}</td>
                  <td className="py-2.5 pr-4 text-xs text-gray-600">
                    {s.avg_fulfillment_days !== null ? `${s.avg_fulfillment_days.toFixed(1)} days` : "No shipped POs yet"}
                  </td>
                  <td className="py-2.5 pr-4 text-xs">
                    <span className={s.cancellation_rate_pct > 10 ? "text-rose-600 font-semibold" : "text-gray-600"}>
                      {s.cancellation_rate_pct.toFixed(1)}%
                    </span>
                    <span className="text-gray-400"> ({s.routed_item_count} routed)</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-gray-400 mt-3">
          Note: inventory accuracy is not scored here — no supplier adapter in this system currently reports promised-vs-actual stock discrepancies.
        </p>
      </div>
    </div>
  );
}
