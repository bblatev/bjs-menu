"use client";

import React from "react";
import { motion } from "framer-motion";
import { LoadingSpinner, ErrorMessage } from "./POHelpers";
import type {
  PurchaseOrder, GoodsReceivedNote, Invoice,
  ApprovalRequest, ThreeWayMatch,
} from "./types";
import {
  poStatusColors, grnStatusColors, invoiceStatusColors, matchStatusColors,
} from "./types";

// ===== Orders Tab =====
interface OrdersTabProps {
  loading: boolean;
  error: string;
  fetchPurchaseOrders: () => void;
  searchTerm: string;
  setSearchTerm: (v: string) => void;
  poStatusFilter: string;
  setPOStatusFilter: (v: string) => void;
  setShowCreatePO: (v: boolean) => void;
  filteredPOs: PurchaseOrder[];
  setSelectedPO: (po: PurchaseOrder) => void;
}

export function OrdersTab(props: OrdersTabProps) {
  const {
    loading, error, fetchPurchaseOrders,
    searchTerm, setSearchTerm, poStatusFilter, setPOStatusFilter,
    setShowCreatePO, filteredPOs, setSelectedPO,
  } = props;

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={fetchPurchaseOrders} />;

  return (
    <>
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex-1 min-w-[200px]">
          <input type="text" placeholder="Search PO number or supplier..." value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
        </div>
        <select value={poStatusFilter} onChange={(e) => setPOStatusFilter(e.target.value)}
          className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="pending_approval">Pending Approval</option>
          <option value="approved">Approved</option>
          <option value="sent">Sent</option>
          <option value="partial">Partial</option>
          <option value="received">Received</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button onClick={() => setShowCreatePO(true)}
          className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2">
          <span>+</span><span>Create PO</span>
        </button>
      </div>
      <div className="space-y-4">
        {filteredPOs.length === 0 ? (
          <div className="text-center py-12 text-gray-500"><div className="text-4xl mb-4">📋</div><p>No purchase orders found</p></div>
        ) : (
          filteredPOs.map((po) => (
            <motion.div key={po.id} layout className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer" onClick={() => setSelectedPO(po)}>
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
                <div>{po.approved_by && (<span className="text-green-600">✓ Approved by {po.approved_by}</span>)}</div>
              </div>
              {po.status === "partial" && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Receiving Progress</span>
                    <span>{Math.round(((po.items || []).reduce((sum, i) => sum + i.quantity_received, 0) / ((po.items || []).reduce((sum, i) => sum + i.quantity_ordered, 0) || 1)) * 100)}%</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-orange-500 rounded-full" style={{ width: `${((po.items || []).reduce((sum, i) => sum + i.quantity_received, 0) / ((po.items || []).reduce((sum, i) => sum + i.quantity_ordered, 0) || 1)) * 100}%` }} />
                  </div>
                </div>
              )}
            </motion.div>
          ))
        )}
      </div>
    </>
  );
}

// ===== Approvals Tab =====
interface ApprovalsTabProps {
  loading: boolean;
  error: string;
  fetchApprovals: () => void;
  approvals: ApprovalRequest[];
  handleApprovePO: (id: string) => void;
  handleRejectPO: (id: string) => void;
  handleApproveVariance: (id: string) => void;
}

export function ApprovalsTab(props: ApprovalsTabProps) {
  const { loading, error, fetchApprovals, approvals, handleApprovePO, handleRejectPO, handleApproveVariance } = props;

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={fetchApprovals} />;

  return (
    <>
      <h3 className="text-lg font-semibold mb-4">Pending Approvals</h3>
      <div className="space-y-4">
        {approvals.filter(a => a.status === "pending").map((approval) => (
          <div key={approval.id} className={`border rounded-lg p-4 ${approval.urgency === "high" ? "border-red-300 bg-red-50" : approval.urgency === "medium" ? "border-yellow-300 bg-yellow-50" : "border-gray-200"}`}>
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="flex items-center gap-3">
                  <span className="font-bold">{approval.reference_number}</span>
                  <span className={`px-2 py-1 rounded text-xs ${approval.type === "purchase_order" ? "bg-blue-100 text-blue-800" : approval.type === "variance" ? "bg-orange-100 text-orange-800" : "bg-gray-100 text-gray-800"}`}>
                    {approval.type.replace("_", " ").toUpperCase()}
                  </span>
                  {approval.urgency === "high" && (<span className="px-2 py-1 rounded text-xs bg-red-100 text-red-800">URGENT</span>)}
                </div>
                <div className="text-gray-600">{approval.supplier_name}</div>
                <div className="text-sm text-gray-500 mt-1">Requested by {approval.requested_by} on {new Date(approval.requested_at).toLocaleDateString()}</div>
              </div>
              <div className="text-right"><div className="font-bold text-lg">{(approval.amount || 0).toFixed(2)} BGN</div></div>
            </div>
            {approval.notes && (<div className="text-sm text-gray-600 mb-3 p-2 bg-white rounded">{approval.notes}</div>)}
            <div className="flex justify-end gap-2">
              <button onClick={() => approval.type === "purchase_order" ? handleRejectPO(approval.reference_id) : null}
                className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50">Reject</button>
              <button onClick={() => approval.type === "purchase_order" ? handleApprovePO(approval.reference_id) : handleApproveVariance(approval.id)}
                className="px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700">Approve</button>
            </div>
          </div>
        ))}
        {approvals.filter(a => a.status === "pending").length === 0 && (
          <div className="text-center py-8 text-gray-500">No pending approvals</div>
        )}
      </div>
      <h3 className="text-lg font-semibold mt-8 mb-4">Recent Decisions</h3>
      <div className="space-y-2">
        {approvals.filter(a => a.status !== "pending").map((approval) => (
          <div key={approval.id} className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <span className="font-medium">{approval.reference_number}</span>
              <span className="text-gray-500 ml-2">{approval.supplier_name}</span>
            </div>
            <span className={`px-2 py-1 rounded text-xs ${approval.status === "approved" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
              {approval.status.toUpperCase()}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

// ===== Receiving Tab =====
interface ReceivingTabProps {
  loading: boolean;
  error: string;
  fetchGRNs: () => void;
  grns: GoodsReceivedNote[];
  purchaseOrders: PurchaseOrder[];
  setShowCreateGRN: (v: boolean) => void;
  setSelectedGRN: (grn: GoodsReceivedNote) => void;
}

export function ReceivingTab(props: ReceivingTabProps) {
  const { loading, error, fetchGRNs, grns, purchaseOrders, setShowCreateGRN, setSelectedGRN } = props;

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={fetchGRNs} />;

  return (
    <>
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold">Goods Received Notes</h3>
        <button onClick={() => setShowCreateGRN(true)} className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2">
          <span>+</span><span>Create GRN</span>
        </button>
      </div>
      <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <h4 className="font-medium text-yellow-800 mb-2">Expected Deliveries Today</h4>
        {purchaseOrders
          .filter(po => po.status === "approved" || po.status === "sent")
          .filter(po => new Date(po.expected_date).toDateString() === new Date().toDateString())
          .map(po => (
            <div key={po.id} className="flex justify-between items-center py-2 border-b border-yellow-200 last:border-0">
              <div><span className="font-medium">{po.po_number}</span><span className="text-gray-600 ml-2">from {po.supplier_name}</span></div>
              <button className="px-3 py-1 bg-yellow-600 text-gray-900 text-sm rounded hover:bg-yellow-700">Receive Now</button>
            </div>
          ))}
        {purchaseOrders
          .filter(po => po.status === "approved" || po.status === "sent")
          .filter(po => new Date(po.expected_date).toDateString() === new Date().toDateString()).length === 0 && (
            <div className="text-yellow-700">No deliveries expected today</div>
          )}
      </div>
      <div className="space-y-4">
        {grns.length === 0 ? (
          <div className="text-center py-12 text-gray-500"><div className="text-4xl mb-4">📦</div><p>No goods received notes found</p></div>
        ) : (
          grns.map((grn) => (
            <div key={grn.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer" onClick={() => setSelectedGRN(grn)}>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-lg">{grn.grn_number}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${grnStatusColors[grn.status]}`}>{grn.status.toUpperCase()}</span>
                  </div>
                  <div className="text-gray-600">PO: {grn.po_number} | {grn.supplier_name}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500">Received: {grn.received_date}</div>
                  <div className="text-sm text-gray-500">By: {grn.received_by}</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-500">Items: </span><span className="font-medium">{grn.items.length}</span></div>
                {grn.temperature_check && (
                  <div><span className="text-gray-500">Temp Check: </span><span className={`font-medium ${grn.temperature_check <= 5 ? "text-green-600" : "text-red-600"}`}>{grn.temperature_check}°C</span></div>
                )}
                {grn.quality_score && (
                  <div><span className="text-gray-500">Quality: </span><span className={`font-medium ${grn.quality_score >= 90 ? "text-green-600" : "text-yellow-600"}`}>{grn.quality_score}%</span></div>
                )}
              </div>
              {grn.items.some(i => i.quantity_rejected > 0) && (
                <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-700">{grn.items.reduce((sum, i) => sum + i.quantity_rejected, 0)} units rejected</div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );
}

// ===== Invoices Tab =====
interface InvoicesTabProps {
  loading: boolean;
  error: string;
  fetchInvoices: () => void;
  invoices: Invoice[];
  setSelectedInvoice: (inv: Invoice) => void;
}

export function InvoicesTab(props: InvoicesTabProps) {
  const { loading, error, fetchInvoices, invoices, setSelectedInvoice } = props;

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={fetchInvoices} />;

  return (
    <>
      <h3 className="text-lg font-semibold mb-4">Supplier Invoices</h3>
      <div className="space-y-4">
        {invoices.length === 0 ? (
          <div className="text-center py-12 text-gray-500"><div className="text-4xl mb-4">🧾</div><p>No invoices found</p></div>
        ) : (
          invoices.map((invoice) => (
            <div key={invoice.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer" onClick={() => setSelectedInvoice(invoice)}>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-lg">{invoice.invoice_number}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${invoiceStatusColors[invoice.status]}`}>{invoice.status.toUpperCase()}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${matchStatusColors[invoice.matching_status]}`}>{invoice.matching_status.toUpperCase()}</span>
                  </div>
                  <div className="text-gray-600">Supplier Ref: {invoice.supplier_invoice_number} | {invoice.supplier_name}</div>
                  <div className="text-sm text-gray-500">PO: {invoice.po_number} | GRN: {invoice.grn_number || "Pending"}</div>
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
                <div className="text-sm text-gray-500">Tax: {(invoice.tax_amount || 0).toFixed(2)} | Subtotal: {(invoice.subtotal || 0).toFixed(2)}</div>
                {(invoice.amount_paid || 0) > 0 && (<div className="text-sm text-green-600">Paid: {(invoice.amount_paid || 0).toFixed(2)} {invoice.currency}</div>)}
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
}

// ===== Matching Tab =====
interface MatchingTabProps {
  loading: boolean;
  error: string;
  fetchMatches: () => void;
  matches: ThreeWayMatch[];
  setSelectedMatch: (m: ThreeWayMatch) => void;
}

export function MatchingTab(props: MatchingTabProps) {
  const { loading, error, fetchMatches, matches, setSelectedMatch } = props;

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={fetchMatches} />;

  return (
    <>
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">Three-Way Matching</h3>
        <p className="text-gray-600 text-sm">Compare Purchase Orders, Goods Received Notes, and Invoices to identify discrepancies</p>
      </div>
      <div className="space-y-6">
        {matches.length === 0 ? (
          <div className="text-center py-12 text-gray-500"><div className="text-4xl mb-4">🔗</div><p>No three-way matches found</p></div>
        ) : (
          matches.map((match) => (
            <div key={match.po_id} className={`border rounded-lg overflow-hidden ${match.status === "variance" ? "border-red-300" : "border-gray-200"}`}>
              <div className={`p-4 ${match.status === "variance" ? "bg-red-50" : match.status === "matched" ? "bg-green-50" : "bg-gray-50"}`}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-4">
                    <span className="font-bold">{match.supplier_name}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${matchStatusColors[match.status]}`}>{match.status.toUpperCase()}</span>
                  </div>
                  <button onClick={() => setSelectedMatch(match)} className="text-blue-600 hover:underline text-sm">View Details</button>
                </div>
              </div>
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
              {match.status === "variance" && (
                <div className="p-4 bg-red-50">
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2"><span className="text-red-600">Warning:</span><span>Quantity Variance: <strong>{match.quantity_variance}</strong> units</span></div>
                    <div className="flex items-center gap-2"><span className="text-red-600">Price:</span><span>Price Variance: <strong>{(match.price_variance || 0).toFixed(2)} BGN</strong></span></div>
                  </div>
                </div>
              )}
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
                      <tr key={idx} className={`border-t ${item.qty_variance !== 0 || item.price_variance !== 0 ? "bg-red-50" : ""}`}>
                        <td className="p-3 font-medium">{item.ingredient_name}</td>
                        <td className="text-center p-3">{item.po_qty}</td>
                        <td className="text-center p-3">{item.grn_qty}</td>
                        <td className="text-center p-3">{item.invoice_qty}</td>
                        <td className="text-center p-3">{(item.po_price || 0).toFixed(2)}</td>
                        <td className="text-center p-3">{(item.invoice_price || 0).toFixed(2)}</td>
                        <td className="text-center p-3">
                          {item.qty_variance !== 0 && (<span className="text-red-600">{item.qty_variance > 0 ? "+" : ""}{item.qty_variance} qty</span>)}
                          {item.price_variance !== 0 && (<span className="text-red-600 ml-2">{(item.price_variance || 0).toFixed(2)} BGN</span>)}
                          {item.qty_variance === 0 && item.price_variance === 0 && (<span className="text-green-600">OK</span>)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {match.status === "variance" && (
                <div className="p-4 border-t flex justify-end gap-2">
                  <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Request Credit Note</button>
                  <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Contact Supplier</button>
                  <button className="px-4 py-2 bg-yellow-600 text-gray-900 rounded-lg hover:bg-yellow-700">Accept Variance</button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );
}

// ===== Analytics Tab =====
export function POAnalyticsTab() {
  return (
    <>
      <h3 className="text-lg font-semibold mb-6">Procurement Analytics</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                <div className="flex justify-between text-sm mb-1"><span>{supplier.name}</span><span className="font-medium">{supplier.amount.toLocaleString()} BGN</span></div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden"><div className="h-full bg-blue-500 rounded-full" style={{ width: `${supplier.percentage}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
        <div className="border rounded-lg p-4">
          <h4 className="font-medium mb-4">Order Status Distribution</h4>
          <div className="grid grid-cols-2 gap-4">
            {[
              { status: "Completed", count: 45, color: "bg-green-500" },
              { status: "In Progress", count: 12, color: "bg-blue-500" },
              { status: "Pending Approval", count: 5, color: "bg-yellow-500" },
              { status: "Cancelled", count: 3, color: "bg-red-500" },
            ].map((item, idx) => (
              <div key={idx} className="flex items-center gap-3"><div className={`w-4 h-4 rounded ${item.color}`} /><div><div className="font-medium">{item.count}</div><div className="text-xs text-gray-500">{item.status}</div></div></div>
            ))}
          </div>
        </div>
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
                  <span className={supplier.onTime >= 90 ? "text-green-600" : "text-yellow-600"}>On-Time: {supplier.onTime}%</span>
                  <span className={supplier.quality >= 90 ? "text-green-600" : "text-yellow-600"}>Quality: {supplier.quality}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
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
                <div className="w-12 bg-blue-500 rounded-t" style={{ height: `${(item.value / 30000) * 100}px` }} />
                <span className="text-xs text-gray-500">{item.month}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="border rounded-lg p-4 md:col-span-2">
          <h4 className="font-medium mb-4">Cost Savings Opportunities</h4>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
              <div><div className="font-medium text-green-800">Bulk Order Discount Available</div><div className="text-sm text-green-600">Quality Meats Ltd offers 8% discount on orders over 5000 BGN</div></div>
              <div className="text-xl font-bold text-green-600">~400 BGN</div>
            </div>
            <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div><div className="font-medium text-blue-800">Consolidate Similar Orders</div><div className="text-sm text-blue-600">3 pending orders to Fresh Farm can be combined</div></div>
              <div className="text-xl font-bold text-blue-600">~150 BGN</div>
            </div>
            <div className="flex items-center justify-between p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div><div className="font-medium text-yellow-800">Alternative Supplier Found</div><div className="text-sm text-yellow-600">Olive Oil cheaper at Mediterranean Imports</div></div>
              <div className="text-xl font-bold text-yellow-600">~200 BGN</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
