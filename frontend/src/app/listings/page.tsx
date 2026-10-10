"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw,
  Store,
  Plus,
  Edit3,
  X,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertTriangle,
  Trash2
} from "lucide-react";
import { fetchApi, Listing } from "@/lib/api";


const STATIC_ALL_TAB = { id: "ALL", name: "All Stores" };

export default function ListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState("ALL");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [deleteConfirmListing, setDeleteConfirmListing] = useState<Listing | null>(null);
  const [deletingListingId, setDeletingListingId] = useState<number | null>(null);
  const [checkingStatusId, setCheckingStatusId] = useState<number | null>(null);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [reconciling, setReconciling] = useState(false);

  // Dynamic marketplace tabs: "All Stores" + one tab per connected marketplace
  const marketplaceTabs = [
    STATIC_ALL_TAB,
    ...marketplaces.map((m) => ({ id: String(m.id), name: m.name })),
  ];

  const handleReconcile = async () => {
    setReconciling(true);
    try {
      const shopifyMarket = marketplaces.find(m => m.name.toLowerCase().includes("shopify"));
      if (!shopifyMarket) {
        setFeedback("No Shopify store connected yet. Connect one on the Marketplaces page first.");
        return;
      }
      const res = await fetchApi<{ success: boolean; synced_count: number; message: string }>(`/listings/reconcile-store/${shopifyMarket.id}`, { method: "POST" });
      setFeedback(res.message || "Successfully synced store listings!");
      await loadListings();
    } catch (err: any) {
      setFeedback("Failed to sync store listings: " + (err.message || String(err)));
    } finally {
      setReconciling(false);
    }
  };

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

  const loadMarketplaces = async () => {
    try {
      const mktRes = await fetchApi<any[]>("/marketplaces");
      setMarketplaces(mktRes);
    } catch (err) {
      console.error("Failed to load marketplaces:", err);
    }
  };

  useEffect(() => {
    loadListings();
    loadMarketplaces();
  }, []);

  const handleToggleHide = async (listing: Listing) => {
    const shouldHide = listing.status === "ACTIVE";
    const actionEndpoint = shouldHide ? `/listings/${listing.id}/withdraw` : `/listings/${listing.id}/reactivate`;
    try {
      await fetchApi(actionEndpoint, { method: "POST" });
      setFeedback(shouldHide ? "Product is now hidden from buyers." : "Product is now live on your store!");
      setTimeout(() => setFeedback(null), 3500);
      await loadListings();
    } catch (err: any) {
      setFeedbackError("Action failed: " + err.message);
      setTimeout(() => setFeedbackError(null), 8000);
    }
  };

  const handleCheckRealStatus = async (listing: Listing) => {
    setCheckingStatusId(listing.id);
    try {
      const res = await fetchApi<{ check_method: string; result: any; feed_id?: string }>(
        `/listings/${listing.id}/real-status`
      );
      const r = res.result || {};
      if (res.check_method === "feed_status") {
        const feedStatus = r.FeedStatus || r.status || JSON.stringify(r).slice(0, 200);
        setFeedback(`Real status from Walmart's feed (${res.feed_id}): ${feedStatus}`);
      } else if (r.error) {
        setFeedbackError(`Still not live on ${listing.marketplace_name || "the store"}: ${r.error}`);
      } else {
        setFeedback(`Live on ${listing.marketplace_name || "the store"}: ${r.status || "confirmed present"}.`);
      }
      setTimeout(() => { setFeedback(null); setFeedbackError(null); }, 8000);
    } catch (err: any) {
      setFeedbackError("Could not check real status: " + err.message);
      setTimeout(() => setFeedbackError(null), 8000);
    } finally {
      setCheckingStatusId(null);
    }
  };

  const handleDeleteListing = async (listing: Listing) => {
    try {
      setDeletingListingId(listing.id);
      await fetchApi(`/listings/${listing.id}`, { method: "DELETE" });
      setFeedback(`Product removed from ${listing.marketplace_name || "store"}. You can re-add it anytime.`);
      setTimeout(() => setFeedback(null), 3500);
      setDeleteConfirmListing(null);
      await loadListings();
    } catch (err: any) {
      setFeedbackError("Failed to remove product: " + err.message);
      setTimeout(() => setFeedbackError(null), 8000);
    } finally {
      setDeletingListingId(null);
    }
  };

  const filteredListings = listings.filter((l) => {
    if (selectedTab === "ALL") return true;
    // selectedTab is the marketplace id (as string); match by id
    return String(l.marketplace_id) === selectedTab;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header - Unboxed on canvas */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-brand font-normal text-[#0a0a0a]">Your Online Stores</h1>
          <p className="text-sm text-[#767676] mt-1 max-w-2xl leading-relaxed">
            See and manage all products currently listed for sale across your connected marketplaces.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => router.push("/catalog")}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium transition-all"
            title="Browse the catalog and list a product using the same product details view everywhere in the app"
          >
            <Plus className="h-4 w-4" />
            <span>List a Product</span>
          </button>
          <button
            onClick={handleReconcile}
            disabled={reconciling}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#1a1a1a] rounded-lg text-xs font-medium transition-all border border-gray-300"
            title="Pull existing products and statuses directly from connected store"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-[#767676] ${reconciling ? "animate-spin" : ""}`} />
            <span>{reconciling ? "Syncing Store..." : "Sync Store Listings"}</span>
          </button>
          <button
            onClick={loadListings}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-gray-50 text-[#1a1a1a] rounded-lg text-xs font-medium transition-all border border-gray-300"
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
      {feedbackError && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-300 text-rose-900 flex items-center gap-2 text-xs font-semibold">
          <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
          <span>{feedbackError}</span>
        </div>
      )}

      {/* Marketplace Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {marketplaceTabs.map((tab) => {
          const isActive = selectedTab === tab.id;
          const count = listings.filter((l) => {
            if (tab.id === "ALL") return true;
            return String(l.marketplace_id) === tab.id;
          }).length;

          return (
            <button
              key={tab.id}
              onClick={() => setSelectedTab(tab.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-2 whitespace-nowrap ${
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
      <div className="bg-white rounded-lg overflow-hidden border border-gray-100">
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
                        <button
                          type="button"
                          onClick={() => router.push(`/catalog?openProduct=${listing.product_id}`)}
                          className="max-w-md text-left group"
                          title="Opens the same product details view used everywhere in the app"
                        >
                          <div className="line-clamp-1 font-semibold group-hover:underline group-hover:text-[#A8560A] transition-colors">
                            {listing.product_title || "Unnamed Product"}
                          </div>
                          <div className="text-[11px] text-[#767676] font-normal mt-0.5">
                            Code: <span className="font-mono text-[#A8560A] font-medium">{listing.product_sku || "N/A"}</span>
                          </div>
                        </button>
                      </td>

                      {/* Store Channel */}
                      <td className="px-4 py-3.5">
                        <span className="text-xs font-medium px-2.5 py-0.5 rounded bg-gray-100 border border-gray-200 text-[#1a1a1a]">
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
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                            <span>Live on store</span>
                          </span>
                        ) : isPaused ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                            <span className="h-1.5 w-1.5 rounded-full bg-gray-400"></span>
                            <span>Hidden from buyers</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
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
                            className={`px-2.5 py-1.5 rounded-lg border text-xs transition-colors font-medium inline-flex items-center gap-1 ${
                              isLive 
                                ? "bg-white border-gray-300 text-gray-600 hover:text-rose-600 hover:border-rose-300" 
                                : "bg-emerald-50 border-emerald-300 text-emerald-800 hover:bg-emerald-100"
                            }`}
                            title={isLive ? "Hide this product from buyers" : "Make this product live again"}
                          >
                            {isLive ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                            <span>{isLive ? "Hide" : "Unhide"}</span>
                          </button>

                          {!isLive && !isPaused && (
                            <button
                              onClick={() => handleCheckRealStatus(listing)}
                              disabled={checkingStatusId === listing.id}
                              className="px-2.5 py-1.5 rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs transition-colors inline-flex items-center gap-1 font-medium disabled:opacity-50"
                              title="Ask the real marketplace what actually happened, instead of trusting our stored status"
                            >
                              <RefreshCw className={`h-3.5 w-3.5 ${checkingStatusId === listing.id ? "animate-spin" : ""}`} />
                              <span>{checkingStatusId === listing.id ? "Checking..." : "Check Real Status"}</span>
                            </button>
                          )}

                          <button
                            onClick={() => router.push(`/catalog?openProduct=${listing.product_id}`)}
                            className="px-3 py-1.5 rounded-lg bg-white hover:bg-gray-50 text-[#0a0a0a] font-medium text-xs transition-colors inline-flex items-center gap-1.5 border border-gray-300"
                            title="Opens the same product details view used everywhere in the app"
                          >
                            <Edit3 className="h-3.5 w-3.5 text-[#767676]" />
                            <span>Edit</span>
                          </button>

                          <button
                            onClick={() => setDeleteConfirmListing(listing)}
                            className="px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-rose-50 hover:border-rose-300 hover:text-rose-600 text-gray-400 text-xs transition-colors inline-flex items-center gap-1 font-medium"
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

      {/* Remove Listing Confirmation Modal */}
      {deleteConfirmListing && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-[#FAFAF8] border border-gray-200 rounded-lg max-w-md w-full p-6 shadow-xl space-y-4">
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
                {(deleteConfirmListing.marketplace_name || "").toLowerCase().includes("walmart") ? (
                  <li className="text-rose-700 font-medium">
                    This permanently retires the item from Walmart's own catalog (not just a stock pause) — to sell it there again later, it would need to be listed from scratch.
                  </li>
                ) : (
                  <li>It will be delisted and withdrawn from {deleteConfirmListing.marketplace_name || "the store"}.</li>
                )}
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
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
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
