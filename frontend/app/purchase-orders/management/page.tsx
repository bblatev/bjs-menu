"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";


import { toast } from '@/lib/toast';

import { api } from '@/lib/api';
// Types
interface PurchaseOrder {
  id: string;
  po_number: string;
  supplier_id: string;
  supplier_name: string;
  venue_id: string;
  warehouse_id: string;
  warehouse_name: string;
  status: "draft" | "pending_approval" | "approved" | "sent" | "partial" | "received" | "cancelled";
  order_date: string;
  expected_date: string;
  total_amount: number;
  currency: string;
  items: POItem[];
  created_by: string;
  approved_by?: string;
  approved_at?: string;
  notes?: string;
  created_at: string;
}

interface POItem {
  id: string;
  ingredient_id: string;
  ingredient_name: string;
  quantity_ordered: number;
  quantity_received: number;
  unit: string;
  unit_price: number;
  total_price: number;
  notes?: string;
}

interface GoodsReceivedNote {
  id: string;
  grn_number: string;
  purchase_order_id: string;
  po_number: string;
  supplier_id: string;
  supplier_name: string;
  warehouse_id: string;
  received_date: string;
  received_by: string;
  status: "pending" | "inspected" | "accepted" | "partial" | "rejected";
  items: GRNItem[];
  notes?: string;
  temperature_check?: number;
  quality_score?: number;
  created_at: string;
}

interface GRNItem {
  id: string;
  po_item_id: string;
  ingredient_name: string;
  quantity_ordered: number;
  quantity_received: number;
  quantity_accepted: number;
  quantity_rejected: number;
  rejection_reason?: string;
  batch_number?: string;
  expiry_date?: string;
  unit: string;
}

interface Invoice {
  id: string;
  invoice_number: string;
  supplier_invoice_number: string;
  purchase_order_id: string;
  po_number: string;
  grn_id?: string;
  grn_number?: string;
  supplier_id: string;
  supplier_name: string;
  invoice_date: string;
  due_date: string;
  status: "pending" | "matched" | "variance" | "approved" | "paid" | "disputed";
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  amount_paid: number;
  currency: string;
  matching_status: "pending" | "matched" | "variance";
  variance_amount?: number;
  items: InvoiceItem[];
  created_at: string;
}

interface InvoiceItem {
  id: string;
  ingredient_name: string;
  quantity_invoiced: number;
  quantity_received: number;
  unit_price_invoiced: number;
  unit_price_ordered: number;
  total_price: number;
  variance_amount: number;
  unit: string;
}

interface ApprovalRequest {
  id: string;
  type: "purchase_order" | "invoice" | "variance";
  reference_id: string;
  reference_number: string;
  supplier_name: string;
  amount: number;
  requested_by: string;
  requested_at: string;
  status: "pending" | "approved" | "rejected";
  urgency: "low" | "medium" | "high";
  notes?: string;
}

interface ThreeWayMatch {
  po_id: string;
  po_number: string;
  grn_id?: string;
  grn_number?: string;
  invoice_id?: string;
  invoice_number?: string;
  supplier_name: string;
  po_total: number;
  grn_total?: number;
  invoice_total?: number;
  status: "pending" | "partial" | "matched" | "variance";
  quantity_variance: number;
  price_variance: number;
  items: MatchItem[];
}

interface MatchItem {
  ingredient_name: string;
  po_qty: number;
  grn_qty: number;
  invoice_qty: number;
  po_price: number;
  invoice_price: number;
  qty_variance: number;
  price_variance: number;
}



// Status colors
const poStatusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  pending_approval: "bg-yellow-100 text-yellow-800",
  approved: "bg-blue-100 text-blue-800",
  sent: "bg-purple-100 text-purple-800",
  partial: "bg-orange-100 text-orange-800",
  received: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const grnStatusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  inspected: "bg-blue-100 text-blue-800",
  accepted: "bg-green-100 text-green-800",
  partial: "bg-orange-100 text-orange-800",
  rejected: "bg-red-100 text-red-800",
};

const invoiceStatusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  matched: "bg-green-100 text-green-800",
  variance: "bg-orange-100 text-orange-800",
  approved: "bg-blue-100 text-blue-800",
  paid: "bg-green-100 text-green-800",
  disputed: "bg-red-100 text-red-800",
};

const matchStatusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-800",
  partial: "bg-yellow-100 text-yellow-800",
  matched: "bg-green-100 text-green-800",
  variance: "bg-red-100 text-red-800",
};

export default function PurchaseOrdersManagementPage() {
  const [activeTab, setActiveTab] = useState("orders");
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [grns, setGRNs] = useState<GoodsReceivedNote[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [matches, setMatches] = useState<ThreeWayMatch[]>([]);
  const [selectedPO, setSelectedPO] = useState<PurchaseOrder | null>(null);
  const [selectedGRN, setSelectedGRN] = useState<GoodsReceivedNote | null>(null);
  const [, setSelectedInvoice] = useState<Invoice | null>(null);
  const [, setSelectedMatch] = useState<ThreeWayMatch | null>(null);
  const [showCreatePO, setShowCreatePO] = useState(false);
  const [, setShowCreateGRN] = useState(false);
  const [poStatusFilter, setPOStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");

  // Loading and error states
  const [loading, setLoading] = useState({
    purchaseOrders: true,
    grns: true,
    invoices: true,
    approvals: true,
    matches: true,
  });
  const [error, setError] = useState({
    purchaseOrders: "",
    grns: "",
    invoices: "",
    approvals: "",
    matches: "",
  });

  // Fetch Purchase Orders
  const fetchPurchaseOrders = async () => {
    try {
      setLoading(prev => ({ ...prev, purchaseOrders: true }));
      setError(prev => ({ ...prev, purchaseOrders: "" }));
      const data: any = await api.get('/purchase-orders/');
      setPurchaseOrders(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching purchase orders:', err);
      setError(prev => ({ ...prev, purchaseOrders: err instanceof Error ? err.message : 'Failed to load purchase orders' }));
    } finally {
      setLoading(prev => ({ ...prev, purchaseOrders: false }));
    }
  };

  // Fetch Goods Received Notes
  const fetchGRNs = async () => {
    try {
      setLoading(prev => ({ ...prev, grns: true }));
      setError(prev => ({ ...prev, grns: "" }));
      const data: any = await api.get('/purchase-orders/grns/');
      setGRNs(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching GRNs:', err);
      setError(prev => ({ ...prev, grns: err instanceof Error ? err.message : 'Failed to load goods received notes' }));
    } finally {
      setLoading(prev => ({ ...prev, grns: false }));
    }
  };

  // Fetch Invoices
  const fetchInvoices = async () => {
    try {
      setLoading(prev => ({ ...prev, invoices: true }));
      setError(prev => ({ ...prev, invoices: "" }));
      const data: any = await api.get('/purchase-orders/invoices/');
      setInvoices(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching invoices:', err);
      setError(prev => ({ ...prev, invoices: err instanceof Error ? err.message : 'Failed to load invoices' }));
    } finally {
      setLoading(prev => ({ ...prev, invoices: false }));
    }
  };

  // Fetch Approvals
  const fetchApprovals = async () => {
    try {
      setLoading(prev => ({ ...prev, approvals: true }));
      setError(prev => ({ ...prev, approvals: "" }));
      const data: any = await api.get('/purchase-orders/approvals/');
      setApprovals(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching approvals:', err);
      setError(prev => ({ ...prev, approvals: err instanceof Error ? err.message : 'Failed to load approvals' }));
    } finally {
      setLoading(prev => ({ ...prev, approvals: false }));
    }
  };

  // Fetch Three-Way Matches
  const fetchMatches = async () => {
    try {
      setLoading(prev => ({ ...prev, matches: true }));
      setError(prev => ({ ...prev, matches: "" }));
      const data: any = await api.get('/purchase-orders/three-way-matches/');
      setMatches(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Error fetching matches:', err);
      setError(prev => ({ ...prev, matches: err instanceof Error ? err.message : 'Failed to load three-way matches' }));
    } finally {
      setLoading(prev => ({ ...prev, matches: false }));
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchPurchaseOrders();
    fetchGRNs();
    fetchInvoices();
    fetchApprovals();
    fetchMatches();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Loading component
  const LoadingSpinner = () => (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-600"></div>
    </div>
  );

  // Error component
  const ErrorMessage = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="text-red-500 mb-4">
        <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p className="text-gray-600 mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        Try Again
      </button>
    </div>
  );

  // Check if all data is loading
  const isInitialLoading = loading.purchaseOrders && loading.grns && loading.invoices && loading.approvals && loading.matches;

  const tabs = [
    { id: "orders", label: "Purchase Orders", icon: "📋", count: purchaseOrders.length },
    { id: "approvals", label: "Approvals", icon: "✅", count: approvals.filter(a => a.status === "pending").length },
    { id: "receiving", label: "Goods Receiving", icon: "📦", count: grns.length },
    { id: "invoices", label: "Invoices", icon: "🧾", count: invoices.length },
    { id: "matching", label: "Three-Way Match", icon: "🔗", count: matches.filter(m => m.status === "variance").length },
    { id: "analytics", label: "Analytics", icon: "📊" },
  ];

  const filteredPOs = purchaseOrders.filter(po => {
    const matchesStatus = poStatusFilter === "all" || po.status === poStatusFilter;
    const matchesSearch = po.po_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      po.supplier_name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const handleApprovePO = async (poId: string) => {
    try {
      await api.post(`/purchase-orders/${poId}/approve`);
      // Refresh data after successful approval
      await Promise.all([fetchPurchaseOrders(), fetchApprovals()]);
    } catch (err) {
      console.error('Error approving purchase order:', err);
      toast.error('Failed to approve purchase order. Please try again.');
    }
  };

  const handleRejectPO = async (poId: string) => {
    try {
      await api.post(`/purchase-orders/${poId}/reject`);
      // Refresh data after successful rejection
      await Promise.all([fetchPurchaseOrders(), fetchApprovals()]);
    } catch (err) {
      console.error('Error rejecting purchase order:', err);
      toast.error('Failed to reject purchase order. Please try again.');
    }
  };

  const handleApproveVariance = async (approvalId: string) => {
    try {
      await api.post(`/purchase-orders/approvals/${approvalId}/approve`);
      // Refresh approvals after successful approval
      await fetchApprovals();
    } catch (err) {
      console.error('Error approving variance:', err);
      toast.error('Failed to approve variance. Please try again.');
    }
  };

  // Show full page loading spinner on initial load
  if (isInitialLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading purchase orders data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Purchase Orders Management</h1>
          <p className="text-gray-600 mt-2">
            Manage purchase orders, approvals, goods receiving, invoices, and three-way matching
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl p-4 shadow-sm border"
          >
            <div className="text-2xl font-bold text-blue-600">{purchaseOrders.filter(p => p.status === "pending_approval").length}</div>
            <div className="text-sm text-gray-600">Pending Approval</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-xl p-4 shadow-sm border"
          >
            <div className="text-2xl font-bold text-orange-600">{purchaseOrders.filter(p => p.status === "partial").length}</div>
            <div className="text-sm text-gray-600">Partial Received</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-xl p-4 shadow-sm border"
          >
            <div className="text-2xl font-bold text-yellow-600">{invoices.filter(i => i.status === "pending").length}</div>
            <div className="text-sm text-gray-600">Unpaid Invoices</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-xl p-4 shadow-sm border"
          >
            <div className="text-2xl font-bold text-red-600">{matches.filter(m => m.status === "variance").length}</div>
            <div className="text-sm text-gray-600">Variances</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-white rounded-xl p-4 shadow-sm border"
          >
            <div className="text-2xl font-bold text-green-600">
              {((purchaseOrders.reduce((sum, po) => sum + po.total_amount, 0) / 1000) || 0).toFixed(1)}K
            </div>
            <div className="text-sm text-gray-600">Total Orders (BGN)</div>
          </motion.div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border mb-6">
          <div className="flex overflow-x-auto border-b">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.count !== undefined && tab.count > 0 && (
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    activeTab === tab.id ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="p-6">
            <AnimatePresence mode="wait">
              {/* Purchase Orders Tab */}
              {activeTab === "orders" && (
                <motion.div
                  key="orders"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  {loading.purchaseOrders ? (
                    <LoadingSpinner />
                  ) : error.purchaseOrders ? (
                    <ErrorMessage message={error.purchaseOrders} onRetry={fetchPurchaseOrders} />
                  ) : (
                    <>
                      {/* Filters */}
                      <div className="flex flex-wrap gap-4 mb-6">
                        <div className="flex-1 min-w-[200px]">
                          <input
                            type="text"
                            placeholder="Search PO number or supplier..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <select
                          value={poStatusFilter}
                          onChange={(e) => setPOStatusFilter(e.target.value)}
                          className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="all">All Status</option>
                          <option value="draft">Draft</option>
                          <option value="pending_approval">Pending Approval</option>
                          <option value="approved">Approved</option>
                          <option value="sent">Sent</option>
                          <option value="partial">Partial</option>
                          <option value="received">Received</option>
                          <option value="cancelled">Cancelled</option>
                        </select>
                        <button
                          onClick={() => setShowCreatePO(true)}
                          className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2"
                        >
                          <span>+</span>
                          <span>Create PO</span>
                        </button>
                      </div>

                      {/* PO List */}
                      <div className="space-y-4">
                        {filteredPOs.length === 0 ? (
                          <div className="text-center py-12 text-gray-500">
                            <div className="text-4xl mb-4">📋</div>
                            <p>No purchase orders found</p>
                          </div>
                        ) : (
                          filteredPOs.map((po) => (
                            <motion.div
                              key={po.id}
                              layout
                              className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                              onClick={() => setSelectedPO(po)}
                            >
                              <div className="flex justify-between items-start mb-3">
                                <div>
                                  <div className="flex items-center gap-3">
                                    <span className="font-bold text-lg">{po.po_number}</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${poStatusColors[po.status]}`}>
                                      {(po.status || '').replace("_", " ").toUpperCase()}
                                    </span>
                                  </div>
                                  <div className="text-gray-600">{po.supplier_name}</div>
                                </div>
                                <div className="text-right">
                                  <div className="font-bold text-lg">{(po.total_amount || 0).toFixed(2)} {po.currency}</div>
                                  <div className="text-sm text-gray-500">Expected: {po.expected_date}</div>
                                </div>
                              </div>
                              <div className="flex justify-between items-center text-sm text-gray-500">
                                <div className="flex items-center gap-4">
                                  <span>📦 {po.warehouse_name}</span>
                                  <span>📝 {(po.items || []).length} items</span>
                                </div>
                                <div>
                                  {po.approved_by && (
                                    <span className="text-green-600">✓ Approved by {po.approved_by}</span>
                                  )}
                                </div>
                              </div>
                              {/* Progress bar for partial orders */}
                              {po.status === "partial" && (
                                <div className="mt-3">
                                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                                    <span>Receiving Progress</span>
                                    <span>
                                      {Math.round(
                                        ((po.items || []).reduce((sum, i) => sum + i.quantity_received, 0) /
                                          ((po.items || []).reduce((sum, i) => sum + i.quantity_ordered, 0) || 1)) * 100
                                      )}%
                                    </span>
                                  </div>
                                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-orange-500 rounded-full"
                                      style={{
                                        width: `${((po.items || []).reduce((sum, i) => sum + i.quantity_received, 0) /
                                          ((po.items || []).reduce((sum, i) => sum + i.quantity_ordered, 0) || 1)) * 100}%`,
                                      }}
                                    />
                                  </div>
                                </div>
                              )}
                            </motion.div>
                          ))
                        )}
                      </div>
                    </>
                  )}
                </motion.div>
              )}

              {/* Approvals Tab */}
              {activeTab === "approvals" && (
                <motion.div
                  key="approvals"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  {loading.approvals ? (
                    <LoadingSpinner />
                  ) : error.approvals ? (
                    <ErrorMessage message={error.approvals} onRetry={fetchApprovals} />
                  ) : (
                    <>
                      <h3 className="text-lg font-semibold mb-4">Pending Approvals</h3>
                      <div className="space-y-4">
                        {approvals.filter(a => a.status === "pending").map((approval) => (
                          <div
                            key={approval.id}
                            className={`border rounded-lg p-4 ${
                              approval.urgency === "high" ? "border-red-300 bg-red-50" :
                              approval.urgency === "medium" ? "border-yellow-300 bg-yellow-50" :
                              "border-gray-200"
                            }`}
                          >
                            <div className="flex justify-between items-start mb-3">
                              <div>
                                <div className="flex items-center gap-3">
                                  <span className="font-bold">{approval.reference_number}</span>
                                  <span className={`px-2 py-1 rounded text-xs ${
                                    approval.type === "purchase_order" ? "bg-blue-100 text-blue-800" :
                                    approval.type === "variance" ? "bg-orange-100 text-orange-800" :
                                    "bg-gray-100 text-gray-800"
                                  }`}>
                                    {approval.type.replace("_", " ").toUpperCase()}
                                  </span>
                                  {approval.urgency === "high" && (
                                    <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-800">URGENT</span>
                                  )}
                                </div>
                                <div className="text-gray-600">{approval.supplier_name}</div>
                                <div className="text-sm text-gray-500 mt-1">
                                  Requested by {approval.requested_by} on {new Date(approval.requested_at).toLocaleDateString()}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold text-lg">{(approval.amount || 0).toFixed(2)} BGN</div>
                              </div>
                            </div>
                            {approval.notes && (
                              <div className="text-sm text-gray-600 mb-3 p-2 bg-white rounded">
                                {approval.notes}
                              </div>
                            )}
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => approval.type === "purchase_order" ? handleRejectPO(approval.reference_id) : null}
                                className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                              >
                                Reject
                              </button>
                              <button
                                onClick={() => approval.type === "purchase_order" ? handleApprovePO(approval.reference_id) : handleApproveVariance(approval.id)}
                                className="px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700"
                              >
                                Approve
                              </button>
                            </div>
                          </div>
                        ))}
                        {approvals.filter(a => a.status === "pending").length === 0 && (
                          <div className="text-center py-8 text-gray-500">
                            No pending approvals
                          </div>
                        )}
                      </div>

                      {/* Recent Decisions */}
                      <h3 className="text-lg font-semibold mt-8 mb-4">Recent Decisions</h3>
                      <div className="space-y-2">
                        {approvals.filter(a => a.status !== "pending").map((approval) => (
                          <div key={approval.id} className="flex items-center justify-between p-3 border rounded-lg">
                            <div>
                              <span className="font-medium">{approval.reference_number}</span>
                              <span className="text-gray-500 ml-2">{approval.supplier_name}</span>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs ${
                              approval.status === "approved" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                            }`}>
                              {approval.status.toUpperCase()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </motion.div>
              )}

              {/* Goods Receiving Tab */}
              {activeTab === "receiving" && (
                <motion.div
                  key="receiving"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  {loading.grns ? (
                    <LoadingSpinner />
                  ) : error.grns ? (
                    <ErrorMessage message={error.grns} onRetry={fetchGRNs} />
                  ) : (
                    <>
                      <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-semibold">Goods Received Notes</h3>
                        <button
                          onClick={() => setShowCreateGRN(true)}
                          className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2"
                        >
                          <span>+</span>
                          <span>Create GRN</span>
                        </button>
                      </div>

                      {/* Pending Deliveries */}
                      <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <h4 className="font-medium text-yellow-800 mb-2">Expected Deliveries Today</h4>
                        {purchaseOrders
                          .filter(po => po.status === "approved" || po.status === "sent")
                          .filter(po => new Date(po.expected_date).toDateString() === new Date().toDateString())
                          .map(po => (
                            <div key={po.id} className="flex justify-between items-center py-2 border-b border-yellow-200 last:border-0">
                              <div>
                                <span className="font-medium">{po.po_number}</span>
                                <span className="text-gray-600 ml-2">from {po.supplier_name}</span>
                              </div>
                              <button className="px-3 py-1 bg-yellow-600 text-gray-900 text-sm rounded hover:bg-yellow-700">
                                Receive Now
                              </button>
                            </div>
                          ))}
                        {purchaseOrders
                          .filter(po => po.status === "approved" || po.status === "sent")
                          .filter(po => new Date(po.expected_date).toDateString() === new Date().toDateString()).length === 0 && (
                            <div className="text-yellow-700">No deliveries expected today</div>
                          )}
                      </div>

                      {/* GRN List */}
                      <div className="space-y-4">
                        {grns.length === 0 ? (
                          <div className="text-center py-12 text-gray-500">
                            <div className="text-4xl mb-4">📦</div>
                            <p>No goods received notes found</p>
                          </div>
                        ) : (
                          grns.map((grn) => (
                            <div
                              key={grn.id}
                              className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                              onClick={() => setSelectedGRN(grn)}
                            >
                              <div className="flex justify-between items-start mb-3">
                                <div>
                                  <div className="flex items-center gap-3">
                                    <span className="font-bold text-lg">{grn.grn_number}</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${grnStatusColors[grn.status]}`}>
                                      {grn.status.toUpperCase()}
                                    </span>
                                  </div>
                                  <div className="text-gray-600">
                                    PO: {grn.po_number} | {grn.supplier_name}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className="text-sm text-gray-500">Received: {grn.received_date}</div>
                                  <div className="text-sm text-gray-500">By: {grn.received_by}</div>
                                </div>
                              </div>
                              <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>
                                  <span className="text-gray-500">Items: </span>
                                  <span className="font-medium">{grn.items.length}</span>
                                </div>
                                {grn.temperature_check && (
                                  <div>
                                    <span className="text-gray-500">Temp Check: </span>
                                    <span className={`font-medium ${grn.temperature_check <= 5 ? "text-green-600" : "text-red-600"}`}>
                                      {grn.temperature_check}°C
                                    </span>
                                  </div>
                                )}
                                {grn.quality_score && (
                                  <div>
                                    <span className="text-gray-500">Quality: </span>
                                    <span className={`font-medium ${grn.quality_score >= 90 ? "text-green-600" : "text-yellow-600"}`}>
                                      {grn.quality_score}%
                                    </span>
                                  </div>
                                )}
                              </div>
                              {grn.items.some(i => i.quantity_rejected > 0) && (
                                <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-700">
                                  {grn.items.reduce((sum, i) => sum + i.quantity_rejected, 0)} units rejected
                                </div>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    </>
                  )}
                </motion.div>
              )}

              {/* Invoices Tab */}
              {activeTab === "invoices" && (
                <motion.div
                  key="invoices"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  {loading.invoices ? (
                    <LoadingSpinner />
                  ) : error.invoices ? (
                    <ErrorMessage message={error.invoices} onRetry={fetchInvoices} />
                  ) : (
                    <>
                      <h3 className="text-lg font-semibold mb-4">Supplier Invoices</h3>
                      <div className="space-y-4">
                        {invoices.length === 0 ? (
                          <div className="text-center py-12 text-gray-500">
                            <div className="text-4xl mb-4">🧾</div>
                            <p>No invoices found</p>
                          </div>
                        ) : (
                          invoices.map((invoice) => (
                            <div
                              key={invoice.id}
                              className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                              onClick={() => setSelectedInvoice(invoice)}
                            >
                              <div className="flex justify-between items-start mb-3">
                                <div>
                                  <div className="flex items-center gap-3">
                                    <span className="font-bold text-lg">{invoice.invoice_number}</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${invoiceStatusColors[invoice.status]}`}>
                                      {invoice.status.toUpperCase()}
                                    </span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${matchStatusColors[invoice.matching_status]}`}>
                                      {invoice.matching_status.toUpperCase()}
                                    </span>
                                  </div>
                                  <div className="text-gray-600">
                                    Supplier Ref: {invoice.supplier_invoice_number} | {invoice.supplier_name}
                                  </div>
                                  <div className="text-sm text-gray-500">
                                    PO: {invoice.po_number} | GRN: {invoice.grn_number || "Pending"}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className="font-bold text-lg">{(invoice.total_amount || 0).toFixed(2)} {invoice.currency}</div>
                                  <div className="text-sm text-gray-500">Due: {invoice.due_date}</div>
                                  {invoice.variance_amount && invoice.variance_amount > 0 && (
                                    <div className="text-sm text-red-600">Variance: {(invoice.variance_amount || 0).toFixed(2)} {invoice.currency}</div>
                                  )}
                                </div>
                              </div>
                              <div className="flex justify-between items-center">
                                <div className="text-sm text-gray-500">
                                  Tax: {(invoice.tax_amount || 0).toFixed(2)} | Subtotal: {(invoice.subtotal || 0).toFixed(2)}
                                </div>
                                {(invoice.amount_paid || 0) > 0 && (
                                  <div className="text-sm text-green-600">
                                    Paid: {(invoice.amount_paid || 0).toFixed(2)} {invoice.currency}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </>
                  )}
                </motion.div>
              )}

              {/* Three-Way Matching Tab */}
              {activeTab === "matching" && (
                <motion.div
                  key="matching"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  {loading.matches ? (
                    <LoadingSpinner />
                  ) : error.matches ? (
                    <ErrorMessage message={error.matches} onRetry={fetchMatches} />
                  ) : (
                    <>
                      <div className="mb-6">
                        <h3 className="text-lg font-semibold mb-2">Three-Way Matching</h3>
                        <p className="text-gray-600 text-sm">
                          Compare Purchase Orders, Goods Received Notes, and Invoices to identify discrepancies
                        </p>
                      </div>

                      <div className="space-y-6">
                        {matches.length === 0 ? (
                          <div className="text-center py-12 text-gray-500">
                            <div className="text-4xl mb-4">🔗</div>
                            <p>No three-way matches found</p>
                          </div>
                        ) : (
                          matches.map((match) => (
                            <div
                              key={match.po_id}
                              className={`border rounded-lg overflow-hidden ${
                                match.status === "variance" ? "border-red-300" : "border-gray-200"
                              }`}
                            >
                              {/* Header */}
                              <div className={`p-4 ${
                                match.status === "variance" ? "bg-red-50" :
                                match.status === "matched" ? "bg-green-50" : "bg-gray-50"
                              }`}>
                                <div className="flex justify-between items-center">
                                  <div className="flex items-center gap-4">
                                    <span className="font-bold">{match.supplier_name}</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${matchStatusColors[match.status]}`}>
                                      {match.status.toUpperCase()}
                                    </span>
                                  </div>
                                  <button
                                    onClick={() => setSelectedMatch(match)}
                                    className="text-blue-600 hover:underline text-sm"
                                  >
                                    View Details
                                  </button>
                                </div>
                              </div>

                              {/* Document Links */}
                              <div className="grid grid-cols-3 gap-4 p-4 border-b">
                                <div className="text-center p-3 bg-blue-50 rounded">
                                  <div className="text-xs text-gray-500 mb-1">Purchase Order</div>
                                  <div className="font-medium">{match.po_number}</div>
                                  <div className="text-lg font-bold text-blue-600">{(match.po_total || 0).toFixed(2)}</div>
                                </div>
                                <div className="text-center p-3 bg-purple-50 rounded">
                                  <div className="text-xs text-gray-500 mb-1">GRN</div>
                                  <div className="font-medium">{match.grn_number || "-"}</div>
                                  <div className="text-lg font-bold text-purple-600">{(match.grn_total || 0).toFixed(2) || "-"}</div>
                                </div>
                                <div className="text-center p-3 bg-green-50 rounded">
                                  <div className="text-xs text-gray-500 mb-1">Invoice</div>
                                  <div className="font-medium">{match.invoice_number || "-"}</div>
                                  <div className="text-lg font-bold text-green-600">{(match.invoice_total || 0).toFixed(2) || "-"}</div>
                                </div>
                              </div>

                              {/* Variance Summary */}
                              {match.status === "variance" && (
                                <div className="p-4 bg-red-50">
                                  <div className="flex items-center gap-4 text-sm">
                                    <div className="flex items-center gap-2">
                                      <span className="text-red-600">Warning:</span>
                                      <span>Quantity Variance: <strong>{match.quantity_variance}</strong> units</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <span className="text-red-600">Price:</span>
                                      <span>Price Variance: <strong>{(match.price_variance || 0).toFixed(2)} BGN</strong></span>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Items Table */}
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th className="text-left p-3">Item</th>
                                      <th className="text-center p-3">PO Qty</th>
                                      <th className="text-center p-3">GRN Qty</th>
                                      <th className="text-center p-3">Invoice Qty</th>
                                      <th className="text-center p-3">PO Price</th>
                                      <th className="text-center p-3">Invoice Price</th>
                                      <th className="text-center p-3">Variance</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {(match.items || []).map((item, idx) => (
                                      <tr key={idx} className={`border-t ${
                                        item.qty_variance !== 0 || item.price_variance !== 0 ? "bg-red-50" : ""
                                      }`}>
                                        <td className="p-3 font-medium">{item.ingredient_name}</td>
                                        <td className="text-center p-3">{item.po_qty}</td>
                                        <td className="text-center p-3">{item.grn_qty}</td>
                                        <td className="text-center p-3">{item.invoice_qty}</td>
                                        <td className="text-center p-3">{(item.po_price || 0).toFixed(2)}</td>
                                        <td className="text-center p-3">{(item.invoice_price || 0).toFixed(2)}</td>
                                        <td className="text-center p-3">
                                          {item.qty_variance !== 0 && (
                                            <span className="text-red-600">{item.qty_variance > 0 ? "+" : ""}{item.qty_variance} qty</span>
                                          )}
                                          {item.price_variance !== 0 && (
                                            <span className="text-red-600 ml-2">{(item.price_variance || 0).toFixed(2)} BGN</span>
                                          )}
                                          {item.qty_variance === 0 && item.price_variance === 0 && (
                                            <span className="text-green-600">OK</span>
                                          )}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>

                              {/* Actions */}
                              {match.status === "variance" && (
                                <div className="p-4 border-t flex justify-end gap-2">
                                  <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                                    Request Credit Note
                                  </button>
                                  <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                                    Contact Supplier
                                  </button>
                                  <button className="px-4 py-2 bg-yellow-600 text-gray-900 rounded-lg hover:bg-yellow-700">
                                    Accept Variance
                                  </button>
                                </div>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    </>
                  )}
                </motion.div>
              )}

              {/* Analytics Tab */}
              {activeTab === "analytics" && (
                <motion.div
                  key="analytics"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <h3 className="text-lg font-semibold mb-6">Procurement Analytics</h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Spending by Supplier */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-medium mb-4">Spending by Supplier (This Month)</h4>
                      <div className="space-y-3">
                        {[
                          { name: "Quality Meats Ltd", amount: 12500, percentage: 45 },
                          { name: "Fresh Farm Produce", amount: 8200, percentage: 30 },
                          { name: "Beverage Distributors", amount: 4500, percentage: 16 },
                          { name: "Others", amount: 2500, percentage: 9 },
                        ].map((supplier, idx) => (
                          <div key={idx}>
                            <div className="flex justify-between text-sm mb-1">
                              <span>{supplier.name}</span>
                              <span className="font-medium">{supplier.amount.toLocaleString()} BGN</span>
                            </div>
                            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-500 rounded-full"
                                style={{ width: `${supplier.percentage}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Order Status Distribution */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-medium mb-4">Order Status Distribution</h4>
                      <div className="grid grid-cols-2 gap-4">
                        {[
                          { status: "Completed", count: 45, color: "bg-green-500" },
                          { status: "In Progress", count: 12, color: "bg-blue-500" },
                          { status: "Pending Approval", count: 5, color: "bg-yellow-500" },
                          { status: "Cancelled", count: 3, color: "bg-red-500" },
                        ].map((item, idx) => (
                          <div key={idx} className="flex items-center gap-3">
                            <div className={`w-4 h-4 rounded ${item.color}`} />
                            <div>
                              <div className="font-medium">{item.count}</div>
                              <div className="text-xs text-gray-500">{item.status}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Delivery Performance */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-medium mb-4">Supplier Delivery Performance</h4>
                      <div className="space-y-3">
                        {[
                          { name: "Fresh Farm Produce", onTime: 95, quality: 92 },
                          { name: "Quality Meats Ltd", onTime: 88, quality: 96 },
                          { name: "Beverage Distributors", onTime: 100, quality: 100 },
                        ].map((supplier, idx) => (
                          <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                            <span className="font-medium">{supplier.name}</span>
                            <div className="flex gap-4 text-sm">
                              <span className={supplier.onTime >= 90 ? "text-green-600" : "text-yellow-600"}>
                                On-Time: {supplier.onTime}%
                              </span>
                              <span className={supplier.quality >= 90 ? "text-green-600" : "text-yellow-600"}>
                                Quality: {supplier.quality}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Monthly Trend */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-medium mb-4">Monthly Procurement Trend</h4>
                      <div className="flex items-end justify-between h-32 px-4">
                        {[
                          { month: "Oct", value: 18500 },
                          { month: "Nov", value: 22000 },
                          { month: "Dec", value: 28000 },
                          { month: "Jan", value: 24500 },
                        ].map((item, idx) => (
                          <div key={idx} className="flex flex-col items-center gap-1">
                            <div
                              className="w-12 bg-blue-500 rounded-t"
                              style={{ height: `${(item.value / 30000) * 100}px` }}
                            />
                            <span className="text-xs text-gray-500">{item.month}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Cost Savings */}
                    <div className="border rounded-lg p-4 md:col-span-2">
                      <h4 className="font-medium mb-4">Cost Savings Opportunities</h4>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                          <div>
                            <div className="font-medium text-green-800">Bulk Order Discount Available</div>
                            <div className="text-sm text-green-600">Quality Meats Ltd offers 8% discount on orders over 5000 BGN</div>
                          </div>
                          <div className="text-xl font-bold text-green-600">~400 BGN</div>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <div>
                            <div className="font-medium text-blue-800">Consolidate Similar Orders</div>
                            <div className="text-sm text-blue-600">3 pending orders to Fresh Farm can be combined</div>
                          </div>
                          <div className="text-xl font-bold text-blue-600">~150 BGN</div>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                          <div>
                            <div className="font-medium text-yellow-800">Alternative Supplier Found</div>
                            <div className="text-sm text-yellow-600">Olive Oil cheaper at Mediterranean Imports</div>
                          </div>
                          <div className="text-xl font-bold text-yellow-600">~200 BGN</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* PO Detail Modal */}
        <AnimatePresence>
          {selectedPO && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
              onClick={() => setSelectedPO(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-xl font-bold">{selectedPO.po_number}</h2>
                      <p className="text-gray-600">{selectedPO.supplier_name}</p>
                    </div>
                    <button onClick={() => setSelectedPO(null)} className="text-gray-500 hover:text-gray-700">
                      ✕
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div>
                      <div className="text-sm text-gray-500">Status</div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${poStatusColors[selectedPO.status]}`}>
                        {selectedPO.status.replace("_", " ").toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Warehouse</div>
                      <div className="font-medium">{selectedPO.warehouse_name}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Order Date</div>
                      <div className="font-medium">{selectedPO.order_date}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Expected Date</div>
                      <div className="font-medium">{selectedPO.expected_date}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Created By</div>
                      <div className="font-medium">{selectedPO.created_by}</div>
                    </div>
                    {selectedPO.approved_by && (
                      <div>
                        <div className="text-sm text-gray-500">Approved By</div>
                        <div className="font-medium">{selectedPO.approved_by}</div>
                      </div>
                    )}
                  </div>

                  <h3 className="font-semibold mb-3">Order Items</h3>
                  <table className="w-full text-sm mb-6">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left p-3">Item</th>
                        <th className="text-center p-3">Ordered</th>
                        <th className="text-center p-3">Received</th>
                        <th className="text-right p-3">Unit Price</th>
                        <th className="text-right p-3">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedPO.items.map((item) => (
                        <tr key={item.id} className="border-t">
                          <td className="p-3 font-medium">{item.ingredient_name}</td>
                          <td className="text-center p-3">{item.quantity_ordered} {item.unit}</td>
                          <td className="text-center p-3">
                            <span className={item.quantity_received < item.quantity_ordered ? "text-orange-600" : "text-green-600"}>
                              {item.quantity_received} {item.unit}
                            </span>
                          </td>
                          <td className="text-right p-3">{(item.unit_price || 0).toFixed(2)}</td>
                          <td className="text-right p-3 font-medium">{(item.total_price || 0).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t-2">
                      <tr>
                        <td colSpan={4} className="p-3 text-right font-semibold">Total</td>
                        <td className="p-3 text-right font-bold">{(selectedPO.total_amount || 0).toFixed(2)} {selectedPO.currency}</td>
                      </tr>
                    </tfoot>
                  </table>

                  {selectedPO.notes && (
                    <div className="p-3 bg-gray-50 rounded mb-4">
                      <div className="text-sm text-gray-500 mb-1">Notes</div>
                      <div>{selectedPO.notes}</div>
                    </div>
                  )}

                  <div className="flex justify-end gap-2">
                    {selectedPO.status === "pending_approval" && (
                      <>
                        <button
                          onClick={() => {
                            handleRejectPO(selectedPO.id);
                            setSelectedPO(null);
                          }}
                          className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                        >
                          Reject
                        </button>
                        <button
                          onClick={() => {
                            handleApprovePO(selectedPO.id);
                            setSelectedPO(null);
                          }}
                          className="px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700"
                        >
                          Approve
                        </button>
                      </>
                    )}
                    {selectedPO.status === "approved" && (
                      <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">
                        Send to Supplier
                      </button>
                    )}
                    {(selectedPO.status === "sent" || selectedPO.status === "partial") && (
                      <button className="px-4 py-2 bg-purple-600 text-gray-900 rounded-lg hover:bg-purple-700">
                        Create GRN
                      </button>
                    )}
                    <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                      Print
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* GRN Detail Modal */}
        <AnimatePresence>
          {selectedGRN && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
              onClick={() => setSelectedGRN(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-xl font-bold">{selectedGRN.grn_number}</h2>
                      <p className="text-gray-600">PO: {selectedGRN.po_number} | {selectedGRN.supplier_name}</p>
                    </div>
                    <button onClick={() => setSelectedGRN(null)} className="text-gray-500 hover:text-gray-700">
                      ✕
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div>
                      <div className="text-sm text-gray-500">Status</div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${grnStatusColors[selectedGRN.status]}`}>
                        {selectedGRN.status.toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Received Date</div>
                      <div className="font-medium">{selectedGRN.received_date}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Received By</div>
                      <div className="font-medium">{selectedGRN.received_by}</div>
                    </div>
                    {selectedGRN.quality_score && (
                      <div>
                        <div className="text-sm text-gray-500">Quality Score</div>
                        <div className={`font-medium ${selectedGRN.quality_score >= 90 ? "text-green-600" : "text-yellow-600"}`}>
                          {selectedGRN.quality_score}%
                        </div>
                      </div>
                    )}
                  </div>

                  <h3 className="font-semibold mb-3">Received Items</h3>
                  <table className="w-full text-sm mb-6">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left p-3">Item</th>
                        <th className="text-center p-3">Ordered</th>
                        <th className="text-center p-3">Received</th>
                        <th className="text-center p-3">Accepted</th>
                        <th className="text-center p-3">Rejected</th>
                        <th className="text-left p-3">Batch #</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedGRN.items.map((item) => (
                        <tr key={item.id} className={`border-t ${item.quantity_rejected > 0 ? "bg-red-50" : ""}`}>
                          <td className="p-3 font-medium">{item.ingredient_name}</td>
                          <td className="text-center p-3">{item.quantity_ordered} {item.unit}</td>
                          <td className="text-center p-3">{item.quantity_received} {item.unit}</td>
                          <td className="text-center p-3 text-green-600">{item.quantity_accepted}</td>
                          <td className="text-center p-3 text-red-600">{item.quantity_rejected}</td>
                          <td className="p-3 text-xs">
                            {item.batch_number}
                            {item.expiry_date && (
                              <div className="text-gray-500">Exp: {item.expiry_date}</div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {selectedGRN.notes && (
                    <div className="p-3 bg-gray-50 rounded mb-4">
                      <div className="text-sm text-gray-500 mb-1">Notes</div>
                      <div>{selectedGRN.notes}</div>
                    </div>
                  )}

                  <div className="flex justify-end gap-2">
                    <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                      Print
                    </button>
                    <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">
                      Match Invoice
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Create PO Modal */}
        <AnimatePresence>
          {showCreatePO && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4"
              onClick={() => setShowCreatePO(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-xl max-w-2xl w-full"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-6 border-b">
                  <div className="flex justify-between items-center">
                    <h2 className="text-xl font-bold">Create Purchase Order</h2>
                    <button onClick={() => setShowCreatePO(false)} className="text-gray-500 hover:text-gray-700">
                      ✕
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Supplier
                      <select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                        <option>Select supplier...</option>
                        <option>Fresh Farm Produce</option>
                        <option>Quality Meats Ltd</option>
                        <option>Beverage Distributors</option>
                      </select>
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Warehouse
                      <select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
                        <option>Main Kitchen</option>
                        <option>Bar Storage</option>
                        <option>Cold Storage</option>
                      </select>
                      </label>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Order Date
                        <input type="date" className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
                        </label>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Expected Delivery
                        <input type="date" className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
                        </label>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Notes
                      <textarea
                        rows={3}
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        placeholder="Add any notes..."
                      />
                      </label>
                    </div>

                    <div className="border-t pt-4">
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="font-medium">Create From</h3>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left">
                          <div className="font-medium">📊 Demand Forecast</div>
                          <div className="text-sm text-gray-500">Auto-generate from AI predictions</div>
                        </button>
                        <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left">
                          <div className="font-medium">⚠️ Low Stock Items</div>
                          <div className="text-sm text-gray-500">Items below reorder point</div>
                        </button>
                        <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left">
                          <div className="font-medium">📋 Recipe Requirements</div>
                          <div className="text-sm text-gray-500">Based on production plan</div>
                        </button>
                        <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left">
                          <div className="font-medium">✏️ Manual Entry</div>
                          <div className="text-sm text-gray-500">Add items manually</div>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t flex justify-end gap-2">
                  <button
                    onClick={() => setShowCreatePO(false)}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">
                    Continue
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
