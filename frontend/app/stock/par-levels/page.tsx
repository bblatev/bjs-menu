'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface ParLevelItem {
  id: number;
  name: string;
  sku: string;
  category: string;
  current_stock: number;
  par_level: number;
  reorder_point: number;
  reorder_quantity: number;
  unit: string;
  avg_daily_usage: number;
  lead_time_days: number;
  safety_stock: number;
  status: 'ok' | 'reorder' | 'critical' | 'overstock';
  supplier_name: string;
  last_order_date: string;
  cost_per_unit: number;
  auto_reorder: boolean;
}

interface ParLevelStats {
  total_items: number;
  items_below_par: number;
  items_at_reorder: number;
  critical_items: number;
  overstocked_items: number;
  total_reorder_value: number;
  avg_stock_days: number;
}

export default function ParLevelsPage() {
  const [items, setItems] = useState<ParLevelItem[]>([]);
  const [stats, setStats] = useState<ParLevelStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<ParLevelItem | null>(null);
  const [showAutoReorderModal, setShowAutoReorderModal] = useState(false);


  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/stock/par-levels`, {
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        const data = await response.json();
        setItems(data.items || []);
        if (data.stats) {
          setStats(data.stats);
        } else {
          calculateStats(data.items || []);
        }
      } else {
        console.error('Failed to load par levels:', response.status);
      }
    } catch (err) {
      console.error('Failed to fetch par levels:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateStats = (data: ParLevelItem[]) => {
    const itemsBelowPar = data.filter(i => i.current_stock < i.par_level).length;
    const itemsAtReorder = data.filter(i => i.status === 'reorder').length;
    const criticalItems = data.filter(i => i.status === 'critical').length;
    const overstockedItems = data.filter(i => i.status === 'overstock').length;
    const reorderItems = data.filter(i => i.status === 'reorder' || i.status === 'critical');
    const totalReorderValue = reorderItems.reduce((sum, i) => sum + (i.reorder_quantity * i.cost_per_unit), 0);
    const avgStockDays = data.reduce((sum, i) => sum + (i.avg_daily_usage > 0 ? i.current_stock / i.avg_daily_usage : 0), 0) / data.length;

    setStats({
      total_items: data.length,
      items_below_par: itemsBelowPar,
      items_at_reorder: itemsAtReorder,
      critical_items: criticalItems,
      overstocked_items: overstockedItems,
      total_reorder_value: totalReorderValue,
      avg_stock_days: avgStockDays,
    });
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical': return 'bg-error-100 text-error-700 border-error-300';
      case 'reorder': return 'bg-warning-100 text-warning-700 border-warning-300';
      case 'overstock': return 'bg-primary-100 text-primary-700 border-primary-300';
      default: return 'bg-success-100 text-success-700 border-success-300';
    }
  };

  const getStockPercentage = (item: ParLevelItem) => {
    return Math.min((item.current_stock / item.par_level) * 100, 150);
  };

  const filteredItems = items
    .filter(item => item.name.toLowerCase().includes(searchQuery.toLowerCase()) || item.sku.toLowerCase().includes(searchQuery.toLowerCase()))
    .filter(item => categoryFilter === 'all' || item.category === categoryFilter)
    .filter(item => statusFilter === 'all' || item.status === statusFilter);

  const categories = [...new Set(items.map(i => i.category))];

  const handleGeneratePO = (item: ParLevelItem) => {
    alert(`Purchase Order generated for ${item.name}: ${item.reorder_quantity} ${item.unit} from ${item.supplier_name}`);
  };

  const handleBulkReorder = () => {
    const reorderItems = items.filter(i => i.status === 'reorder' || i.status === 'critical');
    if (reorderItems.length === 0) {
      alert('No items need reordering');
      return;
    }
    alert(`Generating ${reorderItems.length} purchase orders for items below reorder point`);
  };

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading par levels...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/stock" className="p-2 hover:bg-surface-100 rounded-lg transition-colors">
            <svg className="w-5 h-5 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Par Levels & Reorder Management</h1>
            <p className="text-surface-600 mt-1">Set optimal stock levels and automate reordering</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAutoReorderModal(true)}
            className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Auto-Reorder Rules
          </button>
          <button
            onClick={handleBulkReorder}
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Generate Bulk PO
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Total Items</p>
            <p className="text-2xl font-bold text-surface-900">{stats.total_items}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Below Par</p>
            <p className="text-2xl font-bold text-warning-600">{stats.items_below_par}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Need Reorder</p>
            <p className="text-2xl font-bold text-warning-600">{stats.items_at_reorder}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Critical</p>
            <p className="text-2xl font-bold text-error-600">{stats.critical_items}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Overstocked</p>
            <p className="text-2xl font-bold text-primary-600">{stats.overstocked_items}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Reorder Value</p>
            <p className="text-2xl font-bold text-surface-900">${stats.total_reorder_value.toFixed(0)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Avg Stock Days</p>
            <p className="text-2xl font-bold text-success-600">{stats.avg_stock_days.toFixed(1)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <input
          type="text"
          placeholder="Search items..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 w-64"
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Status</option>
          <option value="critical">Critical</option>
          <option value="reorder">Need Reorder</option>
          <option value="ok">OK</option>
          <option value="overstock">Overstocked</option>
        </select>
      </div>

      {/* Items Table */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Item</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Stock Level</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Par Level</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Reorder Point</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Daily Usage</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Days Left</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Status</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Auto</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-surface-50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-surface-900">{item.name}</p>
                      <p className="text-sm text-surface-500">{item.sku} • {item.category}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col items-center">
                      <span className="font-medium text-surface-900">{item.current_stock} {item.unit}</span>
                      <div className="w-24 h-2 bg-surface-200 rounded-full overflow-hidden mt-1">
                        <div
                          className={`h-full rounded-full ${
                            item.status === 'critical' ? 'bg-error-500' :
                            item.status === 'reorder' ? 'bg-warning-500' :
                            item.status === 'overstock' ? 'bg-primary-500' :
                            'bg-success-500'
                          }`}
                          style={{ width: `${Math.min(getStockPercentage(item), 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="font-medium text-surface-900">{item.par_level} {item.unit}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-surface-700">{item.reorder_point} {item.unit}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-surface-700">{item.avg_daily_usage} {item.unit}/day</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-medium ${
                      item.avg_daily_usage > 0 && item.current_stock / item.avg_daily_usage < 3 ? 'text-error-600' :
                      item.avg_daily_usage > 0 && item.current_stock / item.avg_daily_usage < 7 ? 'text-warning-600' :
                      'text-success-600'
                    }`}>
                      {item.avg_daily_usage > 0 ? (item.current_stock / item.avg_daily_usage).toFixed(1) : '∞'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(item.status)}`}>
                      {item.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {item.auto_reorder ? (
                      <span className="text-success-600">
                        <svg className="w-5 h-5 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      </span>
                    ) : (
                      <span className="text-surface-400">
                        <svg className="w-5 h-5 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => {
                          setSelectedItem(item);
                          setShowEditModal(true);
                        }}
                        className="p-2 text-surface-600 hover:bg-surface-100 rounded-lg"
                        title="Edit Par Levels"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {(item.status === 'reorder' || item.status === 'critical') && (
                        <button
                          onClick={() => handleGeneratePO(item)}
                          className="px-3 py-1 bg-primary-600 text-gray-900 rounded-lg text-sm hover:bg-primary-700"
                        >
                          Order
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      {showEditModal && selectedItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-lg mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">Edit Par Levels - {selectedItem.name}</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Par Level ({selectedItem.unit})</label>
                  <input
                    type="number"
                    defaultValue={selectedItem.par_level}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="text-xs text-surface-500 mt-1">Optimal stock level to maintain</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Reorder Point ({selectedItem.unit})</label>
                  <input
                    type="number"
                    defaultValue={selectedItem.reorder_point}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="text-xs text-surface-500 mt-1">Trigger point for reordering</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Reorder Quantity ({selectedItem.unit})</label>
                  <input
                    type="number"
                    defaultValue={selectedItem.reorder_quantity}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Safety Stock ({selectedItem.unit})</label>
                  <input
                    type="number"
                    defaultValue={selectedItem.safety_stock}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Lead Time (days)</label>
                  <input
                    type="number"
                    defaultValue={selectedItem.lead_time_days}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Avg Daily Usage</label>
                  <input
                    type="number"
                    step="0.1"
                    defaultValue={selectedItem.avg_daily_usage}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-surface-50 rounded-lg">
                <input
                  type="checkbox"
                  id="auto_reorder"
                  defaultChecked={selectedItem.auto_reorder}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <label htmlFor="auto_reorder" className="text-sm text-surface-700">
                  Enable automatic reorder when stock falls below reorder point
                </label>
              </div>
              <div className="bg-primary-50 p-4 rounded-lg">
                <h4 className="font-medium text-primary-900 mb-2">Calculated Values</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-primary-700">Recommended Reorder Point:</span>
                    <span className="font-medium text-primary-900 ml-2">
                      {(selectedItem.avg_daily_usage * selectedItem.lead_time_days + selectedItem.safety_stock).toFixed(0)} {selectedItem.unit}
                    </span>
                  </div>
                  <div>
                    <span className="text-primary-700">Days of Stock:</span>
                    <span className="font-medium text-primary-900 ml-2">
                      {selectedItem.avg_daily_usage > 0 ? (selectedItem.current_stock / selectedItem.avg_daily_usage).toFixed(1) : '∞'} days
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  alert('Par levels updated successfully');
                }}
                className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Auto-Reorder Rules Modal */}
      {showAutoReorderModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-2xl mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">Auto-Reorder Rules Configuration</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-surface-50 p-4 rounded-lg">
                <h4 className="font-medium text-surface-900 mb-3">Global Settings</h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-surface-700">Enable Auto-Reorder System</span>
                    <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 rounded" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-surface-700">Notify manager before ordering</span>
                    <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 rounded" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-surface-700">Consolidate orders by supplier</span>
                    <input type="checkbox" defaultChecked className="w-4 h-4 text-primary-600 rounded" />
                  </div>
                </div>
              </div>
              <div className="bg-surface-50 p-4 rounded-lg">
                <h4 className="font-medium text-surface-900 mb-3">Order Schedule</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-surface-700 mb-1">Check inventory at</label>
                    <input type="time" defaultValue="06:00" className="w-full px-3 py-2 border border-surface-300 rounded-lg" />
                  </div>
                  <div>
                    <label className="block text-sm text-surface-700 mb-1">Generate POs at</label>
                    <input type="time" defaultValue="07:00" className="w-full px-3 py-2 border border-surface-300 rounded-lg" />
                  </div>
                </div>
              </div>
              <div className="bg-warning-50 p-4 rounded-lg">
                <h4 className="font-medium text-warning-900 mb-2">Items with Auto-Reorder Enabled</h4>
                <p className="text-sm text-warning-700">{items.filter(i => i.auto_reorder).length} of {items.length} items have auto-reorder enabled</p>
              </div>
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowAutoReorderModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowAutoReorderModal(false);
                  alert('Auto-reorder rules saved');
                }}
                className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
              >
                Save Rules
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
