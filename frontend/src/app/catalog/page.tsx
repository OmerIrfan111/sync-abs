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
  AlertCircle
} from "lucide-react";
import { fetchApi, Product } from "@/lib/api";

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

  const handlePublishToChannel = async (product: Product, targetMarketplaceId?: number) => {
    const channelId = targetMarketplaceId || selectedChannelId;
    setPublishingId(product.id);
    setPublishSuccess(null);
    try {
      const channel = marketplaces.find(m => m.id === channelId);
      const channelName = channel ? channel.name : "Your Store";
      const res = await fetchApi<any>("/listings/publish", {
        method: "POST",
        body: JSON.stringify({
          product_id: product.id,
          marketplace_id: channelId,
        }),
      });
      setPublishSuccess(`Successfully listed on ${channelName}!`);
      setTimeout(() => setPublishSuccess(null), 4000);
    } catch (err: any) {
      alert("Could not start selling: " + err.message);
    } finally {
      setPublishingId(null);
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
        if (res.length > 0) setSelectedChannelId(res[0].id);
      })
      .catch((err) => console.error("Could not fetch marketplaces:", err));
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
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#0e1526] p-6 rounded-2xl border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Products to Sell</h1>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Wholesale Catalog
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Browse all products provided by your suppliers. Pick what you want to sell and list them on your stores with one click.
          </p>
        </div>
        <div className="text-right self-start sm:self-auto">
          <span className="text-xs text-gray-400 block">Total Catalog Items</span>
          <span className="text-2xl font-black text-white">{total.toLocaleString()}</span>
        </div>
      </div>

      {/* Search & Plain-English Filter Toolbar */}
      <div className="p-5 bg-[#0e1526] border border-gray-800 rounded-2xl space-y-4 shadow-lg">
        <div className="flex flex-col md:flex-row gap-3">
          <form onSubmit={handleSearchSubmit} className="flex-1 relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search products by title, brand, or product code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-gray-900/80 border border-gray-700/80 rounded-xl text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </form>
          <button
            onClick={() => { setPage(1); loadProducts(); }}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-bold transition-all shadow-md shadow-indigo-600/20 shrink-0"
          >
            Find Products
          </button>
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-gray-800/80 text-xs">
          <div className="flex items-center gap-1.5 font-bold text-gray-300">
            <Filter className="h-3.5 w-3.5 text-indigo-400" />
            <span>Filter By:</span>
          </div>

          {/* Brand Filter */}
          <div className="flex items-center gap-1.5">
            <select
              value={selectedBrand}
              onChange={(e) => { setSelectedBrand(e.target.value); setPage(1); }}
              className="px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Brands</option>
              {filterOptions.brands.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-1.5">
            <select
              value={selectedCategory}
              onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
              className="px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Categories</option>
              {filterOptions.categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* In-Stock Toggle */}
          <label className="flex items-center gap-2 cursor-pointer select-none bg-gray-900 border border-gray-700 px-3 py-1.5 rounded-lg hover:border-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={inStockOnly}
              onChange={(e) => { setInStockOnly(e.target.checked); setPage(1); }}
              className="rounded border-gray-700 bg-gray-800 text-indigo-600 focus:ring-0 h-3.5 w-3.5 cursor-pointer"
            />
            <span className="text-xs text-gray-300 font-medium">In Stock Only (Ready to ship)</span>
          </label>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300 px-2.5 py-1.5 bg-rose-500/10 rounded-lg border border-rose-500/20 transition-colors font-medium ml-auto"
            >
              <X className="h-3 w-3" />
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* Success Notification Bar */}
      {publishSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between text-xs font-semibold shadow-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>{publishSuccess} You can view and edit it anytime under &apos;Your Online Stores&apos;.</span>
          </div>
          <button onClick={() => setPublishSuccess(null)} className="text-gray-400 hover:text-white">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Simplified Products Table (Spec Requirement 8) */}
      <div className="bg-[#0e1526] border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-[#131b2e] text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="px-6 py-4">Product</th>
                <th className="px-4 py-4">Your Cost</th>
                <th className="px-4 py-4">Selling Price</th>
                <th className="px-4 py-4">Stock Available</th>
                <th className="px-4 py-4">Live Stores</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-16 text-gray-500">
                    Loading products...
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-16 text-gray-500">
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
                      className={`hover:bg-gray-900/40 transition-colors ${isExcluded ? "opacity-50" : ""}`}
                    >
                      {/* 1. Product Image & Name */}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          {product.images && product.images[0] ? (
                            <img
                              src={product.images[0]}
                              alt={product.title}
                              className="h-12 w-12 rounded-xl object-cover bg-gray-800 border border-gray-700 shrink-0"
                            />
                          ) : (
                            <div className="h-12 w-12 rounded-xl bg-gray-800 border border-gray-700 flex items-center justify-center text-gray-500 shrink-0">
                              <Layers className="h-5 w-5" />
                            </div>
                          )}
                          <div className="max-w-xs sm:max-w-md">
                            <button
                              onClick={() => setSelectedProduct(product)}
                              className="font-bold text-white hover:text-indigo-400 text-left line-clamp-1 transition-colors"
                            >
                              {product.title}
                            </button>
                            <div className="text-xs text-gray-400 mt-0.5">
                              {product.brand || "Standard Brand"} • {product.category || "General Merchandise"}
                            </div>
                            <button
                              onClick={() => setSelectedProduct(product)}
                              className="text-[11px] text-indigo-400 hover:text-indigo-300 underline mt-0.5 block"
                            >
                              View product codes & details &rarr;
                            </button>
                          </div>
                        </div>
                      </td>

                      {/* 2. Your Cost */}
                      <td className="px-4 py-4">
                        <div className="font-bold text-white text-base">
                          {cost > 0 ? `$${cost.toFixed(2)}` : "—"}
                        </div>
                        <div className="text-[10px] text-gray-500">What you pay supplier</div>
                      </td>

                      {/* 3. Suggested Selling Price */}
                      <td className="px-4 py-4">
                        <div className="font-black text-emerald-400 text-base">
                          {cost > 0 ? `$${suggestedPrice}` : "—"}
                        </div>
                        <div className="text-[10px] text-gray-500">With 15% profit markup</div>
                      </td>

                      {/* 4. Stock Available */}
                      <td className="px-4 py-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                          product.total_stock > 0
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}>
                          {product.total_stock > 0 ? `${product.total_stock} ready to ship` : "Out of Stock"}
                        </span>
                        <div className="text-[10px] text-gray-500 mt-0.5">
                          {product.supplier_products.length} {product.supplier_products.length === 1 ? "supplier" : "suppliers"}
                        </div>
                      </td>

                      {/* 5. Live In Stores */}
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-1 flex-wrap">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700">
                            Ready to List
                          </span>
                        </div>
                      </td>

                      {/* 6. Prominent Action Buttons */}
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handlePublishToChannel(product)}
                            disabled={publishingId === product.id || isExcluded}
                            className="px-3.5 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 flex items-center gap-1.5 shrink-0"
                          >
                            <Store className="h-3.5 w-3.5" />
                            <span>{publishingId === product.id ? "Listing..." : "Start Selling This"}</span>
                          </button>

                          <button
                            onClick={() => toggleNotSelling(product.id)}
                            className={`p-2 rounded-xl border text-xs transition-colors ${
                              isExcluded 
                                ? "bg-amber-500/10 border-amber-500/30 text-amber-300" 
                                : "bg-gray-900 border-gray-800 text-gray-400 hover:text-gray-200"
                            }`}
                            title={isExcluded ? "Click to enable" : "Don't sell this product"}
                          >
                            <span className="text-[11px] font-semibold">
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
        <div className="p-4 bg-[#131b2e] border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
          <div>
            Showing Page <span className="text-white font-bold">{page}</span> of{" "}
            <span className="text-white font-bold">{totalPages}</span> ({total} total products)
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-white font-semibold flex items-center gap-1"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Previous Page
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-white font-semibold flex items-center gap-1"
            >
              Next Page <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Product Details Drawer (Collapsible Drawer per Requirement 8) */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-6">
            <div className="flex items-start justify-between pb-4 border-b border-gray-800">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedProduct.title}</h3>
                <p className="text-xs text-gray-400 mt-0.5">Product Details & Wholesale Breakdown</p>
              </div>
              <button
                onClick={() => setSelectedProduct(null)}
                className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Product Overview Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 block">Brand</span>
                <span className="font-bold text-white text-sm">{selectedProduct.brand || "Unbranded"}</span>
              </div>
              <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 block">Category</span>
                <span className="font-bold text-white text-sm">{selectedProduct.category || "General"}</span>
              </div>
              <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 block">Available Stock</span>
                <span className="font-bold text-emerald-400 text-sm">{selectedProduct.total_stock} units</span>
              </div>
              <div className="p-3 bg-gray-900/80 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 block">Lowest Supplier Cost</span>
                <span className="font-bold text-white text-sm">${selectedProduct.lowest_cost ? Number(selectedProduct.lowest_cost).toFixed(2) : "0.00"}</span>
              </div>
            </div>

            {/* Technical Identifiers (Hidden from main table, available here) */}
            <div className="p-4 bg-gray-900/50 rounded-xl border border-gray-800 space-y-2">
              <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Product Identifiers</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div>
                  <span className="text-gray-500 block text-[10px]">Product Code (SKU)</span>
                  <span className="text-indigo-400 font-bold">{selectedProduct.sku}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[10px]">Barcode (UPC)</span>
                  <span className="text-gray-300">{selectedProduct.upc || "None"}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[10px]">European Barcode (EAN)</span>
                  <span className="text-gray-300">{selectedProduct.ean || "None"}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[10px]">Part Number (MPN)</span>
                  <span className="text-gray-300">{selectedProduct.mpn || "None"}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <div>
              <h4 className="text-xs font-bold text-gray-300 mb-1">Product Description</h4>
              <p className="text-xs text-gray-400 leading-relaxed bg-gray-900/30 p-3 rounded-xl border border-gray-800/60">
                {selectedProduct.description || "Standard manufacturer product details."}
              </p>
            </div>

            {/* Distributors carrying this item */}
            <div>
              <h4 className="text-xs font-bold text-white mb-2 flex items-center gap-2">
                <Truck className="h-4 w-4 text-indigo-400" />
                <span>Wholesale Distributors Supplying This Item</span>
              </h4>
              <div className="border border-gray-800 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#131b2e] text-gray-400 uppercase text-[10px]">
                    <tr>
                      <th className="px-4 py-2.5">Distributor</th>
                      <th className="px-4 py-2.5">What You Pay</th>
                      <th className="px-4 py-2.5">Stock Ready</th>
                      <th className="px-4 py-2.5">Shipping</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {selectedProduct.supplier_products.map((sp) => (
                      <tr key={sp.id} className="hover:bg-gray-900/50">
                        <td className="px-4 py-2.5 font-bold text-white">{sp.supplier_name || "Supplier"}</td>
                        <td className="px-4 py-2.5 font-black text-emerald-400">${Number(sp.cost).toFixed(2)}</td>
                        <td className="px-4 py-2.5 text-gray-300 font-semibold">{sp.qty_available} units</td>
                        <td className="px-4 py-2.5 text-gray-400">Standard Warehouse</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* One-click list action in drawer */}
            <div className="pt-4 border-t border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-300 font-bold">Choose Store to List on:</span>
                <select
                  value={selectedChannelId}
                  onChange={(e) => setSelectedChannelId(Number(e.target.value))}
                  className="bg-gray-900 border border-gray-700 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
                >
                  {marketplaces.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={() => handlePublishToChannel(selectedProduct)}
                disabled={publishingId === selectedProduct.id}
                className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
              >
                <Store className="h-4 w-4" />
                <span>{publishingId === selectedProduct.id ? "Listing..." : "Start Selling on Store"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
