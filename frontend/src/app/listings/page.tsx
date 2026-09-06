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
  Sparkles,
  Trash2
} from "lucide-react";
import { fetchApi, Listing, Product } from "@/lib/api";

const MARKETPLACE_TABS = [
  { id: "ALL", name: "All Stores" },
  { id: "eBay", name: "eBay" },
  { id: "Walmart", name: "Walmart" },
  { id: "Amazon", name: "Amazon" },
  { id: "Shopify", name: "Shopify" },
  { id: "Newegg", name: "Newegg" },
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
  const [deleteConfirmListing, setDeleteConfirmListing] = useState<Listing | null>(null);
  const [deletingListingId, setDeletingListingId] = useState<number | null>(null);

  // Add Product to Store state
  const [showAddModal, setShowAddModal] = useState(false);
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | "">("");
  const [selectedMarketplaceId, setSelectedMarketplaceId] = useState<number>(1);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [addingListing, setAddingListing] = useState(false);
  const [addCustomPrice, setAddCustomPrice] = useState("");

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

  const updateAddPrice = (pId: number, mId: number) => {
    const existing = listings.find(
      l => l.product_id === pId && 
           (l.marketplace_id === mId || 
            (l.marketplace_name || '').toLowerCase() === marketplaces.find(m => m.id === mId)?.name.toLowerCase())
    );
    if (existing && Number(existing.selling_price) > 0) {
      setAddCustomPrice(Number(existing.selling_price).toFixed(2));
    } else {
      const prod = catalogProducts.find(p => p.id === pId);
      if (prod) {
        const cost = Number(prod.lowest_cost || 0);
        setAddCustomPrice((cost * 1.15).toFixed(2));
      }
    }
  };

  useEffect(() => {
    if (selectedProductId) {
      updateAddPrice(Number(selectedProductId), selectedMarketplaceId);
    }
  }, [selectedProductId, selectedMarketplaceId, catalogProducts, listings, marketplaces]);

  const randomizeAddPrice = (cost: number) => {
    const mult = 1 + (Math.floor(Math.random() * 25) + 10) / 100; // 10% to 35% margin
    const p = Math.floor(cost * mult) + 0.99;
    setAddCustomPrice(p.toFixed(2));
  };

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

  const handleDeleteListing = async (listing: Listing) => {
    try {
      setDeletingListingId(listing.id);
      await fetchApi(`/listings/${listing.id}`, { method: "DELETE" });
      setFeedback(`Product removed from ${listing.marketplace_name || "store"}. You can re-add it anytime.`);
      setTimeout(() => setFeedback(null), 3500);
      setDeleteConfirmListing(null);
      if (editingListing && editingListing.id === listing.id) {
        setEditingListing(null);
      }
      await loadListings();
    } catch (err: any) {
      alert("Failed to remove product: " + err.message);
    } finally {
      setDeletingListingId(null);
    }
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProductId) return;

    setAddingListing(true);
    try {
      const targetStore = marketplaces.find(m => m.id === selectedMarketplaceId);
      const isAlreadyListed = listings.some(
        l => l.product_id === Number(selectedProductId) && 
             (l.marketplace_id === selectedMarketplaceId || 
              (l.marketplace_name || '').toLowerCase() === (targetStore?.name || '').toLowerCase())
      );

      await fetchApi("/listings/publish", {
        method: "POST",
        body: JSON.stringify({
          product_id: Number(selectedProductId),
          marketplace_id: selectedMarketplaceId,
          custom_price: addCustomPrice ? Number(addCustomPrice) : undefined,
        }),
      });
      setShowAddModal(false);
      const mName = targetStore?.name || "store";
      setFeedback(isAlreadyListed ? `Price & stock updated on ${mName}!` : `Product added to ${mName} successfully!`);
      setTimeout(() => setFeedback(null), 3500);
      loadListings();
    } catch (err: any) {
      alert("Could not save listing: " + err.message);
    } finally {
      setAddingListing(false);
    }
  };

  const filteredListings = listings.filter((l) => {
    if (selectedTab === "ALL") return true;
    const mName = (l.marketplace_name || "").toLowerCase();
    const tabTarget = selectedTab.toLowerCase();
    return mName.includes(tabTarget) || tabTarget.includes(mName);
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
            const mName = (l.marketplace_name || "").toLowerCase();
            const tabTarget = tab.id.toLowerCase();
            return mName.includes(tabTarget) || tabTarget.includes(mName);
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

                          <button
                            onClick={() => setDeleteConfirmListing(listing)}
                            className="px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-rose-50 hover:border-rose-300 hover:text-rose-600 text-gray-400 text-xs transition-colors inline-flex items-center gap-1 shadow-sm font-medium"
                            title="Completely remove product from this store"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            <span>Remove</span>
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
                  onChange={(e) => {
                    const pId = Number(e.target.value);
                    setSelectedProductId(pId);
                    updateAddPrice(pId, selectedMarketplaceId);
                  }}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] font-medium focus:outline-none focus:border-[#0a0a0a]"
                >
                  {catalogProducts.map((p) => {
                    const listedCount = listings.filter(l => l.product_id === p.id).length;
                    return (
                      <option key={p.id} value={p.id}>
                        {p.title} (Cost: ${Number(p.lowest_cost || 0).toFixed(2)}) {listedCount > 0 ? `[In ${listedCount} Store${listedCount > 1 ? "s" : ""}]` : ""}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1a1a1a] mb-1">
                  2. Choose Store to Sell On
                </label>
                <select
                  value={selectedMarketplaceId}
                  onChange={(e) => {
                    const mId = Number(e.target.value);
                    setSelectedMarketplaceId(mId);
                    updateAddPrice(Number(selectedProductId), mId);
                  }}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] font-medium focus:outline-none focus:border-[#0a0a0a]"
                >
                  {marketplaces.map((m) => {
                    const existing = listings.find(
                      l => l.product_id === Number(selectedProductId) && (l.marketplace_id === m.id || (l.marketplace_name || '').toLowerCase() === m.name.toLowerCase())
                    );
                    return (
                      <option key={m.id} value={m.id}>
                        {m.name} {existing ? `— Listed ($${Number(existing.selling_price).toFixed(2)})` : ""}
                      </option>
                    );
                  })}
                </select>
              </div>

              {/* 3. Selling Price (Custom or Random) */}
              {(() => {
                const prod = catalogProducts.find(p => p.id === Number(selectedProductId));
                const cost = Number(prod?.lowest_cost || 0);
                const formulaPrice = (cost * 1.15).toFixed(2);
                return (
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-semibold text-[#1a1a1a]">
                        3. Selling Price ($)
                      </label>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => randomizeAddPrice(cost || 50)}
                          className="text-[11px] text-[#905831] hover:text-[#0a0a0a] font-medium flex items-center gap-1 bg-[#905831]/10 px-2 py-0.5 rounded border border-[#905831]/20 transition-colors"
                          title="Generate a random price with 10%-35% margin"
                        >
                          <Sparkles className="h-3 w-3" />
                          <span>Random Price</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setAddCustomPrice(formulaPrice)}
                          className="text-[11px] text-gray-500 hover:text-gray-800 underline font-medium"
                          title="Reset to rule formula (+15% margin)"
                        >
                          Reset Rule
                        </button>
                      </div>
                    </div>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#767676] font-medium text-sm">$</span>
                      <input
                        type="number"
                        step="0.01"
                        value={addCustomPrice}
                        onChange={(e) => setAddCustomPrice(e.target.value)}
                        placeholder="Enter custom selling price..."
                        className="w-full pl-7 pr-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-[#0a0a0a] font-semibold focus:outline-none focus:border-[#0a0a0a]"
                      />
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-[#767676] mt-1">
                      <span>Wholesale cost: ${cost.toFixed(2)}</span>
                      <span>Formula (+15%): ${formulaPrice}</span>
                    </div>
                  </div>
                );
              })()}

              {(() => {
                const targetStore = marketplaces.find(m => m.id === selectedMarketplaceId);
                const isAlreadyListed = listings.some(
                  l => l.product_id === Number(selectedProductId) && (l.marketplace_id === selectedMarketplaceId || (l.marketplace_name || '').toLowerCase() === (targetStore?.name || '').toLowerCase())
                );

                return isAlreadyListed ? (
                  <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-900 space-y-1">
                    <div className="font-semibold flex items-center gap-1.5 text-amber-800">
                      <RefreshCw className="h-3.5 w-3.5" />
                      <span>Already Listed on {targetStore?.name || "this store"}</span>
                    </div>
                    <p className="text-[11px] text-amber-800/80">
                      Submitting will update the price and stock for this existing listing without creating a duplicate.
                    </p>
                  </div>
                ) : (
                  <div className="p-3 bg-[#905831]/[0.06] rounded-lg border border-[#905831]/20 text-xs text-[#905831]">
                    <div className="font-semibold mb-0.5 flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5" />
                      Automated Price & Stock Sync:
                    </div>
                    <span className="text-[11px] text-[#767676]">Your selling price will be published and maintained across sales channels.</span>
                  </div>
                );
              })()}

              <div className="pt-3 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-medium text-[#767676] hover:text-[#0a0a0a]"
                >
                  Cancel
                </button>
                {(() => {
                  const targetStore = marketplaces.find(m => m.id === selectedMarketplaceId);
                  const isAlreadyListed = listings.some(
                    l => l.product_id === Number(selectedProductId) && (l.marketplace_id === selectedMarketplaceId || (l.marketplace_name || '').toLowerCase() === (targetStore?.name || '').toLowerCase())
                  );

                  return (
                    <button
                      type="submit"
                      disabled={addingListing}
                      className="px-5 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium transition-all shadow-sm disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isAlreadyListed ? <RefreshCw className="h-3.5 w-3.5" /> : <Store className="h-3.5 w-3.5" />}
                      <span>
                        {addingListing 
                          ? (isAlreadyListed ? "Updating..." : "Publishing...") 
                          : (isAlreadyListed ? "Update Price on Store" : "Start Selling")}
                      </span>
                    </button>
                  );
                })()}
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Remove Listing Confirmation Modal */}
      {deleteConfirmListing && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5 text-rose-600">
                <div className="w-9 h-9 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center">
                  <Trash2 className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#0a0a0a]">Remove from Store?</h3>
                  <p className="text-xs text-[#767676]">{deleteConfirmListing.marketplace_name || "Sales Channel"}</p>
                </div>
              </div>
              <button
                onClick={() => setDeleteConfirmListing(null)}
                className="p-1 rounded-lg text-[#767676] hover:text-[#0a0a0a] hover:bg-gray-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="text-xs text-[#444444] space-y-2 bg-gray-50 p-3.5 rounded-lg border border-gray-200">
              <p className="font-medium text-[#0a0a0a]">
                Are you sure you want to remove <span className="font-bold">"{deleteConfirmListing.product_title}"</span>?
              </p>
              <ul className="list-disc list-inside space-y-1 text-[#666666]">
                <li>It will be delisted and withdrawn from {deleteConfirmListing.marketplace_name || "the store"}.</li>
                <li>It will be removed from your Active Stores table.</li>
                <li>You can add it again from the Wholesale Catalog at any time.</li>
              </ul>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setDeleteConfirmListing(null)}
                className="px-4 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg text-xs font-medium text-[#0a0a0a] transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deletingListingId === deleteConfirmListing.id}
                onClick={() => handleDeleteListing(deleteConfirmListing)}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-medium transition-colors shadow-sm disabled:opacity-50"
              >
                {deletingListingId === deleteConfirmListing.id ? "Removing..." : "Yes, Remove from Store"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
