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
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Store Activity & Alerts</h1>
          <p className="text-sm text-gray-400 mt-1">
            See everything happening behind the scenes: recent price changes, stock adjustments, and issues needing your attention.
          </p>
        </div>
        <button
          onClick={loadLogs}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-sm font-semibold transition-all border border-gray-700 shadow-sm self-start sm:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Activity</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-3 border-b border-gray-800 pb-3">
        <button
          onClick={() => setActiveTab("sync")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
            activeTab === "sync"
              ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/50"
          }`}
        >
          <History className="h-4 w-4" />
          <span>Recent Price & Stock Updates</span>
        </button>
        <button
          onClick={() => setActiveTab("errors")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
            activeTab === "errors"
              ? "bg-rose-600 text-white shadow-md shadow-rose-600/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/50"
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          <span>Issues Needing Attention</span>
          {errorLogs.filter(e => e.status !== "RESOLVED").length > 0 && (
            <span className="ml-1.5 px-2 py-0.5 text-xs font-bold bg-rose-500/30 text-rose-200 rounded-full">
              {errorLogs.filter(e => e.status !== "RESOLVED").length}
            </span>
          )}
        </button>
      </div>

      {/* Content */}
      {activeTab === "sync" ? (
        <div className="space-y-4">
          <div className="p-4 bg-indigo-950/20 border border-indigo-500/20 rounded-xl text-sm text-indigo-200 flex items-start gap-3">
            <HelpCircle className="h-5 w-5 text-indigo-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-indigo-300">Continuous Automatic Record</p>
              <p className="text-xs text-indigo-300/80 mt-0.5">
                Every time a wholesale supplier updates their wholesale price or stock count, the system automatically notes what changed and updates your stores based on your pricing rules.
              </p>
            </div>
          </div>

          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-300">
                <thead className="bg-[#131b2e] text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800">
                  <tr>
                    <th className="px-6 py-4">When</th>
                    <th className="px-6 py-4">Product Code</th>
                    <th className="px-6 py-4">Wholesale Supplier</th>
                    <th className="px-6 py-4">What Changed</th>
                    <th className="px-6 py-4">Previous Value</th>
                    <th className="px-6 py-4">Updated Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 text-xs">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="text-center py-16 text-gray-500 font-sans">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-indigo-400" />
                        Loading recent updates...
                      </td>
                    </tr>
                  ) : syncLogs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-16 text-gray-400 font-sans">
                        <div className="max-w-md mx-auto space-y-2">
                          <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
                          <p className="font-semibold text-gray-200">No recent updates recorded yet.</p>
                          <p className="text-xs text-gray-500">
                            Click &quot;Update Everything Now&quot; on the Store Overview or wait for the automatic sync to detect changes.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    syncLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-gray-900/40 transition-colors">
                        <td className="px-6 py-4 text-gray-400 whitespace-nowrap">
                          {new Date(log.synced_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="px-6 py-4 font-mono font-bold text-indigo-400">
                          {log.product_sku || "Main Product"}
                        </td>
                        <td className="px-6 py-4 text-gray-200 font-medium">
                          {log.supplier_name || "Primary Supplier"}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 rounded-md bg-gray-800 text-amber-300 font-semibold border border-gray-700 capitalize">
                            {formatFieldName(log.field_changed)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-rose-400 font-medium line-through">
                          {log.old_value || "—"}
                        </td>
                        <td className="px-6 py-4 text-emerald-400 font-bold">
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
          <div className="p-4 bg-rose-950/20 border border-rose-500/20 rounded-xl text-sm text-rose-200 flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-300">Plain English Issue Resolver</p>
              <p className="text-xs text-rose-300/80 mt-0.5">
                When something unexpected happens (e.g., a store API rate limit or discontinued wholesale item), this list translates the technical issue into plain terms so you know whether you need to take action.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="bg-[#0e1526] border border-gray-800 rounded-2xl p-16 text-center text-gray-500">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-rose-400" />
              Loading issues...
            </div>
          ) : errorLogs.length === 0 ? (
            <div className="bg-[#0e1526] border border-emerald-500/20 rounded-2xl p-12 text-center">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 className="h-7 w-7" />
              </div>
              <h3 className="text-lg font-bold text-white">All Clear! Everything is Running Smoothly</h3>
              <p className="text-sm text-gray-400 max-w-md mx-auto mt-1">
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
                    className={`bg-[#0e1526] border rounded-2xl p-5 transition-all shadow-md ${
                      isResolved
                        ? "border-gray-800/80 opacity-75"
                        : "border-rose-500/30 bg-rose-950/5"
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                      {/* Left: What happened, why it matters, what to do */}
                      <div className="space-y-3 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                              isResolved
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            }`}
                          >
                            {isResolved ? "Resolved" : "Needs Attention"}
                          </span>
                          <span className="text-xs text-gray-400">
                            Reported {new Date(err.created_at).toLocaleString()}
                          </span>
                          {(err.marketplace_name || err.supplier_name) && (
                            <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 text-xs font-medium border border-gray-700">
                              Channel: {err.marketplace_name || err.supplier_name}
                            </span>
                          )}
                          {err.product_sku && (
                            <span className="px-2 py-0.5 rounded bg-indigo-950/40 text-indigo-300 text-xs font-mono border border-indigo-800/40">
                              Product: {err.product_sku}
                            </span>
                          )}
                        </div>

                        {/* Three plain English pillars */}
                        <div className="space-y-2 bg-[#121a2d] p-3.5 rounded-xl border border-gray-800 text-xs">
                          <div>
                            <span className="font-bold text-gray-200">What happened: </span>
                            <span className="text-gray-300">{guidance.what}</span>
                          </div>
                          <div>
                            <span className="font-bold text-amber-400">Why it matters: </span>
                            <span className="text-gray-300">{guidance.why}</span>
                          </div>
                          <div>
                            <span className="font-bold text-emerald-400">What to do: </span>
                            <span className="text-gray-300">{guidance.action}</span>
                          </div>
                        </div>

                        {/* Collapsible technical details */}
                        <div>
                          <button
                            onClick={() => toggleTechnicalDetails(err.id)}
                            className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 font-medium transition-colors"
                          >
                            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                            <span>{isExpanded ? "Hide technical diagnostic details" : "Show technical diagnostic details (Advanced)"}</span>
                          </button>

                          {isExpanded && (
                            <div className="mt-2 p-3 bg-gray-950/80 rounded-lg border border-gray-800 text-xs font-mono text-gray-400 space-y-1">
                              <div><span className="text-gray-500">Error Code:</span> <span className="text-rose-400">{err.error_type}</span></div>
                              <div><span className="text-gray-500">Retry Count:</span> {err.retry_count}</div>
                              <div><span className="text-gray-500">Raw Message:</span> {err.message}</div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right Action Button */}
                      <div className="flex md:flex-col items-end justify-between md:justify-start gap-2">
                        {!isResolved && (
                          <button
                            onClick={() => handleResolveError(err.id)}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold inline-flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all"
                          >
                            <Check className="h-4 w-4" />
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
