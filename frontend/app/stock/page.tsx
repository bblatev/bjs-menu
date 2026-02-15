"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface StockItem {
  id: number;
  name: string | { bg?: string; en?: string } | null;
  sku?: string;
  quantity: number;
  unit: string;
  low_stock_threshold: number;
  cost_per_unit?: number;
  is_active: boolean;
  category?: string;
  supplier?: string;
  last_restock?: string;
  expiry_date?: string;
  location?: string;
}

interface Supplier {
  id: string;
  name: string;
  contact: string;
  email: string;
  phone: string;
  lead_time_days: number;
  min_order: number;
}

interface StockMovement {
  id: string;
  item_id: number;
  item_name: string;
  type: string;
  quantity: number;
  reason: string;
  date: string;
  user: string;
}

interface StockAlert {
  id: string;
  item_id: number;
  item_name: string;
  type: 'low_stock' | 'expiring' | 'out_of_stock';
  message: string;
  created_at: string;
  acknowledged: boolean;
}

export default function StockPage() {
  const [items, setItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'inventory' | 'movements' | 'suppliers' | 'alerts'>('inventory');
  const [showModal, setShowModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showMovementModal, setShowMovementModal] = useState(false);
  const [showItemDetail, setShowItemDetail] = useState<StockItem | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterLowStock, setFilterLowStock] = useState(false);
  const [filterCategory, setFilterCategory] = useState("all");
  const [importData, setImportData] = useState("");
  const [importResult, setImportResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    name: "",
    sku: "",
    quantity: 0,
    unit: "kg",
    low_stock_threshold: 10,
    cost_per_unit: 0,
    category: "ingredients",
    supplier: "",
    location: "",
  });

  const [movementForm, setMovementForm] = useState({
    item_id: 0,
    type: 'in' as 'in' | 'out' | 'adjustment' | 'waste',
    quantity: 0,
    reason: '',
  });

  // Data states for movements, suppliers, and alerts - fetched from API
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [alerts, setAlerts] = useState<StockAlert[]>([]);
  const [categories, setCategories] = useState<string[]>(['all']);

  useEffect(() => {
    loadStock();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, filterLowStock, filterCategory]);

  useEffect(() => {
    loadMovements();
    loadSuppliers();
    loadAlerts();
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `${API_URL}/stock/categories`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        const categoryNames = data.map((c: any) => typeof c === 'string' ? c : (c.name || c.category || ''));
        setCategories(['all', ...categoryNames]);
      } else {
        // Fallback to default categories
        setCategories(['all', 'ingredients', 'beverages', 'dry goods', 'frozen', 'dairy', 'produce', 'meat', 'seafood']);
      }
    } catch (error) {
      // Fallback to default categories on error
      setCategories(['all', 'ingredients', 'beverages', 'dry goods', 'frozen', 'dairy', 'produce', 'meat', 'seafood']);
    }
  };

  const loadStock = async () => {
    try {
      const token = localStorage.getItem("access_token");
      let url = `${API_URL}/stock/`;
      const params = new URLSearchParams();
      if (searchTerm) params.append("search", searchTerm);
      if (filterLowStock) params.append("low_stock_only", "true");
      if (filterCategory !== 'all') params.append("category", filterCategory);
      if (params.toString()) url += `?${params.toString()}`;

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        const raw = Array.isArray(data) ? data : (data.items || data.stock || []);
        // Map backend field names to frontend interface
        setItems(raw.map((item: any) => ({
          ...item,
          low_stock_threshold: item.low_stock_threshold ?? item.min_stock ?? item.par_level ?? 0,
          cost_per_unit: item.cost_per_unit ?? item.cost_price ?? 0,
          is_active: item.is_active ?? true,
        })));
      } else {
        setItems([]);
      }
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const loadMovements = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `${API_URL}/stock/movements/`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        const movementList = Array.isArray(data) ? data : (data.movements || []);
        setMovements(movementList.map((m: any) => ({
          id: String(m.id),
          item_id: m.product_id || m.stock_item_id || m.item_id,
          item_name: m.product_name || m.stock_item_name || m.item_name || 'Item #' + (m.product_id || ''),
          type: m.reason || m.movement_type || m.type || 'adjustment',
          quantity: m.qty_delta != null ? m.qty_delta : m.quantity,
          reason: m.notes || m.reason || '',
          date: m.timestamp || m.created_at || m.date,
          user: m.created_by_name || m.created_by || m.user || 'System',
        })));
      } else {
        setMovements([]);
      }
    } catch {
      setMovements([]);
    }
  };

  const loadSuppliers = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `${API_URL}/suppliers/`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setSuppliers(data.map((s: { id: number; name?: string; company_name?: string; contact_name?: string; contact_person?: string; email?: string; phone?: string; phone_number?: string; lead_time_days?: number; delivery_days?: number; min_order?: number; minimum_order?: number }) => ({
          id: String(s.id),
          name: s.name || s.company_name || '',
          contact: s.contact_name || s.contact_person || '',
          email: s.email || '',
          phone: s.phone || s.phone_number || '',
          lead_time_days: s.lead_time_days || s.delivery_days || 0,
          min_order: s.min_order || s.minimum_order || 0,
        })));
      } else {
        setSuppliers([]);
      }
    } catch {
      setSuppliers([]);
    }
  };

  const loadAlerts = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `${API_URL}/stock/alerts/`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        const alertList = Array.isArray(data) ? data : (data.alerts || []);
        setAlerts(alertList.map((a: any, idx: number) => ({
          id: String(a.id || idx),
          item_id: a.product_id || a.stock_item_id || a.item_id,
          item_name: a.product_name || a.stock_item_name || a.item_name || 'Unknown Item',
          type: a.type || a.alert_type || 'low_stock',
          message: a.message || a.description || '',
          created_at: a.created_at || new Date().toISOString(),
          acknowledged: a.acknowledged || a.is_acknowledged || false,
        })));
      } else {
        setAlerts([]);
      }
    } catch {
      setAlerts([]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");

    try {
      const params = new URLSearchParams();
      params.append("name", form.name);
      if (form.quantity) params.append("quantity", String(form.quantity));
      if (form.unit) params.append("unit", form.unit);
      if (form.cost_per_unit) params.append("cost_price", String(form.cost_per_unit));
      if (form.low_stock_threshold) params.append("par_level", String(form.low_stock_threshold));
      if (form.sku) params.append("barcode", form.sku);

      const response = await fetch(
        `${API_URL}/stock/?${params.toString()}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        setShowModal(false);
        setForm({ name: "", sku: "", quantity: 0, unit: "kg", low_stock_threshold: 10, cost_per_unit: 0, category: "ingredients", supplier: "", location: "" });
        loadStock();
        toast.success("Item created successfully");
      } else {
        const err = await response.json().catch(() => null);
        toast.error(err?.detail || "Failed to create item");
      }
    } catch {
      toast.error("Error creating item");
    }
  };

  const handleMovementSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");

    try {
      // Backend expects query params: product_id, quantity (signed), reason, notes
      const qty = movementForm.type === 'out' || movementForm.type === 'waste'
        ? -Math.abs(movementForm.quantity)
        : Math.abs(movementForm.quantity);

      const params = new URLSearchParams();
      params.append("product_id", String(movementForm.item_id));
      params.append("quantity", String(qty));
      params.append("reason", movementForm.type);
      if (movementForm.reason) params.append("notes", movementForm.reason);

      const response = await fetch(
        `${API_URL}/stock/movements/?${params.toString()}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        setShowMovementModal(false);
        setMovementForm({ item_id: 0, type: 'in', quantity: 0, reason: '' });
        loadStock();
        loadMovements();
        toast.success("Movement recorded");
      } else {
        const err = await response.json().catch(() => null);
        toast.error(err?.detail || "Failed to record movement");
      }
    } catch {
      toast.error("Error recording movement");
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setImportData(text);
    };
    reader.readAsText(file);
  };

  const parseCSV = (csv: string): any[] => {
    const lines = csv.trim().split("\n");
    if (lines.length < 2) return [];

    const headers = lines[0].split(",").map(h => h.trim().toLowerCase());
    const items = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(",").map(v => v.trim());
      const item: any = {};

      headers.forEach((header, idx) => {
        item[header] = values[idx];
      });

      items.push(item);
    }

    return items;
  };

  const handleImport = async () => {
    const token = localStorage.getItem("access_token");

    try {
      if (!importData.trim()) {
        toast.error("No CSV data to import");
        return;
      }

      // Create a CSV file from the text data and send as FormData
      const blob = new Blob([importData], { type: "text/csv" });
      const file = new File([blob], "stock_import.csv", { type: "text/csv" });
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API_URL}/stock/import`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      if (response.ok) {
        const result = await response.json();
        setImportResult(result);
        loadStock();
      } else {
        const err = await response.json().catch(() => null);
        toast.error(err?.detail || "Import failed");
      }
    } catch (error) {
      toast.error("Error importing data");
    }
  };

  const handleExport = async () => {
    const token = localStorage.getItem("access_token");

    try {
      const response = await fetch(
        `${API_URL}/stock/export`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        // Backend returns CSV text directly with text/csv content type
        const csvText = await response.text();

        const blob = new Blob([csvText], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `stock_export_${new Date().toISOString().split("T")[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        toast.error("Export failed");
      }
    } catch (error) {
      toast.error("Error exporting data");
    }
  };

  const getStatus = (item: StockItem) => {
    if (item.quantity === 0) return { label: "Out of Stock", color: "bg-red-100 text-red-800" };
    if (item.quantity <= item.low_stock_threshold) return { label: "Low Stock", color: "bg-yellow-100 text-yellow-800" };
    return { label: "In Stock", color: "bg-green-100 text-green-800" };
  };

  const getMovementTypeStyle = (type: string) => {
    switch (type) {
      case 'in':
      case 'purchase':
      case 'receive':
        return 'bg-green-100 text-green-800';
      case 'out':
      case 'sale':
        return 'bg-blue-100 text-blue-800';
      case 'adjustment':
        return 'bg-purple-100 text-purple-800';
      case 'waste':
      case 'damage':
        return 'bg-red-100 text-red-800';
      case 'transfer_in':
        return 'bg-teal-100 text-teal-800';
      case 'transfer_out':
        return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getAlertTypeStyle = (type: string) => {
    switch (type) {
      case 'low_stock': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'expiring': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'out_of_stock': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getItemName = (item: StockItem) => {
    if (typeof item.name === 'object' && item.name) {
      return item.name.bg || item.name.en || 'Item';
    }
    return String(item.name || 'Item');
  };

  // Stats calculations
  const totalItems = items.length;
  const lowStockItems = items.filter(i => i.quantity > 0 && i.quantity <= i.low_stock_threshold).length;
  const outOfStockItems = items.filter(i => i.quantity === 0).length;
  const totalValue = items.reduce((sum, i) => sum + (i.quantity * (i.cost_per_unit || 0)), 0);

  const tabs = [
    { id: 'inventory', label: 'Inventory', icon: '📦' },
    { id: 'movements', label: 'Movements', icon: '🔄' },
    { id: 'suppliers', label: 'Suppliers', icon: '🏭' },
    { id: 'alerts', label: 'Alerts', icon: '🔔', badge: alerts.filter(a => !a.acknowledged).length },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading stock data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Stock Management</h1>
            <p className="text-gray-500 mt-1">Track inventory, movements, and suppliers</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => window.location.href = '/stock/features'}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-xl hover:from-purple-700 hover:to-purple-800 transition-colors flex items-center gap-2 shadow-sm"
            >
              <span>All Features</span>
            </button>
            <button
              onClick={() => setShowImportModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
            >
              Import CSV
            </button>
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors shadow-sm"
            >
              Export CSV
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="px-6 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors font-medium shadow-sm"
            >
              + Add Item
            </button>
          </div>
        </div>

        {/* Advanced Features Quick Links */}
        <div className="grid grid-cols-4 md:grid-cols-8 gap-2 mb-4">
          <button onClick={() => window.location.href = '/stock/features'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">📊</span>
            <p className="text-purple-700 text-xs mt-1">Barcodes</p>
          </button>
          <button onClick={() => window.location.href = '/stock/features'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">🔄</span>
            <p className="text-purple-700 text-xs mt-1">Auto-Reorder</p>
          </button>
          <button onClick={() => window.location.href = '/stock/features'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">📦</span>
            <p className="text-purple-700 text-xs mt-1">FIFO/FEFO</p>
          </button>
          <button onClick={() => window.location.href = '/stock/features'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">📉</span>
            <p className="text-purple-700 text-xs mt-1">Shrinkage</p>
          </button>
          <button onClick={() => window.location.href = '/stock/counts'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">📋</span>
            <p className="text-purple-700 text-xs mt-1">Counts</p>
          </button>
          <button onClick={() => window.location.href = '/stock/features'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">✅</span>
            <p className="text-purple-700 text-xs mt-1">Reconcile</p>
          </button>
          <button onClick={() => window.location.href = '/stock/transfers'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">🚚</span>
            <p className="text-purple-700 text-xs mt-1">Transfers</p>
          </button>
          <button onClick={() => window.location.href = '/stock/waste'} className="bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-xl p-2 text-center transition-colors">
            <span className="text-xl">🗑️</span>
            <p className="text-purple-700 text-xs mt-1">Waste</p>
          </button>
        </div>

        {/* Advanced Analytics Quick Links */}
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-6">
          <button onClick={() => window.location.href = '/stock/par-levels'} className="bg-green-50 hover:bg-green-100 border border-green-200 rounded-xl p-3 text-center transition-colors">
            <span className="text-xl">📏</span>
            <p className="text-green-700 text-xs mt-1 font-medium">Par Levels</p>
          </button>
          <button onClick={() => window.location.href = '/stock/variance'} className="bg-red-50 hover:bg-red-100 border border-red-200 rounded-xl p-3 text-center transition-colors">
            <span className="text-xl">🔍</span>
            <p className="text-red-700 text-xs mt-1 font-medium">Variance</p>
          </button>
          <button onClick={() => window.location.href = '/stock/aging'} className="bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-xl p-3 text-center transition-colors">
            <span className="text-xl">⏳</span>
            <p className="text-orange-700 text-xs mt-1 font-medium">Aging</p>
          </button>
          <button onClick={() => window.location.href = '/stock/forecasting'} className="bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-xl p-3 text-center transition-colors">
            <span className="text-xl">🔮</span>
            <p className="text-blue-700 text-xs mt-1 font-medium">Forecasting</p>
          </button>
          <button onClick={() => window.location.href = '/stock/supplier-performance'} className="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl p-3 text-center transition-colors">
            <span className="text-xl">🏭</span>
            <p className="text-indigo-700 text-xs mt-1 font-medium">Suppliers</p>
          </button>
          <button onClick={() => window.location.href = '/stock/recipe-costs'} className="bg-yellow-50 hover:bg-yellow-100 border border-yellow-200 rounded-xl p-3 text-center transition-colors">
            <span className="text-xl">🍳</span>
            <p className="text-yellow-700 text-xs mt-1 font-medium">Recipes</p>
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Items</p>
                <p className="text-2xl font-bold text-gray-900">{totalItems}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
                📦
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Low Stock</p>
                <p className="text-2xl font-bold text-yellow-600">{lowStockItems}</p>
              </div>
              <div className="w-12 h-12 bg-yellow-100 rounded-xl flex items-center justify-center text-2xl">
                ⚠️
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Out of Stock</p>
                <p className="text-2xl font-bold text-red-600">{outOfStockItems}</p>
              </div>
              <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center text-2xl">
                ❌
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Value</p>
                <p className="text-2xl font-bold text-green-600">{(totalValue || 0).toFixed(2)} EUR</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center text-2xl">
                💰
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 mb-6">
          <div className="flex border-b border-gray-100">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex-1 py-4 px-6 text-sm font-medium transition-colors relative ${
                  activeTab === tab.id
                    ? 'text-orange-600 border-b-2 border-orange-500'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
                {tab.badge && tab.badge > 0 && (
                  <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Inventory Tab */}
          {activeTab === 'inventory' && (
            <div className="p-4">
              {/* Filters */}
              <div className="flex gap-4 mb-4">
                <input
                  type="text"
                  placeholder="Search items..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
                <select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500"
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
                  ))}
                </select>
                <button
                  onClick={() => setFilterLowStock(!filterLowStock)}
                  className={`px-6 py-2 rounded-xl transition-colors ${
                    filterLowStock
                      ? "bg-yellow-500 text-gray-900"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Low Stock Only
                </button>
                <button
                  onClick={() => setShowMovementModal(true)}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
                >
                  Record Movement
                </button>
              </div>

              {/* Table */}
              <div className="overflow-hidden rounded-xl border border-gray-200">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Item</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SKU</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Quantity</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Unit Cost</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Value</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {items.map((item) => {
                      const status = getStatus(item);
                      return (
                        <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-6 py-4">
                            <div className="font-medium text-gray-900">{getItemName(item)}</div>
                            {item.supplier && <div className="text-xs text-gray-500">{item.supplier}</div>}
                          </td>
                          <td className="px-6 py-4 text-gray-500 font-mono text-sm">{item.sku || "-"}</td>
                          <td className="px-6 py-4">
                            <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs capitalize">
                              {item.category || 'uncategorized'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right font-medium text-gray-900">
                            {item.quantity} {item.unit}
                          </td>
                          <td className="px-6 py-4 text-center">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${status.color}`}>
                              {status.label}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right text-gray-600">
                            {item.cost_per_unit ? `${(item.cost_per_unit || 0).toFixed(2)} EUR` : "-"}
                          </td>
                          <td className="px-6 py-4 text-right font-medium text-gray-900">
                            {item.cost_per_unit ? `${((item.quantity * item.cost_per_unit) || 0).toFixed(2)} EUR` : "-"}
                          </td>
                          <td className="px-6 py-4 text-center">
                            <button
                              onClick={() => setShowItemDetail(item)}
                              className="text-orange-600 hover:text-orange-800 font-medium text-sm"
                            >
                              View
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                    {items.length === 0 && (
                      <tr>
                        <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                          No items found. Add your first stock item to get started.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Movements Tab */}
          {activeTab === 'movements' && (
            <div className="p-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Stock Movements History</h3>
                <button
                  onClick={() => setShowMovementModal(true)}
                  className="px-4 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors"
                >
                  + Record Movement
                </button>
              </div>
              <div className="space-y-3">
                {movements.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    No movements recorded yet. Record your first stock movement to get started.
                  </div>
                ) : (
                  movements.map((movement) => (
                    <div key={movement.id} className="bg-gray-50 rounded-xl p-4 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${getMovementTypeStyle(movement.type)}`}>
                          {movement.type}
                        </span>
                        <div>
                          <p className="font-medium text-gray-900">{movement.item_name}</p>
                          <p className="text-sm text-gray-500">{movement.reason}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`font-bold ${movement.quantity > 0 ? 'text-green-600' : movement.type === 'waste' || movement.type === 'damage' ? 'text-red-600' : 'text-blue-600'}`}>
                          {movement.quantity > 0 ? '+' : ''}{movement.quantity}
                        </p>
                        <p className="text-xs text-gray-500">{new Date(movement.date).toLocaleString()} by {movement.user}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Suppliers Tab */}
          {activeTab === 'suppliers' && (
            <div className="p-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Supplier Directory</h3>
                <button className="px-4 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors">
                  + Add Supplier
                </button>
              </div>
              {suppliers.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  No suppliers found. Add your first supplier to get started.
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {suppliers.map((supplier) => (
                    <div key={supplier.id} className="bg-gray-50 rounded-xl p-5 border border-gray-200">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h4 className="font-semibold text-gray-900">{supplier.name}</h4>
                          <p className="text-sm text-gray-500">{supplier.contact}</p>
                        </div>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-lg text-xs">
                          Lead: {supplier.lead_time_days}d
                        </span>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-gray-600">
                          <span>Email:</span>
                          <span className="text-gray-900">{supplier.email}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                          <span>Phone:</span>
                          <span className="text-gray-900">{supplier.phone}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                          <span>Min Order:</span>
                          <span className="text-gray-900">{supplier.min_order} EUR</span>
                        </div>
                      </div>
                      <div className="flex gap-2 mt-4">
                        <button className="flex-1 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition-colors">
                          Edit
                        </button>
                        <button className="flex-1 py-2 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 transition-colors">
                          Order
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="p-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Stock Alerts</h3>
                <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors">
                  Mark All Read
                </button>
              </div>
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`rounded-xl p-4 border ${getAlertTypeStyle(alert.type)} ${alert.acknowledged ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">
                          {alert.type === 'low_stock' ? '⚠️' : alert.type === 'expiring' ? '⏰' : '❌'}
                        </span>
                        <div>
                          <p className="font-medium">{alert.item_name}</p>
                          <p className="text-sm opacity-80">{alert.message}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs opacity-70">{new Date(alert.created_at).toLocaleString()}</p>
                        {!alert.acknowledged && (
                          <button className="text-xs underline mt-1">Acknowledge</button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {alerts.length === 0 && (
                  <div className="text-center py-12 text-gray-500">
                    No alerts at this time.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Item Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Add Stock Item</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    placeholder="Item name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SKU</label>
                    <input
                      type="text"
                      placeholder="SKU code"
                      value={form.sku}
                      onChange={(e) => setForm({ ...form, sku: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                    <select
                      value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500"
                    >
                      {categories.filter(c => c !== 'all').map(cat => (
                        <option key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                    <input
                      type="number"
                      placeholder="0"
                      value={form.quantity}
                      onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
                      required
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
                    <select
                      value={form.unit}
                      onChange={(e) => setForm({ ...form, unit: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500"
                    >
                      <option value="kg">kg</option>
                      <option value="g">g</option>
                      <option value="l">l</option>
                      <option value="ml">ml</option>
                      <option value="pcs">pcs</option>
                      <option value="bottles">bottles</option>
                      <option value="boxes">boxes</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cost per Unit (EUR)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={form.cost_per_unit}
                      onChange={(e) => setForm({ ...form, cost_per_unit: Number(e.target.value) })}
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Low Stock Threshold</label>
                    <input
                      type="number"
                      placeholder="10"
                      value={form.low_stock_threshold}
                      onChange={(e) => setForm({ ...form, low_stock_threshold: Number(e.target.value) })}
                      required
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                  <input
                    type="text"
                    placeholder="Storage location"
                    value={form.location}
                    onChange={(e) => setForm({ ...form, location: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors font-medium"
                  >
                    Create Item
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Movement Modal */}
      <AnimatePresence>
        {showMovementModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Record Stock Movement</h2>
              <form onSubmit={handleMovementSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Item</label>
                  <select
                    value={movementForm.item_id}
                    onChange={(e) => setMovementForm({ ...movementForm, item_id: Number(e.target.value) })}
                    required
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500"
                  >
                    <option value={0}>Select item...</option>
                    {items.map(item => (
                      <option key={item.id} value={(item as any).product_id || item.id}>{getItemName(item)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Movement Type</label>
                  <select
                    value={movementForm.type}
                    onChange={(e) => setMovementForm({ ...movementForm, type: e.target.value as any })}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500"
                  >
                    <option value="in">Stock In (Received)</option>
                    <option value="out">Stock Out (Used)</option>
                    <option value="adjustment">Adjustment</option>
                    <option value="waste">Waste / Spoilage</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                  <input
                    type="number"
                    placeholder="0"
                    value={movementForm.quantity}
                    onChange={(e) => setMovementForm({ ...movementForm, quantity: Number(e.target.value) })}
                    required
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reason / Notes</label>
                  <textarea
                    placeholder="Reason for this movement..."
                    value={movementForm.reason}
                    onChange={(e) => setMovementForm({ ...movementForm, reason: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
                  />
                </div>
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowMovementModal(false)}
                    className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors font-medium"
                  >
                    Record Movement
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Item Detail Modal */}
      <AnimatePresence>
        {showItemDetail && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-xl"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{getItemName(showItemDetail)}</h2>
                  <p className="text-gray-500">{showItemDetail.sku || 'No SKU'}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatus(showItemDetail).color}`}>
                  {getStatus(showItemDetail).label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-sm text-gray-500">Current Stock</p>
                  <p className="text-2xl font-bold text-gray-900">{showItemDetail.quantity} {showItemDetail.unit}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-sm text-gray-500">Total Value</p>
                  <p className="text-2xl font-bold text-green-600">
                    {showItemDetail.cost_per_unit
                      ? `${((showItemDetail.quantity * showItemDetail.cost_per_unit) || 0).toFixed(2)} EUR`
                      : '-'
                    }
                  </p>
                </div>
              </div>

              <div className="space-y-3 mb-6">
                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-gray-500">Unit Cost</span>
                  <span className="font-medium text-gray-900">
                    {showItemDetail.cost_per_unit ? `${(showItemDetail.cost_per_unit || 0).toFixed(2)} EUR` : '-'}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-gray-500">Low Stock Threshold</span>
                  <span className="font-medium text-gray-900">{showItemDetail.low_stock_threshold} {showItemDetail.unit}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-gray-500">Category</span>
                  <span className="font-medium text-gray-900 capitalize">{showItemDetail.category || 'Uncategorized'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-gray-500">Supplier</span>
                  <span className="font-medium text-gray-900">{showItemDetail.supplier || '-'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-gray-500">Location</span>
                  <span className="font-medium text-gray-900">{showItemDetail.location || '-'}</span>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowItemDetail(null)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    setMovementForm({ ...movementForm, item_id: (showItemDetail as any).product_id || showItemDetail.id });
                    setShowItemDetail(null);
                    setShowMovementModal(true);
                  }}
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 transition-colors font-medium"
                >
                  Record Movement
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Import Modal */}
      <AnimatePresence>
        {showImportModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl p-6 max-w-2xl w-full shadow-xl"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Import Stock from CSV</h2>

              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
                <p className="text-blue-800 text-sm mb-2 font-medium">CSV Format (first row = headers):</p>
                <code className="text-xs text-blue-900 block bg-blue-100 p-3 rounded-lg font-mono">
                  name,barcode,unit,min_stock,cost_price,par_level<br/>
                  Vodka,5012345678901,l,2,15.00,5<br/>
                  Tomatoes,5098765432101,kg,1,2.50,3
                </code>
              </div>

              <div className="mb-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full py-4 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-orange-400 hover:text-orange-500 transition-colors"
                >
                  Click to choose CSV file
                </button>
              </div>

              <textarea
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder="Or paste CSV data here..."
                className="w-full h-40 px-4 py-3 border border-gray-200 rounded-xl mb-4 font-mono text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
              />

              {importResult && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-4">
                  <p className="text-green-800 font-medium">
                    Created: {importResult.created} | Updated: {importResult.updated}
                  </p>
                  {importResult.errors?.length > 0 && (
                    <p className="text-red-600 text-sm mt-2">
                      Errors: {importResult.errors.join(", ")}
                    </p>
                  )}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => { setShowImportModal(false); setImportData(""); setImportResult(null); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImport}
                  disabled={!importData}
                  className="flex-1 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  Import Data
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
