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
  Boxes,
  DollarSign,
  Truck,
  ExternalLink,
  ShieldCheck,
  Check,
  Store
} from "lucide-react";
import { fetchApi, Product } from "@/lib/api";

export default function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishingId, setPublishingId] = useState<number | null>(null);
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<number>(1);

  const handlePublishToChannel = async (product: Product) => {
    setPublishingId(product.id);
    setPublishSuccess(null);
    try {
      const channel = marketplaces.find(m => m.id === selectedChannelId);
      const channelName = channel ? channel.name : "Channel";
      const res = await fetchApi<any>("/listings/publish", {
        method: "POST",
        body: JSON.stringify({
          product_id: product.id,
          marketplace_id: selectedChannelId,
        }),
      });
      setPublishSuccess(`Published to ${channelName}! ID: ${res.external_listing_id}`);
    } catch (err: any) {
      alert("Publish failed: " + err.message);
    } finally {
      setPublishingId(null);
    }
  };

  const loadProducts = async () => {
    setLoading(true);
    try {
      const qParam = searchQuery ? `&q=${encodeURIComponent(searchQuery)}` : "";
      const res = await fetchApi<{
        items: Product[];
        total: number;
        page: number;
        page_size: number;
        total_pages: number;
      }>(`/products?page=${page}&page_size=${pageSize}${qParam}`);

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
    loadProducts();
    fetchApi<any[]>("/marketplaces")
      .then((res) => {
        setMarketplaces(res);
        if (res.length > 0) setSelectedChannelId(res[0].id);
      })
      .catch((err) => console.error("Could not fetch marketplaces:", err));
  }, [page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadProducts();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Central Product Catalog</h1>
          <p className="text-sm text-gray-400 mt-1">
            Canonical products matched and synchronized across multiple wholesale distributors.
          </p>
        </div>
        <div className="text-sm text-gray-400 font-medium">
          Total Products: <span className="text-white font-bold">{total}</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="p-4 bg-[#0e1526] border border-gray-800 rounded-2xl flex flex-col md:flex-row gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by SKU, UPC, EAN, MPN, Brand, or Title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-900/80 border border-gray-700/60 rounded-xl text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </form>
        <button
          onClick={() => { setPage(1); loadProducts(); }}
          className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-md shadow-indigo-600/20"
        >
          Search
        </button>
      </div>

      {/* Products Table */}
      <div className="bg-[#0e1526] border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="bg-[#131b2e] text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="px-6 py-4">Product Details</th>
                <th className="px-6 py-4">Identifiers</th>
                <th className="px-6 py-4">Suppliers</th>
                <th className="px-6 py-4">Total Stock</th>
                <th className="px-6 py-4">Lowest Cost</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    Loading catalog items...
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    No products found matching your search.
                  </td>
                </tr>
              ) : (
                products.map((product) => (
                  <tr key={product.id} className="hover:bg-gray-900/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {product.images && product.images[0] ? (
                          <img
                            src={product.images[0]}
                            alt={product.title}
                            className="h-10 w-10 rounded-lg object-cover bg-gray-800 border border-gray-700"
                          />
                        ) : (
                          <div className="h-10 w-10 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center text-gray-500">
                            <Layers className="h-5 w-5" />
                          </div>
                        )}
                        <div className="max-w-xs">
                          <div className="font-semibold text-white truncate">{product.title}</div>
                          <div className="text-xs text-gray-400">{product.brand || "Unbranded"} • {product.category || "General"}</div>
                        </div>
                      </div>
                    </td>

                    <td className="px-6 py-4 font-mono text-xs">
                      <div className="text-indigo-400 font-semibold">{product.sku}</div>
                      {product.upc && <div className="text-gray-500 text-[11px]">UPC: {product.upc}</div>}
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {product.supplier_products.map((sp) => (
                          <span
                            key={sp.id}
                            className="text-[11px] font-medium px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700"
                          >
                            {sp.supplier_name || "Supplier"} (${Number(sp.cost).toFixed(2)})
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        product.total_stock > 0
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}>
                        {product.total_stock > 0 ? `${product.total_stock} units` : "Out of Stock"}
                      </span>
                    </td>

                    <td className="px-6 py-4 font-semibold text-white">
                      {product.lowest_cost ? `$${Number(product.lowest_cost).toFixed(2)}` : "—"}
                    </td>

                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => setSelectedProduct(product)}
                        className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition-colors"
                        title="View Product Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 bg-[#131b2e] border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
          <div>
            Showing Page <span className="text-white font-semibold">{page}</span> of{" "}
            <span className="text-white font-semibold">{totalPages}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-white font-medium flex items-center gap-1"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-white font-medium flex items-center gap-1"
            >
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Product Details Modal (Spec Section 25) */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6">
            <div className="flex items-start justify-between pb-4 border-b border-gray-800">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedProduct.title}</h3>
                <div className="text-xs text-gray-400 font-mono mt-1">SKU: {selectedProduct.sku}</div>
              </div>
              <button
                onClick={() => setSelectedProduct(null)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="py-4 space-y-4 text-sm">
              <p className="text-gray-300 leading-relaxed">{selectedProduct.description || "No description provided."}</p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-gray-900 rounded-xl border border-gray-800">
                  <span className="text-xs text-gray-500 block">Brand</span>
                  <span className="font-semibold text-white">{selectedProduct.brand || "N/A"}</span>
                </div>
                <div className="p-3 bg-gray-900 rounded-xl border border-gray-800">
                  <span className="text-xs text-gray-500 block">Category</span>
                  <span className="font-semibold text-white">{selectedProduct.category || "N/A"}</span>
                </div>
                <div className="p-3 bg-gray-900 rounded-xl border border-gray-800">
                  <span className="text-xs text-gray-500 block">Total Quantity</span>
                  <span className="font-semibold text-emerald-400">{selectedProduct.total_stock} units</span>
                </div>
                <div className="p-3 bg-gray-900 rounded-xl border border-gray-800">
                  <span className="text-xs text-gray-500 block">Lowest Cost</span>
                  <span className="font-semibold text-white">${selectedProduct.lowest_cost ? Number(selectedProduct.lowest_cost).toFixed(2) : "0.00"}</span>
                </div>
              </div>

              {/* Linked Suppliers Table */}
              <div>
                <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                  <Truck className="h-4 w-4 text-indigo-400" />
                  <span>Linked Wholesale Distributors</span>
                </h4>
                <div className="border border-gray-800 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#131b2e] text-gray-400 uppercase">
                      <tr>
                        <th className="px-4 py-2.5">Supplier</th>
                        <th className="px-4 py-2.5">Supplier SKU</th>
                        <th className="px-4 py-2.5">Cost</th>
                        <th className="px-4 py-2.5">Stock</th>
                        <th className="px-4 py-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {selectedProduct.supplier_products.map((sp) => (
                        <tr key={sp.id} className="hover:bg-gray-900/50">
                          <td className="px-4 py-2.5 font-semibold text-white">{sp.supplier_name || "Supplier"}</td>
                          <td className="px-4 py-2.5 font-mono text-gray-400">{sp.supplier_sku}</td>
                          <td className="px-4 py-2.5 font-semibold text-white">${Number(sp.cost).toFixed(2)}</td>
                          <td className="px-4 py-2.5 text-gray-300">{sp.qty_available} units</td>
                          <td className="px-4 py-2.5">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {sp.stock_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              {/* Multi-Channel Publish Action */}
              <div className="pt-4 border-t border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-medium">Channel:</span>
                  <select
                    value={selectedChannelId}
                    onChange={(e) => setSelectedChannelId(Number(e.target.value))}
                    className="bg-gray-900 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {marketplaces.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.adapter_class})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-3">
                  {publishSuccess && (
                    <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                      <Check className="h-4 w-4 text-emerald-400" />
                      {publishSuccess}
                    </span>
                  )}
                  <button
                    onClick={() => handlePublishToChannel(selectedProduct)}
                    disabled={publishingId === selectedProduct.id}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                  >
                    <Store className="h-3.5 w-3.5" />
                    <span>{publishingId === selectedProduct.id ? "Publishing..." : "Publish Offer to Channel"}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
