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
      await fetchApi<{ success: boolean; message: string }>(`/suppliers/${id}/test`, {
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
    <div className="space-y-7 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="glass-card p-8 rounded-[2rem] shadow-wandor-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-3xl font-black text-[#0a0a0a] tracking-tight">Wholesale Suppliers</h1>
            <span className="text-xs font-semibold px-3 py-0.5 rounded-full bg-[#905831]/10 text-[#905831] border border-[#905831]/20">
              Distributor Feeds
            </span>
          </div>
          <p className="text-sm text-[#767676] mt-1.5 max-w-2xl leading-relaxed">
            Connect to distributors who provide products and ship customer orders for you. We check their inventory and wholesale prices continuously.
          </p>
        </div>

        <button
          onClick={loadSuppliers}
          className="inline-flex items-center gap-2 px-5 py-3 bg-white hover:bg-black/[0.02] text-[#0a0a0a] rounded-full text-xs font-bold transition-all border border-black/[0.08] shadow-wandor-sm self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5 text-[#767676]" />
          <span>Refresh List</span>
        </button>
      </div>

      {/* Supplier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full py-20 text-center text-[#767676]">
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
                className="glass-card glass-card-hover p-7 rounded-[2rem] flex flex-col justify-between shadow-wandor-sm relative overflow-hidden space-y-4"
              >
                <div>
                  {/* Top Row: Name & Status */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-2xl bg-[#905831]/10 text-[#905831]">
                        <Truck className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-black text-[#0a0a0a]">{sup.name}</h2>
                        <span className="text-[11px] text-[#767676] font-medium">Authorized Distributor</span>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-wandor-sm ${
                      sup.is_active
                        ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                        : "bg-black/[0.04] text-[#767676] border border-black/[0.06]"
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${sup.is_active ? "bg-emerald-500" : "bg-[#767676]"}`} />
                      <span>{sup.is_active ? "Connected & Ready" : "Paused"}</span>
                    </span>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-3 my-4">
                    <div className="p-3.5 bg-black/[0.02] rounded-2xl border border-black/[0.05]">
                      <span className="text-[11px] text-[#767676] block">Products Available</span>
                      <span className="text-xl font-black text-[#0a0a0a]">{sup.product_count}</span>
                      <span className="text-[10px] text-[#767676] block mt-0.5">In wholesale feed</span>
                    </div>
                    <div className="p-3.5 bg-black/[0.02] rounded-2xl border border-black/[0.05]">
                      <span className="text-[11px] text-[#767676] block">Last Update Check</span>
                      <span className="text-xs font-bold text-[#0a0a0a] block truncate mt-1" suppressHydrationWarning>
                        {sup.last_synced_at ? new Date(sup.last_synced_at).toLocaleTimeString() : "Pending check"}
                      </span>
                      <span className="text-[10px] text-emerald-700 font-bold block mt-0.5">Auto-sync active</span>
                    </div>
                  </div>

                  {/* Feedback Notification */}
                  {itemFeedback && (
                    <div className={`p-3.5 rounded-2xl text-xs mb-3 flex items-start gap-2 shadow-wandor-sm ${
                      itemFeedback.type === "success"
                        ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
                        : "bg-rose-50 text-rose-900 border border-rose-200"
                    }`}>
                      {itemFeedback.type === "success" ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 mt-0.5" />
                      ) : (
                        <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
                      )}
                      <span>{itemFeedback.message}</span>
                    </div>
                  )}
                </div>

                {/* Plain Actions */}
                <div className="space-y-3 pt-4 border-t border-black/[0.05]">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSyncNow(sup.id)}
                      disabled={isTesting || isSyncing}
                      className="flex-1 px-4 py-3 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-full text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-wandor-sm hover:shadow-wandor-md disabled:opacity-50"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 text-[#905831] ${isSyncing ? "animate-spin" : ""}`} />
                      <span>{isSyncing ? "Checking Feed..." : "Check for New Stock & Prices"}</span>
                    </button>

                    <button
                      onClick={() => handleTestConnection(sup.id)}
                      disabled={isTesting || isSyncing}
                      className="px-4 py-3 bg-white hover:bg-black/[0.02] text-[#0a0a0a] rounded-full text-xs font-bold flex items-center justify-center gap-1.5 transition-all border border-black/[0.08] shadow-wandor-sm disabled:opacity-50"
                      title="Test API Connection"
                    >
                      <Wifi className={`h-3.5 w-3.5 text-[#767676] ${isTesting ? "animate-pulse text-[#905831]" : ""}`} />
                      <span>{isTesting ? "Testing..." : "Test"}</span>
                    </button>
                  </div>

                  {/* Collapsible Connection Settings */}
                  <div className="pt-1">
                    <button
                      onClick={() => setExpandedSettingsId(isExpanded ? null : sup.id)}
                      className="text-[11px] text-[#767676] hover:text-[#0a0a0a] flex items-center gap-1 transition-colors font-medium"
                    >
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      <span>Connection details (Advanced)</span>
                    </button>

                    {isExpanded && (
                      <div className="mt-2.5 p-3.5 bg-black/[0.02] rounded-2xl border border-black/[0.05] text-[11px] font-mono text-[#767676] space-y-1">
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
