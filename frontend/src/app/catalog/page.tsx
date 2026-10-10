"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Search,
  Filter,
  Layers,
  ChevronLeft,
  ChevronRight,
  X,
  Truck,
  Store,
  Check,
  CheckCircle2,
  Sparkles,
  RefreshCw,
  Camera,
  ImageIcon,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";
import { fetchApi, Product, Listing } from "@/lib/api";

export default function CatalogPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBrand, setSelectedBrand] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [inStockOnly, setInStockOnly] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [walmartMatchStatus, setWalmartMatchStatus] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const [filterOptions, setFilterOptions] = useState<{ brands: string[]; categories: string[] }>({
    brands: [],
    categories: [],
  });

  // -- Single unified product drawer --
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishingId, setPublishingId] = useState<number | null>(null);
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<number>(1);
  const [existingListingsMap, setExistingListingsMap] = useState<
    Record<number, { id: number; marketplace_id: number; marketplace_name: string; status: string; selling_price: number }[]>
  >({});
  const [drawerCustomPrice, setDrawerCustomPrice] = useState<string>("");
  const [drawerCustomTitle, setDrawerCustomTitle] = useState<string>("");
  const [drawerCustomDescription, setDrawerCustomDescription] = useState<string>("");
  const [drawerCustomWeight, setDrawerCustomWeight] = useState<string>("");
  const [weightLookupLoading, setWeightLookupLoading] = useState(false);
  const [weightLookupNote, setWeightLookupNote] = useState<string | null>(null);
  const [showDrawerContentEdit, setShowDrawerContentEdit] = useState<boolean>(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  // -- Photo picker --
  const [imageSuggestions, setImageSuggestions] = useState<string[]>([]);
  const [selectedImageUrl, setSelectedImageUrl] = useState<string>("");
  const [loadingImages, setLoadingImages] = useState(false);
  const [imageSearchQuery, setImageSearchQuery] = useState<string>("");
  const [customImageUrlInput, setCustomImageUrlInput] = useState<string>("");
  const [savingImage, setSavingImage] = useState(false);
  const [imageSaveSuccess, setImageSaveSuccess] = useState<string | null>(null);

  const randomizeDrawerPrice = (cost: number) => {
    const mult = 1 + (Math.floor(Math.random() * 25) + 10) / 100;
    const p = Math.floor(cost * mult) + 0.99;
    setDrawerCustomPrice(p.toFixed(2));
  };

  const loadListingsMap = async () => {
    try {
      const res = await fetchApi<{ items: Listing[] }>("/listings?page=1&page_size=100");
      const map: Record<number, { id: number; marketplace_id: number; marketplace_name: string; status: string; selling_price: number }[]> = {};
      res.items.forEach((l) => {
        if (!map[l.product_id]) map[l.product_id] = [];
        map[l.product_id].push({
          id: l.id,
          marketplace_id: l.marketplace_id,
          marketplace_name: l.marketplace_name || "Store",
          status: l.status,
          selling_price: Number(l.selling_price || 0),
        });
      });
      setExistingListingsMap(map);
    } catch (err) {
      console.error("Could not load listings map:", err);
    }
  };

  const fetchImageSuggestions = async (productId: number, queryOverride?: string) => {
    setLoadingImages(true);
    try {
      const qParam = queryOverride ? `?q=${encodeURIComponent(queryOverride)}` : "";
      const res = await fetchApi<{ product_id: number; suggestions: string[]; query_used?: string }>(
        `/products/${productId}/image-suggestions${qParam}`
      );
      const suggestions = res.suggestions || [];
      setImageSuggestions(suggestions);
      if (suggestions.length > 0 && (!selectedImageUrl || queryOverride)) {
        setSelectedImageUrl(suggestions[0]);
      }
      if (res.query_used && !queryOverride) {
        setImageSearchQuery(res.query_used);
      }
    } catch (err) {
      console.error("Could not fetch image suggestions:", err);
    } finally {
      setLoadingImages(false);
    }
  };

  const handleSaveProductImage = async (imageUrlToSave: string) => {
    if (!selectedProduct || !imageUrlToSave) return;
    setSavingImage(true);
    setImageSaveSuccess(null);
    try {
      const updated = await fetchApi<Product>(`/products/${selectedProduct.id}/set-image`, {
        method: "POST",
        body: JSON.stringify({ image_url: imageUrlToSave }),
      });
      setSelectedProduct((prev) => (prev ? { ...prev, images: updated.images || [imageUrlToSave] } : null));
      setProducts((prev) =>
        prev.map((p) =>
          p.id === selectedProduct.id
            ? { ...p, images: updated.images || [imageUrlToSave] }
            : p
        )
      );
      setImageSaveSuccess("Photo saved as the permanent product image!");
      setTimeout(() => setImageSaveSuccess(null), 4000);
    } catch (err: any) {
      setPublishError("Failed to save image: " + err.message);
      setTimeout(() => setPublishError(null), 8000);
    } finally {
      setSavingImage(false);
    }
  };

  const handlePublishToChannel = async (
    product: Product,
    targetMarketplaceId: number,
    customPrice?: number,
    customTitle?: string,
    customDescription?: string,
    customImageUrl?: string,
    customWeightLbs?: number,
  ) => {
    setPublishingId(product.id);
    setPublishSuccess(null);
    setPublishError(null);
    try {
      const channel = marketplaces.find((m) => m.id === targetMarketplaceId);
      const channelName = channel ? channel.name : "Your Store";
      const isUpdate = (existingListingsMap[product.id] || []).some(
        (l) => l.marketplace_id === targetMarketplaceId
      );

      await fetchApi<any>("/listings/publish", {
        method: "POST",
        body: JSON.stringify({
          product_id: product.id,
          marketplace_id: targetMarketplaceId,
          custom_price: customPrice !== undefined && !isNaN(customPrice) ? customPrice : undefined,
          custom_title: customTitle?.trim() || undefined,
          custom_description: customDescription?.trim() || undefined,
          custom_image_url: customImageUrl || undefined,
          custom_weight_lbs: customWeightLbs !== undefined && !isNaN(customWeightLbs) && customWeightLbs > 0 ? customWeightLbs : undefined,
        }),
      });
      const priceText =
        customPrice !== undefined && !isNaN(customPrice) ? ` at $${customPrice.toFixed(2)}` : "";
      setPublishSuccess(
        isUpdate
          ? `Successfully updated "${customTitle || product.title}" on ${channelName}${priceText}!`
          : `Successfully listed "${customTitle || product.title}" on ${channelName}${priceText}!`
      );
      setTimeout(() => setPublishSuccess(null), 5000);
      setSelectedProduct(null);
      await loadListingsMap();
    } catch (err: any) {
      setPublishError(err.message || "Action failed. Please try again.");
      setTimeout(() => setPublishError(null), 8000);
    } finally {
      setPublishingId(null);
    }
  };

  /**
   * Opens the unified product drawer.
   * Called both from the product name click AND from the action button.
   */
  const handleOpenProductDrawer = (product: Product, currentListingsMap: typeof existingListingsMap, currentMarketplaces: typeof marketplaces, currentChannelId: number) => {
    setSelectedProduct(product);
    setDrawerCustomTitle(product.title || "");
    setDrawerCustomDescription(product.description || "");
    setShowDrawerContentEdit(false);

    const live = currentListingsMap[product.id] || [];
    const listedStoreIds = live.map((l) => l.marketplace_id);
    const unlisted = currentMarketplaces.filter((m) => !listedStoreIds.includes(m.id));
    const targetId = unlisted.length > 0 ? unlisted[0].id : (currentMarketplaces[0]?.id ?? currentChannelId);
    setSelectedChannelId(targetId);

    const existing = live.find((l) => l.marketplace_id === targetId);
    if (existing && existing.selling_price > 0) {
      setDrawerCustomPrice(existing.selling_price.toFixed(2));
    } else {
      const cost = Number(product.lowest_cost || 0);
      setDrawerCustomPrice((cost * 1.15).toFixed(2));
    }

    const realWeight = product.supplier_products
      ?.map((sp) => sp.shipping_info?.weight_lbs)
      .find((w) => w !== null && w !== undefined && Number(w) > 0);
    setDrawerCustomWeight(realWeight ? String(realWeight) : "");

    // Default search is exact title + brand (what the user actually typed
    // into their catalog, not a barcode) — more precise for the common case
    // where the title is specific. The UPC-anchored multi-tier algorithm
    // (merges UPC-alone/UPC+brand/UPC+brand+MPN, trusted-CDN filtered) is
    // available as a deliberate secondary action via the "Verified UPC
    // Search" button below, not the default.
    const defaultQuery = [product.title, product.brand].filter(Boolean).join(" ");
    setImageSearchQuery(defaultQuery);
    setCustomImageUrlInput("");
    setImageSaveSuccess(null);
    setImageSuggestions([]);
    setSelectedImageUrl(product.images?.[0] || "");
    fetchImageSuggestions(product.id, defaultQuery);
  };

  const toggleNotSelling = async (productId: number) => {
    const product = products.find((p) => p.id === productId);
    if (!product) return;
    const nextEnabled = !product.is_enabled;
    setProducts((prev) =>
      prev.map((p) => (p.id === productId ? { ...p, is_enabled: nextEnabled } : p))
    );
    try {
      await fetchApi(`/products/${productId}`, {
        method: "PUT",
        body: JSON.stringify({ is_enabled: nextEnabled }),
      });
    } catch (err: any) {
      setProducts((prev) =>
        prev.map((p) => (p.id === productId ? { ...p, is_enabled: !nextEnabled } : p))
      );
      setPublishError("Could not save this change: " + err.message);
      setTimeout(() => setPublishError(null), 8000);
    }
  };

  const loadProducts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      if (searchQuery.trim()) params.append("q", searchQuery.trim());
      if (selectedBrand) params.append("brand", selectedBrand);
      if (selectedCategory) params.append("category", selectedCategory);
      if (inStockOnly) params.append("in_stock", "true");
      if (selectedSupplierId) params.append("supplier_id", selectedSupplierId);
      if (minPrice) params.append("min_price", minPrice);
      if (maxPrice) params.append("max_price", maxPrice);
      if (walmartMatchStatus) params.append("walmart_match_status", walmartMatchStatus);

      const res = await fetchApi<{
        items: Product[];
        total: number;
        page: number;
        page_size: number;
        total_pages: number;
      }>(`/products?${params.toString()}`);

      setProducts(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err) {
      console.error("Failed to load catalog products:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApi<{ brands: string[]; categories: string[] }>("/products/filters/options")
      .then((data) => setFilterOptions(data))
      .catch((err) => console.error("Could not fetch filter options:", err));

    fetchApi<any[]>("/marketplaces")
      .then((res) => {
        setMarketplaces(res);
        if (res.length > 0) setSelectedChannelId(res[0].id);
      })
      .catch((err) => console.error("Could not fetch marketplaces:", err));

    fetchApi<any[]>("/suppliers")
      .then((res) => setSuppliers(res.map((s: any) => ({ id: s.id, name: s.name }))))
      .catch((err) => console.error("Could not fetch suppliers:", err));

    loadListingsMap();
  }, []);

  useEffect(() => {
    loadProducts();
  }, [page, selectedBrand, selectedCategory, inStockOnly, selectedSupplierId, walmartMatchStatus]);

  // Opens the same unified drawer when arriving via a deep link, e.g.
  // /catalog?openProduct=123 from the Listings page's "Edit"/"List a
  // Product" actions — so there is exactly one product-detail interface in
  // the whole app, not a second, different one duplicated on another page.
  useEffect(() => {
    const openProductId = searchParams.get("openProduct");
    if (!openProductId || marketplaces.length === 0) return;

    fetchApi<Product>(`/products/${openProductId}`)
      .then((product) => {
        handleOpenProductDrawer(product, existingListingsMap, marketplaces, selectedChannelId);
      })
      .catch((err) => console.error("Could not open requested product:", err))
      .finally(() => {
        router.replace("/catalog");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, marketplaces]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadProducts();
  };

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedBrand("");
    setSelectedCategory("");
    setInStockOnly(false);
    setSelectedSupplierId("");
    setMinPrice("");
    setMaxPrice("");
    setWalmartMatchStatus("");
    setPage(1);
  };

  const hasActiveFilters = Boolean(
    searchQuery || selectedBrand || selectedCategory || inStockOnly || selectedSupplierId || minPrice || maxPrice || walmartMatchStatus
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-brand font-normal text-[#0a0a0a]">Products to Sell</h1>
          <p className="text-sm text-[#767676] mt-1 max-w-2xl leading-relaxed">
            Browse all products provided by your suppliers. Pick what you want to sell and list them on your stores with one click.
          </p>
        </div>
        <div className="text-left sm:text-right self-start sm:self-auto">
          <span className="text-xs text-[#767676] block font-medium">Total Catalog Items</span>
          <span className="text-2xl font-bold tabular-nums text-[#0a0a0a]">{total.toLocaleString()}</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-white p-5 rounded-lg border border-gray-100 space-y-3.5">
        <div className="flex flex-col md:flex-row gap-3">
          <form onSubmit={handleSearchSubmit} className="flex-1 relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#767676]" />
            <input
              type="text"
              placeholder="Search products by title, brand, or product code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-[#1a1a1a] placeholder-[#767676] focus:outline-none focus:border-[#0a0a0a] focus:ring-2 focus:ring-[#0a0a0a]/[0.06] transition-all"
            />
          </form>
          <button
            onClick={() => { setPage(1); loadProducts(); }}
            className="px-6 py-2.5 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-sm font-medium transition-all shrink-0"
          >
            Find Products
          </button>
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-2.5 pt-3 border-t border-gray-100 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-[#1a1a1a]">
            <Filter className="h-3.5 w-3.5 text-[#D9720F]" />
            <span>Filter By:</span>
          </div>

          <select
            value={selectedBrand}
            onChange={(e) => { setSelectedBrand(e.target.value); setPage(1); }}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#1a1a1a] font-medium focus:outline-none focus:border-[#0a0a0a] focus:ring-2 focus:ring-[#0a0a0a]/[0.06]"
          >
            <option value="">All Brands</option>
            {filterOptions.brands.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>

          <select
            value={selectedCategory}
            onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#1a1a1a] font-medium focus:outline-none focus:border-[#0a0a0a] focus:ring-2 focus:ring-[#0a0a0a]/[0.06]"
          >
            <option value="">All Categories</option>
            {filterOptions.categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <select
            value={selectedSupplierId}
            onChange={(e) => { setSelectedSupplierId(e.target.value); setPage(1); }}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#1a1a1a] font-medium focus:outline-none focus:border-[#0a0a0a] focus:ring-2 focus:ring-[#0a0a0a]/[0.06]"
          >
            <option value="">All Suppliers</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          <select
            value={walmartMatchStatus}
            onChange={(e) => { setWalmartMatchStatus(e.target.value); setPage(1); }}
            title="Whether each product's UPC has a real match in Walmart's own catalog (required for MP_ITEM_MATCH listing)"
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#1a1a1a] font-medium focus:outline-none focus:border-[#0a0a0a] focus:ring-2 focus:ring-[#0a0a0a]/[0.06]"
          >
            <option value="">Walmart Match: Any</option>
            <option value="matchable">Walmart: Matchable</option>
            <option value="not_matchable">Walmart: Not Matchable</option>
            <option value="unchecked">Walmart: Not Checked Yet</option>
          </select>

          <div className="flex items-center gap-1.5 bg-white border border-gray-300 rounded-lg px-2 py-1">
            <span className="text-[11px] text-[#767676]">$</span>
            <input
              type="number" min="0" step="0.01" placeholder="Min"
              value={minPrice} onChange={(e) => setMinPrice(e.target.value)}
              onBlur={() => { setPage(1); loadProducts(); }}
              className="w-14 text-xs text-[#1a1a1a] focus:outline-none"
            />
            <span className="text-[#767676] text-[11px]">-</span>
            <span className="text-[11px] text-[#767676]">$</span>
            <input
              type="number" min="0" step="0.01" placeholder="Max"
              value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)}
              onBlur={() => { setPage(1); loadProducts(); }}
              className="w-14 text-xs text-[#1a1a1a] focus:outline-none"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none bg-white border border-gray-300 px-3 py-1.5 rounded-lg hover:border-gray-400 transition-colors">
            <input
              type="checkbox" checked={inStockOnly}
              onChange={(e) => { setInStockOnly(e.target.checked); setPage(1); }}
              className="rounded border-gray-300 h-3.5 w-3.5 cursor-pointer accent-[#0a0a0a]"
            />
            <span className="text-xs text-[#1a1a1a] font-medium">In Stock Only</span>
          </label>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 text-xs text-rose-700 hover:text-rose-800 px-3 py-1.5 bg-rose-50 rounded-lg border border-rose-200 transition-colors font-medium ml-auto"
            >
              <X className="h-3 w-3" />
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* Success Notification */}
      {publishSuccess && (
        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-900 flex items-center justify-between text-xs font-semibold">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>{publishSuccess} You can view and edit it anytime under &apos;Your Online Stores&apos;.</span>
          </div>
          <button onClick={() => setPublishSuccess(null)} className="text-emerald-800 hover:text-emerald-950">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Error Notification */}
      {publishError && (
        <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-300 text-rose-900 flex items-center justify-between text-xs font-semibold">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{publishError}</span>
          </div>
          <button onClick={() => setPublishError(null)} className="text-rose-800 hover:text-rose-950 shrink-0">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Products Table */}
      <div className="bg-white rounded-lg overflow-hidden border border-gray-100">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-[#1a1a1a]">
            <thead className="bg-gray-50/80 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
              <tr>
                <th className="px-6 py-3.5">Product</th>
                <th className="px-4 py-3.5">Your Cost</th>
                <th className="px-4 py-3.5">Selling Price</th>
                <th className="px-4 py-3.5">Stock Available</th>
                <th className="px-4 py-3.5">Live Stores</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-20 text-[#767676]">Loading products...</td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-20 text-[#767676]">
                    No products found. Try changing your search query or filters.
                  </td>
                </tr>
              ) : (
                products.map((product) => {
                  const cost = Number(product.lowest_cost || 0);
                  const suggestedPrice = (cost * 1.15).toFixed(2);
                  const isExcluded = !product.is_enabled;

                  return (
                    <tr
                      key={product.id}
                      className={`hover:bg-gray-50/60 transition-colors ${isExcluded ? "opacity-50" : ""}`}
                    >
                      {/* Product Image & Name */}
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-3">
                          {product.images && product.images[0] ? (
                            <img
                              src={product.images[0]}
                              alt={product.title}
                              referrerPolicy="no-referrer"
                              onError={(e) => {
                                e.currentTarget.onerror = null;
                                e.currentTarget.src = "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=800&auto=format&fit=crop&q=80";
                              }}
                              className="h-12 w-12 rounded-lg object-cover bg-white border border-gray-200 shrink-0"
                            />
                          ) : (
                            <div className="h-12 w-12 rounded-lg bg-gray-50 border border-gray-200 flex items-center justify-center text-[#767676] shrink-0">
                              <Layers className="h-4 w-4" />
                            </div>
                          )}
                          <div className="max-w-xs sm:max-w-md">
                            {/* Name click -> same unified drawer */}
                            <button
                              onClick={() => handleOpenProductDrawer(product, existingListingsMap, marketplaces, selectedChannelId)}
                              className="font-semibold text-[#0a0a0a] hover:text-[#A8560A] text-left line-clamp-1 transition-colors"
                            >
                              {product.title}
                            </button>
                            <div className="text-xs text-[#767676] mt-0.5">
                              {product.brand || "Standard Brand"}
                              {product.category && (
                                <><span className="mx-1 opacity-40">&bull;</span>{product.category}</>
                              )}
                            </div>
                            {product.specs_json?.walmart_match_status === "matchable" && (
                              <span className="inline-flex items-center gap-1 mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                                Walmart match found
                              </span>
                            )}
                            {product.specs_json?.walmart_match_status === "not_matchable" && (
                              <span className="inline-flex items-center gap-1 mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500 border border-gray-200">
                                No Walmart match
                              </span>
                            )}
                            <button
                              onClick={() => handleOpenProductDrawer(product, existingListingsMap, marketplaces, selectedChannelId)}
                              className="text-[11px] text-[#A8560A] hover:underline mt-0.5 font-medium block"
                            >
                              View details &amp; list &rarr;
                            </button>
                          </div>
                        </div>
                      </td>

                      {/* Your Cost */}
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-[#0a0a0a] text-sm">
                          {cost > 0 ? `$${cost.toFixed(2)}` : "-"}
                        </div>
                        <div className="text-[11px] text-[#767676]">What you pay supplier</div>
                      </td>

                      {/* Suggested Selling Price */}
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-[#A8560A] text-sm">
                          {cost > 0 ? `$${suggestedPrice}` : "-"}
                        </div>
                        <div className="text-[11px] text-[#767676]">With 15% profit markup</div>
                      </td>

                      {/* Stock Available */}
                      <td className="px-4 py-3.5">
                        {(() => {
                          const hasUnlimited = product.is_unlimited_stock || product.supplier_products?.some(sp => sp.is_unlimited_stock || sp.qty_available >= 9999999);
                          const inStockCount = product.total_stock;
                          const inStockSuppliers = product.supplier_products?.filter(sp => sp.qty_available > 0 || sp.stock_status === "IN_STOCK") || [];

                          if (inStockCount > 0) {
                            return (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                                {inStockCount} ready to ship
                              </span>
                            );
                          }

                          if (hasUnlimited || inStockSuppliers.length > 0) {
                            return (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                                In Stock (License / Digital)
                              </span>
                            );
                          }

                          return (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-800 border border-rose-200">
                              Out of Stock
                            </span>
                          );
                        })()}
                        <div className="text-[11px] text-[#767676] mt-0.5">
                          {product.supplier_products.length}{" "}
                          {product.supplier_products.length === 1 ? "supplier" : "suppliers"}
                        </div>
                      </td>

                      {/* Live In Stores */}
                      <td className="px-4 py-3.5">
                        {(() => {
                          const currentListings = existingListingsMap[product.id] || [];
                          if (currentListings.length === 0) {
                            return (
                              <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-gray-100 text-gray-500 border border-gray-200">
                                Not listed yet
                              </span>
                            );
                          }
                          return (
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {currentListings.map((l) => (
                                <span
                                  key={l.id}
                                  className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                                    l.status === "ACTIVE"
                                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                                      : "bg-gray-100 text-gray-600 border-gray-200"
                                  }`}
                                  title={l.status === "ACTIVE" ? `Live on ${l.marketplace_name}` : `Hidden on ${l.marketplace_name}`}
                                >
                                  {l.marketplace_name}
                                </span>
                              ))}
                            </div>
                          );
                        })()}
                      </td>

                      {/* Action Buttons */}
                      <td className="px-6 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {(() => {
                            const liveList = existingListingsMap[product.id] || [];
                            const listedStoreIds = liveList.map((l) => l.marketplace_id);
                            const allListed = marketplaces.length > 0 && marketplaces.every((m) => listedStoreIds.includes(m.id));
                            const someListed = liveList.length > 0;

                            return (
                              // Both name click and this button open the same drawer
                              <button
                                onClick={() => handleOpenProductDrawer(product, existingListingsMap, marketplaces, selectedChannelId)}
                                disabled={publishingId === product.id || isExcluded}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all disabled:opacity-50 flex items-center gap-1.5 shrink-0 ${
                                  allListed
                                    ? "bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100"
                                    : "bg-[#0a0a0a] hover:bg-[#222222] text-white"
                                }`}
                              >
                                {allListed ? (
                                  <><Check className="h-3.5 w-3.5 text-emerald-600" /><span>Listed Everywhere (Update)</span></>
                                ) : someListed ? (
                                  <><RefreshCw className="h-3.5 w-3.5 text-white/80" /><span>Sell / Update</span></>
                                ) : (
                                  <><Store className="h-3.5 w-3.5" /><span>Start Selling This</span></>
                                )}
                              </button>
                            );
                          })()}

                          <button
                            onClick={() => toggleNotSelling(product.id)}
                            className={`px-2.5 py-1.5 rounded-lg border text-xs transition-colors ${
                              isExcluded
                                ? "bg-amber-50 border-amber-300 text-amber-800"
                                : "bg-white border-gray-300 text-gray-600 hover:text-gray-900"
                            }`}
                            title={isExcluded ? "Click to enable" : "Don't sell this product"}
                          >
                            <span className="text-[11px] font-medium">{isExcluded ? "Disabled" : "Hide"}</span>
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

        {/* Pagination */}
        <div className="p-4 bg-gray-50/80 border-t border-gray-200 flex items-center justify-between text-xs text-[#767676]">
          <div>
            Showing Page <span className="text-[#0a0a0a] font-semibold">{page}</span> of{" "}
            <span className="text-[#0a0a0a] font-semibold">{totalPages}</span> ({total} total products)
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 text-[#1a1a1a] font-medium border border-gray-300 flex items-center gap-1"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 text-[#1a1a1a] font-medium border border-gray-300 flex items-center gap-1"
            >
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* {/*
          UNIFIED PRODUCT DRAWER
          Opened by BOTH: product name click AND "Start Selling" button.
          Contains: product details, 3-photo picker (real supplier API
          images), store selector, price, title/desc edit, publish action.
           */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="relative bg-[#FAFAF8] border border-gray-200 rounded-lg max-w-3xl w-full max-h-[92vh] overflow-y-auto shadow-2xl">
            <button
              onClick={() => setSelectedProduct(null)}
              className="absolute top-4 right-4 z-10 p-1.5 rounded-full bg-white/90 text-[#767676] hover:text-[#0a0a0a] hover:bg-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Hero: Photo picker + Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 p-6 pb-4">
              {/* Left: Photo picker */}
              <div>
                {/* Primary selected image preview */}
                <div className="relative">
                  {selectedImageUrl ? (
                    <img
                      src={selectedImageUrl}
                      alt={selectedProduct.title}
                      referrerPolicy="no-referrer"
                      onError={(e) => {
                        e.currentTarget.onerror = null;
                        e.currentTarget.src = "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=800&auto=format&fit=crop&q=80";
                      }}
                      className="w-full aspect-square object-cover rounded-lg bg-gray-50 border border-gray-100"
                    />
                  ) : (
                    <div className="w-full aspect-square rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center text-[#767676]">
                      <Layers className="h-10 w-10" />
                    </div>
                  )}

                  {/* Status badges */}
                  <div className="absolute bottom-2 left-2 flex items-center gap-1.5">
                    {selectedProduct.images?.[0] && selectedImageUrl === selectedProduct.images[0] ? (
                      <span className="text-[10px] font-semibold bg-emerald-600 text-white px-2 py-0.5 rounded-full shadow-sm flex items-center gap-1">
                        <Check className="h-3 w-3" /> Current Product Photo
                      </span>
                    ) : selectedImageUrl ? (
                      <span className="text-[10px] font-semibold bg-amber-600 text-white px-2 py-0.5 rounded-full shadow-sm">
                        Previewing Candidate
                      </span>
                    ) : null}
                  </div>
                </div>

                {/* Permanent Save Button when a different image is selected */}
                {selectedImageUrl && selectedImageUrl !== selectedProduct.images?.[0] && (
                  <button
                    type="button"
                    onClick={() => handleSaveProductImage(selectedImageUrl)}
                    disabled={savingImage}
                    className="w-full mt-2 py-2 px-3 bg-[#A8560A] hover:bg-[#8F4708] text-white text-xs font-semibold rounded-lg shadow-sm flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                  >
                    {savingImage ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" />
                    )}
                    <span>{savingImage ? "Saving Photo..." : "Set as Permanent Product Photo"}</span>
                  </button>
                )}

                {/* Success feedback toast */}
                {imageSaveSuccess && (
                  <div className="mt-2 p-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium rounded-lg flex items-center gap-1.5 animate-fadeIn">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    <span>{imageSaveSuccess}</span>
                  </div>
                )}

                {/* Web Search Box */}
                <div className="mt-3 p-2.5 bg-gray-50 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-semibold text-[#1a1a1a] flex items-center gap-1">
                      <Search className="h-3.5 w-3.5 text-[#D9720F]" /> Search Web for Photos
                    </span>
                    {selectedProduct.upc && (
                      <button
                        type="button"
                        onClick={() => {
                          setImageSearchQuery(`${selectedProduct.upc} ${selectedProduct.brand || ""}`.trim());
                          // No query override -> backend runs the full verified
                          // UPC-anchored algorithm (merges UPC-alone / UPC+brand /
                          // UPC+brand+MPN tiers, trusted-supplier-CDN filtered),
                          // not a plain text search.
                          fetchImageSuggestions(selectedProduct.id);
                        }}
                        disabled={loadingImages}
                        className="text-[10px] text-[#A8560A] hover:underline font-medium disabled:opacity-50"
                        title="Runs the verified multi-tier UPC search algorithm instead of a plain text search"
                      >
                        Verified UPC Search
                      </button>
                    )}
                  </div>
                  <div className="flex gap-1.5">
                    <input
                      type="text"
                      value={imageSearchQuery}
                      onChange={(e) => setImageSearchQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          fetchImageSuggestions(selectedProduct.id, imageSearchQuery);
                        }
                      }}
                      placeholder="Search UPC, brand, model..."
                      className="flex-1 px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded-md text-[#0a0a0a] focus:outline-none focus:border-[#D9720F]"
                    />
                    <button
                      type="button"
                      onClick={() => fetchImageSuggestions(selectedProduct.id, imageSearchQuery)}
                      disabled={loadingImages}
                      className="px-3 py-1.5 bg-[#D9720F] hover:bg-[#A8560A] text-white text-xs font-medium rounded-md transition-colors flex items-center gap-1 shrink-0 disabled:opacity-50"
                    >
                      {loadingImages ? (
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Search className="h-3.5 w-3.5" />
                      )}
                      <span>Search</span>
                    </button>
                  </div>
                </div>

                {/* Photo suggestions strip */}
                <div className="mt-2.5">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Camera className="h-3.5 w-3.5 text-[#D9720F]" />
                    <span className="text-[11px] font-semibold text-[#1a1a1a]">Select Photo Candidate</span>
                    {loadingImages && (
                      <RefreshCw className="h-3 w-3 text-[#767676] animate-spin ml-auto" />
                    )}
                  </div>

                  {loadingImages ? (
                    <div className="flex gap-2">
                      {[0, 1, 2, 3].map((i) => (
                        <div key={i} className="h-16 w-16 rounded-lg bg-gray-100 border border-gray-200 animate-pulse" />
                      ))}
                    </div>
                  ) : imageSuggestions.length > 0 ? (
                    <div className="flex gap-2 flex-wrap max-h-36 overflow-y-auto p-0.5">
                      {imageSuggestions.map((url, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => setSelectedImageUrl(url)}
                          title={`Candidate ${i + 1}`}
                          className={`relative h-16 w-16 rounded-lg overflow-hidden border-2 transition-all ${
                            selectedImageUrl === url
                              ? "border-[#D9720F] ring-2 ring-[#D9720F]/30 scale-105 z-10"
                              : "border-gray-200 hover:border-gray-400"
                          }`}
                        >
                          <img
                            src={url}
                            alt={`Photo option ${i + 1}`}
                            referrerPolicy="no-referrer"
                            onError={(e) => {
                              e.currentTarget.onerror = null;
                              e.currentTarget.src = "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=200&auto=format&fit=crop&q=60";
                            }}
                            className="h-full w-full object-cover"
                          />
                          {selectedImageUrl === url && (
                            <span className="absolute inset-0 flex items-center justify-center bg-[#D9720F]/25">
                              <Check className="h-5 w-5 text-white drop-shadow" />
                            </span>
                          )}
                          {selectedProduct.images?.[0] === url && (
                            <span className="absolute bottom-0 left-0 right-0 text-center text-[7px] font-bold bg-emerald-600/90 text-white py-0.5">
                              Current
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-[11px] text-[#767676] bg-gray-50 border border-gray-200 rounded-lg p-2.5">
                      <ImageIcon className="h-4 w-4 shrink-0" />
                      <span>No photos found. Try searching by UPC above.</span>
                    </div>
                  )}
                  <p className="text-[10px] text-[#767676] mt-1.5">
                    Click any thumbnail above to preview it, then click &ldquo;Set as Permanent Product Photo&rdquo;.
                  </p>
                </div>

                {/* Paste direct URL */}
                <div className="mt-2.5 pt-2 border-t border-gray-200">
                  <label className="text-[10px] font-medium text-[#767676] block mb-1">
                    Or paste direct image URL from Google / manufacturer:
                  </label>
                  <div className="flex gap-1.5">
                    <input
                      type="url"
                      value={customImageUrlInput}
                      onChange={(e) => setCustomImageUrlInput(e.target.value)}
                      placeholder="https://example.com/product-photo.jpg"
                      className="flex-1 px-2.5 py-1.5 text-xs bg-white border border-gray-300 rounded-md text-[#0a0a0a] focus:outline-none focus:border-[#D9720F]"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const cleanUrl = customImageUrlInput.trim();
                        if (cleanUrl.startsWith("http://") || cleanUrl.startsWith("https://")) {
                          setSelectedImageUrl(cleanUrl);
                          handleSaveProductImage(cleanUrl);
                          setCustomImageUrlInput("");
                        } else {
                          setPublishError("Please enter a valid URL starting with http:// or https://");
                          setTimeout(() => setPublishError(null), 8000);
                        }
                      }}
                      disabled={!customImageUrlInput.trim() || savingImage}
                      className="px-3 py-1.5 bg-gray-900 hover:bg-gray-800 text-white text-xs font-medium rounded-md transition-colors disabled:opacity-50 shrink-0"
                    >
                      Use &amp; Save
                    </button>
                  </div>
                </div>
              </div>

              {/* Right: Summary */}
              <div className="flex flex-col">
                <span className="text-[11px] font-semibold text-[#A8560A] uppercase tracking-wide">
                  {selectedProduct.brand || "Unbranded"}
                  {selectedProduct.category && (
                    <><span className="mx-1 opacity-60">&middot;</span>{selectedProduct.category}</>
                  )}
                </span>
                <h3 className="text-lg font-bold text-[#0a0a0a] mt-1 leading-snug">{selectedProduct.title}</h3>

                <div className="flex items-baseline gap-2 mt-3">
                  <span className="text-2xl font-bold text-[#0a0a0a]">
                    ${selectedProduct.lowest_cost ? (Number(selectedProduct.lowest_cost) * 1.15).toFixed(2) : "0.00"}
                  </span>
                  <span className="text-xs text-[#767676]">suggested selling price</span>
                </div>
                <div className="text-xs text-[#767676] mt-0.5">
                  Your cost: ${selectedProduct.lowest_cost ? Number(selectedProduct.lowest_cost).toFixed(2) : "0.00"}
                </div>

                <span className={`inline-flex items-center gap-1.5 mt-3 self-start px-2.5 py-1 rounded-md text-xs font-medium ${
                  selectedProduct.total_stock > 0
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    : "bg-rose-50 text-rose-800 border border-rose-200"
                }`}>
                  {selectedProduct.total_stock > 0 ? `${selectedProduct.total_stock} in stock` : "Out of stock"}
                </span>

                <p className="text-xs text-[#767676] leading-relaxed mt-4">
                  {selectedProduct.description || "No manufacturer description provided for this item."}
                </p>

                <div className="mt-4 pt-3 border-t border-gray-100 grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px] font-mono text-[#767676]">
                  <div>SKU: <span className="text-[#1a1a1a]">{selectedProduct.sku}</span></div>
                  <div>UPC: <span className="text-[#1a1a1a]">{selectedProduct.upc || "None"}</span></div>
                  <div>EAN: <span className="text-[#1a1a1a]">{selectedProduct.ean || "None"}</span></div>
                  <div>MPN: <span className="text-[#1a1a1a]">{selectedProduct.mpn || "None"}</span></div>
                </div>
              </div>
            </div>

            <div className="px-6 pb-6 space-y-5">
              {/* Distributors table */}
              <div>
                <h4 className="text-xs font-semibold text-[#0a0a0a] mb-2 flex items-center gap-2">
                  <Truck className="h-4 w-4 text-[#D9720F]" />
                  <span>Wholesale Distributors Supplying This Item</span>
                </h4>
                <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-gray-50 text-[#767676] uppercase text-[10px] border-b border-gray-200">
                      <tr>
                        <th className="px-3.5 py-2.5">Distributor</th>
                        <th className="px-3.5 py-2.5">Wholesale Cost</th>
                        <th className="px-3.5 py-2.5">Base Shipping</th>
                        <th className="px-3.5 py-2.5">Cost Basis</th>
                        <th className="px-3.5 py-2.5">Stock Ready</th>
                        <th className="px-3.5 py-2.5">Lead Time</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {selectedProduct.supplier_products.map((sp) => {
                        const cost = Number(sp.cost);
                        const ship = sp.base_shipping_charge != null ? Number(sp.base_shipping_charge) : 0;
                        const totalBasis = cost + ship;

                        return (
                          <tr key={sp.id} className="hover:bg-gray-50/60">
                            <td className="px-3.5 py-2.5 font-medium text-[#0a0a0a]">{sp.supplier_name || "Supplier"}</td>
                            <td className="px-3.5 py-2.5 font-semibold text-[#A8560A]">${cost.toFixed(2)}</td>
                            <td className="px-3.5 py-2.5 font-medium text-[#0a0a0a]">
                              {sp.base_shipping_charge != null ? (
                                <span>
                                  ${ship.toFixed(2)}
                                  <span className="text-[10px] text-[#767676] block lowercase">{sp.shipping_source || "base"}</span>
                                </span>
                              ) : (
                                <span className="text-gray-400">$0.00</span>
                              )}
                            </td>
                            <td className="px-3.5 py-2.5 font-bold text-[#0a0a0a]">
                              ${totalBasis.toFixed(2)}
                            </td>
                            <td className="px-3.5 py-2.5 text-emerald-800 font-medium">
                              {sp.is_unlimited_stock ? "License / Service - no unit limit" : `${sp.qty_available} units`}
                            </td>
                            <td className="px-3.5 py-2.5 text-[#767676]">
                              {sp.shipping_info?.lead_time_days != null ? `Ships in ${sp.shipping_info.lead_time_days}d` : "-"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Already listed on stores */}
              {(() => {
                const live = existingListingsMap[selectedProduct.id] || [];
                if (live.length === 0) return null;
                return (
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="text-xs font-semibold text-[#1a1a1a] block mb-1.5">Already Listed On:</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {live.map((l) => (
                        <span key={l.id} className="text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                          {l.marketplace_name} ({l.status === "ACTIVE" ? "Live" : "Hidden"}) - ${l.selling_price.toFixed(2)}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {/* Listing action form */}
              {(() => {
                const liveList = existingListingsMap[selectedProduct.id] || [];
                const isStoreListed = liveList.some((l) => l.marketplace_id === selectedChannelId);
                const selectedChannel = marketplaces.find((m) => m.id === selectedChannelId);
                const isWalmartChannel = (selectedChannel?.name || "").toLowerCase().includes("walmart");
                const hasRealWeight = (selectedProduct.supplier_products || []).some(
                  (sp) => sp.shipping_info?.weight_lbs && Number(sp.shipping_info.weight_lbs) > 0
                );

                const handleStartSelling = async () => {
                  // Walmart's MP_ITEM_MATCH can only succeed if this GTIN
                  // already exists somewhere in Walmart's own catalog — real-
                  // world-confirmed: a known-existing item returns matches
                  // here, while GTINs that later failed real feed submissions
                  // returned zero, every time. Checking this first avoids
                  // firing a real submission we already know will fail.
                  if (isWalmartChannel && !isStoreListed && selectedProduct.upc) {
                    setWeightLookupLoading(true);
                    setWeightLookupNote(null);
                    try {
                      const check = await fetchApi<{ matchable: boolean; matches_found: number }>(
                        `/products/${selectedProduct.id}/walmart-match-check`
                      );
                      if (!check.matchable) {
                        setPublishError(
                          `This product's UPC isn't matchable to anything in Walmart's catalog, so a listing attempt would fail. Walmart only supports creating an offer by matching an existing catalog item — this GTIN doesn't have one. Submission was not sent.`
                        );
                        setTimeout(() => setPublishError(null), 10000);
                        return;
                      }
                    } catch (err: any) {
                      // Pre-check itself failed (network/API issue) — proceed
                      // anyway rather than blocking on a diagnostic failure;
                      // the real publish call will surface any real error.
                    } finally {
                      setWeightLookupLoading(false);
                    }
                  }

                  let weightToUse = drawerCustomWeight ? Number(drawerCustomWeight) : undefined;

                  // Only worth the rate-limited lookup call when it's actually
                  // needed: Walmart, no real supplier weight, and staff hasn't
                  // already typed one in. Every other publish (any other
                  // marketplace, or weight already known) skips this entirely.
                  if (isWalmartChannel && !hasRealWeight && !weightToUse) {
                    setWeightLookupLoading(true);
                    setWeightLookupNote(null);
                    try {
                      const res = await fetchApi<{ weight_lbs: number; confidence: number; source_title: string }>(
                        `/products/${selectedProduct.id}/lookup-weight`,
                        { method: "POST" }
                      );
                      weightToUse = res.weight_lbs;
                      setDrawerCustomWeight(String(res.weight_lbs));
                      setWeightLookupNote(`Third-party database reports ${res.weight_lbs} lbs for a title-matched product ("${res.source_title}") — used for this listing. The title match is verified, but double-check the number against the real product if it looks off.`);
                    } catch (err: any) {
                      // No verified weight found — proceed anyway. The publish
                      // call will surface Walmart's own honest "needs a real
                      // weight" error if it actually can't create the item,
                      // same as a manual attempt would.
                      setWeightLookupNote(err.message || "No verified weight found automatically — enter one manually if listing fails.");
                    } finally {
                      setWeightLookupLoading(false);
                    }
                  }

                  handlePublishToChannel(
                    selectedProduct,
                    selectedChannelId,
                    drawerCustomPrice ? Number(drawerCustomPrice) : Number((Number(selectedProduct.lowest_cost || 0) * 1.15).toFixed(2)),
                    drawerCustomTitle,
                    drawerCustomDescription,
                    selectedImageUrl || undefined,
                    weightToUse,
                  );
                };

                return (
                  <div className="pt-3.5 border-t border-gray-200 space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-[#1a1a1a] font-semibold block mb-1">Choose Store to List on:</label>
                        <select
                          value={selectedChannelId}
                          onChange={(e) => {
                            const mId = Number(e.target.value);
                            setSelectedChannelId(mId);
                            const existing = liveList.find((l) => l.marketplace_id === mId);
                            if (existing && existing.selling_price > 0) {
                              setDrawerCustomPrice(existing.selling_price.toFixed(2));
                            } else {
                              const cost = Number(selectedProduct.lowest_cost || 0);
                              setDrawerCustomPrice((cost * 1.15).toFixed(2));
                            }
                          }}
                          className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-xs text-[#0a0a0a] font-medium focus:outline-none"
                        >
                          {marketplaces.map((m) => {
                            const existing = liveList.find((l) => l.marketplace_id === m.id);
                            return (
                              <option key={m.id} value={m.id}>
                                {m.name}{existing ? ` - Listed ($${existing.selling_price.toFixed(2)})` : ""}
                              </option>
                            );
                          })}
                        </select>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-xs text-[#1a1a1a] font-semibold block">Selling Price ($):</label>
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => randomizeDrawerPrice(Number(selectedProduct.lowest_cost || 50))}
                              className="text-[10px] text-[#A8560A] font-medium bg-[#D9720F]/10 px-1.5 py-0.5 rounded border border-[#D9720F]/20 flex items-center gap-0.5"
                            >
                              <Sparkles className="h-2.5 w-2.5" />
                              <span>Random</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => setDrawerCustomPrice((Number(selectedProduct.lowest_cost || 0) * 1.15).toFixed(2))}
                              className="text-[10px] text-gray-500 underline font-medium"
                            >
                              Reset
                            </button>
                          </div>
                        </div>
                        <div className="relative">
                          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#767676] font-medium text-xs">$</span>
                          <input
                            type="number" step="0.01"
                            value={drawerCustomPrice || (Number(selectedProduct.lowest_cost || 0) * 1.15).toFixed(2)}
                            onChange={(e) => setDrawerCustomPrice(e.target.value)}
                            className="w-full pl-6 pr-2 py-1.5 bg-white border border-gray-300 rounded-lg text-xs font-semibold text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                          />
                        </div>
                      </div>
                    </div>

                    {(() => {
                      if (!isWalmartChannel || hasRealWeight) return null;
                      return (
                        <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 space-y-1.5">
                          <label className="text-xs font-semibold text-amber-900 block">
                            Shipping Weight (lbs) — required for Walmart to create this item
                          </label>
                          <p className="text-[11px] text-amber-800/80">
                            Your supplier doesn&apos;t report a weight for this product. Walmart needs a real one to create a brand-new catalog listing.
                          </p>
                          <div className="flex gap-1.5">
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              placeholder="e.g. 2.5"
                              value={drawerCustomWeight}
                              onChange={(e) => {
                                setDrawerCustomWeight(e.target.value);
                                setWeightLookupNote(null);
                              }}
                              className="flex-1 px-3 py-1.5 bg-white border border-amber-300 rounded-lg text-xs font-semibold text-[#0a0a0a] focus:outline-none focus:border-amber-500"
                            />
                            <button
                              type="button"
                              disabled={weightLookupLoading || !selectedProduct.upc}
                              onClick={async () => {
                                setWeightLookupLoading(true);
                                setWeightLookupNote(null);
                                try {
                                  const res = await fetchApi<{ weight_lbs: number; confidence: number; source_title: string }>(
                                    `/products/${selectedProduct.id}/lookup-weight`,
                                    { method: "POST" }
                                  );
                                  setDrawerCustomWeight(String(res.weight_lbs));
                                  setWeightLookupNote(`Third-party database reports ${res.weight_lbs} lbs for a title-matched product ("${res.source_title}"). The title match is verified, but the number itself is seller-entered data — double-check it against the real product before trusting it.`);
                                } catch (err: any) {
                                  setWeightLookupNote(err.message || "No verified weight found for this UPC.");
                                } finally {
                                  setWeightLookupLoading(false);
                                }
                              }}
                              title={!selectedProduct.upc ? "No UPC on file to look up" : "Look up real weight by UPC from a third-party barcode database"}
                              className="px-3 py-1.5 bg-white hover:bg-amber-100 border border-amber-300 text-amber-900 text-xs font-medium rounded-lg transition-colors shrink-0 disabled:opacity-50 flex items-center gap-1"
                            >
                              {weightLookupLoading ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
                              <span>Auto-Lookup</span>
                            </button>
                            <a
                              href={`https://www.google.com/search?q=${encodeURIComponent(
                                `${selectedProduct.brand || ""} ${selectedProduct.mpn || selectedProduct.title} weight specifications`.trim()
                              )}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Search Google manually for the real spec sheet / weight"
                              className="px-3 py-1.5 bg-white hover:bg-amber-100 border border-amber-300 text-amber-900 text-xs font-medium rounded-lg transition-colors shrink-0 flex items-center gap-1"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              <span>Google</span>
                            </a>
                          </div>
                          {weightLookupNote && (
                            <p className="text-[11px] text-amber-900 font-medium">{weightLookupNote}</p>
                          )}
                          <p className="text-[10px] text-amber-800/70">
                            Auto-Lookup checks a barcode database automatically. Google opens a manual search in a new tab for when the automatic lookup can&apos;t find it (or you want to verify the number yourself) — enter whatever you find into the field above.
                          </p>
                        </div>
                      );
                    })()}

                    {/* Title & Description customisation */}
                    <div className="border border-gray-200 rounded-lg p-3 bg-gray-50/70 space-y-2">
                      <button
                        type="button"
                        onClick={() => setShowDrawerContentEdit(!showDrawerContentEdit)}
                        className="w-full flex items-center justify-between text-xs font-semibold text-[#0a0a0a]"
                      >
                        <span className="flex items-center gap-1.5">
                          <Sparkles className="h-3.5 w-3.5 text-[#D9720F]" />
                          <span>Customize Title &amp; Description</span>
                          {(drawerCustomTitle !== selectedProduct.title || drawerCustomDescription !== (selectedProduct.description || "")) && (
                            <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-medium">Modified</span>
                          )}
                        </span>
                        <span className="text-[11px] text-[#A8560A] font-medium">
                          {showDrawerContentEdit ? "Hide fields" : "Edit before listing"}
                        </span>
                      </button>

                      {showDrawerContentEdit && (
                        <div className="space-y-3 pt-2 border-t border-gray-200">
                          <div>
                            <label className="block text-[11px] font-semibold text-[#1a1a1a] mb-1">Store Listing Title</label>
                            <input
                              type="text"
                              value={drawerCustomTitle}
                              onChange={(e) => setDrawerCustomTitle(e.target.value)}
                              className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-semibold text-[#1a1a1a] mb-1">Store Product Description</label>
                            <textarea
                              rows={3}
                              value={drawerCustomDescription}
                              onChange={(e) => setDrawerCustomDescription(e.target.value)}
                              className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    {isStoreListed && (
                      <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-900 flex items-center gap-2">
                        <RefreshCw className="h-3.5 w-3.5 text-amber-700 shrink-0" />
                        <span>Already listed in this store. Submitting will update the title, photo, price, and stock without creating duplicates.</span>
                      </div>
                    )}

                    <div className="flex items-center justify-end gap-2.5">
                      <button
                        onClick={() => setSelectedProduct(null)}
                        className="px-4 py-2 text-xs font-medium text-[#767676] hover:text-[#0a0a0a]"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleStartSelling}
                        disabled={publishingId === selectedProduct.id || weightLookupLoading}
                        className="px-5 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all disabled:opacity-50"
                      >
                        {isStoreListed ? <RefreshCw className="h-3.5 w-3.5" /> : <Store className="h-4 w-4" />}
                        <span>
                          {weightLookupLoading
                            ? "Checking..."
                            : publishingId === selectedProduct.id
                            ? (isStoreListed ? "Updating..." : "Listing...")
                            : (isStoreListed ? "Update Listing on Store" : "Start Selling on Store")}
                        </span>
                      </button>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
