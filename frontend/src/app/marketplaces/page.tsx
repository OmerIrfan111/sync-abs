"use client";

import React from "react";
import { Store, Wifi, RefreshCw, ExternalLink, ShieldCheck, Check } from "lucide-react";

const marketplaces = [
  {
    id: 1,
    name: "eBay",
    type: "MockMarketplaceAdapter (Phase 2)",
    status: "STANDBY",
    listings: 0,
    lastSync: "Phase 2 Target",
    description: "Supports Sell Inventory API, Offer Creation, and stock feeds.",
    badge: "Phase 2 Primary"
  },
  {
    id: 2,
    name: "Amazon SP-API",
    type: "MockMarketplaceAdapter (Phase 4)",
    status: "CONFIGURED",
    listings: 0,
    lastSync: "Phase 4 Target",
    description: "Supports Selling Partner Listings Items & Pricing APIs.",
    badge: "Phase 4"
  },
  {
    id: 3,
    name: "Walmart Marketplace",
    type: "MockMarketplaceAdapter (Phase 4)",
    status: "CONFIGURED",
    listings: 0,
    lastSync: "Phase 4 Target",
    description: "Item management, price feeds, and lag time synchronization.",
    badge: "Phase 4"
  },
  {
    id: 4,
    name: "Shopify Storefront",
    type: "MockMarketplaceAdapter (Phase 4)",
    status: "CONFIGURED",
    listings: 0,
    lastSync: "Phase 4 Target",
    description: "GraphQL Admin API, inventory level adjustments, and webhooks.",
    badge: "Phase 4"
  },
  {
    id: 5,
    name: "Newegg Marketplace",
    type: "MockMarketplaceAdapter (Phase 4)",
    status: "CONFIGURED",
    listings: 0,
    lastSync: "Phase 4 Target",
    description: "Data feeds for consumer electronics and components.",
    badge: "Phase 4"
  }
];

export default function MarketplacesPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-white tracking-tight">Connected Marketplace Channels</h1>
        <p className="text-sm text-gray-400 mt-1">
          Downstream retail destinations where product inventory, pricing rules, and offers are published.
        </p>
      </div>

      {/* Marketplaces Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {marketplaces.map((mkt) => (
          <div
            key={mkt.id}
            className="bg-[#0e1526] border border-gray-800 rounded-2xl p-6 flex flex-col justify-between shadow-lg"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-violet-600/10 text-violet-400 border border-violet-500/20">
                    <Store className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">{mkt.name}</h2>
                    <div className="text-xs text-gray-400 font-mono">{mkt.type}</div>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {mkt.badge}
                </span>
              </div>

              <p className="text-xs text-gray-400 my-3 leading-relaxed">{mkt.description}</p>

              <div className="grid grid-cols-2 gap-3 my-4">
                <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                  <span className="text-[11px] text-gray-500 block">Active Listings</span>
                  <span className="text-base font-bold text-white">{mkt.listings}</span>
                </div>
                <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/80">
                  <span className="text-[11px] text-gray-500 block">Status</span>
                  <span className="text-xs font-semibold text-gray-300">{mkt.status}</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-800/80 flex items-center gap-2">
              <button
                disabled
                className="w-full px-3 py-2 bg-gray-800/60 text-gray-400 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 cursor-not-allowed"
              >
                <Wifi className="h-3.5 w-3.5" />
                <span>Ready for Phase 2 Deployment</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
