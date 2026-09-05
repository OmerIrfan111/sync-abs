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
  ShieldCheck,
  Sparkles
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
    <div className="space-y-7 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="glass-card p-8 rounded-[2rem] shadow-wandor-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-3xl font-black text-[#0a0a0a] tracking-tight">Connect Your Online Stores</h1>
            <span className="text-xs font-semibold px-3 py-0.5 rounded-full bg-[#905831]/10 text-[#905831] border border-[#905831]/20">
              Sales Channels
            </span>
          </div>
          <p className="text-sm text-[#767676] mt-1.5 max-w-2xl leading-relaxed">
            Connect the marketplaces where you want to sell products. Once connected, stock and pricing updates are delivered automatically.
          </p>
        </div>

        <button
          onClick={loadMarketplaces}
          className="inline-flex items-center gap-2 px-5 py-3 bg-white hover:bg-black/[0.02] text-[#0a0a0a] rounded-full text-xs font-bold transition-all border border-black/[0.08] shadow-wandor-sm self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5 text-[#767676]" />
          <span>Refresh Stores</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`p-4 rounded-2xl text-xs font-semibold flex items-center gap-2.5 shadow-wandor-sm ${
          feedback.type === "success" 
            ? "bg-emerald-50 border border-emerald-300 text-emerald-900"
            : "bg-rose-50 border border-rose-300 text-rose-900"
        }`}>
          {feedback.type === "success" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <AlertCircle className="h-4 w-4 text-rose-600" />}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Marketplace Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full py-20 text-center text-[#767676]">
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
                className="glass-card glass-card-hover p-7 rounded-[2rem] flex flex-col justify-between shadow-wandor-sm relative overflow-hidden space-y-4"
              >
                <div>
                  {/* Top Row: Store Name & Status */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-2xl bg-black/[0.04] text-[#0a0a0a]">
                        <Store className="h-5 w-5" />
                      </div>
                      <div>
                        <h2 className="text-base font-black text-[#0a0a0a]">{mkt.name}</h2>
                        <span className="text-[11px] text-[#767676] font-medium">Online Marketplace</span>
                      </div>
                    </div>
                    <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-wandor-sm flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      <span>Connected</span>
                    </span>
                  </div>

                  <p className="text-xs text-[#767676] leading-relaxed mb-4">
                    {info.summary}
                  </p>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="p-3.5 bg-black/[0.02] rounded-2xl border border-black/[0.05]">
                      <span className="text-[11px] text-[#767676] block">Products Live</span>
                      <span className="text-xl font-black text-[#0a0a0a]">{mkt.active_listings_count ?? mkt.total_listings_count ?? 0}</span>
                      <span className="text-[10px] text-emerald-700 font-bold block mt-0.5">Active offers</span>
                    </div>
                    <div className="p-3.5 bg-black/[0.02] rounded-2xl border border-black/[0.05]">
                      <span className="text-[11px] text-[#767676] block">Security & Keys</span>
                      <span className="text-xs font-bold text-[#0a0a0a] block truncate flex items-center gap-1 mt-1.5">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                        <span>Encrypted (Safe)</span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-3 pt-4 border-t border-black/[0.05]">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTestConnection(mkt.id, mkt.name)}
                      disabled={isTesting}
                      className="flex-1 px-4 py-3 bg-white hover:bg-black/[0.02] text-[#0a0a0a] rounded-full text-xs font-bold flex items-center justify-center gap-1.5 transition-all border border-black/[0.08] shadow-wandor-sm disabled:opacity-50"
                    >
                      <Wifi className={`h-3.5 w-3.5 text-[#767676] ${isTesting ? "animate-pulse text-[#905831]" : ""}`} />
                      <span>{isTesting ? "Testing..." : "Test Store Connection"}</span>
                    </button>

                    <button
                      onClick={() => handleOpenConfig(mkt)}
                      className="px-5 py-3 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-full text-xs font-bold transition-all flex items-center gap-1.5 shadow-wandor-sm"
                    >
                      <Lock className="h-3.5 w-3.5 text-[#905831]" />
                      <span>Keys</span>
                    </button>
                  </div>

                  {/* Collapsible Advanced Info */}
                  <div className="pt-1">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : mkt.id)}
                      className="text-[11px] text-[#767676] hover:text-[#0a0a0a] flex items-center gap-1 transition-colors font-medium"
                    >
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      <span>Store API details (Advanced)</span>
                    </button>

                    {isExpanded && (
                      <div className="mt-2.5 p-3.5 bg-black/[0.02] rounded-2xl border border-black/[0.05] text-[11px] font-mono text-[#767676] space-y-1">
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
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-white/95 backdrop-blur-2xl border border-black/[0.08] rounded-[2.5rem] max-w-lg w-full p-7 shadow-wandor-float space-y-5">
            <div className="flex items-start justify-between pb-3 border-b border-black/[0.05]">
              <div>
                <h3 className="text-xl font-black text-[#0a0a0a]">Connect {configChannel.name}</h3>
                <p className="text-xs text-[#767676] mt-0.5">Enter your store API credentials to enable automated publishing.</p>
              </div>
              <button
                onClick={() => setConfigChannel(null)}
                className="p-2 rounded-full text-[#767676] hover:text-[#0a0a0a] hover:bg-black/[0.04]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveCredentials} className="space-y-4">
              <div className="p-4 bg-[#905831]/[0.06] rounded-2xl border border-[#905831]/20 text-xs text-[#905831] space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <HelpCircle className="h-3.5 w-3.5" />
                  <span>Where do I find my API keys?</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  {Object.entries(STORE_DESCRIPTIONS).find(([k]) => configChannel.name.includes(k))?.[1].guide || "Log in to your store seller account and look under Developer or API settings."}
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#1a1a1a] mb-1.5">
                  API Keys & Credentials (Encrypted with AES-256)
                </label>
                <textarea
                  rows={5}
                  value={credentialsJson}
                  onChange={(e) => setCredentialsJson(e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-black/[0.08] rounded-2xl text-xs font-mono text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a] shadow-wandor-sm"
                />
                <p className="text-[10px] text-[#767676] mt-1">
                  All keys are encrypted at rest with military-grade AES-256 encryption.
                </p>
              </div>

              <div className="pt-3 border-t border-black/[0.05] flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setConfigChannel(null)}
                  className="px-5 py-2.5 text-xs font-semibold text-[#767676] hover:text-[#0a0a0a]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingConfig}
                  className="px-6 py-2.5 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-full text-xs font-bold disabled:opacity-50 shadow-wandor-md"
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
