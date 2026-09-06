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

  // Form fields for user-friendly configuration
  const [shopifyDomain, setShopifyDomain] = useState("");
  const [shopifyToken, setShopifyToken] = useState("");
  const [ebayToken, setEbayToken] = useState("");
  const [ebayEnv, setEbayEnv] = useState("sandbox");
  const [ebayAppId, setEbayAppId] = useState("");
  const [ebayCertId, setEbayCertId] = useState("");
  const [genericClientId, setGenericClientId] = useState("");
  const [genericClientSecret, setGenericClientSecret] = useState("");
  const [isAdvancedJson, setIsAdvancedJson] = useState(false);

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
    setIsAdvancedJson(false);

    // Reset fields
    setShopifyDomain("");
    setShopifyToken("");
    setEbayToken("");
    setEbayEnv("sandbox");
    setEbayAppId("");
    setEbayCertId("");
    setGenericClientId("");
    setGenericClientSecret("");

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
      let creds: Record<string, any> = {};

      if (isAdvancedJson) {
        if (credentialsJson.trim()) {
          try {
            creds = JSON.parse(credentialsJson);
          } catch (_) {
            throw new Error("Please enter valid JSON format or leave empty");
          }
        }
      } else {
        const name = configChannel.name.toLowerCase();
        if (name.includes("shopify")) {
          if (!shopifyDomain.trim() && !shopifyToken.trim()) {
            throw new Error("Please enter your Shopify store domain and Admin API access token.");
          }
          creds = {
            shop_url: shopifyDomain.trim(),
            shop_domain: shopifyDomain.trim(),
            access_token: shopifyToken.trim(),
            adapter_class: "LiveShopifyAdapter"
          };
        } else if (name.includes("ebay")) {
          if (!ebayToken.trim() && !ebayAppId.trim()) {
            throw new Error("Please provide your eBay OAuth User Token.");
          }
          creds = {
            environment: ebayEnv,
            user_token: ebayToken.trim(),
            app_id: ebayAppId.trim(),
            cert_id: ebayCertId.trim(),
            adapter_class: "LiveEBayAdapter"
          };
        } else {
          creds = {
            client_id: genericClientId.trim(),
            client_secret: genericClientSecret.trim(),
            api_key: genericClientId.trim()
          };
        }
      }

      await fetchApi(`/marketplaces/${configChannel.id}`, {
        method: "PUT",
        body: JSON.stringify({ credentials: creds })
      });

      showFeedback(`Keys for ${configChannel.name} encrypted and connected successfully!`, "success");
      setConfigChannel(null);
      loadMarketplaces();
    } catch (err: any) {
      showFeedback(err.message || "Failed to save credentials", "error");
    } finally {
      setSavingConfig(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header - Unboxed on canvas */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-[#0a0a0a] tracking-tight">Connect Your Online Stores</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-[#905831]/10 text-[#905831] border border-[#905831]/20">
              Sales Channels
            </span>
          </div>
          <p className="text-sm text-[#767676] mt-1 max-w-2xl leading-relaxed">
            Connect the marketplaces where you want to sell products. Once connected, stock and pricing updates are delivered automatically.
          </p>
        </div>

        <button
          onClick={loadMarketplaces}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#0a0a0a] rounded-lg text-xs font-medium transition-all border border-gray-300 shadow-sm self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5 text-[#767676]" />
          <span>Refresh Stores</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`p-3.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 ${
          feedback.type === "success" 
            ? "bg-emerald-50 border border-emerald-300 text-emerald-900"
            : "bg-rose-50 border border-rose-300 text-rose-900"
        }`}>
          {feedback.type === "success" ? <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" /> : <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Marketplace Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
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
                className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between space-y-4"
              >
                <div>
                  {/* Top Row: Store Name & Status */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-lg bg-gray-100 text-[#0a0a0a]">
                        <Store className="h-4 w-4" />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-[#0a0a0a]">{mkt.name}</h2>
                        <span className="text-[11px] text-[#767676]">Online Marketplace</span>
                      </div>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-medium uppercase tracking-wider flex items-center gap-1.5 ${
                      mkt.has_credentials
                        ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                        : "bg-gray-100 text-gray-700 border border-gray-200"
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${mkt.has_credentials ? "bg-emerald-500" : "bg-gray-400"}`} />
                      <span>{mkt.has_credentials ? "Connected" : "Not Linked"}</span>
                    </span>
                  </div>

                  <p className="text-xs text-[#767676] leading-relaxed mb-3.5">
                    {info.summary}
                  </p>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-2.5 mb-3.5">
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <span className="text-[11px] text-[#767676] block">Products Live</span>
                      <span className="text-lg font-bold text-[#0a0a0a]">{mkt.active_listings_count ?? mkt.total_listings_count ?? 0}</span>
                      <span className="text-[10px] text-emerald-700 font-semibold block mt-0.5">Active offers</span>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <span className="text-[11px] text-[#767676] block">Security & Keys</span>
                      <span className="text-xs font-semibold text-[#0a0a0a] block truncate flex items-center gap-1 mt-1">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                        <span>{mkt.has_credentials ? "Encrypted (Safe)" : "Keys Needed"}</span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-2.5 pt-3.5 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTestConnection(mkt.id, mkt.name)}
                      disabled={isTesting}
                      className="flex-1 px-3 py-2 bg-white hover:bg-gray-50 text-[#0a0a0a] rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all border border-gray-300 shadow-sm disabled:opacity-50"
                    >
                      <Wifi className={`h-3.5 w-3.5 text-[#767676] ${isTesting ? "animate-pulse text-[#905831]" : ""}`} />
                      <span>{isTesting ? "Testing..." : "Test Connection"}</span>
                    </button>

                    <button
                      onClick={() => handleOpenConfig(mkt)}
                      className="px-4 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 shadow-sm"
                    >
                      <Lock className="h-3.5 w-3.5 text-[#905831]" />
                      <span>{mkt.has_credentials ? "Edit Keys" : "Connect Store"}</span>
                    </button>
                  </div>

                  {/* Collapsible Advanced Info */}
                  <div className="pt-0.5">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : mkt.id)}
                      className="text-[11px] text-[#767676] hover:text-[#0a0a0a] flex items-center gap-1 transition-colors font-medium"
                    >
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      <span>Store API details (Advanced)</span>
                    </button>

                    {isExpanded && (
                      <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200 text-[11px] font-mono text-[#767676] space-y-0.5">
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
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-bold text-[#0a0a0a]">Connect {configChannel.name}</h3>
                <p className="text-xs text-[#767676] mt-0.5">Enter your store API credentials to enable automated publishing and sync.</p>
              </div>
              <button
                onClick={() => setConfigChannel(null)}
                className="p-1.5 rounded-lg text-[#767676] hover:text-[#0a0a0a] hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveCredentials} className="space-y-4">
              <div className="p-3 bg-[#905831]/[0.06] rounded-lg border border-[#905831]/20 text-xs text-[#905831] space-y-1">
                <div className="font-semibold flex items-center gap-1.5">
                  <HelpCircle className="h-3.5 w-3.5" />
                  <span>How to connect {configChannel.name}:</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  {Object.entries(STORE_DESCRIPTIONS).find(([k]) => configChannel.name.includes(k))?.[1].guide || "Log in to your store seller account and look under Developer or API settings."}
                </p>
              </div>

              {/* Specific Form Fields */}
              {!isAdvancedJson ? (
                <div className="space-y-3">
                  {configChannel.name.toLowerCase().includes("shopify") && (
                    <>
                      <div>
                        <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                          Shopify Store Domain / URL
                        </label>
                        <input
                          type="text"
                          value={shopifyDomain}
                          onChange={(e) => setShopifyDomain(e.target.value)}
                          placeholder="e.g. your-store.myshopify.com"
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                          Admin API Access Token
                        </label>
                        <input
                          type="password"
                          value={shopifyToken}
                          onChange={(e) => setShopifyToken(e.target.value)}
                          placeholder="shpat_••••••••••••••••••••••••"
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs font-mono text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                        />
                        <p className="text-[10px] text-[#767676] mt-1">
                          Found in Shopify Admin ➔ Settings ➔ Apps ➔ Develop apps ➔ API credentials.
                        </p>
                      </div>
                    </>
                  )}

                  {configChannel.name.toLowerCase().includes("ebay") && (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                            Environment
                          </label>
                          <select
                            value={ebayEnv}
                            onChange={(e) => setEbayEnv(e.target.value)}
                            className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                          >
                            <option value="sandbox">Sandbox (Testing)</option>
                            <option value="production">Production (Live)</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                            App ID (Client ID)
                          </label>
                          <input
                            type="text"
                            value={ebayAppId}
                            onChange={(e) => setEbayAppId(e.target.value)}
                            placeholder="Optional App ID"
                            className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                          OAuth User Token
                        </label>
                        <textarea
                          rows={3}
                          value={ebayToken}
                          onChange={(e) => setEbayToken(e.target.value)}
                          placeholder="Paste your eBay OAuth user token (v^1.1#...)"
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs font-mono text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                        />
                      </div>
                    </>
                  )}

                  {!configChannel.name.toLowerCase().includes("shopify") && !configChannel.name.toLowerCase().includes("ebay") && (
                    <>
                      <div>
                        <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                          Client ID / API Key
                        </label>
                        <input
                          type="text"
                          value={genericClientId}
                          onChange={(e) => setGenericClientId(e.target.value)}
                          placeholder="Enter your Client ID or API Key..."
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                          Client Secret / Private Key
                        </label>
                        <input
                          type="password"
                          value={genericClientSecret}
                          onChange={(e) => setGenericClientSecret(e.target.value)}
                          placeholder="Enter your Client Secret..."
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs font-mono text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                        />
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                    Raw JSON Credentials (AES-256 Encrypted)
                  </label>
                  <textarea
                    rows={5}
                    value={credentialsJson}
                    onChange={(e) => setCredentialsJson(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs font-mono text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                  />
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={() => setIsAdvancedJson(!isAdvancedJson)}
                  className="text-[11px] text-gray-500 hover:text-gray-900 underline font-medium"
                >
                  {isAdvancedJson ? "← Switch to Simple Form" : "Switch to Raw JSON →"}
                </button>
                <div className="flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>AES-256 Encrypted</span>
                </div>
              </div>

              <div className="pt-3 border-t border-gray-200 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setConfigChannel(null)}
                  className="px-4 py-2 text-xs font-medium text-[#767676] hover:text-[#0a0a0a]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingConfig}
                  className="px-5 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium disabled:opacity-50 shadow-sm"
                >
                  {savingConfig ? "Encrypting & Saving..." : "Save & Connect Store"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}


