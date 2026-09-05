"use client";

import React, { useEffect, useState } from "react";
import { 
  ShoppingBag, 
  RefreshCw, 
  Store, 
  Check, 
  Plus, 
  Edit3, 
  X, 
  Eye, 
  EyeOff, 
  HelpCircle, 
  AlertCircle,
  CheckCircle2
} from "lucide-react";
import { fetchApi, Listing, Product } from "@/lib/api";

const MARKETPLACE_TABS = [
  { id: "ALL", name: "All Stores" },
  { id: "Amazon US", name: "Amazon" },
  { id: "eBay US", name: "eBay" },
  { id: "Walmart US", name: "Walmart" },
  { id: "Shopify US", name: "Shopify" },
  { id: "Newegg US", name: "Newegg" },
];

export default function ListingsPage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState("ALL");
  const [editingListing, setEditingListing] = useState<Listing | null>(null);
  const [editPrice, setEditPrice] = useState("");
  const [editQty, setEditQty] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Add Product to Store state
  const [showAddModal, setShowAddModal] = useState(false);
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | "">("");
  const [selectedMarketplaceId, setSelectedMarketplaceId] = useState<number>(1);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [addingListing, setAddingListing] = useState(false);

  const loadListings = async () => {
    try {
      const res = await fetchApi<{ items: Listing[]; total: number }>("/listings?page=1&page_size=100");
      setListings(res.items);
    } catch (err) {
      console.error("Failed to load listings:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadCatalogAndChannels = async () => {
    try {
      const [prodRes, mktRes] = await Promise.all([
        fetchApi<{ items: Product[] }>("/products?page=1&page_size=100"),
        fetchApi<any[]>("/marketplaces")
      ]);
      setCatalogProducts(prodRes.items);
      setMarketplaces(mktRes);
      if (prodRes.items.length > 0) setSelectedProductId(prodRes.items[0].id);
      if (mktRes.length > 0) setSelectedMarketplaceId(mktRes[0].id);
    } catch (err) {
      console.error("Failed to load catalog or channels:", err);
    }
  };

  useEffect(() => {
    loadListings();
    loadCatalogAndChannels();
  }, []);

  const openEditModal = (listing: Listing) => {
    setEditingListing(listing);
    setEditPrice(Number(listing.selling_price).toFixed(2));
    setEditQty(String(listing.listed_qty));
  };

  const handleSaveEdit = async () => {
    if (!editingListing) return;
    setSavingEdit(true);
    try {
      await fetchApi(`/listings/${editingListing.id}`, {
        method: "PUT",
        body: JSON.stringify({
          selling_price: Number(editPrice),
          listed_qty: Number(editQty),
        }),
      });
      setFeedback("Price & stock updated successfully on your store!");
      setTimeout(() => setFeedback(null), 3500);
      setEditingListing(null);
      await loadListings();
    } catch (err: any) {
      alert("Update failed: " + err.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleToggleHide = async (listing: Listing) => {
    const shouldHide = listing.status === "ACTIVE";
    const actionEndpoint = shouldHide ? `/listings/${listing.id}/withdraw` : `/listings/${listing.id}/sync`;
    try {
      await fetchApi(actionEndpoint, { method: "POST" });
      setFeedback(shouldHide ? "Product is now hidden from buyers." : "Product is now live on your store!");
      setTimeout(() => setFeedback(null), 3500);
      if (editingListing && editingListing.id === listing.id) {
        setEditingListing(null);
      }
      await loadListings();
    } catch (err: any) {
      alert("Action failed: " + err.message);
    }
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProductId) return;

    setAddingListing(true);
    try {
      await fetchApi("/listings/publish", {
        method: "POST",
        body: JSON.stringify({
          product_id: Number(selectedProductId),
          marketplace_id: selectedMarketplaceId,
        }),
      });
      setShowAddModal(false);
      setFeedback("Product added to your store successfully!");
      setTimeout(() => setFeedback(null), 3500);
      loadListings();
    } catch (err: any) {
      alert("Could not add product: " + err.message);
    } finally {
      setAddingListing(false);
    }
  };

  // Filter listings by store tab
  const filteredListings = listings.filter((l) => {
    if (selectedTab === "ALL") return true;
    return l.marketplace_name?.toLowerCase().includes(selectedTab.toLowerCase());
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0e1526] p-6 rounded-2xl border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Your Online Stores</h1>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Live Selling
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            See and manage all products currently listed for sale across your connected marketplaces.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-sm font-bold transition-all shadow-md shadow-indigo-600/20"
          >
            <Plus className="h-4 w-4" />
            <span>List a Product</span>
          </button>
          <button
            onClick={loadListings}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-sm font-semibold transition-all border border-gray-700"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-2 text-xs font-semibold shadow-lg">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Marketplace Tabs (Spec Requirement 9) */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-gray-800">
        {MARKETPLACE_TABS.map((tab) => {
          const isActive = selectedTab === tab.id;
          const count = listings.filter((l) => {
            if (tab.id === "ALL") return true;
            return l.marketplace_name?.toLowerCase().includes(tab.id.toLowerCase());
          }).length;

          return (
            <button
              key={tab.id}
              onClick={() => setSelectedTab(tab.id)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap ${
                isActive
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/80"
              }`}
            >
              <span>{tab.name}</span>
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                isActive ? "bg-indigo-700 text-indigo-100" : "bg-gray-800 text-gray-400"
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Simplified Listings Table (Spec Requirement 9) */}
      <div className="bg-[#0e1526] border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-[#131b2e] text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="px-6 py-4">Product Name</th>
                <th className="px-4 py-4">Store</th>
                <th className="px-4 py-4">Selling Price</th>
                <th className="px-4 py-4">Stock for Buyers</th>
                <th className="px-4 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-16 text-gray-500">
                    Loading your store listings...
                  </td>
                </tr>
              ) : filteredListings.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-16 text-gray-500">
                    <Store className="h-8 w-8 mx-auto text-gray-600 mb-2" />
                    <div>No products listed in this store yet.</div>
                    <p className="text-xs text-gray-500 mt-1">Click &apos;List a Product&apos; above or go to &apos;Products to Sell&apos; to add items.</p>
                  </td>
                </tr>
              ) : (
                filteredListings.map((listing) => {
                  const isLive = listing.status === "ACTIVE";
                  const isPaused = listing.status === "PAUSED" || listing.status === "WITHDRAWN";

                  return (
                    <tr key={listing.id} className="hover:bg-gray-900/40 transition-colors">
                      {/* Product Name */}
                      <td className="px-6 py-4 font-bold text-white">
                        <div className="max-w-md">
                          <div className="line-clamp-1">{listing.product_title || "Enterprise Product"}</div>
                          <div className="text-[11px] text-gray-500 font-normal">
                            Code: {listing.product_sku || "N/A"}
                          </div>
                        </div>
                      </td>

                      {/* Store Channel */}
                      <td className="px-4 py-4">
                        <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-gray-900 border border-gray-800 text-gray-200">
                          {listing.marketplace_name || "Online Store"}
                        </span>
                      </td>

                      {/* Selling Price */}
                      <td className="px-4 py-4">
                        <div className="font-black text-white text-base">
                          ${Number(listing.selling_price).toFixed(2)}
                        </div>
                        <span className="text-[10px] text-gray-500">Price customers pay</span>
                      </td>

                      {/* Stock Shown to Buyers */}
                      <td className="px-4 py-4">
                        <div className="font-bold text-gray-200">
                          {listing.listed_qty} {listing.listed_qty === 1 ? "unit" : "units"}
                        </div>
                        <span className="text-[10px] text-gray-500">Shown in store</span>
                      </td>

                      {/* Status Badge (Requirement 6) */}
                      <td className="px-4 py-4">
                        {isLive ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                            <span>Live on store</span>
                          </span>
                        ) : isPaused ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-gray-800 text-gray-400 border border-gray-700">
                            <span className="h-1.5 w-1.5 rounded-full bg-gray-500"></span>
                            <span>Hidden from buyers</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
                            <span>Updating...</span>
                          </span>
                        )}
                      </td>

                      {/* Single Edit Button (Requirement 9) */}
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => openEditModal(listing)}
                          className="px-3.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-white font-semibold text-xs transition-colors inline-flex items-center gap-1.5 border border-gray-700"
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                          <span>Edit</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Listing Modal (Plain English per Requirement 9) */}
      {editingListing && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-start justify-between pb-3 border-b border-gray-800">
              <div>
                <h3 className="text-lg font-bold text-white">Edit Store Listing</h3>
                <p className="text-xs text-gray-400 mt-0.5">{editingListing.product_title}</p>
              </div>
              <button
                onClick={() => setEditingListing(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">
                  Customer Selling Price ($)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-bold">$</span>
                  <input
                    type="number"
                    step="0.01"
                    value={editPrice}
                    onChange={(e) => setEditPrice(e.target.value)}
                    className="w-full pl-8 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <p className="text-[11px] text-gray-500 mt-1">What buyers will pay on {editingListing.marketplace_name}.</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">
                  Stock Shown to Buyers (Quantity)
                </label>
                <input
                  type="number"
                  value={editQty}
                  onChange={(e) => setEditQty(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[11px] text-gray-500 mt-1">How many units the marketplace shows as available.</p>
              </div>

              {/* Visibility / Hide Toggle */}
              <div className="p-3.5 bg-gray-900/60 rounded-xl border border-gray-800 flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-white">Visibility on Store</div>
                  <div className="text-[11px] text-gray-400">
                    {editingListing.status === "ACTIVE" 
                      ? "Currently visible to online buyers" 
                      : "Currently hidden from online buyers"}
                  </div>
                </div>

                <button
                  onClick={() => handleToggleHide(editingListing)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                    editingListing.status === "ACTIVE"
                      ? "bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 border border-rose-500/30"
                      : "bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 border border-emerald-500/30"
                  }`}
                >
                  {editingListing.status === "ACTIVE" ? "Hide from Buyers" : "Make Live Again"}
                </button>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-800 flex items-center justify-end gap-3">
              <button
                onClick={() => setEditingListing(null)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={savingEdit}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-50"
              >
                {savingEdit ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List a Product Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-800">
              <div>
                <h3 className="text-lg font-bold text-white">List a Product in Your Store</h3>
                <p className="text-xs text-gray-400 mt-0.5">Select an item from your wholesale catalog to sell.</p>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleAddSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">
                  1. Choose Product to Sell
                </label>
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
                >
                  {catalogProducts.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title} (Cost: ${Number(p.lowest_cost || 0).toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">
                  2. Choose Store to Sell On
                </label>
                <select
                  value={selectedMarketplaceId}
                  onChange={(e) => setSelectedMarketplaceId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
                >
                  {marketplaces.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20 text-xs text-indigo-300">
                <div className="font-bold mb-0.5">Automated Price & Stock:</div>
                <span>Your pricing rule markup and safety buffer will be applied automatically.</span>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingListing}
                  className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                >
                  {addingListing ? "Publishing..." : "Start Selling"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
