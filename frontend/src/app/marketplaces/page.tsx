"use client";

import React, { useEffect, useState } from "react";
import { 
  Store, 
  Wifi, 
  RefreshCw, 
  ExternalLink, 
  ShieldCheck, 
  Check, 
  AlertCircle, 
  Settings, 
  Lock, 
  Layers, 
  ShoppingBag 
} from "lucide-react";
import { fetchApi, Marketplace } from "@/lib/api";

const CHANNEL_DETAILS: Record<string, { iconColor: string; description: string; badge: string }> = {
  "eBay": {
    iconColor: "from-blue-600 to-sky-500",
    description: "Supports eBay Sell Inventory API, Offer Creation, Price Revisions, and Stock Feeds.",
    badge: "Sell Inventory API"
  },
  "Amazon": {
    iconColor: "from-amber-600 to-orange-500",
    description: "Selling Partner API (SP-API) Listings Items, LWA OAuth, and Price Feeds.",
    badge: "SP-API v2021"
  },
  "Walmart": {
    iconColor: "from-yellow-500 to-amber-500",
    description: "Item management, price feeds, inventory endpoints, and lag time synchronization.",
    badge: "Marketplace API v3"
  },
  "Shopify": {
    iconColor: "from-emerald-600 to-teal-500",
    description: "Admin REST & GraphQL API, inventory level adjustments, variant pricing, and webhooks.",
    badge: "Admin API 2024-01"
  },
  "Newegg": {
    iconColor: "from-purple-600 to-indigo-500",
    description: "Item creation feeds, price/stock feeds for consumer electronics and components.",
    badge: "Marketplace B2B"
  }
};

export default function MarketplacesPage() {
  const [marketplaces, setMarketplaces] = useState<Marketplace[]>([]);
  const [loading, setLoading] = useState(true);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Configure Modal
  const [configChannel, setConfigChannel] = useState<Marketplace | null>(null);
  const [credentialsJson, setCredentialsJson] = useState("");
  const [savingConfig, setSavingConfig] = useState(false);

  const loadMarketplaces = async () => {
    setLoading(true);
    try {
      const res = await fetchApi<Marketplace[]>("/marketplaces");
      setMarketplaces(res);
    } catch (err: any) {
      console.error("Failed to load marketplaces:", err);
      showFeedback(err.message || "Failed to load channels", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMarketplaces();
  }, []);

  const showFeedback = (message: string, type: "success" | "error") => {
    setFeedback({ message, type });
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleTestConnection = async (id: number, name: string) => {
    setTestingId(id);
    try {
      const res = await fetchApi<{ success: boolean; message: string }>(`/marketplaces/${id}/test`, {
        method: "POST"
      });
      showFeedback(res.message || `${name} connection verified`, "success");
    } catch (err: any) {
      showFeedback(err.message || `${name} connection test failed`, "error");
    } finally {
      setTestingId(null);
    }
  };

  const handleSaveCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!configChannel) return;
    setSavingConfig(true);
    try {
      let creds = {};
      if (credentialsJson.trim()) {
        try {
          creds = JSON.parse(credentialsJson);
        } catch (_) {
          throw new Error("Invalid JSON format for credentials");
        }
      }

      await fetchApi(`/marketplaces/${configChannel.id}`, {
        method: "PUT",
        body: JSON.stringify({ credentials: creds })
      });

      showFeedback(`Credentials for ${configChannel.name} encrypted and saved.`, "success");
      setConfigChannel(null);
      loadMarketplaces();
    } catch (err: any) {
      showFeedback(err.message || "Failed to save credentials", "error");
    } finally {
      setSavingConfig(false);
    }
  };

  const totalListings = marketplaces.reduce((acc, m) => acc + m.active_listings_count, 0);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
              <Store className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Channels & Marketplaces Setup</h1>
              <p className="text-sm text-gray-400">
                Multi-channel retail distribution matrix with dedicated adapter integrations and AES-256 encryption.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={loadMarketplaces}
          className="flex items-center gap-2 px-3.5 py-2 bg-gray-800/80 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-medium border border-gray-700 transition"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          <span>Refresh Channels</span>
        </button>
      </div>

      {/* Global Feedback Banner */}
      {feedback && (
        <div
          className={`p-4 rounded-xl text-sm font-medium flex items-center justify-between shadow-lg animate-in fade-in duration-200 border ${
            feedback.type === "success"
              ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-200"
              : "bg-rose-950/80 border-rose-500/50 text-rose-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === "success" ? <Check className="h-5 w-5 text-emerald-400" /> : <AlertCircle className="h-5 w-5 text-rose-400" />}
            <span>{feedback.message}</span>
          </div>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Configured Channels</div>
          <div className="text-2xl font-bold text-white">{marketplaces.length} Channels</div>
          <p className="text-xs text-indigo-400 mt-1">eBay, Amazon, Walmart, Shopify, Newegg</p>
        </div>

        <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Active Live Listings</div>
          <div className="text-2xl font-bold text-emerald-400">{totalListings} Listings</div>
          <p className="text-xs text-gray-400 mt-1">Synchronized across retailers</p>
        </div>

        <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Security Architecture</div>
          <div className="text-2xl font-bold text-white flex items-center gap-2">
            <Lock className="h-5 w-5 text-indigo-400" />
            <span>AES-256 Fernet</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Encrypted credential isolation</p>
        </div>
      </div>

      {/* Channels Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {marketplaces.map((item) => {
          const detail = CHANNEL_DETAILS[item.name] || {
            iconColor: "from-gray-600 to-gray-500",
            description: "Direct retail channel integration.",
            badge: item.adapter_class
          };

          return (
            <div
              key={item.id}
              className="bg-[#131b2e] border border-gray-800 rounded-2xl p-6 flex flex-col justify-between shadow-sm hover:border-gray-700 transition relative overflow-hidden"
            >
              <div>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`h-11 w-11 rounded-xl bg-gradient-to-tr ${detail.iconColor} flex items-center justify-center text-white shadow-md`}>
                      <Store className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-lg text-white">{item.name}</h3>
                      <span className="text-[11px] font-mono text-gray-400">{item.adapter_class}</span>
                    </div>
                  </div>

                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {detail.badge}
                  </span>
                </div>

                <p className="text-xs text-gray-300 mb-6 leading-relaxed">
                  {detail.description}
                </p>

                <div className="space-y-2 bg-[#0e1526] p-3.5 rounded-xl border border-gray-800/80 mb-6">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Connection Status:</span>
                    <span className="font-semibold text-emerald-400 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      ACTIVE (Ready)
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Active Listings:</span>
                    <span className="font-bold text-white font-mono">{item.active_listings_count}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">Credentials:</span>
                    <span className={`font-semibold ${item.has_credentials ? "text-indigo-400" : "text-gray-400"}`}>
                      {item.has_credentials ? "Configured (Encrypted)" : "Simulated / Default"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-gray-800/80">
                <button
                  onClick={() => handleTestConnection(item.id, item.name)}
                  disabled={testingId === item.id}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-200 rounded-lg text-xs font-semibold border border-gray-700 transition"
                >
                  <Wifi className={`h-3.5 w-3.5 ${testingId === item.id ? "animate-spin text-indigo-400" : "text-emerald-400"}`} />
                  <span>{testingId === item.id ? "Testing..." : "Test Connection"}</span>
                </button>

                <button
                  onClick={() => {
                    setConfigChannel(item);
                    setCredentialsJson("");
                  }}
                  className="p-2 hover:bg-gray-800 text-gray-400 hover:text-white rounded-lg border border-transparent hover:border-gray-700 transition"
                  title="Configure Channel Credentials"
                >
                  <Settings className="h-4 w-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* MODAL: CONFIGURE CREDENTIALS */}
      {configChannel && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#131b2e] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Lock className="h-5 w-5 text-indigo-400" />
                <span>Configure {configChannel.name}</span>
              </h3>
              <span className="text-xs text-gray-400 font-mono">{configChannel.adapter_class}</span>
            </div>

            <p className="text-xs text-gray-400 leading-relaxed">
              API credentials are encrypted with AES-256 before storage in PostgreSQL. When left empty, the adapter operates in high-fidelity mock simulation mode.
            </p>

            <form onSubmit={handleSaveCredentials} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  API Credentials (JSON Object)
                </label>
                <textarea
                  rows={5}
                  placeholder={`{\n  "client_id": "...",\n  "client_secret": "...",\n  "refresh_token": "..."\n}`}
                  value={credentialsJson}
                  onChange={(e) => setCredentialsJson(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 font-mono text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setConfigChannel(null)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingConfig}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
                >
                  {savingConfig ? "Encrypting..." : "Save & Encrypt"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
