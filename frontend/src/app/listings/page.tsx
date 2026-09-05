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
  CheckCircle2,
  Sparkles
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
    const actionEndpoint = shouldHide ? `/listings/${listing.id}/withdraw` : `/listings/${listing.id}/reactivate`;
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

  const filteredListings = listings.filter((l) => {
    if (selectedTab === "ALL") return true;
    return l.marketplace_name?.toLowerCase().includes(selectedTab.toLowerCase());
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header - Unboxed on canvas */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-[#0a0a0a] tracking-tight">Your Online Stores</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">
              Live Selling
            </span>
          </div>
          <p className="text-sm text-[#767676] mt-1 max-w-2xl leading-relaxed">
            See and manage all products currently listed for sale across your connected marketplaces.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium transition-all shadow-sm"
          >
            <Plus className="h-4 w-4" />
            <span>List a Product</span>
          </button>
          <button
            onClick={loadListings}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#1a1a1a] rounded-lg text-xs font-medium transition-all border border-gray-300 shadow-sm"
          >
            <RefreshCw className="h-3.5 w-3.5 text-[#767676]" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-900 flex items-center gap-2 text-xs font-semibold">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Marketplace Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
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
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 whitespace-nowrap shadow-sm ${
                isActive
                  ? "bg-[#0a0a0a] text-white"
                  : "bg-white text-[#767676] hover:text-[#0a0a0a] border border-gray-300 hover:bg-gray-50"
              }`}
            >
              <span>{tab.name}</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                isActive ? "bg-white/20 text-white" : "bg-gray-100 text-gray-600"
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Simplified Listings Table */}
      <div className="bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-[#1a1a1a]">
            <thead className="bg-gray-50/80 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
              <tr>
                <th className="px-6 py-3.5">Product Name</th>
                <th className="px-4 py-3.5">Store</th>
                <th className="px-4 py-3.5">Selling Price</th>
                <th className="px-4 py-3.5">Stock for Buyers</th>
                <th className="px-4 py-3.5">Status</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-20 text-[#767676]">
                    Loading your store listings...
                  </td>
                </tr>
              ) : filteredListings.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-20 text-[#767676]">
                    <Store className="h-8 w-8 mx-auto text-[#767676] mb-2 opacity-50" />
                    <div className="font-semibold text-[#0a0a0a]">No products listed in this store yet.</div>
                    <p className="text-xs text-[#767676] mt-1">Click &apos;List a Product&apos; above or go to &apos;Products to Sell&apos; to add items.</p>
                  </td>
                </tr>
              ) : (
                filteredListings.map((listing) => {
                  const isLive = listing.status === "ACTIVE";
                  const isPaused = listing.status === "PAUSED" || listing.status === "WITHDRAWN";

                  return (
                    <tr key={listing.id} className="hover:bg-gray-50/60 transition-colors">
                      {/* Product Name */}
                      <td className="px-6 py-3.5 font-medium text-[#0a0a0a]">
                        <div className="max-w-md">
                          <div className="line-clamp-1 font-semibold">{listing.product_title || "Enterprise Product"}</div>
                          <div className="text-[11px] text-[#767676] font-normal mt-0.5">
                            Code: <span className="font-mono text-[#905831] font-medium">{listing.product_sku || "N/A"}</span>
                          </div>
                        </div>
                      </td>

                      {/* Store Channel */}
                      <td className="px-4 py-3.5">
                        <span className="text-xs font-medium px-2.5 py-0.5 rounded-md bg-gray-100 border border-gray-200 text-[#1a1a1a]">
                          {listing.marketplace_name || "Online Store"}
                        </span>
                      </td>

                      {/* Selling Price */}
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-[#0a0a0a] text-sm">
                          ${Number(listing.selling_price).toFixed(2)}
                        </div>
                        <span className="text-[11px] text-[#767676]">Price customers pay</span>
                      </td>

                      {/* Stock Shown to Buyers */}
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-[#1a1a1a] text-sm">
                          {listing.listed_qty} {listing.listed_qty === 1 ? "unit" : "units"}
                        </div>
                        <span className="text-[11px] text-[#767676]">Shown in store</span>
                      </td>

                      {/* Status Badge */}
                      <td className="px-4 py-3.5">
                        {isLive ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                            <span>Live on store</span>
                          </span>
                        ) : isPaused ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                            <span className="h-1.5 w-1.5 rounded-full bg-gray-400"></span>
                            <span>Hidden from buyers</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-500"></span>
                            <span>Updating...</span>
                          </span>
                        )}
                      </td>

                      {/* Action Buttons: Hide/Unhide & Edit */}
                      <td className="px-6 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleHide(listing)}
                            className={`px-2.5 py-1.5 rounded-lg border text-xs transition-colors shadow-sm font-medium inline-flex items-center gap-1 ${
                              isLive 
                                ? "bg-white border-gray-300 text-gray-600 hover:text-rose-600 hover:border-rose-300" 
                                : "bg-emerald-50 border-emerald-300 text-emerald-800 hover:bg-emerald-100"
                            }`}
                            title={isLive ? "Hide this product from buyers" : "Make this product live again"}
                          >
                            {isLive ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                            <span>{isLive ? "Hide" : "Unhide"}</span>
                          </button>

                          <button
                            onClick={() => openEditModal(listing)}
                            className="px-3 py-1.5 rounded-lg bg-white hover:bg-gray-50 text-[#0a0a0a] font-medium text-xs transition-colors inline-flex items-center gap-1.5 border border-gray-300 shadow-sm"
                          >
                            <Edit3 className="h-3.5 w-3.5 text-[#767676]" />
                            <span>Edit</span>
                          </button>
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

      {/* Edit Listing Modal */}
      {editingListing && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-xl max-w-lg w-full p-6 shadow-xl space-y-5">
            <div className="flex items-start justify-between pb-3 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-bold text-[#0a0a0a]">Edit Store Listing</h3>
                <p className="text-xs text-[#767676] mt-0.5">{editingListing.product_title}</p>
              </div>
              <button
                onClick={() => setEditingListing(null)}
                className="p-1.5 rounded-lg text-[#767676] hover:text-[#0a0a0a] hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                  Customer Selling Price ($)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#767676] font-medium text-sm">$</span>
                  <input
                    type="number"
                    step="0.01"
                    value={editPrice}
                    onChange={(e) => setEditPrice(e.target.value)}
                    className="w-full pl-7 pr-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-[#0a0a0a] font-semibold focus:outline-none focus:border-[#0a0a0a]"
                  />
                </div>
                <p className="text-[11px] text-[#767676] mt-1">What buyers will pay on {editingListing.marketplace_name}.</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                  Stock Shown to Buyers (Quantity)
                </label>
                <input
                  type="number"
                  value={editQty}
                  onChange={(e) => setEditQty(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-[#0a0a0a] font-semibold focus:outline-none focus:border-[#0a0a0a]"
                />
                <p className="text-[11px] text-[#767676] mt-1">How many units the marketplace shows as available.</p>
              </div>

              {/* Visibility / Hide Toggle */}
              <div className="p-3.5 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-[#0a0a0a]">Visibility on Store</div>
                  <div className="text-[11px] text-[#767676] mt-0.5">
                    {editingListing.status === "ACTIVE" 
                      ? "Currently visible to online buyers" 
                      : "Currently hidden from online buyers"}
                  </div>
                </div>

                <button
                  onClick={() => handleToggleHide(editingListing)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shadow-sm ${
                    editingListing.status === "ACTIVE"
                      ? "bg-rose-50 text-rose-800 hover:bg-rose-100 border border-rose-200"
                      : "bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200"
                  }`}
                >
                  {editingListing.status === "ACTIVE" ? "Hide from Buyers" : "Make Live Again"}
                </button>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-200 flex items-center justify-end gap-2.5">
              <button
                onClick={() => setEditingListing(null)}
                className="px-4 py-2 text-xs font-medium text-[#767676] hover:text-[#0a0a0a]"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={savingEdit}
                className="px-4 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium transition-all shadow-sm disabled:opacity-50"
              >
                {savingEdit ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List a Product Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-bold text-[#0a0a0a]">List a Product in Your Store</h3>
                <p className="text-xs text-[#767676] mt-0.5">Select an item from your wholesale catalog to sell.</p>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1.5 rounded-lg text-[#767676] hover:text-[#0a0a0a] hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleAddSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                  1. Choose Product to Sell
                </label>
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] font-medium focus:outline-none focus:border-[#0a0a0a]"
                >
                  {catalogProducts.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title} (Cost: ${Number(p.lowest_cost || 0).toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                  2. Choose Store to Sell On
                </label>
                <select
                  value={selectedMarketplaceId}
                  onChange={(e) => setSelectedMarketplaceId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] font-medium focus:outline-none focus:border-[#0a0a0a]"
                >
                  {marketplaces.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="p-3 bg-[#905831]/[0.06] rounded-lg border border-[#905831]/20 text-xs text-[#905831]">
                <div className="font-semibold mb-0.5 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" />
                  Automated Price & Stock:
                </div>
                <span>Your pricing rule markup and safety buffer will be applied automatically.</span>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-medium text-[#767676] hover:text-[#0a0a0a]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingListing}
                  className="px-5 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium transition-all shadow-sm disabled:opacity-50"
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
