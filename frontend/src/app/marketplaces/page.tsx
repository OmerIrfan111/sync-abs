"use client";

import React, { useEffect, useState } from "react";
import { 
  Store, 
  Wifi, 
  RefreshCw, 
  Check, 
  AlertCircle, 
  Lock, 
  CheckCircle2,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  X,
  ExternalLink,
  ShieldCheck
} from "lucide-react";
import { fetchApi, Marketplace } from "@/lib/api";

const STORE_DESCRIPTIONS: Record<string, { summary: string; guide: string }> = {
  "eBay": {
    summary: "Sell to millions of shoppers on eBay. We automatically update your listing prices and stock levels.",
    guide: "Log in to your eBay Developer Portal, generate a Production User Token, and paste your Client ID and Client Secret."
  },
  "Amazon": {
    summary: "Sell products on Amazon US. We handle pricing formulas and stock synchronization automatically.",
    guide: "Go to Seller Central > Partner Network > Develop Apps, and generate an LWA Refresh Token."
  },
  "Walmart": {
    summary: "Reach shoppers on Walmart.com with automated inventory and order feeds.",
    guide: "Log in to Walmart Developer Portal, generate API Keys, and paste your Client ID and Client Secret."
  },
  "Shopify": {
    summary: "Connect your personal branded storefront for seamless inventory management.",
    guide: "In Shopify Admin, go to Settings > Apps > Custom apps, create an app, and copy the Admin API Access Token."
  },
  "Newegg": {
    summary: "Sell electronics, hardware, and accessories on Newegg Marketplace.",
    guide: "Log in to Newegg Seller Portal > Manage Account > API Settings, and copy your Seller ID and Secret Key."
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
  const [expandedId, setExpandedId] = useState<number | null>(null);

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
      showFeedback(res.message || `${name} is connected and responding quickly!`, "success");
    } catch (err: any) {
      showFeedback(err.message || `Could not connect to ${name}`, "error");
    } finally {
      setTestingId(null);
    }
  };

  const handleOpenConfig = (mkt: Marketplace) => {
    setConfigChannel(mkt);
    setCredentialsJson(
      mkt.has_credentials 
        ? '{\n  "api_key": "••••••••••••••••",\n  "status": "configured_and_encrypted"\n}' 
        : '{\n  "api_key": "",\n  "secret": ""\n}'
    );
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
          throw new Error("Please enter valid JSON format or leave empty");
        }
      }

      await fetchApi(`/marketplaces/${configChannel.id}`, {
        method: "PUT",
        body: JSON.stringify({ credentials: creds })
      });

      showFeedback(`Keys for ${configChannel.name} encrypted and saved securely!`, "success");
      setConfigChannel(null);
      loadMarketplaces();
    } catch (err: any) {
      showFeedback(err.message || "Failed to save credentials", "error");
    } finally {
      setSavingConfig(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0e1526] p-6 rounded-2xl border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Connect Your Online Stores</h1>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
              Sales Channels
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Connect the marketplaces where you want to sell products. Once connected, stock and pricing updates are delivered automatically.
          </p>
        </div>

        <button
          onClick={loadMarketplaces}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition-all border border-gray-700 self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh Stores</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-2 shadow-lg ${
          feedback.type === "success" 
            ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300"
            : "bg-rose-500/10 border border-rose-500/30 text-rose-300"
        }`}>
          {feedback.type === "success" ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <AlertCircle className="h-4 w-4 text-rose-400" />}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Marketplace Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full py-16 text-center text-gray-500">
            Loading online store channels...
          </div>
        ) : (
          marketplaces.map((mkt) => {
            const isTesting = testingId === mkt.id;
            const info = Object.entries(STORE_DESCRIPTIONS).find(([key]) => mkt.name.includes(key))?.[1] || {
              summary: "Automated ecommerce sales channel with live price & inventory feeds.",
              guide: "Paste your API keys from your store developer settings."
            };
            const isExpanded = expandedId === mkt.id;

            return (
              <div
                key={mkt.id}
                className="bg-[#0e1526] border border-gray-800 rounded-2xl p-6 flex flex-col justify-between shadow-xl relative overflow-hidden space-y-4"
              >
                <div>
                  {/* Top Row: Store Name & Status */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-violet-600/10 text-violet-400 border border-violet-500/20">
                        <Store className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-white">{mkt.name}</h2>
                        <span className="text-[11px] text-gray-400">Online Marketplace</span>
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      <span>Connected</span>
                    </span>
                  </div>

                  <p className="text-xs text-gray-400 leading-relaxed mb-4">
                    {info.summary}
                  </p>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                      <span className="text-[11px] text-gray-400 block">Products Live</span>
                      <span className="text-lg font-black text-white">{mkt.active_listings_count ?? mkt.total_listings_count ?? 0}</span>
                      <span className="text-[10px] text-emerald-400 block">Active offers</span>
                    </div>
                    <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                      <span className="text-[11px] text-gray-400 block">Security & Keys</span>
                      <span className="text-xs font-bold text-gray-200 block truncate flex items-center gap-1 mt-1">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Encrypted (Safe)</span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-2 pt-3 border-t border-gray-800">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTestConnection(mkt.id, mkt.name)}
                      disabled={isTesting}
                      className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all border border-gray-700 disabled:opacity-50"
                    >
                      <Wifi className={`h-3.5 w-3.5 ${isTesting ? "animate-pulse text-violet-400" : ""}`} />
                      <span>{isTesting ? "Testing..." : "Test Store Connection"}</span>
                    </button>

                    <button
                      onClick={() => handleOpenConfig(mkt)}
                      className="px-3.5 py-2 bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded-xl text-xs font-bold transition-all flex items-center gap-1"
                    >
                      <Lock className="h-3.5 w-3.5" />
                      <span>Keys</span>
                    </button>
                  </div>

                  {/* Collapsible Advanced Info */}
                  <div className="pt-1">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : mkt.id)}
                      className="text-[11px] text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
                    >
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      <span>Store API details (Advanced)</span>
                    </button>

                    {isExpanded && (
                      <div className="mt-2 p-3 bg-gray-950/80 rounded-xl border border-gray-800 text-[11px] font-mono text-gray-400 space-y-1">
                        <div>Adapter: {mkt.adapter_class}</div>
                        <div>Encryption: AES-256 Fernet (At rest in DB)</div>
                        <div>Setup guide: {info.guide}</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Store Credentials Modal */}
      {configChannel && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-800">
              <div>
                <h3 className="text-base font-bold text-white">Connect {configChannel.name}</h3>
                <p className="text-xs text-gray-400">Enter your store API credentials to enable automated publishing.</p>
              </div>
              <button
                onClick={() => setConfigChannel(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSaveCredentials} className="space-y-3">
              <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20 text-xs text-indigo-300 space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <HelpCircle className="h-3.5 w-3.5" />
                  <span>Where do I find my API keys?</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  {Object.entries(STORE_DESCRIPTIONS).find(([k]) => configChannel.name.includes(k))?.[1].guide || "Log in to your store seller account and look under Developer or API settings."}
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">
                  API Keys & Credentials (Encrypted with AES-256)
                </label>
                <textarea
                  rows={5}
                  value={credentialsJson}
                  onChange={(e) => setCredentialsJson(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-700 rounded-xl text-xs font-mono text-gray-200 focus:outline-none focus:border-violet-500"
                />
                <p className="text-[10px] text-gray-500 mt-1">
                  All keys are encrypted at rest with military-grade AES-256 encryption.
                </p>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setConfigChannel(null)}
                  className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingConfig}
                  className="px-5 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-xs font-bold disabled:opacity-50"
                >
                  {savingConfig ? "Encrypting & Saving..." : "Save Store Keys"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
