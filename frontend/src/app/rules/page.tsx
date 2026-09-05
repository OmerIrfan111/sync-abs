"use client";

import React, { useEffect, useState } from "react";
import { 
  SlidersHorizontal, 
  DollarSign, 
  Package, 
  Truck, 
  Plus, 
  Trash2, 
  Check, 
  AlertCircle, 
  RefreshCw, 
  Play, 
  ArrowRight, 
  ShieldCheck, 
  TrendingUp, 
  Boxes, 
  HelpCircle, 
  Sparkles,
  ChevronDown,
  ChevronUp,
  Store,
  CheckCircle2,
  X
} from "lucide-react";
import { 
  fetchApi, 
  PricingRule, 
  InventoryRule, 
  SupplierPriority, 
  Product, 
  Supplier, 
  RulePreview 
} from "@/lib/api";

export default function RulesPage() {
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Core laymen state
  const [pricingMode, setPricingMode] = useState<"PERCENTAGE_MARKUP" | "FIXED_PROFIT">("PERCENTAGE_MARKUP");
  const [markupPercent, setMarkupPercent] = useState("20");
  const [fixedDollar, setFixedDollar] = useState("10.00");
  const [sampleCost, setSampleCost] = useState("50.00");
  const [safetyBuffer, setSafetyBuffer] = useState("2");
  const [outOfStockAction, setOutOfStockAction] = useState("DISABLE_LISTING");
  const [savingGlobal, setSavingGlobal] = useState(false);

  // Advanced section toggle
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Data states
  const [pricingRules, setPricingRules] = useState<PricingRule[]>([]);
  const [inventoryRules, setInventoryRules] = useState<InventoryRule[]>([]);
  const [supplierPriorities, setSupplierPriorities] = useState<SupplierPriority[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);

  // Simulator states
  const [simProductId, setSimProductId] = useState<number | "">("");
  const [simPreview, setSimPreview] = useState<RulePreview | null>(null);
  const [simulating, setSimulating] = useState(false);

  // Advanced Overrides modal
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideProductId, setOverrideProductId] = useState("");
  const [overridePercent, setOverridePercent] = useState("25");

  const loadData = async () => {
    setLoading(true);
    try {
      const [pricingRes, invRes, priorityRes, prodRes, suppRes] = await Promise.all([
        fetchApi<PricingRule[]>("/rules/pricing"),
        fetchApi<InventoryRule[]>("/rules/inventory"),
        fetchApi<SupplierPriority[]>("/rules/supplier-priority"),
        fetchApi<{ items: Product[] }>("/products?page=1&page_size=100"),
        fetchApi<Supplier[]>("/suppliers"),
      ]);
      setPricingRules(pricingRes);
      setInventoryRules(invRes);
      setSupplierPriorities(priorityRes);
      setProducts(prodRes.items);
      setSuppliers(suppRes);

      // Find global rule if set
      const globalRule = pricingRes.find(r => !r.product_id && !r.marketplace_id);
      if (globalRule) {
        if (globalRule.rule_type === "PERCENTAGE_MARKUP") {
          setPricingMode("PERCENTAGE_MARKUP");
          setMarkupPercent(String(globalRule.percentage || "20"));
        } else if (globalRule.rule_type === "FIXED_PROFIT") {
          setPricingMode("FIXED_PROFIT");
          setFixedDollar(String(globalRule.fixed_amount || "10.00"));
        }
      }

      // Find global inventory rule if set
      const globalInv = invRes.find(r => !r.product_id);
      if (globalInv) {
        setSafetyBuffer(String(globalInv.safety_buffer || 2));
        setOutOfStockAction(globalInv.out_of_stock_action || "DISABLE_LISTING");
      }

      if (prodRes.items.length > 0 && simProductId === "") {
        setSimProductId(prodRes.items[0].id);
      }
    } catch (err: any) {
      console.error("Error loading rules data:", err);
      showFeedback(err.message || "Failed to load rules", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const showFeedback = (message: string, type: "success" | "error") => {
    setFeedback({ message, type });
    setTimeout(() => setFeedback(null), 4000);
  };

  // Save Main Profit & Stock Goal (Requirement 10)
  const handleSaveGlobalRules = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingGlobal(true);
    try {
      // 1. Save pricing rule
      await fetchApi("/rules/pricing", {
        method: "POST",
        body: JSON.stringify({
          rule_type: pricingMode,
          percentage: pricingMode === "PERCENTAGE_MARKUP" ? parseFloat(markupPercent) : 0,
          fixed_amount: pricingMode === "FIXED_PROFIT" ? parseFloat(fixedDollar) : 0,
          notes: "Primary shop owner profit rule"
        })
      });

      // 2. Save inventory safety rule
      await fetchApi("/rules/inventory", {
        method: "POST",
        body: JSON.stringify({
          safety_buffer: parseInt(safetyBuffer) || 0,
          out_of_stock_action: outOfStockAction
        })
      });

      showFeedback("Profit & stock rules saved! All your stores will now use these settings.", "success");
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to save settings", "error");
    } finally {
      setSavingGlobal(false);
    }
  };

  // Run Simulator
  const handleRunSimulator = async () => {
    if (!simProductId) return;
    setSimulating(true);
    try {
      const data = await fetchApi<RulePreview>(`/rules/preview/${simProductId}`);
      setSimPreview(data);
    } catch (err: any) {
      showFeedback("Simulator error: " + err.message, "error");
    } finally {
      setSimulating(false);
    }
  };

  // Delete an override rule
  const handleDeleteRule = async (endpoint: string, id: number) => {
    try {
      await fetchApi(`/rules/${endpoint}/${id}`, { method: "DELETE" });
      showFeedback("Override rule removed successfully.", "success");
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to delete rule", "error");
    }
  };

  // Live calculation for preview
  const costNum = parseFloat(sampleCost) || 0;
  let sellingPricePreview = 0;
  let profitAmountPreview = 0;

  if (pricingMode === "PERCENTAGE_MARKUP") {
    const pct = parseFloat(markupPercent) || 0;
    profitAmountPreview = (costNum * pct) / 100;
    sellingPricePreview = costNum + profitAmountPreview;
  } else {
    profitAmountPreview = parseFloat(fixedDollar) || 0;
    sellingPricePreview = costNum + profitAmountPreview;
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-[#0e1526] p-6 rounded-2xl border border-gray-800 shadow-xl">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-black text-white tracking-tight">Pricing & Stock Rules</h1>
          <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Automated Calculations
          </span>
        </div>
        <p className="text-sm text-gray-400 mt-1">
          Set how much profit you want to make on each product. The system will automatically calculate the selling price and update your stores.
        </p>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-2 shadow-lg ${
          feedback.type === "success" 
            ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300"
            : "bg-rose-500/10 border border-rose-500/30 text-rose-300"
        }`}>
          {feedback.type === "success" ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <AlertCircle className="h-4 w-4 text-rose-400" />}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Main Plain English Profit Form (Requirement 10) */}
      <form onSubmit={handleSaveGlobalRules} className="space-y-6">
        <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-xl space-y-6">
          <div className="border-b border-gray-800 pb-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-emerald-400" />
              <span>How much profit do you want to make?</span>
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Choose percentage markup or fixed dollar profit. We automatically adjust every item in your catalog.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Option A: Percentage Markup */}
            <div 
              onClick={() => setPricingMode("PERCENTAGE_MARKUP")}
              className={`p-5 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between ${
                pricingMode === "PERCENTAGE_MARKUP"
                  ? "bg-indigo-950/40 border-indigo-500 shadow-md shadow-indigo-500/10"
                  : "bg-gray-900/60 border-gray-800 hover:border-gray-700"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Option A (Most Popular)</span>
                  <input 
                    type="radio" 
                    name="pricingMode" 
                    checked={pricingMode === "PERCENTAGE_MARKUP"}
                    onChange={() => setPricingMode("PERCENTAGE_MARKUP")}
                    className="text-indigo-600 focus:ring-0 cursor-pointer h-4 w-4"
                  />
                </div>
                <div className="text-sm font-bold text-white mb-2">
                  Make a percentage profit on every product
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">Add</span>
                  <input
                    type="number"
                    min="1"
                    max="500"
                    value={markupPercent}
                    onChange={(e) => setMarkupPercent(e.target.value)}
                    className="w-24 px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-xl text-sm font-black text-white text-center focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-sm font-bold text-indigo-400">% profit</span>
                </div>
              </div>
              <p className="text-[11px] text-gray-400 mt-3">
                Example: On a $50 product, a 20% markup sells for $60.
              </p>
            </div>

            {/* Option B: Fixed Dollar Amount */}
            <div 
              onClick={() => setPricingMode("FIXED_PROFIT")}
              className={`p-5 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between ${
                pricingMode === "FIXED_PROFIT"
                  ? "bg-indigo-950/40 border-indigo-500 shadow-md shadow-indigo-500/10"
                  : "bg-gray-900/60 border-gray-800 hover:border-gray-700"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">Option B</span>
                  <input 
                    type="radio" 
                    name="pricingMode" 
                    checked={pricingMode === "FIXED_PROFIT"}
                    onChange={() => setPricingMode("FIXED_PROFIT")}
                    className="text-indigo-600 focus:ring-0 cursor-pointer h-4 w-4"
                  />
                </div>
                <div className="text-sm font-bold text-white mb-2">
                  Make a flat dollar profit on every product
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">Add</span>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-bold">$</span>
                    <input
                      type="number"
                      step="0.50"
                      min="0"
                      value={fixedDollar}
                      onChange={(e) => setFixedDollar(e.target.value)}
                      className="w-28 pl-7 pr-3 py-1.5 bg-gray-900 border border-gray-700 rounded-xl text-sm font-black text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <span className="text-sm font-bold text-emerald-400">flat profit</span>
                </div>
              </div>
              <p className="text-[11px] text-gray-400 mt-3">
                Example: On a $50 product, adding $10 sells for $60.
              </p>
            </div>
          </div>

          {/* Live Preview Box (Requirement 10) */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-gray-900/90 via-slate-900 to-indigo-950/40 border border-indigo-500/20 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-indigo-400" />
                <span>Live Calculation Preview</span>
              </span>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span>Test with Supplier Cost:</span>
                <div className="relative">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                  <input
                    type="number"
                    value={sampleCost}
                    onChange={(e) => setSampleCost(e.target.value)}
                    className="w-20 pl-5 pr-2 py-1 bg-gray-950 border border-gray-700 rounded-lg text-xs font-bold text-white text-right"
                  />
                </div>
              </div>
            </div>

            <div className="p-4 bg-gray-950/80 rounded-xl border border-gray-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-sm">
              <div className="text-gray-300">
                If the wholesale supplier charges you <span className="font-bold text-white">${costNum.toFixed(2)}</span>:
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <span className="text-xs text-gray-500 block">Customer Pays</span>
                  <span className="text-xl font-black text-emerald-400">${sellingPricePreview.toFixed(2)}</span>
                </div>
                <div className="text-right pl-4 border-l border-gray-800">
                  <span className="text-xs text-gray-500 block">Your Profit</span>
                  <span className="text-base font-bold text-indigo-400">+${profitAmountPreview.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stock Safety Buffer Section (Requirement 1 & 3) */}
        <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-xl space-y-5">
          <div className="border-b border-gray-800 pb-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-400" />
              <span>Stock Protection & Safety Buffer</span>
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Prevent accidentally selling items that are already out of stock at the warehouse.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Safety Buffer Units */}
            <div className="p-4 bg-gray-900/60 rounded-xl border border-gray-800 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-gray-300">
                  Keep this many units as backup
                </label>
                <div className="flex items-center gap-1.5 text-xs">
                  <input
                    type="number"
                    min="0"
                    max="20"
                    value={safetyBuffer}
                    onChange={(e) => setSafetyBuffer(e.target.value)}
                    className="w-16 px-2 py-1 bg-gray-950 border border-gray-700 rounded-lg text-xs font-black text-white text-center focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-gray-400 font-medium">units</span>
                </div>
              </div>
              <p className="text-[11px] text-gray-400 leading-snug">
                If the supplier warehouse has 10 units and backup is set to 2, your online stores will show 8 available.
              </p>
            </div>

            {/* What to do when out of stock */}
            <div className="p-4 bg-gray-900/60 rounded-xl border border-gray-800 space-y-2">
              <label className="text-xs font-bold text-gray-300 block">
                What to do when a product runs out
              </label>
              <div className="space-y-1.5 text-xs text-gray-300">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="outOfStockAction"
                    value="DISABLE_LISTING"
                    checked={outOfStockAction === "DISABLE_LISTING"}
                    onChange={(e) => setOutOfStockAction(e.target.value)}
                    className="text-indigo-600 focus:ring-0 h-3.5 w-3.5"
                  />
                  <span>Hide product from buyers until restocked (Recommended)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="outOfStockAction"
                    value="SET_QUANTITY_ZERO"
                    checked={outOfStockAction === "SET_QUANTITY_ZERO"}
                    onChange={(e) => setOutOfStockAction(e.target.value)}
                    className="text-indigo-600 focus:ring-0 h-3.5 w-3.5"
                  />
                  <span>Keep listing active showing &apos;0 available&apos;</span>
                </label>
              </div>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={savingGlobal}
              className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-sm font-bold transition-all shadow-md shadow-emerald-600/20 disabled:opacity-50"
            >
              {savingGlobal ? "Saving Settings..." : "Save Profit & Stock Rules"}
            </button>
          </div>
        </div>
      </form>

      {/* Advanced Collapsible Section (Requirement 3 & 10) */}
      <div className="p-6 rounded-2xl bg-[#0e1526] border border-gray-800 shadow-xl space-y-4">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between text-left"
        >
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4 text-indigo-400" />
              <span>Set different rules for specific products or stores (Advanced)</span>
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Override your main profit rule for individual items, or test scenario calculations with the live simulator.
            </p>
          </div>
          <div className="p-1.5 rounded-lg bg-gray-800 text-gray-400 hover:text-white">
            {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </div>
        </button>

        {showAdvanced && (
          <div className="pt-4 border-t border-gray-800 space-y-6">
            {/* Custom Overrides Table */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Active Custom Overrides</h4>
                <button
                  onClick={() => setShowOverrideModal(true)}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 border border-gray-700"
                >
                  <Plus className="h-3 w-3" />
                  <span>Add Product Override</span>
                </button>
              </div>

              {pricingRules.filter(r => r.product_id).length === 0 ? (
                <div className="text-center py-6 text-xs text-gray-500 bg-gray-900/40 rounded-xl border border-gray-800/80">
                  No individual product overrides configured. All products are currently using your main {pricingMode === "PERCENTAGE_MARKUP" ? `${markupPercent}% markup` : `$${fixedDollar} profit`} rule.
                </div>
              ) : (
                <div className="border border-gray-800 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-xs text-gray-300">
                    <thead className="bg-[#131b2e] text-gray-400 uppercase text-[10px]">
                      <tr>
                        <th className="px-4 py-2.5">Product</th>
                        <th className="px-4 py-2.5">Custom Markup</th>
                        <th className="px-4 py-2.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {pricingRules.filter(r => r.product_id).map((r) => (
                        <tr key={r.id}>
                          <td className="px-4 py-2.5 font-bold text-white">{r.product_title || `Product #${r.product_id}`}</td>
                          <td className="px-4 py-2.5 text-indigo-400 font-black">{r.percentage}% markup</td>
                          <td className="px-4 py-2.5 text-right">
                            <button
                              onClick={() => handleDeleteRule("pricing", r.id)}
                              className="text-rose-400 hover:text-rose-300 font-semibold"
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Live Scenario Simulator */}
            <div className="p-4 bg-gray-900/50 rounded-xl border border-gray-800 space-y-3">
              <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                <Play className="h-3.5 w-3.5 text-indigo-400" />
                <span>Live Calculator Simulator</span>
              </h4>
              <p className="text-[11px] text-gray-400">
                Select any product to see exactly how its supplier cost, safety buffer, and profit rule will calculate in real-time.
              </p>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                <select
                  value={simProductId}
                  onChange={(e) => setSimProductId(Number(e.target.value))}
                  className="flex-1 px-3 py-2 bg-gray-950 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title} (Cost: ${Number(p.lowest_cost || 0).toFixed(2)})
                    </option>
                  ))}
                </select>

                <button
                  onClick={handleRunSimulator}
                  disabled={simulating || !simProductId}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-colors disabled:opacity-50"
                >
                  {simulating ? "Calculating..." : "Test Calculation"}
                </button>
              </div>

              {simPreview && (
                <div className="mt-3 p-3.5 bg-gray-950 rounded-xl border border-indigo-500/20 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-gray-500 block text-[10px]">Supplier Cost</span>
                    <span className="font-bold text-white">${Number(simPreview.pricing?.supplier_cost ?? 0).toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block text-[10px]">Calculated Selling Price</span>
                    <span className="font-black text-emerald-400">${Number(simPreview.pricing?.calculated_price ?? 0).toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block text-[10px]">Stock Shown in Store</span>
                    <span className="font-bold text-indigo-400">{simPreview.inventory?.calculated_marketplace_qty ?? 0} units</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block text-[10px]">Store Status</span>
                    <span className="font-bold text-emerald-400">{simPreview.inventory?.target_listing_status ?? "ACTIVE"}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Add Product Override Modal */}
      {showOverrideModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1526] border border-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-800">
              <div>
                <h3 className="text-base font-bold text-white">Add Custom Product Rule</h3>
                <p className="text-xs text-gray-400">Set a specific markup for one product.</p>
              </div>
              <button
                onClick={() => setShowOverrideModal(false)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">Choose Product</label>
                <select
                  value={overrideProductId}
                  onChange={(e) => setOverrideProductId(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select a product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">Custom Profit Markup (%)</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={overridePercent}
                    onChange={(e) => setOverridePercent(e.target.value)}
                    className="w-24 px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-xl text-sm font-bold text-white focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-xs text-indigo-400 font-bold">% profit</span>
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <button
                onClick={() => setShowOverrideModal(false)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!overrideProductId) return;
                  try {
                    await fetchApi("/rules/pricing", {
                      method: "POST",
                      body: JSON.stringify({
                        product_id: parseInt(overrideProductId),
                        rule_type: "PERCENTAGE_MARKUP",
                        percentage: parseFloat(overridePercent) || 0
                      })
                    });
                    setShowOverrideModal(false);
                    showFeedback("Custom product rule created!", "success");
                    loadData();
                  } catch (err: any) {
                    alert("Error: " + err.message);
                  }
                }}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold"
              >
                Save Override
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
