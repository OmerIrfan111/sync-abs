"use client";

import React, { useEffect, useState } from "react";
import { 
  Truck, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Play, 
  Check, 
  Wifi, 
  AlertCircle
} from "lucide-react";
import { fetchApi, Supplier } from "@/lib/api";

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ id: number; message: string; type: "success" | "error" } | null>(null);

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
      setFeedback({ id, message: res.message || "Connection verified successfully!", type: "success" });
    } catch (err: any) {
      setFeedback({ id, message: err.message || "Connection test failed", type: "error" });
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
        message: `Synced successfully: ${res.products_imported || 0} products processed, ${res.changes_detected || 0} changes logged.`, 
        type: "success" 
      });
      loadSuppliers();
    } catch (err: any) {
      setFeedback({ id, message: err.message || "Sync failed", type: "error" });
    } finally {
      setSyncingId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Wholesale Supplier Integrations</h1>
          <p className="text-sm text-gray-400 mt-1">
            Configure, monitor, and synchronize catalog feeds from authorized wholesale distributors.
          </p>
        </div>
        <button
          onClick={loadSuppliers}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-semibold transition-all self-start sm:self-auto"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Supplier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full py-12 text-center text-gray-500">
            Loading supplier configurations...
          </div>
        ) : (
          suppliers.map((sup) => {
            const isSyncing = syncingId === sup.id;
            const isTesting = testingId === sup.id;
            const itemFeedback = feedback?.id === sup.id ? feedback : null;

            return (
              <div
                key={sup.id}
                className="bg-[#0e1526] border border-gray-800 rounded-2xl p-6 flex flex-col justify-between shadow-lg relative overflow-hidden"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
                        <Truck className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-white">{sup.name}</h2>
                        <div className="text-xs text-gray-400 font-mono">{sup.adapter_class}</div>
                      </div>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      sup.is_active
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                    }`}>
                      {sup.is_active ? "Active" : "Disabled"}
                    </span>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-3 my-4">
                    <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                      <span className="text-[11px] text-gray-500 block">Catalog Products</span>
                      <span className="text-base font-bold text-white">{sup.product_count}</span>
                    </div>
                    <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                      <span className="text-[11px] text-gray-500 block">Last Synced</span>
                      <span className="text-xs font-semibold text-gray-300">
                        {sup.last_synced_at ? new Date(sup.last_synced_at).toLocaleTimeString() : "Never"}
                      </span>
                    </div>
                  </div>

                  {/* Feedback Notification */}
                  {itemFeedback && (
                    <div className={`p-3 rounded-xl text-xs mb-4 flex items-start gap-2 ${
                      itemFeedback.type === "success"
                        ? "bg-emerald-950/40 text-emerald-300 border border-emerald-800/50"
                        : "bg-rose-950/40 text-rose-300 border border-rose-800/50"
                    }`}>
                      {itemFeedback.type === "success" ? (
                        <Check className="h-4 w-4 shrink-0 text-emerald-400" />
                      ) : (
                        <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                      )}
                      <span>{itemFeedback.message}</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="pt-4 border-t border-gray-800/80 flex items-center gap-2">
                  <button
                    onClick={() => handleTestConnection(sup.id)}
                    disabled={isTesting || isSyncing}
                    className="flex-1 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                  >
                    <Wifi className={`h-3.5 w-3.5 ${isTesting ? "animate-pulse text-indigo-400" : ""}`} />
                    <span>{isTesting ? "Testing..." : "Test Conn"}</span>
                  </button>
                  <button
                    onClick={() => handleSyncNow(sup.id)}
                    disabled={isTesting || isSyncing}
                    className="flex-1 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? "animate-spin" : ""}`} />
                    <span>{isSyncing ? "Syncing..." : "Sync Now"}</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
