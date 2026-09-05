"use client";

import React, { useEffect, useState } from "react";
import { History, AlertTriangle, CheckCircle2, Clock, RefreshCw, Check, ChevronDown, ChevronUp, ShieldAlert, Store, HelpCircle } from "lucide-react";
import { fetchApi } from "@/lib/api";

interface SyncLog {
  id: number;
  product_id?: number;
  product_sku?: string;
  supplier_id?: number;
  supplier_name?: string;
  field_changed: string;
  old_value?: string;
  new_value?: string;
  synced_at: string;
}

interface ErrorLog {
  id: number;
  error_type: string;
  product_sku?: string;
  marketplace_name?: string;
  supplier_name?: string;
  message: string;
  retry_count: number;
  status: string;
  resolved_at?: string;
  created_at: string;
}

export default function LogsPage() {
  const [activeTab, setActiveTab] = useState<"sync" | "errors">("sync");
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [errorLogs, setErrorLogs] = useState<ErrorLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedErrorIds, setExpandedErrorIds] = useState<number[]>([]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      if (activeTab === "sync") {
        const res = await fetchApi<{ items: SyncLog[] }>("/sync-logs?page=1&page_size=50");
        setSyncLogs(res.items);
      } else {
        const res = await fetchApi<{ items: ErrorLog[] }>("/errors?page=1&page_size=50");
        setErrorLogs(res.items);
      }
    } catch (err) {
      console.error("Failed to load activity logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [activeTab]);

  const handleResolveError = async (errorId: number) => {
    try {
      await fetchApi(`/errors/${errorId}/resolve`, { method: "POST" });
      loadLogs();
    } catch (err) {
      console.error("Failed to resolve issue:", err);
    }
  };

  const toggleTechnicalDetails = (id: number) => {
    setExpandedErrorIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const formatFieldName = (field: string) => {
    switch (field.toLowerCase()) {
      case "price":
      case "cost":
      case "wholesale_price":
        return "Wholesale Cost";
      case "quantity":
      case "stock":
        return "Available Stock";
      case "status":
        return "Availability Status";
      default:
        return field.replace(/_/g, " ");
    }
  };

  const getLaymanErrorGuidance = (err: ErrorLog) => {
    const type = (err.error_type || "").toUpperCase();
    const msg = err.message || "";

    if (type.includes("MARKETPLACE") || type.includes("RATE_LIMIT") || msg.toLowerCase().includes("rate limit")) {
      return {
        what: `Your ${err.marketplace_name || "online store"} requested a brief pause because too many updates were sent at once.`,
        why: "To keep your store account safe from automated spam penalties, the system automatically slows down updates.",
        action: "No action needed. The system will automatically resume updating your listings in a few moments.",
      };
    }

    if (type.includes("TIMEOUT") || type.includes("NETWORK") || msg.toLowerCase().includes("timeout")) {
      return {
        what: `Connection to ${err.supplier_name || err.marketplace_name || "external service"} took too long to answer.`,
        why: "Temporary internet latency or the partner site had brief downtime.",
        action: "The system will retry on the next scheduled check. Click 'Mark Resolved' if subsequent updates have succeeded.",
      };
    }

    if (type.includes("AUTH") || type.includes("INVALID_TOKEN") || msg.toLowerCase().includes("credentials")) {
      return {
        what: `Login credentials or API keys for ${err.marketplace_name || err.supplier_name || "your store"} were rejected.`,
        why: "Prices and inventory cannot update on this channel until valid keys are provided.",
        action: "Visit the 'Connect Stores' page and re-enter your API keys, then mark this issue resolved.",
      };
    }

    if (type.includes("STOCK") || type.includes("OUT_OF_STOCK")) {
      return {
        what: `Supplier reported zero units in stock for product ${err.product_sku || ""}.`,
        why: "Listing was protected to prevent customers from buying items that cannot be fulfilled.",
        action: "Verify if an alternate supplier has stock in your Central Catalog, or keep listing paused.",
      };
    }

    return {
      what: msg || "A temporary synchronization discrepancy occurred during routine operations.",
      why: "The system logged this event to safeguard inventory counts and profit margins.",
      action: "Review the affected item and click 'Mark Resolved' once verified.",
    };
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header - Unboxed on canvas */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-[#0a0a0a] tracking-tight">Store Activity & Alerts</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-[#905831]/10 text-[#905831] border border-[#905831]/20">
              Audit Logs
            </span>
          </div>
          <p className="text-sm text-[#767676] mt-1 max-w-2xl leading-relaxed">
            See everything happening behind the scenes: recent price changes, stock adjustments, and issues needing your attention.
          </p>
        </div>
        <button
          onClick={loadLogs}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#0a0a0a] rounded-lg text-xs font-medium transition-all border border-gray-300 shadow-sm self-start sm:self-auto"
        >
          <RefreshCw className={`h-3.5 w-3.5 text-[#767676] ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Activity</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab("sync")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all shadow-sm ${
            activeTab === "sync"
              ? "bg-[#0a0a0a] text-white"
              : "bg-white text-[#767676] hover:text-[#0a0a0a] border border-gray-300 hover:bg-gray-50"
          }`}
        >
          <History className="h-4 w-4" />
          <span>Recent Price & Stock Updates</span>
        </button>
        <button
          onClick={() => setActiveTab("errors")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all shadow-sm ${
            activeTab === "errors"
              ? "bg-rose-600 text-white"
              : "bg-white text-[#767676] hover:text-[#0a0a0a] border border-gray-300 hover:bg-gray-50"
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          <span>Issues Needing Attention</span>
          {errorLogs.filter(e => e.status !== "RESOLVED").length > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded text-[10px] font-semibold bg-white/20 text-white">
              {errorLogs.filter(e => e.status !== "RESOLVED").length}
            </span>
          )}
        </button>
      </div>

      {/* Content */}
      {activeTab === "sync" ? (
        <div className="space-y-4">
          <div className="p-3.5 bg-gray-50 rounded-xl border border-gray-200 text-xs text-[#767676] flex items-start gap-2.5">
            <HelpCircle className="h-4 w-4 text-[#905831] flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-[#0a0a0a]">Continuous Automatic Record</p>
              <p className="mt-0.5 leading-relaxed">
                Every time a wholesale supplier updates their wholesale price or stock count, the system automatically notes what changed and updates your stores based on your pricing rules.
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-[#1a1a1a]">
                <thead className="bg-gray-50/80 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3.5">When</th>
                    <th className="px-6 py-3.5">Product Code</th>
                    <th className="px-6 py-3.5">Wholesale Supplier</th>
                    <th className="px-6 py-3.5">What Changed</th>
                    <th className="px-6 py-3.5">Previous Value</th>
                    <th className="px-6 py-3.5">Updated Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-xs">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="text-center py-20 text-[#767676]">
                        <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-[#905831]" />
                        Loading recent updates...
                      </td>
                    </tr>
                  ) : syncLogs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-20 text-[#767676]">
                        <div className="max-w-md mx-auto space-y-2">
                          <CheckCircle2 className="h-8 w-8 text-emerald-600 mx-auto" />
                          <p className="font-semibold text-[#0a0a0a]">No recent updates recorded yet.</p>
                          <p className="text-xs text-[#767676]">
                            Click &quot;Update Everything Now&quot; on the Store Overview or wait for the automatic sync to detect changes.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    syncLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-gray-50/60 transition-colors">
                        <td className="px-6 py-3.5 text-[#767676] whitespace-nowrap" suppressHydrationWarning>
                          {new Date(log.synced_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="px-6 py-3.5 font-mono font-medium text-[#905831]">
                          {log.product_sku || "Main Product"}
                        </td>
                        <td className="px-6 py-3.5 text-[#0a0a0a] font-medium">
                          {log.supplier_name || "Primary Supplier"}
                        </td>
                        <td className="px-6 py-3.5">
                          <span className="px-2 py-0.5 rounded-md bg-gray-100 text-[#0a0a0a] font-medium border border-gray-200 capitalize">
                            {formatFieldName(log.field_changed)}
                          </span>
                        </td>
                        <td className="px-6 py-3.5 text-rose-600 font-medium line-through">
                          {log.old_value || "—"}
                        </td>
                        <td className="px-6 py-3.5 text-emerald-700 font-semibold">
                          {log.new_value || "—"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-3.5 bg-rose-50/70 border border-rose-200 rounded-xl text-xs text-rose-900 flex items-start gap-2.5">
            <ShieldAlert className="h-4 w-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-950">Plain English Issue Resolver</p>
              <p className="mt-0.5 leading-relaxed">
                When something unexpected happens (e.g., a store API rate limit or discontinued wholesale item), this list translates the technical issue into plain terms so you know whether you need to take action.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="bg-white rounded-xl border border-gray-200 p-20 text-center text-[#767676]">
              <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-rose-600" />
              Loading issues...
            </div>
          ) : errorLogs.length === 0 ? (
            <div className="bg-white rounded-xl p-12 text-center border border-gray-200 shadow-sm">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-2.5">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <h3 className="text-base font-bold text-[#0a0a0a]">All Clear! Everything is Running Smoothly</h3>
              <p className="text-xs text-[#767676] max-w-md mx-auto mt-1">
                None of your wholesale suppliers or online store channels have reported any errors. Your products and inventory counts are in sync.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {errorLogs.map((err) => {
                const guidance = getLaymanErrorGuidance(err);
                const isExpanded = expandedErrorIds.includes(err.id);
                const isResolved = err.status === "RESOLVED";

                return (
                  <div
                    key={err.id}
                    className={`bg-white rounded-xl p-5 transition-all border shadow-sm ${
                      isResolved
                        ? "border-gray-200 opacity-75"
                        : "border-rose-200 bg-rose-50/10"
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                      {/* Left: What happened, why it matters, what to do */}
                      <div className="space-y-3 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded-md text-[11px] font-medium uppercase tracking-wider ${
                              isResolved
                                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                                : "bg-rose-50 text-rose-800 border border-rose-200"
                            }`}
                          >
                            {isResolved ? "Resolved" : "Needs Attention"}
                          </span>
                          <span className="text-xs text-[#767676]" suppressHydrationWarning>
                            Reported {new Date(err.created_at).toLocaleString()}
                          </span>
                          {(err.marketplace_name || err.supplier_name) && (
                            <span className="px-2 py-0.5 rounded-md bg-gray-100 text-[#1a1a1a] text-xs font-medium border border-gray-200">
                              Channel: {err.marketplace_name || err.supplier_name}
                            </span>
                          )}
                          {err.product_sku && (
                            <span className="px-2 py-0.5 rounded-md bg-[#905831]/10 text-[#905831] text-xs font-mono font-medium border border-[#905831]/20">
                              Product: {err.product_sku}
                            </span>
                          )}
                        </div>

                        {/* Three plain English pillars */}
                        <div className="space-y-1.5 bg-gray-50/80 p-3.5 rounded-lg border border-gray-200 text-xs">
                          <div>
                            <span className="font-semibold text-[#0a0a0a]">What happened: </span>
                            <span className="text-[#1a1a1a]">{guidance.what}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-[#905831]">Why it matters: </span>
                            <span className="text-[#1a1a1a]">{guidance.why}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-emerald-700">What to do: </span>
                            <span className="text-[#1a1a1a]">{guidance.action}</span>
                          </div>
                        </div>

                        {/* Collapsible technical details */}
                        <div>
                          <button
                            onClick={() => toggleTechnicalDetails(err.id)}
                            className="inline-flex items-center gap-1 text-xs text-[#767676] hover:text-[#0a0a0a] font-medium transition-colors"
                          >
                            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                            <span>{isExpanded ? "Hide technical diagnostic details" : "Show technical diagnostic details (Advanced)"}</span>
                          </button>

                          {isExpanded && (
                            <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200 text-xs font-mono text-[#767676] space-y-0.5">
                              <div><span className="text-[#767676]">Error Code:</span> <span className="text-rose-600 font-medium">{err.error_type}</span></div>
                              <div><span className="text-[#767676]">Retry Count:</span> {err.retry_count}</div>
                              <div><span className="text-[#767676]">Raw Message:</span> {err.message}</div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right Action Button */}
                      <div className="flex md:flex-col items-end justify-between md:justify-start gap-2">
                        {!isResolved && (
                          <button
                            onClick={() => handleResolveError(err.id)}
                            className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-medium inline-flex items-center gap-1.5 shadow-sm transition-all"
                          >
                            <Check className="h-3.5 w-3.5" />
                            <span>Mark as Resolved</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
