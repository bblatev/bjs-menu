"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { PurchaseOrder, GoodsReceivedNote } from "./types";
import { poStatusColors, grnStatusColors } from "./types";

interface POModalsProps {
  selectedPO: PurchaseOrder | null;
  setSelectedPO: (v: PurchaseOrder | null) => void;
  selectedGRN: GoodsReceivedNote | null;
  setSelectedGRN: (v: GoodsReceivedNote | null) => void;
  showCreatePO: boolean;
  setShowCreatePO: (v: boolean) => void;
  handleApprovePO: (id: string) => void;
  handleRejectPO: (id: string) => void;
}

export default function POModals(props: POModalsProps) {
  const {
    selectedPO, setSelectedPO,
    selectedGRN, setSelectedGRN,
    showCreatePO, setShowCreatePO,
    handleApprovePO, handleRejectPO,
  } = props;

  return (
    <>
      {/* PO Detail Modal */}
      <AnimatePresence>
        {selectedPO && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedPO(null)}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <div className="p-6 border-b">
                <div className="flex justify-between items-start">
                  <div><h2 className="text-xl font-bold">{selectedPO.po_number}</h2><p className="text-gray-600">{selectedPO.supplier_name}</p></div>
                  <button onClick={() => setSelectedPO(null)} className="text-gray-500 hover:text-gray-700">✕</button>
                </div>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div><div className="text-sm text-gray-500">Status</div><span className={`px-2 py-1 rounded-full text-xs font-medium ${poStatusColors[selectedPO.status]}`}>{selectedPO.status.replace("_", " ").toUpperCase()}</span></div>
                  <div><div className="text-sm text-gray-500">Warehouse</div><div className="font-medium">{selectedPO.warehouse_name}</div></div>
                  <div><div className="text-sm text-gray-500">Order Date</div><div className="font-medium">{selectedPO.order_date}</div></div>
                  <div><div className="text-sm text-gray-500">Expected Date</div><div className="font-medium">{selectedPO.expected_date}</div></div>
                  <div><div className="text-sm text-gray-500">Created By</div><div className="font-medium">{selectedPO.created_by}</div></div>
                  {selectedPO.approved_by && (<div><div className="text-sm text-gray-500">Approved By</div><div className="font-medium">{selectedPO.approved_by}</div></div>)}
                </div>
                <h3 className="font-semibold mb-3">Order Items</h3>
                <table className="w-full text-sm mb-6">
                  <thead className="bg-gray-50"><tr><th className="text-left p-3">Item</th><th className="text-center p-3">Ordered</th><th className="text-center p-3">Received</th><th className="text-right p-3">Unit Price</th><th className="text-right p-3">Total</th></tr></thead>
                  <tbody>
                    {selectedPO.items.map((item) => (
                      <tr key={item.id} className="border-t">
                        <td className="p-3 font-medium">{item.ingredient_name}</td>
                        <td className="text-center p-3">{item.quantity_ordered} {item.unit}</td>
                        <td className="text-center p-3"><span className={item.quantity_received < item.quantity_ordered ? "text-orange-600" : "text-green-600"}>{item.quantity_received} {item.unit}</span></td>
                        <td className="text-right p-3">{(item.unit_price || 0).toFixed(2)}</td>
                        <td className="text-right p-3 font-medium">{(item.total_price || 0).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="border-t-2"><tr><td colSpan={4} className="p-3 text-right font-semibold">Total</td><td className="p-3 text-right font-bold">{(selectedPO.total_amount || 0).toFixed(2)} {selectedPO.currency}</td></tr></tfoot>
                </table>
                {selectedPO.notes && (<div className="p-3 bg-gray-50 rounded mb-4"><div className="text-sm text-gray-500 mb-1">Notes</div><div>{selectedPO.notes}</div></div>)}
                <div className="flex justify-end gap-2">
                  {selectedPO.status === "pending_approval" && (
                    <>
                      <button onClick={() => { handleRejectPO(selectedPO.id); setSelectedPO(null); }} className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50">Reject</button>
                      <button onClick={() => { handleApprovePO(selectedPO.id); setSelectedPO(null); }} className="px-4 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700">Approve</button>
                    </>
                  )}
                  {selectedPO.status === "approved" && (<button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">Send to Supplier</button>)}
                  {(selectedPO.status === "sent" || selectedPO.status === "partial") && (<button className="px-4 py-2 bg-purple-600 text-gray-900 rounded-lg hover:bg-purple-700">Create GRN</button>)}
                  <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Print</button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* GRN Detail Modal */}
      <AnimatePresence>
        {selectedGRN && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedGRN(null)}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <div className="p-6 border-b">
                <div className="flex justify-between items-start">
                  <div><h2 className="text-xl font-bold">{selectedGRN.grn_number}</h2><p className="text-gray-600">PO: {selectedGRN.po_number} | {selectedGRN.supplier_name}</p></div>
                  <button onClick={() => setSelectedGRN(null)} className="text-gray-500 hover:text-gray-700">✕</button>
                </div>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div><div className="text-sm text-gray-500">Status</div><span className={`px-2 py-1 rounded-full text-xs font-medium ${grnStatusColors[selectedGRN.status]}`}>{selectedGRN.status.toUpperCase()}</span></div>
                  <div><div className="text-sm text-gray-500">Received Date</div><div className="font-medium">{selectedGRN.received_date}</div></div>
                  <div><div className="text-sm text-gray-500">Received By</div><div className="font-medium">{selectedGRN.received_by}</div></div>
                  {selectedGRN.quality_score && (<div><div className="text-sm text-gray-500">Quality Score</div><div className={`font-medium ${selectedGRN.quality_score >= 90 ? "text-green-600" : "text-yellow-600"}`}>{selectedGRN.quality_score}%</div></div>)}
                </div>
                <h3 className="font-semibold mb-3">Received Items</h3>
                <table className="w-full text-sm mb-6">
                  <thead className="bg-gray-50"><tr><th className="text-left p-3">Item</th><th className="text-center p-3">Ordered</th><th className="text-center p-3">Received</th><th className="text-center p-3">Accepted</th><th className="text-center p-3">Rejected</th><th className="text-left p-3">Batch #</th></tr></thead>
                  <tbody>
                    {selectedGRN.items.map((item) => (
                      <tr key={item.id} className={`border-t ${item.quantity_rejected > 0 ? "bg-red-50" : ""}`}>
                        <td className="p-3 font-medium">{item.ingredient_name}</td>
                        <td className="text-center p-3">{item.quantity_ordered} {item.unit}</td>
                        <td className="text-center p-3">{item.quantity_received} {item.unit}</td>
                        <td className="text-center p-3 text-green-600">{item.quantity_accepted}</td>
                        <td className="text-center p-3 text-red-600">{item.quantity_rejected}</td>
                        <td className="p-3 text-xs">{item.batch_number}{item.expiry_date && (<div className="text-gray-500">Exp: {item.expiry_date}</div>)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {selectedGRN.notes && (<div className="p-3 bg-gray-50 rounded mb-4"><div className="text-sm text-gray-500 mb-1">Notes</div><div>{selectedGRN.notes}</div></div>)}
                <div className="flex justify-end gap-2">
                  <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Print</button>
                  <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">Match Invoice</button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Create PO Modal */}
      <AnimatePresence>
        {showCreatePO && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setShowCreatePO(false)}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl max-w-2xl w-full" onClick={(e) => e.stopPropagation()}>
              <div className="p-6 border-b">
                <div className="flex justify-between items-center"><h2 className="text-xl font-bold">Create Purchase Order</h2><button onClick={() => setShowCreatePO(false)} className="text-gray-500 hover:text-gray-700">✕</button></div>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Supplier<select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"><option>Select supplier...</option><option>Fresh Farm Produce</option><option>Quality Meats Ltd</option><option>Beverage Distributors</option></select></label></div>
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Warehouse<select className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"><option>Main Kitchen</option><option>Bar Storage</option><option>Cold Storage</option></select></label></div>
                  <div className="grid grid-cols-2 gap-4">
                    <div><label className="block text-sm font-medium text-gray-700 mb-1">Order Date<input type="date" className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" /></label></div>
                    <div><label className="block text-sm font-medium text-gray-700 mb-1">Expected Delivery<input type="date" className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" /></label></div>
                  </div>
                  <div><label className="block text-sm font-medium text-gray-700 mb-1">Notes<textarea rows={3} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Add any notes..." /></label></div>
                  <div className="border-t pt-4">
                    <div className="flex justify-between items-center mb-3"><h3 className="font-medium">Create From</h3></div>
                    <div className="grid grid-cols-2 gap-3">
                      <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left"><div className="font-medium">📊 Demand Forecast</div><div className="text-sm text-gray-500">Auto-generate from AI predictions</div></button>
                      <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left"><div className="font-medium">⚠️ Low Stock Items</div><div className="text-sm text-gray-500">Items below reorder point</div></button>
                      <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left"><div className="font-medium">📋 Recipe Requirements</div><div className="text-sm text-gray-500">Based on production plan</div></button>
                      <button className="p-4 border-2 border-dashed rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left"><div className="font-medium">✏️ Manual Entry</div><div className="text-sm text-gray-500">Add items manually</div></button>
                    </div>
                  </div>
                </div>
              </div>
              <div className="p-6 border-t flex justify-end gap-2">
                <button onClick={() => setShowCreatePO(false)} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
                <button className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">Continue</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
