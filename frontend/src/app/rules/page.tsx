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
  Sparkles
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
  const [activeTab, setActiveTab] = useState<"pricing" | "inventory" | "supplier" | "simulator">("pricing");
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ message: string; type: "success" | "error" } | null>(null);

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

  // Modal states
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [showInventoryModal, setShowInventoryModal] = useState(false);
  const [showPriorityModal, setShowPriorityModal] = useState(false);

  // Pricing Form State
  const [priceForm, setPriceForm] = useState({
    product_id: "",
    rule_type: "PERCENTAGE_MARKUP",
    percentage: "15.00",
    fixed_amount: "0.00",
    marketplace_fee: "0.00",
    desired_margin: "0.00",
    notes: ""
  });

  // Inventory Form State
  const [invForm, setInvForm] = useState({
    product_id: "",
    safety_buffer: "2",
    out_of_stock_action: "SET_QUANTITY_ZERO"
  });

  // Supplier Priority Form State
  const [priorityForm, setPriorityForm] = useState({
    product_id: "",
    supplier_id: "",
    priority_rank: "1",
    selection_rule: "LOWEST_COST"
  });

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

  // --- Handlers: Pricing Rule ---
  const handleCreatePricingRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        rule_type: priceForm.rule_type,
        notes: priceForm.notes || undefined,
      };
      if (priceForm.product_id) payload.product_id = parseInt(priceForm.product_id);
      if (priceForm.rule_type === "PERCENTAGE_MARKUP") payload.percentage = parseFloat(priceForm.percentage) || 0;
      if (priceForm.rule_type === "FIXED_PROFIT") payload.fixed_amount = parseFloat(priceForm.fixed_amount) || 0;
      if (priceForm.rule_type === "FEE_MARGIN") {
        payload.marketplace_fee = parseFloat(priceForm.marketplace_fee) || 0;
        payload.desired_margin = parseFloat(priceForm.desired_margin) || 0;
      }

      await fetchApi("/rules/pricing", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      showFeedback("Pricing rule created successfully", "success");
      setShowPricingModal(false);
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to create pricing rule", "error");
    }
  };

  const handleDeletePricingRule = async (id: number) => {
    if (!confirm("Are you sure you want to delete this pricing rule?")) return;
    try {
      await fetchApi(`/rules/pricing/${id}`, { method: "DELETE" });
      showFeedback("Pricing rule deleted", "success");
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to delete pricing rule", "error");
    }
  };

  // --- Handlers: Inventory Rule ---
  const handleCreateInventoryRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        safety_buffer: parseInt(invForm.safety_buffer) || 0,
        out_of_stock_action: invForm.out_of_stock_action,
      };
      if (invForm.product_id) payload.product_id = parseInt(invForm.product_id);

      await fetchApi("/rules/inventory", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      showFeedback("Inventory rule created successfully", "success");
      setShowInventoryModal(false);
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to create inventory rule", "error");
    }
  };

  const handleDeleteInventoryRule = async (id: number) => {
    if (!confirm("Are you sure you want to delete this inventory rule?")) return;
    try {
      await fetchApi(`/rules/inventory/${id}`, { method: "DELETE" });
      showFeedback("Inventory rule deleted", "success");
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to delete inventory rule", "error");
    }
  };

  // --- Handlers: Supplier Priority ---
  const handleCreatePriority = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!priorityForm.product_id || !priorityForm.supplier_id) {
      showFeedback("Please select both product and supplier", "error");
      return;
    }
    try {
      await fetchApi("/rules/supplier-priority", {
        method: "POST",
        body: JSON.stringify({
          product_id: parseInt(priorityForm.product_id),
          supplier_id: parseInt(priorityForm.supplier_id),
          priority_rank: parseInt(priorityForm.priority_rank) || 1,
          selection_rule: priorityForm.selection_rule,
        }),
      });

      showFeedback("Supplier priority configured successfully", "success");
      setShowPriorityModal(false);
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to configure supplier priority", "error");
    }
  };

  const handleDeletePriority = async (id: number) => {
    if (!confirm("Are you sure you want to delete this supplier priority?")) return;
    try {
      await fetchApi(`/rules/supplier-priority/${id}`, { method: "DELETE" });
      showFeedback("Supplier priority deleted", "success");
      loadData();
    } catch (err: any) {
      showFeedback(err.message || "Failed to delete supplier priority", "error");
    }
  };

  // --- Handlers: Simulator ---
  const handleRunSimulator = async () => {
    if (!simProductId) return;
    setSimulating(true);
    try {
      const res = await fetchApi<RulePreview>(`/rules/preview/${simProductId}`);
      setSimPreview(res);
    } catch (err: any) {
      showFeedback(err.message || "Failed to run rule simulator", "error");
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
              <SlidersHorizontal className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Rules & Automation Engine</h1>
              <p className="text-sm text-gray-400">
                Configure hierarchical pricing formulas, inventory safety buffers, and multi-supplier routing.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3.5 py-2 bg-gray-800/80 hover:bg-gray-700 text-gray-200 rounded-lg text-sm font-medium border border-gray-700 transition"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-indigo-400" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Global Toast Feedback */}
      {feedback && (
        <div
          className={`p-4 rounded-xl text-sm font-medium flex items-center justify-between shadow-lg animate-in fade-in duration-200 border ${
            feedback.type === "success"
              ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-200"
              : "bg-rose-950/80 border-rose-500/50 text-rose-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === "success" ? <Check className="h-5 w-5 text-emerald-400" /> : <AlertCircle className="h-5 w-5 text-rose-400" />}
            <span>{feedback.message}</span>
          </div>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Pricing Rules</span>
            <DollarSign className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">{pricingRules.length}</div>
          <p className="text-xs text-gray-400 mt-1">Hierarchical markups & fees</p>
        </div>

        <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Inventory Rules</span>
            <Package className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">{inventoryRules.length}</div>
          <p className="text-xs text-gray-400 mt-1">Safety buffers & OOS actions</p>
        </div>

        <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Supplier Priorities</span>
            <Truck className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">{supplierPriorities.length}</div>
          <p className="text-xs text-gray-400 mt-1">Multi-supplier order routing</p>
        </div>

        <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Catalog Coverage</span>
            <Boxes className="h-4 w-4 text-violet-400" />
          </div>
          <div className="text-2xl font-bold text-white">{products.length} Products</div>
          <p className="text-xs text-gray-400 mt-1">Active canonical items</p>
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex border-b border-gray-800 gap-2">
        <button
          onClick={() => setActiveTab("pricing")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "pricing"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <DollarSign className="h-4 w-4" />
          <span>Pricing Rules</span>
          <span className="ml-1 text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-300">
            {pricingRules.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("inventory")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "inventory"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Package className="h-4 w-4" />
          <span>Inventory Rules & Safety Buffers</span>
          <span className="ml-1 text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-300">
            {inventoryRules.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("supplier")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "supplier"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Truck className="h-4 w-4" />
          <span>Multi-Supplier Routing</span>
          <span className="ml-1 text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-300">
            {supplierPriorities.length}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveTab("simulator");
            if (!simPreview && simProductId) handleRunSimulator();
          }}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "simulator"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Sparkles className="h-4 w-4 text-amber-400" />
          <span>Live Rule Simulator</span>
        </button>
      </div>

      {/* TAB 1: PRICING RULES */}
      {activeTab === "pricing" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Pricing Formula Hierarchy</h2>
              <p className="text-xs text-gray-400">
                Evaluation order: Product & Marketplace &rarr; Product &rarr; Marketplace &rarr; Global Default (+15%).
              </p>
            </div>
            <button
              onClick={() => setShowPricingModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
            >
              <Plus className="h-4 w-4" />
              <span>Add Pricing Rule</span>
            </button>
          </div>

          <div className="bg-[#131b2e] border border-gray-800 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-[#0e1526] text-xs uppercase font-semibold text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="px-6 py-3.5">Scope</th>
                  <th className="px-6 py-3.5">Rule Type</th>
                  <th className="px-6 py-3.5">Calculation Formula</th>
                  <th className="px-6 py-3.5">Notes</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {pricingRules.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No custom pricing rules configured. Global fallback is active: <strong>Cost + 15% Markup</strong>.
                    </td>
                  </tr>
                ) : (
                  pricingRules.map((rule) => (
                    <tr key={rule.id} className="hover:bg-gray-800/30 transition">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-white">
                          {rule.product_title || (rule.product_sku ? `SKU: ${rule.product_sku}` : "Global Default (All Products)")}
                        </div>
                        {rule.marketplace_name && (
                          <div className="text-xs text-indigo-400 font-medium mt-0.5">
                            Marketplace: {rule.marketplace_name}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {rule.rule_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-gray-200">
                        {rule.rule_type === "PERCENTAGE_MARKUP" && `Cost + ${rule.percentage}%`}
                        {rule.rule_type === "FIXED_PROFIT" && `Cost + $${Number(rule.fixed_amount).toFixed(2)}`}
                        {rule.rule_type === "FEE_MARGIN" && `(Cost * ${1 + Number(rule.desired_margin) / 100}) / (1 - ${Number(rule.marketplace_fee) / 100})`}
                      </td>
                      <td className="px-6 py-4 text-xs text-gray-400">
                        {rule.notes || "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDeletePricingRule(rule.id)}
                          className="p-1.5 hover:bg-rose-500/20 text-gray-400 hover:text-rose-400 rounded-lg transition"
                          title="Delete Rule"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: INVENTORY RULES */}
      {activeTab === "inventory" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Safety Buffers & Out-of-Stock Protection</h2>
              <p className="text-xs text-gray-400">
                Ensures you never oversell: <strong>Marketplace Qty = max(Supplier Stock - Safety Buffer, 0)</strong> with zero floor guarantee.
              </p>
            </div>
            <button
              onClick={() => setShowInventoryModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
            >
              <Plus className="h-4 w-4" />
              <span>Add Inventory Rule</span>
            </button>
          </div>

          <div className="bg-[#131b2e] border border-gray-800 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-[#0e1526] text-xs uppercase font-semibold text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="px-6 py-3.5">Scope</th>
                  <th className="px-6 py-3.5">Safety Buffer</th>
                  <th className="px-6 py-3.5">Out-of-Stock Action</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {inventoryRules.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                      No custom inventory rules configured. System defaults: <strong>Buffer = 0, OOS Action = SET_QUANTITY_ZERO</strong>.
                    </td>
                  </tr>
                ) : (
                  inventoryRules.map((rule) => (
                    <tr key={rule.id} className="hover:bg-gray-800/30 transition">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-white">
                          {rule.product_title || (rule.product_sku ? `SKU: ${rule.product_sku}` : "Global Default (All Products)")}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full text-xs border border-emerald-500/20">
                          {rule.safety_buffer} Units Reserved
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {rule.out_of_stock_action}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDeleteInventoryRule(rule.id)}
                          className="p-1.5 hover:bg-rose-500/20 text-gray-400 hover:text-rose-400 rounded-lg transition"
                          title="Delete Rule"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SUPPLIER PRIORITY */}
      {activeTab === "supplier" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Multi-Supplier Selection & Routing</h2>
              <p className="text-xs text-gray-400">
                Controls which supplier is chosen when multiple distributors offer the same product.
              </p>
            </div>
            <button
              onClick={() => setShowPriorityModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
            >
              <Plus className="h-4 w-4" />
              <span>Configure Supplier Priority</span>
            </button>
          </div>

          <div className="bg-[#131b2e] border border-gray-800 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-[#0e1526] text-xs uppercase font-semibold text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="px-6 py-3.5">Product</th>
                  <th className="px-6 py-3.5">Preferred Supplier</th>
                  <th className="px-6 py-3.5">Priority Rank</th>
                  <th className="px-6 py-3.5">Selection Strategy</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {supplierPriorities.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No explicit priorities set. All products dynamically route to <strong>LOWEST_COST (In-Stock)</strong>.
                    </td>
                  </tr>
                ) : (
                  supplierPriorities.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-800/30 transition">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-white">{item.product_title || `Product #${item.product_id}`}</div>
                        <div className="text-xs text-gray-400 font-mono mt-0.5">{item.product_sku}</div>
                      </td>
                      <td className="px-6 py-4 font-medium text-indigo-300">
                        {item.supplier_name || `Supplier #${item.supplier_id}`}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-gray-800 text-gray-200 border border-gray-700">
                          Rank #{item.priority_rank}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {item.selection_rule}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDeletePriority(item.id)}
                          className="p-1.5 hover:bg-rose-500/20 text-gray-400 hover:text-rose-400 rounded-lg transition"
                          title="Delete Priority"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: LIVE SIMULATOR */}
      {activeTab === "simulator" && (
        <div className="space-y-6">
          <div className="bg-[#131b2e] border border-gray-800 rounded-xl p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-amber-400" />
                  <span>Real-Time Rule Calculation Dry-Run</span>
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  Simulate live supplier selection, inventory deductions, and pricing formulas without altering marketplace offers.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={simProductId}
                  onChange={(e) => setSimProductId(Number(e.target.value))}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.title}
                    </option>
                  ))}
                </select>

                <button
                  onClick={handleRunSimulator}
                  disabled={simulating || !simProductId}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
                >
                  <Play className={`h-4 w-4 ${simulating ? "animate-spin" : ""}`} />
                  <span>Simulate Now</span>
                </button>
              </div>
            </div>

            {simPreview && (
              <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Supplier Routing Card */}
                <div className="bg-[#0e1526] border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs uppercase font-semibold text-gray-400">1. Winning Supplier</span>
                    <Truck className="h-4 w-4 text-indigo-400" />
                  </div>
                  {simPreview.selected_supplier ? (
                    <div className="space-y-3">
                      <div className="text-xl font-bold text-white">
                        {simPreview.selected_supplier.supplier_name}
                      </div>
                      <div className="space-y-1.5 text-xs text-gray-300">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Wholesale Cost:</span>
                          <span className="font-semibold text-emerald-400 font-mono">
                            ${Number(simPreview.selected_supplier.cost).toFixed(2)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Distributor Stock:</span>
                          <span className="font-semibold text-white font-mono">
                            {simPreview.selected_supplier.stock} units
                          </span>
                        </div>
                        {simPreview.selected_supplier.lead_time_days && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">Lead Time:</span>
                            <span className="text-gray-200">
                              {simPreview.selected_supplier.lead_time_days} days
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-sm text-rose-400 font-medium">No active supplier with stock</div>
                  )}
                </div>

                {/* Inventory Calculation Card */}
                <div className="bg-[#0e1526] border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs uppercase font-semibold text-gray-400">2. Inventory Computation</span>
                    <Package className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="space-y-3">
                    <div className="text-xl font-bold text-emerald-400 font-mono">
                      {simPreview.inventory.calculated_marketplace_qty} units
                    </div>
                    <div className="space-y-1.5 text-xs text-gray-300">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Raw Supplier Stock:</span>
                        <span className="font-mono">{simPreview.inventory.raw_supplier_stock}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Safety Buffer Subtracted:</span>
                        <span className="font-mono text-rose-400">-{simPreview.inventory.safety_buffer_applied}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">OOS Action:</span>
                        <span className="text-amber-400 font-semibold">{simPreview.inventory.out_of_stock_action}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Target Listing Status:</span>
                        <span className="text-emerald-400 font-semibold">{simPreview.inventory.target_listing_status}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Pricing Calculation Card */}
                <div className="bg-[#0e1526] border border-gray-800/80 rounded-xl p-5 relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs uppercase font-semibold text-gray-400">3. Price Computation</span>
                    <DollarSign className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="space-y-3">
                    <div className="text-xl font-bold text-indigo-400 font-mono">
                      ${Number(simPreview.pricing.calculated_price).toFixed(2)}
                    </div>
                    <div className="space-y-1.5 text-xs text-gray-300">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Matched Rule:</span>
                        <span className="font-semibold text-indigo-300">{simPreview.pricing.rule_type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Base Cost:</span>
                        <span className="font-mono">${Number(simPreview.pricing.supplier_cost).toFixed(2)}</span>
                      </div>
                      {simPreview.pricing.rule_type === "PERCENTAGE_MARKUP" && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Markup Applied:</span>
                          <span className="font-mono text-emerald-400">+{simPreview.pricing.percentage}%</span>
                        </div>
                      )}
                      {simPreview.pricing.rule_type === "FIXED_PROFIT" && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Fixed Profit:</span>
                          <span className="font-mono text-emerald-400">+${simPreview.pricing.fixed_amount.toFixed(2)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL: ADD PRICING RULE */}
      {showPricingModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#131b2e] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <h3 className="text-lg font-bold text-white">Create Pricing Rule</h3>
            <form onSubmit={handleCreatePricingRule} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Target Product (Optional)</label>
                <select
                  value={priceForm.product_id}
                  onChange={(e) => setPriceForm({ ...priceForm, product_id: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Global Default (All Products)</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Rule Type</label>
                <select
                  value={priceForm.rule_type}
                  onChange={(e) => setPriceForm({ ...priceForm, rule_type: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="PERCENTAGE_MARKUP">Percentage Markup (e.g. Cost + 15%)</option>
                  <option value="FIXED_PROFIT">Fixed Profit (e.g. Cost + $25.00)</option>
                  <option value="FEE_MARGIN">Marketplace Fee + Desired Margin</option>
                </select>
              </div>

              {priceForm.rule_type === "PERCENTAGE_MARKUP" && (
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Markup Percentage (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={priceForm.percentage}
                    onChange={(e) => setPriceForm({ ...priceForm, percentage: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                    required
                  />
                </div>
              )}

              {priceForm.rule_type === "FIXED_PROFIT" && (
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Fixed Profit ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={priceForm.fixed_amount}
                    onChange={(e) => setPriceForm({ ...priceForm, fixed_amount: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                    required
                  />
                </div>
              )}

              {priceForm.rule_type === "FEE_MARGIN" && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">Channel Fee (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="99"
                      value={priceForm.marketplace_fee}
                      onChange={(e) => setPriceForm({ ...priceForm, marketplace_fee: e.target.value })}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1">Desired Margin (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={priceForm.desired_margin}
                      onChange={(e) => setPriceForm({ ...priceForm, desired_margin: e.target.value })}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                      required
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Notes / Description</label>
                <input
                  type="text"
                  placeholder="e.g. Standard wholesale pricing rule"
                  value={priceForm.notes}
                  onChange={(e) => setPriceForm({ ...priceForm, notes: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowPricingModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
                >
                  Save Pricing Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD INVENTORY RULE */}
      {showInventoryModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#131b2e] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <h3 className="text-lg font-bold text-white">Create Inventory Rule</h3>
            <form onSubmit={handleCreateInventoryRule} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Target Product (Optional)</label>
                <select
                  value={invForm.product_id}
                  onChange={(e) => setInvForm({ ...invForm, product_id: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Global Default (All Products)</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Safety Buffer Units</label>
                <input
                  type="number"
                  min="0"
                  value={invForm.safety_buffer}
                  onChange={(e) => setInvForm({ ...invForm, safety_buffer: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  required
                />
                <p className="text-[11px] text-gray-400 mt-1">
                  Example: 2 units buffer ensures if supplier has 10 units, exactly 8 are listed on marketplace.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Out-of-Stock Action</label>
                <select
                  value={invForm.out_of_stock_action}
                  onChange={(e) => setInvForm({ ...invForm, out_of_stock_action: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="SET_QUANTITY_ZERO">Set Quantity to 0 (Keep Listing Active)</option>
                  <option value="DISABLE_LISTING">Disable / Pause Listing</option>
                  <option value="MARK_UNAVAILABLE">Mark Unavailable</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowInventoryModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
                >
                  Save Inventory Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: CONFIGURE SUPPLIER PRIORITY */}
      {showPriorityModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#131b2e] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <h3 className="text-lg font-bold text-white">Configure Supplier Priority</h3>
            <form onSubmit={handleCreatePriority} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Select Product</label>
                <select
                  value={priorityForm.product_id}
                  onChange={(e) => setPriorityForm({ ...priorityForm, product_id: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  required
                >
                  <option value="">Select a product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Supplier</label>
                <select
                  value={priorityForm.supplier_id}
                  onChange={(e) => setPriorityForm({ ...priorityForm, supplier_id: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  required
                >
                  <option value="">Select a supplier...</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Priority Rank (1 = Top)</label>
                  <input
                    type="number"
                    min="1"
                    value={priorityForm.priority_rank}
                    onChange={(e) => setPriorityForm({ ...priorityForm, priority_rank: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Selection Strategy</label>
                  <select
                    value={priorityForm.selection_rule}
                    onChange={(e) => setPriorityForm({ ...priorityForm, selection_rule: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="LOWEST_COST">Lowest Cost</option>
                    <option value="HIGHEST_STOCK">Highest Stock</option>
                    <option value="PRIORITY_RANK">Priority Rank</option>
                    <option value="SHIPPING_LOCATION">Fastest Lead Time</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowPriorityModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/30 transition"
                >
                  Save Priority
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
