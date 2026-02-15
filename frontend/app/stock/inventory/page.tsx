"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Warehouse {
  id: number;
  name: string;
  code: string;
  warehouse_type: string;
  is_active: boolean;
  is_primary: boolean;
}

interface StockItem {
  id: number;
  name: string;
  sku: string;
  unit: string;
  quantity: number;
  min_quantity?: number;
  unit_cost?: number;
  total_value?: number;
}

interface StockBatch {
  id: number;
  stock_item_id: number;
  warehouse_id: number;
  batch_number: string;
  lot_number?: string;
  quantity: number;
  unit_cost: number;
  manufacture_date?: string;
  expiry_date?: string;
  quality_status: string;
}

interface StockTransfer {
  id: number;
  transfer_number: string;
  from_warehouse_id: number;
  to_warehouse_id: number;
  status: string;
  requested_date: string;
  expected_date?: string;
  items_count?: number;
}

interface StockAdjustment {
  id: number;
  adjustment_number: string;
  warehouse_id: number;
  adjustment_type: string;
  status: string;
  total_items: number;
  total_value_impact: number;
  created_at: string;
}

type TabType = "overview" | "warehouses" | "batches" | "transfers" | "adjustments" | "expiring" | "valuation";
export default function StockInventoryPage() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Data states
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [batches, setBatches] = useState<StockBatch[]>([]);
  const [transfers, setTransfers] = useState<StockTransfer[]>([]);
  const [adjustments, setAdjustments] = useState<StockAdjustment[]>([]);
  const [expiringItems, setExpiringItems] = useState<StockBatch[]>([]);
  const [valuation, setValuation] = useState<any>(null);

  // Selected states
  const [selectedWarehouse, setSelectedWarehouse] = useState<Warehouse | null>(null);

  // Modal states
  const [showWarehouseModal, setShowWarehouseModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showAdjustmentModal, setShowAdjustmentModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);

  // Form states
  const [warehouseForm, setWarehouseForm] = useState({
    name: "",
    code: "",
    warehouse_type: "main",
    is_active: true
  });

  const [transferForm, setTransferForm] = useState({
    from_warehouse_id: 0,
    to_warehouse_id: 0,
    items: [] as { stock_item_id: number; quantity: number }[],
    notes: ""
  });

  const [adjustmentForm, setAdjustmentForm] = useState({
    warehouse_id: 0,
    adjustment_type: "count_variance",
    reason: "",
    items: [] as { stock_item_id: number; counted_quantity: number }[]
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (activeTab === "expiring") {
      fetchExpiringItems();
    } else if (activeTab === "valuation") {
      fetchValuation();
    }
  }, [activeTab]);

  const fetchData = async () => {
    const token = localStorage.getItem("access_token");
    const headers = { Authorization: `Bearer ${token}` };

    try {
      // Fetch warehouses
      const warehousesRes = await fetch(`${API_URL}/warehouses`, { headers });
      if (warehousesRes.ok) {
        const data = await warehousesRes.json();
        setWarehouses(data);
        if (data.length > 0) setSelectedWarehouse(data[0]);
      }

      // Fetch stock items
      const stockRes = await fetch(`${API_URL}/stock`, { headers });
      if (stockRes.ok) setStockItems(await stockRes.json());

      // Fetch batches
      const batchesRes = await fetch(`${API_URL}/stock/batches`, { headers });
      if (batchesRes.ok) setBatches(await batchesRes.json());

      // Fetch transfers
      const transfersRes = await fetch(`${API_URL}/warehouses/transfers`, { headers });
      if (transfersRes.ok) setTransfers(await transfersRes.json());

      // Fetch adjustments
      const adjustmentsRes = await fetch(`${API_URL}/stock/adjustments`, { headers });
      if (adjustmentsRes.ok) setAdjustments(await adjustmentsRes.json());

    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchExpiringItems = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/stock/expiring?days=30`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) setExpiringItems(await res.json());
    } catch (error) {
      console.error("Error fetching expiring items:", error);
    }
  };

  const fetchValuation = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/stock/valuation`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) setValuation(await res.json());
    } catch (error) {
      console.error("Error fetching valuation:", error);
    }
  };

  const handleCreateWarehouse = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/warehouses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(warehouseForm)
      });
      if (res.ok) {
        setShowWarehouseModal(false);
        fetchData();
        setWarehouseForm({ name: "", code: "", warehouse_type: "main", is_active: true });
      }
    } catch (error) {
      console.error("Error creating warehouse:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateTransfer = async () => {
    if (transferForm.from_warehouse_id === transferForm.to_warehouse_id) {
      toast.error("Source and destination warehouses must be different");
      return;
    }
    setSaving(true);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/warehouses/transfers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(transferForm)
      });
      if (res.ok) {
        setShowTransferModal(false);
        fetchData();
      }
    } catch (error) {
      console.error("Error creating transfer:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleCompleteTransfer = async (transferId: number) => {
    if (!confirm("Mark this transfer as completed?")) return;
    try {
      const token = localStorage.getItem("access_token");
      await fetch(`${API_URL}/warehouses/transfers/${transferId}/complete`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        }
      });
      fetchData();
    } catch (error) {
      console.error("Error completing transfer:", error);
    }
  };

  const handleApproveAdjustment = async (adjustmentId: number) => {
    try {
      const token = localStorage.getItem("access_token");
      await fetch(`${API_URL}/stock/adjustments/${adjustmentId}/approve`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchData();
    } catch (error) {
      console.error("Error approving adjustment:", error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "bg-green-600";
      case "pending": return "bg-yellow-600";
      case "in_transit": return "bg-blue-600";
      case "cancelled": return "bg-red-600";
      case "approved": return "bg-green-600";
      case "rejected": return "bg-red-600";
      default: return "bg-gray-600";
    }
  };

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "warehouses", label: "Warehouses", icon: "🏭" },
    { id: "batches", label: "Batch Tracking", icon: "📦" },
    { id: "transfers", label: "Transfers", icon: "🔄" },
    { id: "adjustments", label: "Adjustments", icon: "📝" },
    { id: "expiring", label: "Expiring Soon", icon: "⏰" },
    { id: "valuation", label: "Valuation", icon: "💰" }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white min-h-screen text-gray-900">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Stock & Inventory Management</h1>
          <p className="text-gray-400 mt-1">Multi-warehouse, batch tracking, transfers, and valuations</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowTransferModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
          >
            🔄 New Transfer
          </button>
          <button
            onClick={() => setShowWarehouseModal(true)}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2"
          >
            + Add Warehouse
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Warehouses</div>
          <div className="text-2xl font-bold">{warehouses.length}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Stock Items</div>
          <div className="text-2xl font-bold">{stockItems.length}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Active Batches</div>
          <div className="text-2xl font-bold">{batches.length}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Pending Transfers</div>
          <div className="text-2xl font-bold text-yellow-400">
            {transfers.filter(t => t.status === "pending").length}
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Expiring (30 days)</div>
          <div className="text-2xl font-bold text-red-400">{expiringItems.length}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap transition ${
              activeTab === tab.id
                ? "bg-orange-600"
                : "bg-gray-50 hover:bg-gray-100"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-gray-50 rounded-xl p-6">
        {activeTab === "overview" && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Stock Overview</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-300">
                    <th className="pb-3">Item</th>
                    <th className="pb-3">SKU</th>
                    <th className="pb-3">Quantity</th>
                    <th className="pb-3">Unit</th>
                    <th className="pb-3">Min Level</th>
                    <th className="pb-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {stockItems.slice(0, 20).map((item) => (
                    <tr key={item.id} className="border-b border-gray-300">
                      <td className="py-3 font-medium">{item.name}</td>
                      <td className="py-3 text-gray-400">{item.sku}</td>
                      <td className="py-3">{item.quantity}</td>
                      <td className="py-3">{item.unit}</td>
                      <td className="py-3">{item.min_quantity || "-"}</td>
                      <td className="py-3">
                        {item.min_quantity && item.quantity < item.min_quantity ? (
                          <span className="px-2 py-1 bg-red-600 rounded text-xs">Low Stock</span>
                        ) : (
                          <span className="px-2 py-1 bg-green-600 rounded text-xs">OK</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "warehouses" && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Warehouses</h3>
            <div className="grid grid-cols-3 gap-4">
              {warehouses.map((warehouse) => (
                <div
                  key={warehouse.id}
                  className={`p-4 rounded-lg border-2 ${
                    warehouse.is_primary ? "border-orange-500 bg-gray-100" : "border-gray-200 bg-gray-100"
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h4 className="font-semibold text-lg">{warehouse.name}</h4>
                      <div className="text-sm text-gray-400">Code: {warehouse.code}</div>
                    </div>
                    {warehouse.is_primary && (
                      <span className="px-2 py-1 bg-orange-600 rounded text-xs">Primary</span>
                    )}
                  </div>
                  <div className="flex gap-2 mt-3">
                    <span className={`px-2 py-1 rounded text-xs ${
                      warehouse.is_active ? "bg-green-600" : "bg-red-600"
                    }`}>
                      {warehouse.is_active ? "Active" : "Inactive"}
                    </span>
                    <span className="px-2 py-1 bg-blue-600 rounded text-xs capitalize">
                      {warehouse.warehouse_type}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "batches" && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Batch Tracking</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-300">
                    <th className="pb-3">Batch #</th>
                    <th className="pb-3">Lot #</th>
                    <th className="pb-3">Quantity</th>
                    <th className="pb-3">Unit Cost</th>
                    <th className="pb-3">Expiry Date</th>
                    <th className="pb-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map((batch) => (
                    <tr key={batch.id} className="border-b border-gray-300">
                      <td className="py-3 font-medium">{batch.batch_number}</td>
                      <td className="py-3 text-gray-400">{batch.lot_number || "-"}</td>
                      <td className="py-3">{batch.quantity}</td>
                      <td className="py-3">{(batch.unit_cost? ?? 0).toFixed(2)} лв</td>
                      <td className="py-3">
                        {batch.expiry_date ? (
                          <span className={
                            new Date(batch.expiry_date) < new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
                              ? "text-red-400"
                              : ""
                          }>
                            {new Date(batch.expiry_date).toLocaleDateString()}
                          </span>
                        ) : "-"}
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          batch.quality_status === "approved" ? "bg-green-600" :
                          batch.quality_status === "quarantine" ? "bg-yellow-600" :
                          batch.quality_status === "rejected" ? "bg-red-600" : "bg-gray-600"
                        }`}>
                          {batch.quality_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "transfers" && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Stock Transfers</h3>
            <div className="space-y-4">
              {transfers.map((transfer) => (
                <div key={transfer.id} className="bg-gray-100 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-semibold">{transfer.transfer_number}</div>
                      <div className="text-sm text-gray-400 mt-1">
                        Warehouse #{transfer.from_warehouse_id} → Warehouse #{transfer.to_warehouse_id}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-3 py-1 rounded ${getStatusColor(transfer.status)}`}>
                        {transfer.status}
                      </span>
                      {transfer.status === "pending" && (
                        <button
                          onClick={() => handleCompleteTransfer(transfer.id)}
                          className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded"
                        >
                          Complete
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="text-sm text-gray-400 mt-2">
                    Requested: {new Date(transfer.requested_date).toLocaleDateString()}
                    {transfer.expected_date && ` | Expected: ${new Date(transfer.expected_date).toLocaleDateString()}`}
                  </div>
                </div>
              ))}
              {transfers.length === 0 && (
                <p className="text-gray-400">No transfers found</p>
              )}
            </div>
          </div>
        )}

        {activeTab === "adjustments" && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Stock Adjustments</h3>
            <div className="space-y-4">
              {adjustments.map((adjustment) => (
                <div key={adjustment.id} className="bg-gray-100 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-semibold">{adjustment.adjustment_number}</div>
                      <div className="text-sm text-gray-400 mt-1">
                        Type: {adjustment.adjustment_type} | Items: {adjustment.total_items}
                      </div>
                      <div className="text-sm mt-1">
                        Value Impact: <span className={adjustment.total_value_impact >= 0 ? "text-green-400" : "text-red-400"}>
                          {adjustment.total_value_impact >= 0 ? "+" : ""}{(adjustment.total_value_impact ?? 0).toFixed(2)} лв
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-3 py-1 rounded ${getStatusColor(adjustment.status)}`}>
                        {adjustment.status}
                      </span>
                      {adjustment.status === "pending" && (
                        <button
                          onClick={() => handleApproveAdjustment(adjustment.id)}
                          className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded"
                        >
                          Approve
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {adjustments.length === 0 && (
                <p className="text-gray-400">No adjustments found</p>
              )}
            </div>
          </div>
        )}

        {activeTab === "expiring" && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Expiring Items (Next 30 Days)</h3>
            {expiringItems.length === 0 ? (
              <p className="text-gray-400">No items expiring soon</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-300">
                      <th className="pb-3">Batch #</th>
                      <th className="pb-3">Item</th>
                      <th className="pb-3">Quantity</th>
                      <th className="pb-3">Expiry Date</th>
                      <th className="pb-3">Days Left</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expiringItems.map((batch) => {
                      const daysLeft = batch.expiry_date
                        ? Math.ceil((new Date(batch.expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
                        : null;
                      return (
                        <tr key={batch.id} className="border-b border-gray-300">
                          <td className="py-3 font-medium">{batch.batch_number}</td>
                          <td className="py-3">Item #{batch.stock_item_id}</td>
                          <td className="py-3">{batch.quantity}</td>
                          <td className="py-3">{batch.expiry_date ? new Date(batch.expiry_date).toLocaleDateString() : "-"}</td>
                          <td className="py-3">
                            {daysLeft !== null && (
                              <span className={`font-bold ${
                                daysLeft <= 7 ? "text-red-400" :
                                daysLeft <= 14 ? "text-yellow-400" : "text-gray-400"
                              }`}>
                                {daysLeft} days
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === "valuation" && (
          <div>
            <h3 className="text-xl font-semibold mb-4">Stock Valuation</h3>
            {valuation ? (
              <div className="grid grid-cols-3 gap-6">
                <div className="bg-gray-100 rounded-lg p-6 text-center">
                  <div className="text-gray-400 text-sm mb-2">Total Stock Value (FIFO)</div>
                  <div className="text-3xl font-bold text-green-400">
                    {(valuation.total_value? ?? 0).toFixed(2) || "0.00"} лв
                  </div>
                </div>
                <div className="bg-gray-100 rounded-lg p-6 text-center">
                  <div className="text-gray-400 text-sm mb-2">Total Items</div>
                  <div className="text-3xl font-bold">
                    {valuation.total_items || stockItems.length}
                  </div>
                </div>
                <div className="bg-gray-100 rounded-lg p-6 text-center">
                  <div className="text-gray-400 text-sm mb-2">Average Item Value</div>
                  <div className="text-3xl font-bold text-orange-400">
                    {(valuation.avg_value? ?? 0).toFixed(2) || "0.00"} лв
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-400">Loading valuation data...</p>
            )}
          </div>
        )}
      </div>

      {/* Warehouse Modal */}
      <AnimatePresence>
        {showWarehouseModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowWarehouseModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Add Warehouse</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name</label>
                  <input
                    type="text"
                    value={warehouseForm.name}
                    onChange={(e) => setWarehouseForm({ ...warehouseForm, name: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    placeholder="Main Kitchen Storage"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Code</label>
                  <input
                    type="text"
                    value={warehouseForm.code}
                    onChange={(e) => setWarehouseForm({ ...warehouseForm, code: e.target.value.toUpperCase() })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    placeholder="WH-MAIN"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Type</label>
                  <select
                    value={warehouseForm.warehouse_type}
                    onChange={(e) => setWarehouseForm({ ...warehouseForm, warehouse_type: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                  >
                    <option value="main">Main</option>
                    <option value="satellite">Satellite</option>
                    <option value="cold_storage">Cold Storage</option>
                    <option value="dry_storage">Dry Storage</option>
                    <option value="prep">Prep Area</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowWarehouseModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateWarehouse}
                  disabled={saving || !warehouseForm.name || !warehouseForm.code}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Creating..." : "Create"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Transfer Modal */}
      <AnimatePresence>
        {showTransferModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowTransferModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">Create Stock Transfer</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">From Warehouse</label>
                    <select
                      value={transferForm.from_warehouse_id}
                      onChange={(e) => setTransferForm({ ...transferForm, from_warehouse_id: parseInt(e.target.value) })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    >
                      <option value={0}>Select...</option>
                      {warehouses.map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">To Warehouse</label>
                    <select
                      value={transferForm.to_warehouse_id}
                      onChange={(e) => setTransferForm({ ...transferForm, to_warehouse_id: parseInt(e.target.value) })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    >
                      <option value={0}>Select...</option>
                      {warehouses.map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Notes</label>
                  <textarea
                    value={transferForm.notes}
                    onChange={(e) => setTransferForm({ ...transferForm, notes: e.target.value })}
                    className="w-full p-2 bg-gray-100 rounded-lg"
                    rows={2}
                    placeholder="Optional notes..."
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowTransferModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateTransfer}
                  disabled={saving || !transferForm.from_warehouse_id || !transferForm.to_warehouse_id}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Creating..." : "Create Transfer"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
