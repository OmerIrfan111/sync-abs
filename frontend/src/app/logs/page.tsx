"use client";

import React, { useEffect, useState } from "react";
import { History, AlertTriangle, CheckCircle2, Clock, RefreshCw, Check } from "lucide-react";
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

  const loadLogs = async () => {
    setLoading(true);
    try {
      if (activeTab === "sync") {
        const res = await fetchApi<{ items: SyncLog[] }>("/sync-logs?page=1&page_size=30");
        setSyncLogs(res.items);
      } else {
        const res = await fetchApi<{ items: ErrorLog[] }>("/errors?page=1&page_size=30");
        setErrorLogs(res.items);
      }
    } catch (err) {
      console.error("Failed to load logs:", err);
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
      console.error("Failed to resolve error:", err);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Audit & Error Logs</h1>
          <p className="text-sm text-gray-400 mt-1">
            Immutable trace of all catalog field changes, inventory swings, and system exceptions.
          </p>
        </div>
        <button
          onClick={loadLogs}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-semibold transition-all self-start sm:self-auto"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-800 pb-2">
        <button
          onClick={() => setActiveTab("sync")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
            activeTab === "sync"
              ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/50"
          }`}
        >
          <History className="h-4 w-4" />
          <span>Catalog Change Audit Logs</span>
        </button>
        <button
          onClick={() => setActiveTab("errors")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
            activeTab === "errors"
              ? "bg-rose-600 text-white shadow-md shadow-rose-600/20"
              : "text-gray-400 hover:text-white hover:bg-gray-800/50"
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          <span>Operational Error Tracking</span>
        </button>
      </div>

      {/* Content */}
      <div className="bg-[#0e1526] border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
        {activeTab === "sync" ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-[#131b2e] text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800">
                <tr>
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">Product SKU</th>
                  <th className="px-6 py-4">Supplier</th>
                  <th className="px-6 py-4">Field Changed</th>
                  <th className="px-6 py-4">Old Value</th>
                  <th className="px-6 py-4">New Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 font-mono text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-gray-500 font-sans">
                      Loading sync change logs...
                    </td>
                  </tr>
                ) : syncLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-gray-500 font-sans">
                      No synchronization change logs recorded yet.
                    </td>
                  </tr>
                ) : (
                  syncLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-900/40">
                      <td className="px-6 py-4 text-gray-400 font-sans">
                        {new Date(log.synced_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-indigo-400 font-semibold font-mono">
                        {log.product_sku || "Canonical"}
                      </td>
                      <td className="px-6 py-4 text-gray-300 font-sans">
                        {log.supplier_name || "—"}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-0.5 rounded bg-gray-800 text-amber-400 font-semibold border border-gray-700">
                          {log.field_changed}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-rose-400">{log.old_value || "—"}</td>
                      <td className="px-6 py-4 text-emerald-400 font-bold">{log.new_value || "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-[#131b2e] text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800">
                <tr>
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">Error Type</th>
                  <th className="px-6 py-4">Context</th>
                  <th className="px-6 py-4">Message</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-gray-500 font-sans">
                      Loading error logs...
                    </td>
                  </tr>
                ) : errorLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-gray-500 font-sans">
                      No operational errors logged. Everything is operational.
                    </td>
                  </tr>
                ) : (
                  errorLogs.map((err) => (
                    <tr key={err.id} className="hover:bg-gray-900/40">
                      <td className="px-6 py-4 text-gray-400 font-sans">
                        {new Date(err.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">
                          {err.error_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-300">
                        {err.supplier_name || err.marketplace_name || err.product_sku || "Global"}
                      </td>
                      <td className="px-6 py-4 font-mono text-gray-300 max-w-md truncate">
                        {err.message}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          err.status === "RESOLVED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>
                          {err.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {err.status !== "RESOLVED" && (
                          <button
                            onClick={() => handleResolveError(err.id)}
                            className="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-all"
                          >
                            <Check className="h-3 w-3" /> Mark Resolved
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
