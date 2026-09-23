"use client";

import React, { useEffect, useState } from "react";
import {
  ShoppingCart,
  RefreshCw,
  Clock,
  Truck,
  DollarSign,
  ChevronDown,
  ChevronUp,
  X,
  CheckCircle2,
  AlertCircle,
  Route,
  FileText,
  Send,
  Ban,
} from "lucide-react";
import { fetchApi, Order, OrderDetail, OrderStats, PurchaseOrder } from "@/lib/api";

const STATUS_TABS = [
  { id: "ALL", name: "All Orders" },
  { id: "PENDING_ROUTING", name: "Pending Routing" },
  { id: "ROUTED", name: "Routed" },
  { id: "PO_SUBMITTED", name: "PO Submitted" },
  { id: "SHIPPED", name: "Shipped" },
  { id: "DELIVERED", name: "Delivered" },
  { id: "CANCELLED", name: "Cancelled" },
];

const STATUS_BADGE: Record<string, string> = {
  PENDING_ROUTING: "bg-amber-50 text-amber-800 border-amber-200",
  ROUTED: "bg-blue-50 text-blue-800 border-blue-200",
  PO_SUBMITTED: "bg-indigo-50 text-indigo-800 border-indigo-200",
  SHIPPED: "bg-teal-50 text-teal-800 border-teal-200",
  DELIVERED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  COMPLETED: "bg-emerald-50 text-emerald-800 border-emerald-200",
  CANCELLED: "bg-rose-50 text-rose-800 border-rose-200",
  REFUNDED: "bg-gray-100 text-gray-600 border-gray-200",
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_BADGE[status] || "bg-gray-100 text-gray-600 border-gray-200";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium border ${cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70"></span>
      <span>{status.replace(/_/g, " ")}</span>
    </span>
  );
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<OrderStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState("ALL");
  const [expandedOrderId, setExpandedOrderId] = useState<number | null>(null);
  const [orderDetails, setOrderDetails] = useState<Record<number, OrderDetail>>({});
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [trackingModalOrder, setTrackingModalOrder] = useState<Order | null>(null);
  const [trackingNumber, setTrackingNumber] = useState("");
  const [carrier, setCarrier] = useState("");
  const [savingTracking, setSavingTracking] = useState(false);
  const [submitPoModal, setSubmitPoModal] = useState<{ po: PurchaseOrder; orderId: number } | null>(null);
  const [supplierOrderId, setSupplierOrderId] = useState("");
  const [savingSubmitPo, setSavingSubmitPo] = useState(false);

  const showFeedback = (type: "success" | "error", message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  const loadOrders = async () => {
    try {
      const query = selectedStatus !== "ALL" ? `?status=${selectedStatus}&page_size=100` : "?page_size=100";
      const res = await fetchApi<{ orders: Order[]; total: number }>(`/orders${query}`);
      setOrders(res.orders);
    } catch (err) {
      console.error("Failed to load orders:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetchApi<OrderStats>("/orders/stats");
      setStats(res);
    } catch (err) {
      console.error("Failed to load order stats:", err);
    }
  };

  useEffect(() => {
    loadOrders();
  }, [selectedStatus]);

  useEffect(() => {
    loadStats();
  }, []);

  const handleSyncOrders = async () => {
    setSyncing(true);
    try {
      const res = await fetchApi<{ total_new_orders: number }>("/orders/sync", { method: "POST" });
      showFeedback("success", `Sync complete: ${res.total_new_orders} new order(s) ingested.`);
      await Promise.all([loadOrders(), loadStats()]);
    } catch (err: any) {
      showFeedback("error", "Order sync failed: " + err.message);
    } finally {
      setSyncing(false);
    }
  };

  const toggleExpand = async (orderId: number) => {
    if (expandedOrderId === orderId) {
      setExpandedOrderId(null);
      return;
    }
    setExpandedOrderId(orderId);
    if (!orderDetails[orderId]) {
      try {
        const detail = await fetchApi<OrderDetail>(`/orders/${orderId}`);
        setOrderDetails((prev) => ({ ...prev, [orderId]: detail }));
      } catch (err) {
        console.error("Failed to load order detail:", err);
      }
    }
  };

  const refreshDetail = async (orderId: number) => {
    try {
      const detail = await fetchApi<OrderDetail>(`/orders/${orderId}`);
      setOrderDetails((prev) => ({ ...prev, [orderId]: detail }));
    } catch (err) {
      console.error("Failed to refresh order detail:", err);
    }
  };

  const runAction = async (key: string, orderId: number, fn: () => Promise<any>, successMsg: string) => {
    setActionLoading((prev) => ({ ...prev, [key]: true }));
    try {
      await fn();
      showFeedback("success", successMsg);
      await Promise.all([loadOrders(), loadStats(), refreshDetail(orderId)]);
    } catch (err: any) {
      showFeedback("error", err.message || "Action failed");
    } finally {
      setActionLoading((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleRoute = (orderId: number) =>
    runAction(`route-${orderId}`, orderId, () => fetchApi(`/orders/${orderId}/route`, { method: "POST" }), `Order #${orderId} routed to suppliers.`);

  const handleCreatePO = (orderId: number) =>
    runAction(`po-${orderId}`, orderId, () => fetchApi(`/orders/${orderId}/create-po`, { method: "POST" }), `Purchase order(s) created for Order #${orderId}.`);

  const handleCancel = (orderId: number) =>
    runAction(`cancel-${orderId}`, orderId, () => fetchApi(`/orders/${orderId}/cancel`, { method: "PUT" }), `Order #${orderId} cancelled.`);

  const openTrackingModal = (order: Order) => {
    setTrackingModalOrder(order);
    setTrackingNumber("");
    setCarrier("");
  };

  const handleSaveTracking = async () => {
    if (!trackingModalOrder || !trackingNumber.trim()) return;
    setSavingTracking(true);
    try {
      await fetchApi(`/orders/${trackingModalOrder.id}/tracking`, {
        method: "PUT",
        body: JSON.stringify({ tracking_number: trackingNumber, carrier: carrier || undefined }),
      });
      showFeedback("success", `Tracking added and pushed to ${trackingModalOrder.marketplace_name || "marketplace"}.`);
      setTrackingModalOrder(null);
      await Promise.all([loadOrders(), loadStats(), refreshDetail(trackingModalOrder.id)]);
    } catch (err: any) {
      showFeedback("error", "Failed to save tracking: " + err.message);
    } finally {
      setSavingTracking(false);
    }
  };

  const openSubmitPoModal = (po: PurchaseOrder, orderId: number) => {
    setSubmitPoModal({ po, orderId });
    setSupplierOrderId("");
  };

  const handleSubmitPo = async () => {
    if (!submitPoModal || !supplierOrderId.trim()) return;
    setSavingSubmitPo(true);
    try {
      await fetchApi(`/orders/purchase-orders/${submitPoModal.po.id}/submit`, {
        method: "PUT",
        body: JSON.stringify({ supplier_order_id: supplierOrderId }),
      });
      showFeedback("success", `PO ${submitPoModal.po.po_number} marked as submitted to ${submitPoModal.po.supplier_name || "supplier"}.`);
      const orderId = submitPoModal.orderId;
      setSubmitPoModal(null);
      await Promise.all([loadOrders(), refreshDetail(orderId)]);
    } catch (err: any) {
      showFeedback("error", "Failed to record PO submission: " + err.message);
    } finally {
      setSavingSubmitPo(false);
    }
  };

  const kpis = [
    { title: "Today's Orders", value: stats?.orders_today ?? 0, icon: ShoppingCart, iconColor: "text-[#6C5DD3]" },
    { title: "Pending Routing", value: stats?.pending_routing ?? 0, icon: Clock, iconColor: "text-amber-700" },
    { title: "Awaiting Shipment", value: stats?.awaiting_shipment ?? 0, icon: Truck, iconColor: "text-blue-700" },
    {
      title: "30-Day Revenue",
      value: `$${Number(stats?.revenue_30d ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      icon: DollarSign,
      iconColor: "text-emerald-700",
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Orders</h1>
          <p className="text-sm text-gray-500 mt-1">
            Track customer orders end-to-end: routing to suppliers, purchase orders, and shipment tracking.
          </p>
        </div>

        <button
          onClick={handleSyncOrders}
          disabled={syncing}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin text-[#6C5DD3]" : "text-[#6C5DD3]"}`} />
          <span>{syncing ? "Syncing Orders..." : "Sync Orders Now"}</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-3.5 rounded-lg border flex items-center gap-2 text-xs font-semibold ${
            feedback.type === "success"
              ? "bg-emerald-50 border-emerald-300 text-emerald-900"
              : "bg-rose-50 border-rose-300 text-rose-900"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <div key={index} className="bg-white border border-gray-100 rounded-2xl shadow-sm p-4 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-gray-500">{kpi.title}</span>
                <div className="text-2xl font-bold text-gray-900 tracking-tight mt-1">{kpi.value}</div>
              </div>
              <div className={`p-2 rounded-md bg-gray-50 ${kpi.iconColor}`}>
                <Icon className="h-5 w-5" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Status Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {STATUS_TABS.map((tab) => {
          const isActive = selectedStatus === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setSelectedStatus(tab.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap shadow-sm ${
                isActive
                  ? "bg-gray-900 text-white"
                  : "bg-white text-gray-500 hover:text-gray-900 border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {tab.name}
            </button>
          );
        })}
      </div>

      {/* Orders Table */}
      <div className="bg-white rounded-2xl overflow-hidden border border-gray-100 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-900">
            <thead className="bg-gray-50/80 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
              <tr>
                <th className="px-6 py-3.5">Order</th>
                <th className="px-4 py-3.5">Marketplace</th>
                <th className="px-4 py-3.5">Buyer</th>
                <th className="px-4 py-3.5">Total</th>
                <th className="px-4 py-3.5">Items</th>
                <th className="px-4 py-3.5">Status</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-20 text-gray-500">
                    Loading orders...
                  </td>
                </tr>
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-20 text-gray-500">
                    <ShoppingCart className="h-8 w-8 mx-auto text-gray-400 mb-2 opacity-50" />
                    <div className="font-semibold text-gray-900">No orders found.</div>
                    <p className="text-xs text-gray-500 mt-1">Click &apos;Sync Orders Now&apos; to pull the latest orders from your marketplaces.</p>
                  </td>
                </tr>
              ) : (
                orders.map((order) => {
                  const isExpanded = expandedOrderId === order.id;
                  const detail = orderDetails[order.id];
                  const canRoute = order.status === "PENDING_ROUTING" || order.status === "ROUTED";
                  const canCreatePO = order.status === "ROUTED";
                  const canTrack = ["PO_SUBMITTED", "SHIPPED"].includes(order.status);
                  const canCancel = !["DELIVERED", "COMPLETED", "CANCELLED"].includes(order.status);

                  return (
                    <React.Fragment key={order.id}>
                      <tr className="hover:bg-gray-50/60 transition-colors cursor-pointer" onClick={() => toggleExpand(order.id)}>
                        <td className="px-6 py-3.5">
                          <div className="font-semibold text-gray-900">#{order.id}</div>
                          <div className="text-[11px] text-gray-500 font-mono">{order.marketplace_order_id}</div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="text-xs font-medium px-2.5 py-0.5 rounded-md bg-gray-100 border border-gray-200 text-gray-900">
                            {order.marketplace_name || "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="text-xs font-medium text-gray-900">{order.buyer_name || "—"}</div>
                          <div className="text-[11px] text-gray-500">{order.buyer_username || ""}</div>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="font-bold text-gray-900 text-sm">${Number(order.order_total).toFixed(2)}</div>
                        </td>
                        <td className="px-4 py-3.5 text-xs text-gray-600">{order.items_count} item(s)</td>
                        <td className="px-4 py-3.5">
                          <StatusBadge status={order.status} />
                        </td>
                        <td className="px-6 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5 flex-wrap">
                            {canRoute && (
                              <button
                                onClick={() => handleRoute(order.id)}
                                disabled={actionLoading[`route-${order.id}`]}
                                className="px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-xs font-medium text-gray-700 transition-colors inline-flex items-center gap-1 shadow-sm disabled:opacity-50"
                                title="Route order items to best suppliers"
                              >
                                <Route className="h-3.5 w-3.5 text-blue-600" />
                                <span>{actionLoading[`route-${order.id}`] ? "Routing..." : "Route"}</span>
                              </button>
                            )}
                            {canCreatePO && (
                              <button
                                onClick={() => handleCreatePO(order.id)}
                                disabled={actionLoading[`po-${order.id}`]}
                                className="px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-xs font-medium text-gray-700 transition-colors inline-flex items-center gap-1 shadow-sm disabled:opacity-50"
                                title="Generate purchase order(s) for routed suppliers"
                              >
                                <FileText className="h-3.5 w-3.5 text-indigo-600" />
                                <span>{actionLoading[`po-${order.id}`] ? "Creating..." : "Generate PO"}</span>
                              </button>
                            )}
                            {canTrack && (
                              <button
                                onClick={() => openTrackingModal(order)}
                                className="px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-xs font-medium text-gray-700 transition-colors inline-flex items-center gap-1 shadow-sm"
                                title="Add tracking and push to marketplace"
                              >
                                <Send className="h-3.5 w-3.5 text-teal-600" />
                                <span>Add Tracking</span>
                              </button>
                            )}
                            {canCancel && (
                              <button
                                onClick={() => handleCancel(order.id)}
                                disabled={actionLoading[`cancel-${order.id}`]}
                                className="px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-rose-50 hover:border-rose-300 hover:text-rose-600 text-gray-400 text-xs transition-colors inline-flex items-center gap-1 shadow-sm font-medium disabled:opacity-50"
                              >
                                <Ban className="h-3.5 w-3.5" />
                                <span>{actionLoading[`cancel-${order.id}`] ? "Cancelling..." : "Cancel"}</span>
                              </button>
                            )}
                            <button
                              onClick={() => toggleExpand(order.id)}
                              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-900 hover:bg-gray-100"
                            >
                              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </button>
                          </div>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr>
                          <td colSpan={7} className="px-6 py-4 bg-gray-50/60 border-t border-gray-100">
                            {!detail ? (
                              <div className="text-xs text-gray-500 py-4 text-center">Loading order details...</div>
                            ) : (
                              <div className="space-y-4">
                                {/* Line Items */}
                                <div>
                                  <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Line Items</h4>
                                  <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                    <table className="w-full text-xs">
                                      <thead className="bg-gray-50 text-gray-500 font-semibold">
                                        <tr>
                                          <th className="px-4 py-2 text-left">Item</th>
                                          <th className="px-4 py-2 text-left">SKU</th>
                                          <th className="px-4 py-2 text-right">Qty</th>
                                          <th className="px-4 py-2 text-right">Unit Price</th>
                                          <th className="px-4 py-2 text-right">Supplier Cost</th>
                                          <th className="px-4 py-2 text-right">Est. Profit</th>
                                          <th className="px-4 py-2 text-left">Supplier</th>
                                          <th className="px-4 py-2 text-left">Status</th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-gray-100">
                                        {detail.items.map((item) => {
                                          const cost = item.supplier_cost ? Number(item.supplier_cost) * item.quantity : null;
                                          const revenue = Number(item.unit_price) * item.quantity;
                                          const profit = cost !== null ? revenue - cost : null;
                                          return (
                                            <tr key={item.id}>
                                              <td className="px-4 py-2 font-medium text-gray-900 max-w-xs truncate">{item.title || "Unknown Item"}</td>
                                              <td className="px-4 py-2 font-mono text-[#6C5DD3]">{item.sku || "—"}</td>
                                              <td className="px-4 py-2 text-right">{item.quantity}</td>
                                              <td className="px-4 py-2 text-right">${Number(item.unit_price).toFixed(2)}</td>
                                              <td className="px-4 py-2 text-right">{cost !== null ? `$${cost.toFixed(2)}` : "—"}</td>
                                              <td className={`px-4 py-2 text-right font-semibold ${profit !== null && profit >= 0 ? "text-emerald-700" : "text-rose-600"}`}>
                                                {profit !== null ? `$${profit.toFixed(2)}` : "—"}
                                              </td>
                                              <td className="px-4 py-2">{item.supplier_name || "—"}</td>
                                              <td className="px-4 py-2">
                                                <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 text-[10px] font-medium">{item.status}</span>
                                              </td>
                                            </tr>
                                          );
                                        })}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>

                                {/* Purchase Orders */}
                                {detail.purchase_orders.length > 0 && (
                                  <div>
                                    <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Purchase Orders</h4>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                                      {detail.purchase_orders.map((po) => (
                                        <div key={po.id} className="bg-white rounded-lg border border-gray-200 p-3 text-xs">
                                          <div className="flex items-center justify-between mb-1">
                                            <span className="font-mono font-semibold text-gray-900">{po.po_number}</span>
                                            <StatusBadge status={po.status} />
                                          </div>
                                          <div className="text-gray-500">Supplier: {po.supplier_name || "—"}</div>
                                          <div className="text-gray-500">Total: ${Number(po.total_cost).toFixed(2)}</div>
                                          {po.supplier_order_id && (
                                            <div className="text-gray-500">
                                              Supplier Order #: <span className="font-mono">{po.supplier_order_id}</span>
                                            </div>
                                          )}
                                          {po.tracking_number && (
                                            <div className="text-gray-500">
                                              Tracking: <span className="font-mono">{po.tracking_number}</span> ({po.carrier || "—"})
                                            </div>
                                          )}
                                          {po.status === "DRAFT" && (
                                            <button
                                              onClick={() => openSubmitPoModal(po, order.id)}
                                              className="mt-2 w-full px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-[11px] font-medium text-gray-700 transition-colors inline-flex items-center justify-center gap-1"
                                              title="Record that this PO was placed with the real supplier"
                                            >
                                              <Send className="h-3 w-3 text-indigo-600" />
                                              <span>Mark as Submitted to Supplier</span>
                                            </button>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* Event Timeline */}
                                {detail.events.length > 0 && (
                                  <div>
                                    <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Audit Trail</h4>
                                    <div className="space-y-1.5">
                                      {detail.events.map((ev) => (
                                        <div key={ev.id} className="flex items-center gap-2 text-[11px] text-gray-600">
                                          <span className="h-1.5 w-1.5 rounded-full bg-gray-400 shrink-0"></span>
                                          <span className="font-semibold text-gray-800">{ev.event_type.replace(/_/g, " ")}</span>
                                          <span suppressHydrationWarning>{ev.created_at ? new Date(ev.created_at).toLocaleString() : ""}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Tracking Modal */}
      {trackingModalOrder && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Add Tracking</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Order #{trackingModalOrder.id} — {trackingModalOrder.marketplace_name}
                </p>
              </div>
              <button
                onClick={() => setTrackingModalOrder(null)}
                className="p-1.5 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-800 mb-1">Tracking Number</label>
                <input
                  type="text"
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  placeholder="e.g. 1Z999AA10123456784"
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 font-medium focus:outline-none focus:border-gray-900"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-800 mb-1">Carrier (optional)</label>
                <input
                  type="text"
                  value={carrier}
                  onChange={(e) => setCarrier(e.target.value)}
                  placeholder="e.g. UPS, FedEx, USPS"
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 font-medium focus:outline-none focus:border-gray-900"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2.5">
              <button
                onClick={() => setTrackingModalOrder(null)}
                className="px-4 py-2 text-xs font-medium text-gray-500 hover:text-gray-900"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTracking}
                disabled={savingTracking || !trackingNumber.trim()}
                className="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-medium transition-all shadow-sm disabled:opacity-50"
              >
                {savingTracking ? "Saving..." : "Save & Push to Marketplace"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submit PO to Supplier Modal */}
      {submitPoModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Mark PO as Submitted</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {submitPoModal.po.po_number} — {submitPoModal.po.supplier_name}
                </p>
              </div>
              <button
                onClick={() => setSubmitPoModal(null)}
                className="p-1.5 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-900">
              This does not place the order automatically. Place it yourself with the supplier first, then record their confirmation number here.
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-800 mb-1">Supplier Order Confirmation #</label>
              <input
                type="text"
                value={supplierOrderId}
                onChange={(e) => setSupplierOrderId(e.target.value)}
                placeholder="e.g. the order number the supplier gave you"
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 font-medium focus:outline-none focus:border-gray-900"
              />
            </div>

            <div className="pt-2 flex items-center justify-end gap-2.5">
              <button
                onClick={() => setSubmitPoModal(null)}
                className="px-4 py-2 text-xs font-medium text-gray-500 hover:text-gray-900"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitPo}
                disabled={savingSubmitPo || !supplierOrderId.trim()}
                className="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-medium transition-all shadow-sm disabled:opacity-50"
              >
                {savingSubmitPo ? "Saving..." : "Confirm Submission"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
