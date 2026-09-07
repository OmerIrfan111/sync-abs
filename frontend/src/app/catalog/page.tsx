"use client";

import React, { useEffect, useState } from "react";
import { 
  Search, 
  Filter, 
  Layers, 
  ChevronLeft, 
  ChevronRight, 
  Tag, 
  Eye, 
  X, 
  DollarSign, 
  Truck, 
  Store, 
  Check, 
  HelpCircle, 
  SlidersHorizontal,
  Info,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RefreshCw
} from "lucide-react";
import { fetchApi, Product, Listing } from "@/lib/api";

export default function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBrand, setSelectedBrand] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [inStockOnly, setInStockOnly] = useState(false);
  const [filterOptions, setFilterOptions] = useState<{ brands: string[]; categories: string[] }>({
    brands: [],
    categories: [],
  });
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishingId, setPublishingId] = useState<number | null>(null);
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<number>(1);
  const [disabledProducts, setDisabledProducts] = useState<Record<number, boolean>>({});

  // Store selection modal state for row listing
  const [listingModalProduct, setListingModalProduct] = useState<Product | null>(null);
  const [selectedModalChannelId, setSelectedModalChannelId] = useState<number>(1);
  const [existingListingsMap, setExistingListingsMap] = useState<Record<number, { id: number; marketplace_id: number; marketplace_name: string; status: string; selling_price: number }[]>>({});
  const [modalCustomPrice, setModalCustomPrice] = useState<string>("");
  const [drawerCustomPrice, setDrawerCustomPrice] = useState<string>("");
  const [modalCustomTitle, setModalCustomTitle] = useState<string>("");
  const [modalCustomDescription, setModalCustomDescription] = useState<string>("");
  const [drawerCustomTitle, setDrawerCustomTitle] = useState<string>("");
  const [drawerCustomDescription, setDrawerCustomDescription] = useState<string>("");
  const [showModalContentEdit, setShowModalContentEdit] = useState<boolean>(false);
  const [showDrawerContentEdit, setShowDrawerContentEdit] = useState<boolean>(false);

  const randomizeModalPrice = (cost: number) => {
    const mult = 1 + (Math.floor(Math.random() * 25) + 10) / 100;
    const p = Math.floor(cost * mult) + 0.99;
    setModalCustomPrice(p.toFixed(2));
  };

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
        if (!map[l.product_id]) {
          map[l.product_id] = [];
        }
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

  const handlePublishToChannel = async (
    product: Product, 
    targetMarketplaceId: number, 
    customPrice?: number,
    customTitle?: string,
    customDescription?: string
  ) => {
    setPublishingId(product.id);
    setPublishSuccess(null);
    try {
      const channel = marketplaces.find(m => m.id === targetMarketplaceId);
      const channelName = channel ? channel.name : "Your Store";
      const isUpdate = (existingListingsMap[product.id] || []).some(l => l.marketplace_id === targetMarketplaceId);

      await fetchApi<any>("/listings/publish", {
        method: "POST",
        body: JSON.stringify({
          product_id: product.id,
          marketplace_id: targetMarketplaceId,
          custom_price: customPrice !== undefined && !isNaN(customPrice) ? customPrice : undefined,
          custom_title: customTitle?.trim() || undefined,
          custom_description: customDescription?.trim() || undefined,
        }),
      });
      const priceText = customPrice !== undefined && !isNaN(customPrice) ? ` at $${customPrice.toFixed(2)}` : "";
      setPublishSuccess(
        isUpdate 
          ? `Successfully updated "${customTitle || product.title}" on ${channelName}${priceText}!` 
          : `Successfully listed "${customTitle || product.title}" on ${channelName}${priceText}!`
      );
      setTimeout(() => setPublishSuccess(null), 5000);
      setListingModalProduct(null);
      await loadListingsMap();
    } catch (err: any) {
      alert("Action failed: " + err.message);
    } finally {
      setPublishingId(null);
    }
  };

  const handleOpenProductDetails = (product: Product) => {
    setSelectedProduct(product);
    setDrawerCustomTitle(product.title || "");
    setDrawerCustomDescription(product.description || "");
    setShowDrawerContentEdit(false);
    const live = existingListingsMap[product.id] || [];
    const existing = live.find(l => l.marketplace_id === selectedChannelId);
    if (existing && existing.selling_price > 0) {
      setDrawerCustomPrice(existing.selling_price.toFixed(2));
    } else {
      const cost = Number(product.lowest_cost || 0);
      setDrawerCustomPrice((cost * 1.15).toFixed(2));
    }
  };

  const toggleNotSelling = (productId: number) => {
    setDisabledProducts(prev => ({
      ...prev,
      [productId]: !prev[productId]
    }));
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
        if (res.length > 0) {
          setSelectedChannelId(res[0].id);
          setSelectedModalChannelId(res[0].id);
        }
      })
      .catch((err) => console.error("Could not fetch marketplaces:", err));

    loadListingsMap();
  }, []);

  useEffect(() => {
    loadProducts();
  }, [page, selectedBrand, selectedCategory, inStockOnly]);

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
    setPage(1);
  };

  const hasActiveFilters = Boolean(searchQuery || selectedBrand || selectedCategory || inStockOnly);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header - Unboxed on canvas */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-[#0a0a0a] tracking-tight">Products to Sell</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-[#905831]/10 text-[#905831] border border-[#905831]/20">
              Wholesale Catalog
            </span>
          </div>
          <p className="text-sm text-[#767676] mt-1 max-w-2xl leading-relaxed">
            Browse all products provided by your suppliers. Pick what you want to sell and list them on your stores with one click.
          </p>
        </div>
        <div className="text-left sm:text-right self-start sm:self-auto">
          <span className="text-xs text-[#767676] block font-medium">Total Catalog Items</span>
          <span className="text-2xl font-bold text-[#0a0a0a] tracking-tight">{total.toLocaleString()}</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-3.5">
        <div className="flex flex-col md:flex-row gap-3">
          <form onSubmit={handleSearchSubmit} className="flex-1 relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#767676]" />
            <input
              type="text"
              placeholder="Search products by title, brand, or product code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-[#1a1a1a] placeholder-[#767676] focus:outline-none focus:border-[#0a0a0a] focus:ring-1 focus:ring-[#0a0a0a] transition-all"
            />
          </form>
          <button
            onClick={() => { setPage(1); loadProducts(); }}
            className="px-6 py-2.5 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-sm font-medium transition-all shadow-sm shrink-0"
          >
            Find Products
          </button>
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-2.5 pt-3 border-t border-gray-100 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-[#1a1a1a]">
            <Filter className="h-3.5 w-3.5 text-[#905831]" />
            <span>Filter By:</span>
          </div>

          {/* Brand Filter */}
          <select
            value={selectedBrand}
            onChange={(e) => { setSelectedBrand(e.target.value); setPage(1); }}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#1a1a1a] font-medium focus:outline-none focus:border-[#0a0a0a]"
          >
            <option value="">All Brands</option>
            {filterOptions.brands.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#1a1a1a] font-medium focus:outline-none focus:border-[#0a0a0a]"
          >
            <option value="">All Categories</option>
            {filterOptions.categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          {/* In-Stock Toggle */}
          <label className="flex items-center gap-2 cursor-pointer select-none bg-white border border-gray-300 px-3 py-1.5 rounded-lg hover:border-gray-400 transition-colors">
            <input
              type="checkbox"
              checked={inStockOnly}
              onChange={(e) => { setInStockOnly(e.target.checked); setPage(1); }}
              className="rounded border-gray-300 text-[#0a0a0a] focus:ring-0 h-3.5 w-3.5 cursor-pointer accent-[#0a0a0a]"
            />
            <span className="text-xs text-[#1a1a1a] font-medium">In Stock Only (Ready to ship)</span>
          </label>

          {/* Clear Filters Button */}
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

      {/* Products Table Card */}
      <div className="bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm">
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
                  <td colSpan={6} className="text-center py-20 text-[#767676]">
                    Loading products...
                  </td>
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
                  const isExcluded = disabledProducts[product.id] || false;

                  return (
                    <tr 
                      key={product.id} 
                      className={`hover:bg-gray-50/60 transition-colors ${isExcluded ? "opacity-50" : ""}`}
                    >
                      {/* 1. Product Image & Name */}
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-3">
                          {product.images && product.images[0] ? (
                            <img
                              src={product.images[0]}
                              alt={product.title}
                              className="h-12 w-12 rounded-lg object-cover bg-white border border-gray-200 shrink-0"
                            />
                          ) : (
                            <div className="h-12 w-12 rounded-lg bg-gray-50 border border-gray-200 flex items-center justify-center text-[#767676] shrink-0">
                              <Layers className="h-4 w-4" />
                            </div>
                          )}
                          <div className="max-w-xs sm:max-w-md">
                            <button
                              onClick={() => handleOpenProductDetails(product)}
                              className="font-semibold text-[#0a0a0a] hover:text-[#905831] text-left line-clamp-1 transition-colors"
                            >
                              {product.title}
                            </button>
                            <div className="text-xs text-[#767676] mt-0.5">
                              {product.brand || "Standard Brand"} • {product.category || "General Merchandise"}
                            </div>
                            <button
                              onClick={() => handleOpenProductDetails(product)}
                              className="text-[11px] text-[#905831] hover:underline mt-0.5 font-medium block"
                            >
                              View product codes & details &rarr;
                            </button>
                          </div>
                        </div>
                      </td>

                      {/* 2. Your Cost */}
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-[#0a0a0a] text-sm">
                          {cost > 0 ? `$${cost.toFixed(2)}` : "—"}
                        </div>
                        <div className="text-[11px] text-[#767676]">What you pay supplier</div>
                      </td>

                      {/* 3. Suggested Selling Price */}
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-[#905831] text-sm">
                          {cost > 0 ? `$${suggestedPrice}` : "—"}
                        </div>
                        <div className="text-[11px] text-[#767676]">With 15% profit markup</div>
                      </td>

                      {/* 4. Stock Available */}
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${
                          product.total_stock > 0
                            ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                            : "bg-rose-50 text-rose-800 border border-rose-200"
                        }`}>
                          {product.total_stock > 0 ? `${product.total_stock} ready to ship` : "Out of Stock"}
                        </span>
                        <div className="text-[11px] text-[#767676] mt-0.5">
                          {product.supplier_products.length} {product.supplier_products.length === 1 ? "supplier" : "suppliers"}
                        </div>
                      </td>

                      {/* 5. Live In Stores */}
                      <td className="px-4 py-3.5">
                        {(() => {
                          const currentListings = existingListingsMap[product.id] || [];
                          if (currentListings.length === 0) {
                            return (
                              <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-gray-100 text-gray-500 border border-gray-200">
                                Not listed yet
                              </span>
                            );
                          }
                          return (
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {currentListings.map((l) => (
                                <span
                                  key={l.id}
                                  className={`text-[11px] font-medium px-2 py-0.5 rounded-md border ${
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

                      {/* 6. Action Buttons */}
                      <td className="px-6 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {(() => {
                            const liveList = existingListingsMap[product.id] || [];
                            const listedStoreIds = liveList.map(l => l.marketplace_id);
                            const allListed = marketplaces.length > 0 && marketplaces.every(m => listedStoreIds.includes(m.id));
                            const someListed = liveList.length > 0;

                            const handleOpenModal = () => {
                              setListingModalProduct(product);
                              setModalCustomTitle(product.title || "");
                              setModalCustomDescription(product.description || "");
                              setShowModalContentEdit(false);
                              const unlisted = marketplaces.filter(m => !listedStoreIds.includes(m.id));
                              const targetChannelId = unlisted.length > 0 ? unlisted[0].id : (marketplaces[0]?.id || 1);
                              setSelectedModalChannelId(targetChannelId);

                              const existing = liveList.find(l => l.marketplace_id === targetChannelId);
                              if (existing && existing.selling_price > 0) {
                                setModalCustomPrice(existing.selling_price.toFixed(2));
                              } else {
                                const cost = Number(product.lowest_cost || 0);
                                setModalCustomPrice((cost * 1.15).toFixed(2));
                              }
                            };

                            return (
                              <button
                                onClick={handleOpenModal}
                                disabled={publishingId === product.id || isExcluded}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all shadow-sm disabled:opacity-50 flex items-center gap-1.5 shrink-0 ${
                                  allListed 
                                    ? "bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100" 
                                    : "bg-[#0a0a0a] hover:bg-[#222222] text-white"
                                }`}
                                title={allListed ? "Manage or update prices across stores" : "Sell or update listing on store"}
                              >
                                {allListed ? (
                                  <>
                                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                                    <span>Listed Everywhere (Update)</span>
                                  </>
                                ) : someListed ? (
                                  <>
                                    <RefreshCw className="h-3.5 w-3.5 text-white/80" />
                                    <span>Sell / Update</span>
                                  </>
                                ) : (
                                  <>
                                    <Store className="h-3.5 w-3.5" />
                                    <span>Start Selling This</span>
                                  </>
                                )}
                              </button>
                            );
                          })()}

                          <button
                            onClick={() => toggleNotSelling(product.id)}
                            className={`px-2.5 py-1.5 rounded-lg border text-xs transition-colors shadow-sm ${
                              isExcluded 
                                ? "bg-amber-50 border-amber-300 text-amber-800" 
                                : "bg-white border-gray-300 text-gray-600 hover:text-gray-900"
                            }`}
                            title={isExcluded ? "Click to enable" : "Don't sell this product"}
                          >
                            <span className="text-[11px] font-medium">
                              {isExcluded ? "Disabled" : "Hide"}
                            </span>
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

        {/* Pagination Bar */}
        <div className="p-4 bg-gray-50/80 border-t border-gray-200 flex items-center justify-between text-xs text-[#767676]">
          <div>
            Showing Page <span className="text-[#0a0a0a] font-semibold">{page}</span> of{" "}
            <span className="text-[#0a0a0a] font-semibold">{totalPages}</span> ({total} total products)
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 text-[#1a1a1a] font-medium border border-gray-300 flex items-center gap-1 shadow-sm"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 text-[#1a1a1a] font-medium border border-gray-300 flex items-center gap-1 shadow-sm"
            >
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Product Details Drawer / Modal */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-xl p-6 space-y-5">
            <div className="flex items-start justify-between pb-3 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-bold text-[#0a0a0a]">{selectedProduct.title}</h3>
                <p className="text-xs text-[#767676] mt-0.5">Product Details & Wholesale Breakdown</p>
              </div>
              <button
                onClick={() => setSelectedProduct(null)}
                className="p-1.5 rounded-lg text-[#767676] hover:text-[#0a0a0a] hover:bg-gray-100 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Product Overview Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <span className="text-[11px] text-[#767676] block">Brand</span>
                <span className="font-semibold text-[#0a0a0a] text-sm">{selectedProduct.brand || "Unbranded"}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <span className="text-[11px] text-[#767676] block">Category</span>
                <span className="font-semibold text-[#0a0a0a] text-sm">{selectedProduct.category || "General"}</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <span className="text-[11px] text-[#767676] block">Available Stock</span>
                <span className="font-semibold text-emerald-700 text-sm">{selectedProduct.total_stock} units</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <span className="text-[11px] text-[#767676] block">Lowest Cost</span>
                <span className="font-semibold text-[#0a0a0a] text-sm">${selectedProduct.lowest_cost ? Number(selectedProduct.lowest_cost).toFixed(2) : "0.00"}</span>
              </div>
            </div>

            {/* Technical Identifiers */}
            <div className="p-3.5 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
              <h4 className="text-xs font-semibold text-[#767676] uppercase tracking-wider">Product Identifiers</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div>
                  <span className="text-[#767676] block text-[10px]">Product Code (SKU)</span>
                  <span className="text-[#905831] font-semibold">{selectedProduct.sku}</span>
                </div>
                <div>
                  <span className="text-[#767676] block text-[10px]">Barcode (UPC)</span>
                  <span className="text-[#1a1a1a]">{selectedProduct.upc || "None"}</span>
                </div>
                <div>
                  <span className="text-[#767676] block text-[10px]">European Barcode (EAN)</span>
                  <span className="text-[#1a1a1a]">{selectedProduct.ean || "None"}</span>
                </div>
                <div>
                  <span className="text-[#767676] block text-[10px]">Part Number (MPN)</span>
                  <span className="text-[#1a1a1a]">{selectedProduct.mpn || "None"}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <div>
              <h4 className="text-xs font-semibold text-[#1a1a1a] mb-1">Product Description</h4>
              <p className="text-xs text-[#767676] leading-relaxed bg-gray-50 p-3.5 rounded-lg border border-gray-200">
                {selectedProduct.description || "Standard manufacturer product details."}
              </p>
            </div>

            {/* Distributors carrying this item */}
            <div>
              <h4 className="text-xs font-semibold text-[#0a0a0a] mb-2 flex items-center gap-2">
                <Truck className="h-4 w-4 text-[#905831]" />
                <span>Wholesale Distributors Supplying This Item</span>
              </h4>
              <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                <table className="w-full text-left text-xs">
                  <thead className="bg-gray-50 text-[#767676] uppercase text-[10px] border-b border-gray-200">
                    <tr>
                      <th className="px-3.5 py-2.5">Distributor</th>
                      <th className="px-3.5 py-2.5">What You Pay</th>
                      <th className="px-3.5 py-2.5">Stock Ready</th>
                      <th className="px-3.5 py-2.5">Shipping</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {selectedProduct.supplier_products.map((sp) => (
                      <tr key={sp.id} className="hover:bg-gray-50/60">
                        <td className="px-3.5 py-2.5 font-medium text-[#0a0a0a]">{sp.supplier_name || "Supplier"}</td>
                        <td className="px-3.5 py-2.5 font-semibold text-[#905831]">${Number(sp.cost).toFixed(2)}</td>
                        <td className="px-3.5 py-2.5 text-emerald-800 font-medium">{sp.qty_available} units</td>
                        <td className="px-3.5 py-2.5 text-[#767676]">Standard Warehouse</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Live in stores info in drawer */}
            {(() => {
              const live = existingListingsMap[selectedProduct.id] || [];
              if (live.length > 0) {
                return (
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="text-xs font-semibold text-[#1a1a1a] block mb-1.5">Already Listed On:</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {live.map((l) => (
                        <span
                          key={l.id}
                          className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200"
                        >
                          ✓ {l.marketplace_name} ({l.status === "ACTIVE" ? "Live" : "Hidden"})
                        </span>
                      ))}
                    </div>
                  </div>
                );
              }
              return null;
            })()}

            {/* Choose store & custom price action in drawer */}
            {(() => {
              const liveList = existingListingsMap[selectedProduct.id] || [];
              const isDrawerStoreListed = liveList.some(l => l.marketplace_id === selectedChannelId);
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
                          const existing = liveList.find(l => l.marketplace_id === mId);
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
                              {m.name} {existing ? `— Listed ($${existing.selling_price.toFixed(2)})` : ""}
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
                            className="text-[10px] text-[#905831] font-medium bg-[#905831]/10 px-1.5 py-0.5 rounded border border-[#905831]/20 flex items-center gap-0.5"
                            title="Pick random price with 10%-35% margin"
                          >
                            <Sparkles className="h-2.5 w-2.5" />
                            <span>Random Price</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setDrawerCustomPrice((Number(selectedProduct.lowest_cost || 0) * 1.15).toFixed(2))}
                            className="text-[10px] text-gray-500 underline font-medium"
                            title="Reset to rule formula (+15% margin)"
                          >
                            Reset
                          </button>
                        </div>
                      </div>
                      <div className="relative">
                        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#767676] font-medium text-xs">$</span>
                        <input
                          type="number"
                          step="0.01"
                          value={drawerCustomPrice || (Number(selectedProduct.lowest_cost || 0) * 1.15).toFixed(2)}
                          onChange={(e) => setDrawerCustomPrice(e.target.value)}
                          placeholder="Custom price..."
                          className="w-full pl-6 pr-2 py-1.5 bg-white border border-gray-300 rounded-lg text-xs font-semibold text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Title & Description Customization (Collapsible) */}
                  <div className="border border-gray-200 rounded-lg p-3 bg-gray-50/70 space-y-2">
                    <button
                      type="button"
                      onClick={() => setShowDrawerContentEdit(!showDrawerContentEdit)}
                      className="w-full flex items-center justify-between text-xs font-semibold text-[#0a0a0a]"
                    >
                      <span className="flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5 text-[#905831]" />
                        <span>Customize Title & Description</span>
                        {(drawerCustomTitle !== selectedProduct.title || drawerCustomDescription !== (selectedProduct.description || "")) && (
                          <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-medium">Modified</span>
                        )}
                      </span>
                      <span className="text-[11px] text-[#905831] font-medium">
                        {showDrawerContentEdit ? "Hide fields" : "Edit before listing"}
                      </span>
                    </button>

                    {showDrawerContentEdit && (
                      <div className="space-y-3 pt-2 border-t border-gray-200">
                        <div>
                          <label className="block text-[11px] font-semibold text-[#1a1a1a] mb-1">
                            Store Listing Title
                          </label>
                          <input
                            type="text"
                            value={drawerCustomTitle}
                            onChange={(e) => setDrawerCustomTitle(e.target.value)}
                            placeholder="Enter listing title..."
                            className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold text-[#1a1a1a] mb-1">
                            Store Product Description
                          </label>
                          <textarea
                            rows={3}
                            value={drawerCustomDescription}
                            onChange={(e) => setDrawerCustomDescription(e.target.value)}
                            placeholder="Enter custom product description..."
                            className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {isDrawerStoreListed && (
                    <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-900 flex items-center gap-2">
                      <RefreshCw className="h-3.5 w-3.5 text-amber-700 shrink-0" />
                      <span>Already listed in this store. Submitting will update the title, price, and stock without creating duplicates.</span>
                    </div>
                  )}

                  <div className="flex items-center justify-end">
                    <button
                      onClick={() => handlePublishToChannel(
                        selectedProduct, 
                        selectedChannelId, 
                        drawerCustomPrice ? Number(drawerCustomPrice) : Number((Number(selectedProduct.lowest_cost || 0) * 1.15).toFixed(2)),
                        drawerCustomTitle,
                        drawerCustomDescription
                      )}
                      disabled={publishingId === selectedProduct.id}
                      className="px-5 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                    >
                      {isDrawerStoreListed ? <RefreshCw className="h-3.5 w-3.5" /> : <Store className="h-4 w-4" />}
                      <span>
                        {publishingId === selectedProduct.id 
                          ? (isDrawerStoreListed ? "Updating..." : "Listing...") 
                          : (isDrawerStoreListed ? "Update Listing on Store" : "Start Selling on Store")}
                      </span>
                    </button>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* Start Selling / List on Store Modal */}
      {listingModalProduct && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-200 rounded-xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-bold text-[#0a0a0a]">Select Store to Sell On</h3>
                <p className="text-xs text-[#767676] mt-0.5">Choose which marketplace to publish this product to.</p>
              </div>
              <button
                onClick={() => setListingModalProduct(null)}
                className="p-1.5 rounded-lg text-[#767676] hover:text-[#0a0a0a] hover:bg-gray-100 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Product Summary */}
            <div className="p-3.5 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
              <div className="font-semibold text-sm text-[#0a0a0a] line-clamp-1">
                {listingModalProduct.title}
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <span className="text-[10px] text-[#767676] block">Wholesale Cost</span>
                  <span className="font-semibold text-[#0a0a0a]">
                    ${Number(listingModalProduct.lowest_cost || 0).toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#767676] block">Selling Price</span>
                  <span className="font-bold text-[#905831]">
                    ${(Number(listingModalProduct.lowest_cost || 0) * 1.15).toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#767676] block">Stock Available</span>
                  <span className="font-semibold text-emerald-700">
                    {listingModalProduct.total_stock} units
                  </span>
                </div>
              </div>
            </div>

            {/* Already Live Stores Status */}
            {(() => {
              const liveOn = existingListingsMap[listingModalProduct.id] || [];
              if (liveOn.length > 0) {
                return (
                  <div className="text-xs">
                    <span className="text-[#767676] block mb-1 font-medium">Currently listed on:</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {liveOn.map((l) => (
                        <span
                          key={l.id}
                          className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200"
                        >
                          ✓ {l.marketplace_name} ({l.status === "ACTIVE" ? "Live" : "Hidden"})
                        </span>
                      ))}
                    </div>
                  </div>
                );
              }
              return null;
            })()}

            {/* Store Selection & Dynamic Update Notice */}
            {(() => {
              const liveOn = existingListingsMap[listingModalProduct.id] || [];
              const isModalStoreListed = liveOn.some(l => l.marketplace_id === selectedModalChannelId);
              const targetStoreName = marketplaces.find(m => m.id === selectedModalChannelId)?.name || "selected store";

              return (
                <>
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-[#1a1a1a]">
                      Choose Target Marketplace:
                    </label>
                    <select
                      value={selectedModalChannelId}
                      onChange={(e) => {
                        const mId = Number(e.target.value);
                        setSelectedModalChannelId(mId);
                        const existing = liveOn.find(l => l.marketplace_id === mId);
                        if (existing && existing.selling_price > 0) {
                          setModalCustomPrice(existing.selling_price.toFixed(2));
                        } else {
                          const cost = Number(listingModalProduct.lowest_cost || 0);
                          setModalCustomPrice((cost * 1.15).toFixed(2));
                        }
                      }}
                      className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-xs font-medium text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                    >
                      {marketplaces.map((m) => {
                        const existing = liveOn.find(l => l.marketplace_id === m.id);
                        return (
                          <option key={m.id} value={m.id}>
                            {m.name} {existing ? `— Listed ($${existing.selling_price.toFixed(2)})` : ""}
                          </option>
                        );
                      })}
                    </select>
                  </div>

                  {isModalStoreListed ? (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-center gap-2">
                      <RefreshCw className="h-4 w-4 text-amber-700 shrink-0" />
                      <span>Already active on <strong>{targetStoreName}</strong>. Changing the price and submitting will update your existing listing without creating duplicates.</span>
                    </div>
                  ) : null}
                </>
              );
            })()}

            {/* Price Selection (Custom or Random) */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-[#1a1a1a]">
                  Selling Price ($)
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => randomizeModalPrice(Number(listingModalProduct.lowest_cost || 50))}
                    className="text-[11px] text-[#905831] hover:text-[#0a0a0a] font-medium flex items-center gap-1 bg-[#905831]/10 px-2 py-0.5 rounded border border-[#905831]/20 transition-colors"
                    title="Generate a random price with 10%-35% margin"
                  >
                    <Sparkles className="h-3 w-3" />
                    <span>Random Price</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setModalCustomPrice((Number(listingModalProduct.lowest_cost || 0) * 1.15).toFixed(2))}
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
                  value={modalCustomPrice}
                  onChange={(e) => setModalCustomPrice(e.target.value)}
                  placeholder="Enter custom selling price..."
                  className="w-full pl-7 pr-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-[#0a0a0a] font-bold focus:outline-none focus:border-[#0a0a0a]"
                />
              </div>
              <div className="flex items-center justify-between text-[11px] text-[#767676]">
                <span>Wholesale cost: ${Number(listingModalProduct.lowest_cost || 0).toFixed(2)}</span>
                <span>Rule formula (+15%): ${(Number(listingModalProduct.lowest_cost || 0) * 1.15).toFixed(2)}</span>
              </div>
            </div>

            {/* Title & Description Customization (Collapsible) */}
            <div className="border border-gray-200 rounded-lg p-3 bg-gray-50/70 space-y-2">
              <button
                type="button"
                onClick={() => setShowModalContentEdit(!showModalContentEdit)}
                className="w-full flex items-center justify-between text-xs font-semibold text-[#0a0a0a]"
              >
                <span className="flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-[#905831]" />
                  <span>Customize Title & Description</span>
                  {(modalCustomTitle !== listingModalProduct.title || modalCustomDescription !== (listingModalProduct.description || "")) && (
                    <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-medium">Modified</span>
                  )}
                </span>
                <span className="text-[11px] text-[#905831] font-medium">
                  {showModalContentEdit ? "Hide fields" : "Edit before listing"}
                </span>
              </button>

              {showModalContentEdit && (
                <div className="space-y-3 pt-2 border-t border-gray-200">
                  <div>
                    <label className="block text-[11px] font-semibold text-[#1a1a1a] mb-1">
                      Store Listing Title
                    </label>
                    <input
                      type="text"
                      value={modalCustomTitle}
                      onChange={(e) => setModalCustomTitle(e.target.value)}
                      placeholder="Enter listing title..."
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-[#1a1a1a] mb-1">
                      Store Product Description
                    </label>
                    <textarea
                      rows={3}
                      value={modalCustomDescription}
                      onChange={(e) => setModalCustomDescription(e.target.value)}
                      placeholder="Enter custom product description..."
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs text-[#0a0a0a] focus:outline-none focus:border-[#0a0a0a]"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="p-3 bg-[#905831]/[0.06] rounded-lg border border-[#905831]/20 text-xs text-[#905831] space-y-0.5">
              <div className="font-semibold flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5" />
                <span>Automated Sync:</span>
              </div>
              <p className="text-[11px] text-[#767676]">
                Once saved, the system keeps distributor stock and your selling price synchronized across connected channels.
              </p>
            </div>

            {/* Modal Actions */}
            {(() => {
              const liveOn = existingListingsMap[listingModalProduct.id] || [];
              const isModalStoreListed = liveOn.some(l => l.marketplace_id === selectedModalChannelId);

              return (
                <div className="pt-3 border-t border-gray-200 flex items-center justify-end gap-2.5">
                  <button
                    onClick={() => setListingModalProduct(null)}
                    className="px-4 py-2 text-xs font-medium text-[#767676] hover:text-[#0a0a0a] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handlePublishToChannel(
                      listingModalProduct, 
                      selectedModalChannelId, 
                      modalCustomPrice ? Number(modalCustomPrice) : undefined,
                      modalCustomTitle,
                      modalCustomDescription
                    )}
                    disabled={publishingId === listingModalProduct.id}
                    className="px-5 py-2 bg-[#0a0a0a] hover:bg-[#222222] text-white rounded-lg text-xs font-medium transition-all shadow-sm disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {isModalStoreListed ? <RefreshCw className="h-3.5 w-3.5" /> : <Store className="h-3.5 w-3.5" />}
                    <span>
                      {publishingId === listingModalProduct.id 
                        ? (isModalStoreListed ? "Updating..." : "Listing...") 
                        : (isModalStoreListed ? "Update Listing on Store" : "Confirm & Start Selling")}
                    </span>
                  </button>
                </div>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
