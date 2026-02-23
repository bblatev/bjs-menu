'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';

interface InventoryItem {
  id: number;
  name: string;
  category: string;
  currentStock: number;
  unit: string;
  reorderLevel: number;
  optimalStock: number;
  lastRestock: string;
  supplier: string;
  costPerUnit: number;
}

interface InventoryStat {
  label: string;
  value: string;
  subvalue: string;
  color: string;
  icon: string;
}

interface InventoryReportData {
  stats: InventoryStat[];
  inventoryItems: InventoryItem[];
  categories: string[];
}

export default function ReportsInventoryPage() {
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<InventoryReportData | null>(null);

  useEffect(() => {
    loadInventoryReport();
  }, []);

  const loadInventoryReport = async () => {
    setLoading(true);
    try {
      const data = await api.get<InventoryReportData>(`/reports/inventory`);
      setData(data);
    } catch (error) {
      console.error('Error loading inventory report:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const categories = data?.categories || ['all'];

  const getStockStatus = (item: InventoryItem) => {
    if (item.currentStock === 0) return { status: 'out', label: 'Out of Stock', color: 'error' };
    if (item.currentStock <= item.reorderLevel) return { status: 'low', label: 'Low Stock', color: 'warning' };
    if (item.currentStock >= item.optimalStock * 0.8) return { status: 'good', label: 'Good Stock', color: 'success' };
    return { status: 'medium', label: 'Medium Stock', color: 'primary' };
  };

  const getStockPercentage = (item: InventoryItem) => {
    return Math.min((item.currentStock / item.optimalStock) * 100, 100);
  };

  const inventoryItems = data?.inventoryItems || [];

  const filteredItems = inventoryItems.filter(item => {
    if (filterCategory !== 'all' && item.category !== filterCategory) return false;
    if (filterStatus !== 'all') {
      const status = getStockStatus(item).status;
      if (filterStatus === 'low' && status !== 'low' && status !== 'out') return false;
      if (filterStatus === 'good' && status !== 'good') return false;
    }
    if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const lowStockItems = inventoryItems.filter(item => {
    const status = getStockStatus(item).status;
    return status === 'low' || status === 'out';
  });

  const stockByCategory = categories.slice(1).map(cat => {
    const items = inventoryItems.filter(i => i.category === cat);
    const totalValue = items.reduce((sum, i) => sum + (i.currentStock * i.costPerUnit), 0);
    const lowStock = items.filter(i => getStockStatus(i).status === 'low' || getStockStatus(i).status === 'out').length;
    return { category: cat, items: items.length, value: totalValue, lowStock };
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📦</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Inventory Data</h2>
          <p className="text-surface-600 mb-4">Unable to load inventory report. Please try again later.</p>
          <button
            onClick={loadInventoryReport}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/reports" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-3xl font-display font-bold text-surface-900">Inventory Reports</h1>
            <p className="text-surface-500 mt-1">Stock levels, reorder alerts, and inventory value</p>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        {(data.stats || []).map((stat, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">{stat.label}</p>
              <span className="text-2xl">{stat.icon}</span>
            </div>
            <p className={`text-2xl font-display font-bold text-${stat.color}-600`}>{stat.value}</p>
            <p className="text-xs text-surface-500 mt-1">{stat.subvalue}</p>
          </motion.div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[250px]">
            <input
              type="text"
              placeholder="Search items..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-surface-200 rounded-lg text-surface-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-surface-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat === 'all' ? 'All Categories' : cat}</option>
              ))}
            </select>
          </div>
          <div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-surface-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="low">Low Stock Only</option>
              <option value="good">Good Stock Only</option>
            </select>
          </div>
          <button className="px-6 py-2 bg-accent-500 text-gray-900 rounded-lg hover:bg-accent-600 transition-colors font-medium">
            Export Report
          </button>
        </div>
      </div>

      {/* Alert Section */}
      {lowStockItems.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-error-50 to-warning-50 border-l-4 border-error-500 rounded-xl p-5"
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <h3 className="font-semibold text-error-900">Reorder Alert</h3>
              <p className="text-sm text-error-700 mt-1">
                {lowStockItems.length} items are below reorder level and need immediate attention
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                {lowStockItems.slice(0, 5).map(item => (
                  <span key={item.id} className="px-3 py-1 bg-white rounded-full text-xs font-medium text-error-700">
                    {item.name}
                  </span>
                ))}
                {lowStockItems.length > 5 && (
                  <span className="px-3 py-1 bg-white rounded-full text-xs font-medium text-error-700">
                    +{lowStockItems.length - 5} more
                  </span>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Inventory List */}
        <div className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-surface-900">Current Inventory</h2>
              <span className="text-sm text-surface-500">{filteredItems.length} items</span>
            </div>
          </div>
          <div className="p-4 max-h-[600px] overflow-y-auto">
            <div className="space-y-3">
              {filteredItems.map((item, i) => {
                const stockStatus = getStockStatus(item);
                const stockPercentage = getStockPercentage(item);
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="bg-surface-50 rounded-xl p-4 hover:bg-surface-100 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-surface-900">{item.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-surface-500">{item.category}</span>
                          <span className="text-xs text-surface-400">•</span>
                          <span className="text-xs text-surface-500">{item.supplier}</span>
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold bg-${stockStatus.color}-50 text-${stockStatus.color}-700`}>
                        {stockStatus.label}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-surface-600">
                          Stock: <span className="font-semibold text-surface-900">{item.currentStock} {item.unit}</span>
                        </span>
                        <span className="text-surface-600">
                          Optimal: <span className="font-semibold">{item.optimalStock} {item.unit}</span>
                        </span>
                      </div>

                      <div className="relative h-2 bg-surface-200 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${stockPercentage}%` }}
                          transition={{ duration: 0.5, delay: i * 0.03 }}
                          className={`absolute inset-y-0 left-0 rounded-full ${
                            stockStatus.status === 'out' ? 'bg-error-500' :
                            stockStatus.status === 'low' ? 'bg-warning-500' :
                            stockStatus.status === 'good' ? 'bg-success-500' : 'bg-primary-500'
                          }`}
                        />
                      </div>

                      <div className="flex items-center justify-between text-xs text-surface-500">
                        <span>Reorder at: {item.reorderLevel} {item.unit}</span>
                        <span>Value: {((item.currentStock * item.costPerUnit) || 0).toFixed(2)} лв</span>
                        <span>Last: {new Date(item.lastRestock).toLocaleDateString('bg-BG', { day: 'numeric', month: 'short' })}</span>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Stock by Category */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Stock by Category</h2>
          </div>
          <div className="p-4">
            <div className="space-y-4">
              {stockByCategory.map((cat, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.05 }}
                  className="space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-surface-900">{cat.category}</span>
                    <div className="flex items-center gap-2">
                      {cat.lowStock > 0 && (
                        <span className="px-2 py-0.5 bg-error-50 text-error-700 rounded-full text-xs font-semibold">
                          {cat.lowStock} low
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs text-surface-500">
                    <span>{cat.items} items</span>
                    <span className="font-semibold text-success-600">{(cat.value || 0).toFixed(0)} лв</span>
                  </div>
                  <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(cat.items / inventoryItems.length) * 100}%` }}
                      transition={{ duration: 0.5, delay: i * 0.05 }}
                      className="h-full bg-primary-500 rounded-full"
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="px-4 pb-4 space-y-2">
            <button className="w-full py-2.5 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors font-medium text-sm">
              Generate Purchase Order
            </button>
            <button className="w-full py-2.5 bg-accent-50 text-accent-700 rounded-lg hover:bg-accent-100 transition-colors font-medium text-sm">
              Stock Take Report
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
