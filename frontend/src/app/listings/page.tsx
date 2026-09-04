"use client";

import React, { useEffect, useState } from "react";
import { 
  ShoppingBag, 
  RefreshCw, 
  ExternalLink, 
  Eye, 
  Trash2, 
  AlertCircle, 
  Check, 
  Boxes, 
  Store,
  Layers,
  Ban,
  Plus
} from "lucide-react";
import { fetchApi, Listing, Product } from "@/lib/api";

export default function ListingsPage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [withdrawingId, setWithdrawingId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ id: number; message: string; type: "success" | "error" } | null>(null);

  // Publish Modal State
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | "">("");
  const [customPrice, setCustomPrice] = useState("");
  const [customQty, setCustomQty] = useState("");
  const [publishing, setPublishing] = useState(false);

  const loadListings = async () => {
    try {
      const res = await fetchApi<{ items: Listing[]; total: number }>("/listings?page=1&page_size=50");
      setListings(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error("Failed to load listings:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadCatalog = async () => {
    try {
      const res = await fetchApi<{ items: Product[] }>("/products?page=1&page_size=50");
      setCatalogProducts(res.items);
      if (res.items.length > 0 && selectedProductId === "") {
        setSelectedProductId(res.items[0].id);
      }
    } catch (err) {
      console.error("Failed to load catalog products:", err);
    }
  };

  useEffect(() => {
    loadListings();
    loadCatalog();
  }, []);

  const handleSyncListing = async (listingId: number) => {
    setSyncingId(listingId);
    setFeedback(null);
    try {
      await fetchApi(`/listings/${listingId}/sync`, { method: "POST" });
      setFeedback({ id: listingId, message: "Listing inventory & price synced with marketplace!", type: "success" });
      loadListings();
    } catch (err: any) {
      setFeedback({ id: listingId, message: err.message || "Sync failed", type: "error" });
    } finally {
      setSyncingId(null);
    }
  };

  const handleWithdrawListing = async (listingId: number) => {
    setWithdrawingId(listingId);
    setFeedback(null);
    try {
      await fetchApi(`/listings/${listingId}/withdraw`, { method: "POST" });
      setFeedback({ id: listingId, message: "Listing withdrawn from marketplace.", type: "success" });
      loadListings();
    } catch (err: any) {
      setFeedback({ id: listingId, message: err.message || "Withdraw failed", type: "error" });
    } finally {
      setWithdrawingId(null);
    }
  };

  const handlePublishSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProductId) return;

    setPublishing(true);
    setFeedback(null);
    try {
      await fetchApi("/listings/publish", {
        method: "POST",
        body: JSON.stringify({
          product_id: Number(selectedProductId),
          marketplace_id: 1, // eBay US
          custom_price: customPrice ? Number(customPrice) : undefined,
          custom_qty: customQty ? Number(customQty) : undefined,
        }),
      });
      setShowPublishModal(false);
      setCustomPrice("");
      setCustomQty("");
      loadListings();
    } catch (err: any) {
      alert("Failed to publish: " + err.message);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Marketplace Listings</h1>
          <p className="text-sm text-gray-400 mt-1">
            Active and pending retail offers distributed to eBay and connected ecommerce sales channels.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowPublishModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-all shadow-md shadow-indigo-600/20"
          >
            <Plus className="h-4 w-4" />
            <span>Publish to eBay</span>
          </button>
          <button
            onClick={loadListings}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-semibold transition-all"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Listings Table */}
      <div className="bg-[#0e1526] border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-[#131b2e] text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="px-6 py-4">Product / Offer</th>
                <th className="px-6 py-4">Marketplace</th>
                <th className="px-6 py-4">External Listing ID</th>
                <th className="px-6 py-4">Listed Price</th>
                <th className="px-6 py-4">Quantity</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-500">
                    Loading marketplace listings...
                  </td>
                </tr>
              ) : listings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-500">
                    No active marketplace listings. Click &apos;Publish to eBay&apos; to launch an offer!
                  </td>
                </tr>
              ) : (
                listings.map((l) => {
                  const isSyncing = syncingId === l.id;
                  const isWithdrawing = withdrawingId === l.id;
                  const itemFeedback = feedback?.id === l.id ? feedback : null;

                  return (
                    <tr key={l.id} className="hover:bg-gray-900/40 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-white truncate max-w-xs">{l.product_title || "Product"}</div>
                        <div className="text-xs text-indigo-400 font-mono">{l.product_sku}</div>
                      </td>

                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span className="p-1 rounded bg-violet-500/10 text-violet-400">
                            <Store className="h-3.5 w-3.5" />
                          </span>
                          <span className="font-medium text-gray-200">{l.marketplace_name || "eBay"}</span>
                        </div>
                      </td>

                      <td className="px-6 py-4 font-mono text-xs text-gray-400">
                        {l.external_listing_id || "Pending"}
                      </td>

                      <td className="px-6 py-4 font-bold text-white">
                        ${Number(l.selling_price).toFixed(2)}
                      </td>

                      <td className="px-6 py-4 font-semibold">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${
                          l.listed_qty > 0 ? "text-emerald-400 bg-emerald-500/10" : "text-rose-400 bg-rose-500/10"
                        }`}>
                          {l.listed_qty} units
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          l.status === "ACTIVE"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : l.status === "WITHDRAWN"
                            ? "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}>
                          {l.status}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleSyncListing(l.id)}
                            disabled={isSyncing || isWithdrawing || l.status === "WITHDRAWN"}
                            className="px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-xs font-semibold flex items-center gap-1 transition-all disabled:opacity-40"
                            title="Sync live quantity and price"
                          >
                            <RefreshCw className={`h-3 w-3 ${isSyncing ? "animate-spin text-indigo-400" : ""}`} />
                            <span>Sync</span>
                          </button>

                          {l.status === "ACTIVE" && (
                            <button
                              onClick={() => handleWithdrawListing(l.id)}
                              disabled={isSyncing || isWithdrawing}
                              className="px-2.5 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/50 rounded-lg text-xs font-semibold flex items-center gap-1 transition-all disabled:opacity-40"
                              title="Withdraw listing from eBay"
                            >
                              <Ban className="h-3 w-3" />
                              <span>Withdraw</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Publish Modal */}
      {showPublishModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl max-w-lg w-full shadow-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-1">Publish Product to eBay US</h3>
            <p className="text-xs text-gray-400 mb-4">
              Create an active eBay Sell offer linked to real-time supplier stock.
            </p>

            <form onSubmit={handlePublishSubmit} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">Select Catalog Product</label>
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(Number(e.target.value))}
                  className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  required
                >
                  {catalogProducts.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title} ({p.sku}) — Stock: {p.total_stock}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                    Custom Selling Price ($)
                    <span className="text-gray-500 font-normal block text-[10px]">Leave blank for 15% markup</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="e.g. 59.99"
                    value={customPrice}
                    onChange={(e) => setCustomPrice(e.target.value)}
                    className="w-full px-3.5 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                    Custom Stock Quantity
                    <span className="text-gray-500 font-normal block text-[10px]">Leave blank for total stock</span>
                  </label>
                  <input
                    type="number"
                    placeholder="e.g. 10"
                    value={customQty}
                    onChange={(e) => setCustomQty(e.target.value)}
                    className="w-full px-3.5 py-2 bg-gray-900 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-gray-800 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowPublishModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl text-sm font-semibold transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={publishing}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Plus className="h-4 w-4" />
                  <span>{publishing ? "Publishing..." : "Confirm & Publish"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
