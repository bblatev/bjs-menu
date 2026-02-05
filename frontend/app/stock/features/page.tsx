"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL } from '@/lib/api';

// Types
interface StockItem {
  id: number;
  name: string;
  sku?: string;
  quantity: number;
  unit: string;
}

interface Barcode {
  id: number;
  stock_item_id: number;
  barcode_value: string;
  barcode_type: string;
  is_primary: boolean;
  is_active: boolean;
}

interface AutoReorderRule {
  id: number;
  stock_item_id: number;
  reorder_point: number;
  reorder_quantity: number;
  supplier_id?: number;
  priority: string;
  is_active: boolean;
  last_triggered?: string;
}

interface StockBatch {
  id: number;
  stock_item_id: number;
  batch_number: string;
  quantity: number;
  received_date: string;
  expiry_date?: string;
  cost_per_unit?: number;
  is_active: boolean;
}

interface ShrinkageRecord {
  id: number;
  stock_item_id: number;
  quantity: number;
  reason: string;
  value_lost?: number;
  recorded_at: string;
  notes?: string;
}

interface CycleCountSchedule {
  id: number;
  name: string;
  count_type: string;
  frequency_days: number;
  next_count_date?: string;
  is_active: boolean;
}

interface CycleCountTask {
  id: number;
  schedule_id: number;
  status: string;
  started_at?: string;
  completed_at?: string;
  items_counted: number;
  discrepancies_found: number;
}

interface ReconciliationSession {
  id: number;
  session_name: string;
  status: string;
  started_at: string;
  completed_at?: string;
  total_items: number;
  discrepancies: number;
  total_variance_value?: number;
}

interface UnitConversion {
  id: number;
  from_unit: string;
  to_unit: string;
  conversion_factor: number;
  is_active: boolean;
}

interface SupplierPerformance {
  id: number;
  supplier_id: number;
  supplier_name?: string;
  on_time_delivery_rate: number;
  quality_rating: number;
  average_lead_time_days: number;
  total_orders: number;
  total_value: number;
}

type TabType = "barcodes" | "reorder" | "batches" | "shrinkage" | "counts" | "reconciliation" | "units" | "suppliers";
export default function StockFeaturesPage() {
  const [activeTab, setActiveTab] = useState<TabType>("barcodes");
  const [loading, setLoading] = useState(true);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<StockItem | null>(null);

  // Data states
  const [barcodes, setBarcodes] = useState<Barcode[]>([]);
  const [reorderRules, setReorderRules] = useState<AutoReorderRule[]>([]);
  const [batches, setBatches] = useState<StockBatch[]>([]);
  const [shrinkage, setShrinkage] = useState<ShrinkageRecord[]>([]);
  const [countSchedules, setCountSchedules] = useState<CycleCountSchedule[]>([]);
  const [countTasks, setCountTasks] = useState<CycleCountTask[]>([]);
  const [reconciliations, setReconciliations] = useState<ReconciliationSession[]>([]);
  const [conversions, setConversions] = useState<UnitConversion[]>([]);
  const [supplierPerf, setSupplierPerf] = useState<SupplierPerformance[]>([]);
  const [reorderAlerts, setReorderAlerts] = useState<any[]>([]);

  // Modal states
  const [showBarcodeModal, setShowBarcodeModal] = useState(false);
  const [showReorderModal, setShowReorderModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [showShrinkageModal, setShowShrinkageModal] = useState(false);
  const [showCountModal, setShowCountModal] = useState(false);
  const [showReconcileModal, setShowReconcileModal] = useState(false);
  const [showConversionModal, setShowConversionModal] = useState(false);

  // Form states
  const [barcodeForm, setBarcodeForm] = useState({
    stock_item_id: 0, barcode_value: "", barcode_type: "ean13", is_primary: false
  });

  const [reorderForm, setReorderForm] = useState({
    stock_item_id: 0, reorder_point: 10, reorder_quantity: 50, priority: "medium"
  });

  const [batchForm, setBatchForm] = useState({
    stock_item_id: 0, batch_number: "", quantity: 0, received_date: "", expiry_date: "", cost_per_unit: 0
  });

  const [shrinkageForm, setShrinkageForm] = useState({
    stock_item_id: 0, quantity: 0, reason: "spoilage", notes: ""
  });

  const [countForm, setCountForm] = useState({
    name: "", count_type: "full", frequency_days: 30
  });

  const [reconcileForm, setReconcileForm] = useState({
    session_name: "", notes: ""
  });

  const [conversionForm, setConversionForm] = useState({
    from_unit: "", to_unit: "", conversion_factor: 1
  });

  const getToken = () => localStorage.getItem("access_token");

  useEffect(() => {
    loadStockItems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadTabData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, selectedItem]);

  const loadStockItems = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/stock`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStockItems(data);
        if (data.length > 0) setSelectedItem(data[0]);
      }
    } catch (error) {
      console.error("Error loading stock items:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadTabData = async () => {
    const token = getToken();
    const headers = { Authorization: `Bearer ${token}` };

    try {
      switch (activeTab) {
        case "barcodes":
          if (selectedItem) {
            const res = await fetch(`${API_URL}/inventory-complete/barcodes/item/${selectedItem.id}`, { headers });
            if (res.ok) {
              const data = await res.json();
              setBarcodes(Array.isArray(data) ? data : (data.barcodes || []));
            }
          }
          break;
        case "reorder":
          const rulesRes = await fetch(`${API_URL}/inventory-complete/auto-reorder/rules`, { headers });
          if (rulesRes.ok) {
            const rulesData = await rulesRes.json();
            setReorderRules(Array.isArray(rulesData) ? rulesData : (rulesData.rules || []));
          }
          const alertsRes = await fetch(`${API_URL}/inventory-complete/auto-reorder/alerts`, { headers });
          if (alertsRes.ok) {
            const alertsData = await alertsRes.json();
            setReorderAlerts(Array.isArray(alertsData) ? alertsData : (alertsData.alerts || []));
          }
          break;
        case "batches":
          if (selectedItem) {
            const res = await fetch(`${API_URL}/inventory-complete/batches/item/${selectedItem.id}`, { headers });
            if (res.ok) {
              const data = await res.json();
              setBatches(Array.isArray(data) ? data : (data.batches || []));
            }
          }
          break;
        case "shrinkage":
          const shrinkRes = await fetch(`${API_URL}/inventory-complete/shrinkage`, { headers });
          if (shrinkRes.ok) setShrinkage(await shrinkRes.json());
          break;
        case "counts":
          const schedRes = await fetch(`${API_URL}/inventory-complete/cycle-counts/schedules`, { headers });
          if (schedRes.ok) {
            const schedData = await schedRes.json();
            setCountSchedules(Array.isArray(schedData) ? schedData : (schedData.schedules || []));
          }
          const tasksRes = await fetch(`${API_URL}/inventory-complete/cycle-counts/tasks`, { headers });
          if (tasksRes.ok) {
            const tasksData = await tasksRes.json();
            setCountTasks(Array.isArray(tasksData) ? tasksData : (tasksData.tasks || []));
          }
          break;
        case "reconciliation":
          const reconRes = await fetch(`${API_URL}/inventory-complete/reconciliation/sessions`, { headers });
          if (reconRes.ok) {
            const reconData = await reconRes.json();
            setReconciliations(Array.isArray(reconData) ? reconData : (reconData.sessions || []));
          }
          break;
        case "units":
          const convRes = await fetch(`${API_URL}/inventory-complete/unit-conversions`, { headers });
          if (convRes.ok) {
            const convData = await convRes.json();
            setConversions(Array.isArray(convData) ? convData : (convData.conversions || []));
          }
          break;
        case "suppliers":
          const perfRes = await fetch(`${API_URL}/inventory-complete/supplier-performance`, { headers });
          if (perfRes.ok) setSupplierPerf(await perfRes.json());
          break;
      }
    } catch (error) {
      console.error("Error loading tab data:", error);
    }
  };

  // CRUD Handlers
  const handleCreateBarcode = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/barcodes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(barcodeForm)
      });
      if (res.ok) {
        setShowBarcodeModal(false);
        setBarcodeForm({ stock_item_id: 0, barcode_value: "", barcode_type: "ean13", is_primary: false });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating barcode");
    }
  };

  const handleCreateReorderRule = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/auto-reorder/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(reorderForm)
      });
      if (res.ok) {
        setShowReorderModal(false);
        setReorderForm({ stock_item_id: 0, reorder_point: 10, reorder_quantity: 50, priority: "medium" });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating reorder rule");
    }
  };

  const handleCreateBatch = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/batches`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(batchForm)
      });
      if (res.ok) {
        setShowBatchModal(false);
        setBatchForm({ stock_item_id: 0, batch_number: "", quantity: 0, received_date: "", expiry_date: "", cost_per_unit: 0 });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating batch");
    }
  };

  const handleRecordShrinkage = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/shrinkage/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          stock_item_id: shrinkageForm.stock_item_id,
          quantity_lost: shrinkageForm.quantity,
          reason: shrinkageForm.reason,
          notes: shrinkageForm.notes
        })
      });
      if (res.ok) {
        setShowShrinkageModal(false);
        setShrinkageForm({ stock_item_id: 0, quantity: 0, reason: "spoilage", notes: "" });
        loadTabData();
      }
    } catch (error) {
      alert("Error recording shrinkage");
    }
  };

  const handleCreateCountSchedule = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/cycle-counts/schedules`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(countForm)
      });
      if (res.ok) {
        setShowCountModal(false);
        setCountForm({ name: "", count_type: "full", frequency_days: 30 });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating schedule");
    }
  };

  const handleStartReconciliation = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/reconciliation/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(reconcileForm)
      });
      if (res.ok) {
        setShowReconcileModal(false);
        setReconcileForm({ session_name: "", notes: "" });
        loadTabData();
      }
    } catch (error) {
      alert("Error starting reconciliation");
    }
  };

  const handleCreateConversion = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/unit-conversions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(conversionForm)
      });
      if (res.ok) {
        setShowConversionModal(false);
        setConversionForm({ from_unit: "", to_unit: "", conversion_factor: 1 });
        loadTabData();
      }
    } catch (error) {
      alert("Error creating conversion");
    }
  };

  const handleProcessReorders = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/inventory-complete/auto-reorder/process`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const result = await res.json();
        alert(`Processed ${result.orders_created || 0} reorder requests`);
        loadTabData();
      }
    } catch (error) {
      alert("Error processing reorders");
    }
  };

  const getItemName = (id: number) => {
    const item = stockItems.find(i => i.id === id);
    return typeof item?.name === 'object' ? (item?.name as any)?.en || (item?.name as any)?.bg : item?.name || `Item #${id}`;
  };

  const tabs = [
    { id: "barcodes", label: "Barcodes", icon: "📊", desc: "Scan & generate" },
    { id: "reorder", label: "Auto-Reorder", icon: "🔄", desc: "Reorder rules" },
    { id: "batches", label: "FIFO/FEFO", icon: "📦", desc: "Batch tracking" },
    { id: "shrinkage", label: "Shrinkage", icon: "📉", desc: "Loss tracking" },
    { id: "counts", label: "Cycle Counts", icon: "📋", desc: "Scheduled counts" },
    { id: "reconciliation", label: "Reconcile", icon: "✅", desc: "Stock matching" },
    { id: "units", label: "Units", icon: "⚖️", desc: "Conversions" },
    { id: "suppliers", label: "Suppliers", icon: "🏭", desc: "Performance" },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Inventory Features</h1>
          <p className="text-gray-500 mt-1">Advanced inventory management: barcodes, auto-reorder, FIFO/FEFO, and more</p>
        </div>

        {/* Tabs */}
        <div className="grid grid-cols-8 gap-2 mb-6">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`p-3 rounded-xl text-center transition-all ${
                activeTab === tab.id
                  ? "bg-purple-600 text-white shadow-lg"
                  : "bg-white text-gray-700 hover:bg-gray-100 shadow"
              }`}
            >
              <div className="text-xl mb-1">{tab.icon}</div>
              <div className="font-medium text-xs">{tab.label}</div>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          {/* Barcodes Tab */}
          {activeTab === "barcodes" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-4">
                  <h2 className="text-xl font-semibold">Barcodes & QR Codes</h2>
                  <select
                    value={selectedItem?.id || ""}
                    onChange={(e) => setSelectedItem(stockItems.find(i => i.id === Number(e.target.value)) || null)}
                    className="px-4 py-2 border rounded-lg"
                  >
                    {stockItems.map(item => (
                      <option key={item.id} value={item.id}>{getItemName(item.id)}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => { setBarcodeForm({...barcodeForm, stock_item_id: selectedItem?.id || 0}); setShowBarcodeModal(true); }}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  + Add Barcode
                </button>
              </div>

              {barcodes.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">📊</div>
                  <p>No barcodes for this item. Add EAN, UPC, or QR codes.</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  {barcodes.map(b => (
                    <div key={b.id} className={`p-4 rounded-xl border-2 ${b.is_primary ? "border-purple-500 bg-purple-50" : "border-gray-200"}`}>
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs px-2 py-1 bg-gray-100 rounded uppercase">{b.barcode_type}</span>
                        {b.is_primary && <span className="text-xs px-2 py-1 bg-purple-500 text-white rounded">Primary</span>}
                      </div>
                      <p className="font-mono text-lg font-bold">{b.barcode_value}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Auto-Reorder Tab */}
          {activeTab === "reorder" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Auto-Reorder Rules</h2>
                <div className="flex gap-3">
                  <button
                    onClick={handleProcessReorders}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    Process Reorders
                  </button>
                  <button
                    onClick={() => setShowReorderModal(true)}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                  >
                    + Add Rule
                  </button>
                </div>
              </div>

              {/* Alerts */}
              {reorderAlerts.length > 0 && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                  <h3 className="font-semibold text-red-700 mb-2">Reorder Alerts ({reorderAlerts.length})</h3>
                  <div className="space-y-2">
                    {reorderAlerts.slice(0, 5).map((alert, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span>{getItemName(alert.stock_item_id)}</span>
                        <span className="text-red-600">Below reorder point!</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {reorderRules.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">🔄</div>
                  <p>No reorder rules. Set up automatic reordering for low stock items.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {reorderRules.map(rule => (
                    <div key={rule.id} className="p-4 rounded-xl bg-gray-50 flex items-center justify-between">
                      <div>
                        <p className="font-medium">{getItemName(rule.stock_item_id)}</p>
                        <p className="text-sm text-gray-500">
                          Reorder at {rule.reorder_point} units | Order {rule.reorder_quantity} units
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded text-xs capitalize ${
                          rule.priority === 'critical' ? 'bg-red-100 text-red-700' :
                          rule.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {rule.priority}
                        </span>
                        <span className={`w-3 h-3 rounded-full ${rule.is_active ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* FIFO/FEFO Batches Tab */}
          {activeTab === "batches" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-4">
                  <h2 className="text-xl font-semibold">Batch Tracking (FIFO/FEFO)</h2>
                  <select
                    value={selectedItem?.id || ""}
                    onChange={(e) => setSelectedItem(stockItems.find(i => i.id === Number(e.target.value)) || null)}
                    className="px-4 py-2 border rounded-lg"
                  >
                    {stockItems.map(item => (
                      <option key={item.id} value={item.id}>{getItemName(item.id)}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => { setBatchForm({...batchForm, stock_item_id: selectedItem?.id || 0}); setShowBatchModal(true); }}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  + Add Batch
                </button>
              </div>

              {batches.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">📦</div>
                  <p>No batches for this item. Track expiry dates and manage FIFO/FEFO.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {batches.map((batch, i) => {
                    const isExpiringSoon = batch.expiry_date && new Date(batch.expiry_date) < new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
                    return (
                      <div key={batch.id} className={`p-4 rounded-xl border-2 ${i === 0 ? 'border-green-500 bg-green-50' : 'border-gray-200'} ${isExpiringSoon ? 'border-red-500 bg-red-50' : ''}`}>
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold">{batch.batch_number}</span>
                              {i === 0 && <span className="text-xs px-2 py-1 bg-green-500 text-white rounded">Use First</span>}
                              {isExpiringSoon && <span className="text-xs px-2 py-1 bg-red-500 text-white rounded">Expiring Soon!</span>}
                            </div>
                            <p className="text-sm text-gray-500">Received: {new Date(batch.received_date).toLocaleDateString()}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-lg">{batch.quantity} units</p>
                            {batch.expiry_date && (
                              <p className={`text-sm ${isExpiringSoon ? 'text-red-600 font-bold' : 'text-gray-500'}`}>
                                Expires: {new Date(batch.expiry_date).toLocaleDateString()}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Shrinkage Tab */}
          {activeTab === "shrinkage" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Shrinkage & Loss Tracking</h2>
                <button
                  onClick={() => setShowShrinkageModal(true)}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                >
                  + Record Loss
                </button>
              </div>

              {/* Summary */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-red-50 border border-red-200">
                  <p className="text-sm text-red-600">Total Losses</p>
                  <p className="text-2xl font-bold text-red-700">{shrinkage.length}</p>
                </div>
                <div className="p-4 rounded-xl bg-orange-50 border border-orange-200">
                  <p className="text-sm text-orange-600">Spoilage</p>
                  <p className="text-2xl font-bold text-orange-700">{shrinkage.filter(s => s.reason === 'spoilage').length}</p>
                </div>
                <div className="p-4 rounded-xl bg-purple-50 border border-purple-200">
                  <p className="text-sm text-purple-600">Theft</p>
                  <p className="text-2xl font-bold text-purple-700">{shrinkage.filter(s => s.reason === 'theft').length}</p>
                </div>
                <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                  <p className="text-sm text-gray-600">Other</p>
                  <p className="text-2xl font-bold text-gray-700">{shrinkage.filter(s => !['spoilage', 'theft'].includes(s.reason)).length}</p>
                </div>
              </div>

              {shrinkage.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">✅</div>
                  <p>No shrinkage recorded. Great inventory management!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {shrinkage.map(s => (
                    <div key={s.id} className="p-4 rounded-xl bg-gray-50 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="text-2xl">
                          {s.reason === 'spoilage' ? '🗑️' : s.reason === 'theft' ? '🚨' : s.reason === 'damage' ? '💔' : '📉'}
                        </div>
                        <div>
                          <p className="font-medium">{getItemName(s.stock_item_id)}</p>
                          <p className="text-sm text-gray-500 capitalize">{s.reason.replace('_', ' ')}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-red-600">-{s.quantity} units</p>
                        <p className="text-xs text-gray-500">{new Date(s.recorded_at).toLocaleString()}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Cycle Counts Tab */}
          {activeTab === "counts" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Cycle Count Schedules</h2>
                <button
                  onClick={() => setShowCountModal(true)}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  + Create Schedule
                </button>
              </div>

              {countSchedules.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">📋</div>
                  <p>No count schedules. Set up regular inventory counts.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {countSchedules.map(schedule => (
                    <div key={schedule.id} className="p-5 rounded-xl border border-gray-200">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="font-semibold">{schedule.name}</h3>
                        <span className={`px-2 py-1 rounded text-xs ${schedule.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {schedule.is_active ? 'Active' : 'Paused'}
                        </span>
                      </div>
                      <div className="text-sm text-gray-500 space-y-1">
                        <p>Type: <span className="capitalize">{schedule.count_type}</span></p>
                        <p>Frequency: Every {schedule.frequency_days} days</p>
                        {schedule.next_count_date && (
                          <p>Next Count: {new Date(schedule.next_count_date).toLocaleDateString()}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {countTasks.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">Recent Count Tasks</h3>
                  <div className="space-y-2">
                    {countTasks.map(task => (
                      <div key={task.id} className="p-3 rounded-lg bg-gray-50 flex items-center justify-between">
                        <div>
                          <span className={`px-2 py-1 rounded text-xs capitalize ${
                            task.status === 'completed' ? 'bg-green-100 text-green-700' :
                            task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-500'
                          }`}>
                            {task.status}
                          </span>
                          <span className="ml-3 text-sm">{task.items_counted} items counted</span>
                        </div>
                        {task.discrepancies_found > 0 && (
                          <span className="text-red-600 text-sm">{task.discrepancies_found} discrepancies</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Reconciliation Tab */}
          {activeTab === "reconciliation" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Stock Reconciliation</h2>
                <button
                  onClick={() => setShowReconcileModal(true)}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  + Start Reconciliation
                </button>
              </div>

              {reconciliations.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">✅</div>
                  <p>No reconciliation sessions. Start one to match physical and system stock.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {reconciliations.map(session => (
                    <div key={session.id} className="p-5 rounded-xl border border-gray-200">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h3 className="font-semibold">{session.session_name}</h3>
                          <p className="text-sm text-gray-500">Started: {new Date(session.started_at).toLocaleString()}</p>
                        </div>
                        <span className={`px-3 py-1 rounded text-sm capitalize ${
                          session.status === 'completed' ? 'bg-green-100 text-green-700' :
                          session.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-500'
                        }`}>
                          {session.status}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-center">
                        <div>
                          <p className="text-2xl font-bold">{session.total_items}</p>
                          <p className="text-sm text-gray-500">Items</p>
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-red-600">{session.discrepancies}</p>
                          <p className="text-sm text-gray-500">Discrepancies</p>
                        </div>
                        <div>
                          <p className="text-2xl font-bold text-orange-600">
                            {session.total_variance_value?.toFixed(2) || '0.00'} EUR
                          </p>
                          <p className="text-sm text-gray-500">Variance</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Unit Conversions Tab */}
          {activeTab === "units" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Unit Conversions</h2>
                <button
                  onClick={() => setShowConversionModal(true)}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  + Add Conversion
                </button>
              </div>

              {conversions.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">⚖️</div>
                  <p>No unit conversions. Define how units relate to each other.</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  {conversions.map(conv => (
                    <div key={conv.id} className="p-4 rounded-xl bg-gray-50 text-center">
                      <div className="flex items-center justify-center gap-3">
                        <span className="font-bold text-lg">{conv.from_unit}</span>
                        <span className="text-gray-400">→</span>
                        <span className="font-bold text-lg">{conv.to_unit}</span>
                      </div>
                      <p className="text-2xl font-bold text-purple-600 mt-2">{conv.conversion_factor}x</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Supplier Performance Tab */}
          {activeTab === "suppliers" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold">Supplier Performance</h2>
              </div>

              {supplierPerf.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-3">🏭</div>
                  <p>No supplier performance data yet. Data will appear after receiving orders.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {supplierPerf.map(perf => (
                    <div key={perf.id} className="p-5 rounded-xl border border-gray-200">
                      <div className="flex justify-between items-start mb-4">
                        <h3 className="font-semibold text-lg">{perf.supplier_name || `Supplier #${perf.supplier_id}`}</h3>
                        <span className="text-sm text-gray-500">{perf.total_orders} orders</span>
                      </div>
                      <div className="grid grid-cols-4 gap-4">
                        <div className="text-center">
                          <div className={`text-2xl font-bold ${perf.on_time_delivery_rate >= 90 ? 'text-green-600' : perf.on_time_delivery_rate >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
                            {perf.on_time_delivery_rate.toFixed(0)}%
                          </div>
                          <p className="text-sm text-gray-500">On-Time</p>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-purple-600">{perf.quality_rating.toFixed(1)}/5</div>
                          <p className="text-sm text-gray-500">Quality</p>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold">{perf.average_lead_time_days.toFixed(1)}d</div>
                          <p className="text-sm text-gray-500">Lead Time</p>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-green-600">{perf.total_value.toFixed(0)} EUR</div>
                          <p className="text-sm text-gray-500">Total Value</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Barcode Modal */}
      <AnimatePresence>
        {showBarcodeModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-white rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Add Barcode</h3>
              <div className="space-y-4">
                <select value={barcodeForm.stock_item_id} onChange={e => setBarcodeForm({...barcodeForm, stock_item_id: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg">
                  <option value={0}>Select item...</option>
                  {stockItems.map(item => <option key={item.id} value={item.id}>{getItemName(item.id)}</option>)}
                </select>
                <input placeholder="Barcode Value" value={barcodeForm.barcode_value} onChange={e => setBarcodeForm({...barcodeForm, barcode_value: e.target.value})} className="w-full px-4 py-2 border rounded-lg font-mono" />
                <select value={barcodeForm.barcode_type} onChange={e => setBarcodeForm({...barcodeForm, barcode_type: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="ean13">EAN-13</option>
                  <option value="ean8">EAN-8</option>
                  <option value="upc">UPC</option>
                  <option value="qr">QR Code</option>
                  <option value="code128">Code 128</option>
                </select>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={barcodeForm.is_primary} onChange={e => setBarcodeForm({...barcodeForm, is_primary: e.target.checked})} />
                  <span>Primary barcode</span>
                </label>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowBarcodeModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateBarcode} className="flex-1 py-2 bg-purple-600 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Reorder Rule Modal */}
      <AnimatePresence>
        {showReorderModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-white rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Create Reorder Rule</h3>
              <div className="space-y-4">
                <select value={reorderForm.stock_item_id} onChange={e => setReorderForm({...reorderForm, stock_item_id: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg">
                  <option value={0}>Select item...</option>
                  {stockItems.map(item => <option key={item.id} value={item.id}>{getItemName(item.id)}</option>)}
                </select>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-500">Reorder Point</label>
                    <input type="number" value={reorderForm.reorder_point} onChange={e => setReorderForm({...reorderForm, reorder_point: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500">Order Quantity</label>
                    <input type="number" value={reorderForm.reorder_quantity} onChange={e => setReorderForm({...reorderForm, reorder_quantity: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                  </div>
                </div>
                <select value={reorderForm.priority} onChange={e => setReorderForm({...reorderForm, priority: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="low">Low Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="high">High Priority</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowReorderModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateReorderRule} className="flex-1 py-2 bg-purple-600 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Batch Modal */}
      <AnimatePresence>
        {showBatchModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-white rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Add Batch</h3>
              <div className="space-y-4">
                <select value={batchForm.stock_item_id} onChange={e => setBatchForm({...batchForm, stock_item_id: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg">
                  <option value={0}>Select item...</option>
                  {stockItems.map(item => <option key={item.id} value={item.id}>{getItemName(item.id)}</option>)}
                </select>
                <input placeholder="Batch Number" value={batchForm.batch_number} onChange={e => setBatchForm({...batchForm, batch_number: e.target.value})} className="w-full px-4 py-2 border rounded-lg" />
                <input type="number" placeholder="Quantity" value={batchForm.quantity || ""} onChange={e => setBatchForm({...batchForm, quantity: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg" />
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-500">Received Date</label>
                    <input type="date" value={batchForm.received_date} onChange={e => setBatchForm({...batchForm, received_date: e.target.value})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                  </div>
                  <div>
                    <label className="text-sm text-gray-500">Expiry Date</label>
                    <input type="date" value={batchForm.expiry_date} onChange={e => setBatchForm({...batchForm, expiry_date: e.target.value})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                  </div>
                </div>
                <input type="number" step="0.01" placeholder="Cost per Unit" value={batchForm.cost_per_unit || ""} onChange={e => setBatchForm({...batchForm, cost_per_unit: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg" />
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowBatchModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateBatch} className="flex-1 py-2 bg-purple-600 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Shrinkage Modal */}
      <AnimatePresence>
        {showShrinkageModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-white rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Record Shrinkage</h3>
              <div className="space-y-4">
                <select value={shrinkageForm.stock_item_id} onChange={e => setShrinkageForm({...shrinkageForm, stock_item_id: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg">
                  <option value={0}>Select item...</option>
                  {stockItems.map(item => <option key={item.id} value={item.id}>{getItemName(item.id)}</option>)}
                </select>
                <input type="number" placeholder="Quantity Lost" value={shrinkageForm.quantity || ""} onChange={e => setShrinkageForm({...shrinkageForm, quantity: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg" />
                <select value={shrinkageForm.reason} onChange={e => setShrinkageForm({...shrinkageForm, reason: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="spoilage">Spoilage</option>
                  <option value="theft">Theft</option>
                  <option value="damage">Damage</option>
                  <option value="expired">Expired</option>
                  <option value="count_error">Count Error</option>
                  <option value="other">Other</option>
                </select>
                <textarea placeholder="Notes" value={shrinkageForm.notes} onChange={e => setShrinkageForm({...shrinkageForm, notes: e.target.value})} className="w-full px-4 py-2 border rounded-lg" rows={2} />
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowShrinkageModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleRecordShrinkage} className="flex-1 py-2 bg-red-600 text-white rounded-lg">Record Loss</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Count Schedule Modal */}
      <AnimatePresence>
        {showCountModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-white rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Create Count Schedule</h3>
              <div className="space-y-4">
                <input placeholder="Schedule Name" value={countForm.name} onChange={e => setCountForm({...countForm, name: e.target.value})} className="w-full px-4 py-2 border rounded-lg" />
                <select value={countForm.count_type} onChange={e => setCountForm({...countForm, count_type: e.target.value})} className="w-full px-4 py-2 border rounded-lg">
                  <option value="full">Full Count</option>
                  <option value="category">By Category</option>
                  <option value="abc">ABC Analysis</option>
                  <option value="random">Random Sample</option>
                </select>
                <div>
                  <label className="text-sm text-gray-500">Frequency (days)</label>
                  <input type="number" value={countForm.frequency_days} onChange={e => setCountForm({...countForm, frequency_days: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowCountModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateCountSchedule} className="flex-1 py-2 bg-purple-600 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Reconciliation Modal */}
      <AnimatePresence>
        {showReconcileModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-white rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Start Reconciliation</h3>
              <div className="space-y-4">
                <input placeholder="Session Name" value={reconcileForm.session_name} onChange={e => setReconcileForm({...reconcileForm, session_name: e.target.value})} className="w-full px-4 py-2 border rounded-lg" />
                <textarea placeholder="Notes" value={reconcileForm.notes} onChange={e => setReconcileForm({...reconcileForm, notes: e.target.value})} className="w-full px-4 py-2 border rounded-lg" rows={3} />
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowReconcileModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleStartReconciliation} className="flex-1 py-2 bg-purple-600 text-white rounded-lg">Start</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Conversion Modal */}
      <AnimatePresence>
        {showConversionModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-white rounded-xl p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4">Add Unit Conversion</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <input placeholder="From Unit (e.g., kg)" value={conversionForm.from_unit} onChange={e => setConversionForm({...conversionForm, from_unit: e.target.value})} className="px-4 py-2 border rounded-lg" />
                  <input placeholder="To Unit (e.g., g)" value={conversionForm.to_unit} onChange={e => setConversionForm({...conversionForm, to_unit: e.target.value})} className="px-4 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="text-sm text-gray-500">Conversion Factor (1 from = X to)</label>
                  <input type="number" step="0.001" value={conversionForm.conversion_factor} onChange={e => setConversionForm({...conversionForm, conversion_factor: Number(e.target.value)})} className="w-full px-4 py-2 border rounded-lg mt-1" />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowConversionModal(false)} className="flex-1 py-2 bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateConversion} className="flex-1 py-2 bg-purple-600 text-white rounded-lg">Create</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
