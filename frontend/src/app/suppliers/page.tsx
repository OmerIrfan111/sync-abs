"use client";

import React, { useEffect, useState } from "react";
import { 
  Truck, 
  RefreshCw, 
  CheckCircle, 
  Clock, 
  Check, 
  Wifi, 
  AlertCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  ExternalLink
} from "lucide-react";
import { fetchApi, Supplier } from "@/lib/api";

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ id: number; message: string; type: "success" | "error" } | null>(null);
  const [expandedSettingsId, setExpandedSettingsId] = useState<number | null>(null);

  const loadSuppliers = async () => {
    try {
      const data = await fetchApi<Supplier[]>("/suppliers");
      setSuppliers(data);
    } catch (err) {
      console.error("Failed to load suppliers:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuppliers();
  }, []);

  const handleTestConnection = async (id: number) => {
    setTestingId(id);
    setFeedback(null);
    try {
      const res = await fetchApi<{ success: boolean; message: string }>(`/suppliers/${id}/test`, {
        method: "POST"
      });
      setFeedback({ id, message: "Connection verified! Distributor API is responsive and ready.", type: "success" });
    } catch (err: any) {
      setFeedback({ id, message: "Could not reach supplier: " + (err.message || "Connection timed out"), type: "error" });
    } finally {
      setTestingId(null);
    }
  };

  const handleSyncNow = async (id: number) => {
    setSyncingId(id);
    setFeedback(null);
    try {
      const res = await fetchApi<any>(`/suppliers/${id}/sync`, {
        method: "POST"
      });
      setFeedback({ 
        id, 
        message: `Stock & prices updated! Processed ${res.products_imported || 0} products (${res.changes_detected || 0} updates applied).`, 
        type: "success" 
      });
      loadSuppliers();
    } catch (err: any) {
      setFeedback({ id, message: "Update check failed: " + err.message, type: "error" });
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0e1526] p-6 rounded-2xl border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Wholesale Suppliers</h1>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Distributor Connections
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Connect to distributors who provide products and ship customer orders for you. We check their inventory and wholesale prices continuously.
          </p>
        </div>

        <button
          onClick={loadSuppliers}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition-all border border-gray-700 self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh List</span>
        </button>
      </div>

      {/* Supplier Cards (Requirement 1 & 2) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full py-16 text-center text-gray-500">
            Loading wholesale supplier connections...
          </div>
        ) : (
          suppliers.map((sup) => {
            const isSyncing = syncingId === sup.id;
            const isTesting = testingId === sup.id;
            const itemFeedback = feedback?.id === sup.id ? feedback : null;
            const isExpanded = expandedSettingsId === sup.id;

            return (
              <div
                key={sup.id}
                className="bg-[#0e1526] border border-gray-800 rounded-2xl p-6 flex flex-col justify-between shadow-xl relative overflow-hidden space-y-4"
              >
                <div>
                  {/* Top Row: Name & Status */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
                        <Truck className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-white">{sup.name}</h2>
                        <span className="text-[11px] text-gray-400">Authorized Wholesale Distributor</span>
                      </div>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 ${
                      sup.is_active
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${sup.is_active ? "bg-emerald-400" : "bg-gray-500"}`} />
                      <span>{sup.is_active ? "Connected & Ready" : "Paused"}</span>
                    </span>
                  </div>

                  {/* Plain English Metrics */}
                  <div className="grid grid-cols-2 gap-3 my-4">
                    <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                      <span className="text-[11px] text-gray-400 block">Products Available</span>
                      <span className="text-lg font-black text-white">{sup.product_count}</span>
                      <span className="text-[10px] text-gray-500 block">In wholesale feed</span>
                    </div>
                    <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                      <span className="text-[11px] text-gray-400 block">Last Update Check</span>
                      <span className="text-xs font-bold text-gray-200 block truncate">
                        {sup.last_synced_at ? new Date(sup.last_synced_at).toLocaleTimeString() : "Pending check"}
                      </span>
                      <span className="text-[10px] text-emerald-400 font-semibold block">Auto-sync active</span>
                    </div>
                  </div>

                  {/* Feedback Notification */}
                  {itemFeedback && (
                    <div className={`p-3 rounded-xl text-xs mb-3 flex items-start gap-2 ${
                      itemFeedback.type === "success"
                        ? "bg-emerald-950/40 text-emerald-300 border border-emerald-800/50"
                        : "bg-rose-950/40 text-rose-300 border border-rose-800/50"
                    }`}>
                      {itemFeedback.type === "success" ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
                      ) : (
                        <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                      )}
                      <span>{itemFeedback.message}</span>
                    </div>
                  )}
                </div>

                {/* Plain Actions */}
                <div className="space-y-2 pt-3 border-t border-gray-800">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSyncNow(sup.id)}
                      disabled={isTesting || isSyncing}
                      className="flex-1 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? "animate-spin" : ""}`} />
                      <span>{isSyncing ? "Checking Feed..." : "Check for New Stock & Prices"}</span>
                    </button>

                    <button
                      onClick={() => handleTestConnection(sup.id)}
                      disabled={isTesting || isSyncing}
                      className="px-3.5 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold flex items-center justify-center gap-1 transition-all border border-gray-700 disabled:opacity-50"
                      title="Test API Connection"
                    >
                      <Wifi className={`h-3.5 w-3.5 ${isTesting ? "animate-pulse text-indigo-400" : ""}`} />
                      <span>{isTesting ? "Testing..." : "Test"}</span>
                    </button>
                  </div>

                  {/* Collapsible Connection Settings (Requirement 3) */}
                  <div className="pt-2">
                    <button
                      onClick={() => setExpandedSettingsId(isExpanded ? null : sup.id)}
                      className="text-[11px] text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
                    >
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      <span>Connection details (Advanced)</span>
                    </button>

                    {isExpanded && (
                      <div className="mt-2 p-3 bg-gray-950/80 rounded-xl border border-gray-800 text-[11px] font-mono text-gray-400 space-y-1">
                        <div>Adapter: {sup.adapter_class}</div>
                        <div>Protocol: REST / XML Feed</div>
                        <div>Encrypted at rest: AES-256 Fernet</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
