'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface StockItem {
  id: number;
  name: string;
  sku: string;
  system_quantity: number;
  counted_quantity: number | null;
  unit: string;
  variance: number | null;
  variance_cost: number | null;
  cost_per_unit: number;
  category: string;
  location: string;
  last_counted: string | null;
}

interface StockCount {
  id: number;
  count_number: string;
  type: 'full' | 'partial' | 'spot';
  status: 'draft' | 'in_progress' | 'pending_review' | 'approved' | 'rejected';
  location: string;
  started_at: string;
  completed_at?: string;
  counted_by: string;
  approved_by?: string;
  items_count: number;
  variance_count: number;
  variance_value: number;
}

export default function StockCountsPage() {
  const [counts, setCounts] = useState<StockCount[]>([]);
  const [activeCount, setActiveCount] = useState<StockCount | null>(null);
  const [countItems, setCountItems] = useState<StockItem[]>([]);
  const [showNewCountModal, setShowNewCountModal] = useState(false);
  const [showCountModal, setShowCountModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  const [newCount, setNewCount] = useState({
    type: 'full' as StockCount['type'],
    location: '',
    categories: [] as string[],
  });

  const [categories, setCategories] = useState<string[]>([]);
  const [locations, setLocations] = useState<string[]>([]);

  useEffect(() => {
    loadCounts();
    loadCategoriesAndLocations();
  }, []);

  const loadCategoriesAndLocations = async () => {
    const token = localStorage.getItem('access_token');
    try {
      // Load categories
      const catRes = await fetch(`${API_URL}/stock/categories`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (catRes.ok) {
        const data = await catRes.json();
        setCategories(data.map((c: any) => typeof c === 'string' ? c : (c.name || c.category || '')));
      } else {
        // Fallback defaults if API not available
        setCategories(['Vegetables', 'Meat', 'Seafood', 'Dairy', 'Alcohol', 'Dry Goods', 'Beverages']);
      }

      // Load locations/warehouses
      const locRes = await fetch(`${API_URL}/warehouses`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (locRes.ok) {
        const data = await locRes.json();
        setLocations(data.map((l: any) => l.name || l.location || ''));
      } else {
        // Fallback defaults if API not available
        setLocations(['Main Storage', 'Kitchen Storage', 'Bar Storage', 'Cold Storage']);
      }
    } catch (error) {
      // Fallback defaults on error
      setCategories(['Vegetables', 'Meat', 'Seafood', 'Dairy', 'Alcohol', 'Dry Goods', 'Beverages']);
      setLocations(['Main Storage', 'Kitchen Storage', 'Bar Storage', 'Cold Storage']);
    }
  };

  const loadCounts = async () => {
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/stock/counts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCounts(data);
      }
    } catch (error) {
      console.error('Error loading counts:', error);
    }
  };

  const loadCountItems = async (countId: number) => {
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/stock/counts/${countId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCountItems(data.items.map((item: any) => ({
          id: item.id,
          name: item.name,
          sku: item.sku,
          system_quantity: item.system_quantity,
          counted_quantity: item.counted_quantity,
          unit: item.unit,
          variance: item.variance,
          variance_cost: item.variance_cost,
          cost_per_unit: item.cost_per_unit,
          category: item.category || '',
          location: '',
          last_counted: null
        })));
      }
    } catch (error) {
      console.error('Error loading count items:', error);
    }
  };

  const handleStartCount = async () => {
    const token = localStorage.getItem('access_token');
    try {
      const params = new URLSearchParams({
        count_type: newCount.type,
      });
      if (newCount.location) params.append('location', newCount.location);

      const res = await fetch(`${API_URL}/stock/counts?${params.toString()}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to create count');
      }

      const data = await res.json();

      // Load the count details
      await loadCountItems(data.id);

      setActiveCount({
        id: data.id,
        count_number: data.count_number,
        type: newCount.type,
        status: 'in_progress',
        location: newCount.location,
        started_at: new Date().toISOString(),
        counted_by: 'Current User',
        items_count: data.items_count,
        variance_count: 0,
        variance_value: 0,
      });

      setShowNewCountModal(false);
      setShowCountModal(true);
      loadCounts();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      toast.error(message);
    }
  };

  const handleUpdateCount = async (itemId: number, countedQty: number) => {
    if (!activeCount) return;

    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/stock/counts/${activeCount.id}/items/${itemId}?counted_quantity=${countedQty}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        // Update local state
        setCountItems(prev => prev.map(item => {
          if (item.id === itemId) {
            return {
              ...item,
              counted_quantity: countedQty,
              variance: data.variance,
              variance_cost: data.variance_cost,
            };
          }
          return item;
        }));
      }
    } catch (error) {
      console.error('Error updating count:', error);
    }
  };

  const handleCompleteCount = async () => {
    if (!activeCount) return;

    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/stock/counts/${activeCount.id}/complete`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to complete count');
      }

      setShowCountModal(false);
      setActiveCount(null);
      loadCounts();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      toast.error(message);
    }
  };

  const handleApproveCount = async (countId: number) => {
    const token = localStorage.getItem('access_token');
    try {
      const res = await fetch(`${API_URL}/stock/counts/${countId}/approve?apply_adjustments=true`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to approve count');
      }

      loadCounts();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      toast.error(message);
    }
  };

  const getStatusColor = (status: StockCount['status']) => {
    switch (status) {
      case 'draft': return 'bg-surface-100 text-surface-600';
      case 'in_progress': return 'bg-primary-100 text-primary-700';
      case 'pending_review': return 'bg-warning-100 text-warning-700';
      case 'approved': return 'bg-success-100 text-success-700';
      case 'rejected': return 'bg-error-100 text-error-700';
    }
  };

  const getTypeColor = (type: StockCount['type']) => {
    switch (type) {
      case 'full': return 'bg-accent-100 text-accent-700';
      case 'partial': return 'bg-primary-100 text-primary-700';
      case 'spot': return 'bg-warning-100 text-warning-700';
    }
  };

  const filteredItems = countItems.filter(item => {
    if (categoryFilter !== 'all' && item.category !== categoryFilter) return false;
    if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    // Location filter removed: item.location is not populated from the API, so filtering by location would exclude all items for non-full counts
    return true;
  });

  const countedItems = filteredItems.filter(i => i.counted_quantity !== null).length;
  const itemsWithVariance = filteredItems.filter(i => i.variance !== null && i.variance !== 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/stock" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Stock Counts</h1>
            <p className="text-surface-500 mt-1">Physical inventory counts and audits</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewCountModal(true)}
          className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Count
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">In Progress</p>
          <p className="text-2xl font-display font-bold text-primary-600 mt-1">
            {counts.filter(c => c.status === 'in_progress').length}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Pending Review</p>
          <p className="text-2xl font-display font-bold text-warning-600 mt-1">
            {counts.filter(c => c.status === 'pending_review').length}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Completed This Month</p>
          <p className="text-2xl font-display font-bold text-success-600 mt-1">
            {counts.filter(c => c.status === 'approved').length}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Total Variance</p>
          <p className={`text-2xl font-display font-bold mt-1 ${counts.reduce((sum, c) => sum + (c.variance_value ?? 0), 0) < 0 ? 'text-error-600' : 'text-success-600'}`}>
            {counts.reduce((sum, c) => sum + (c.variance_value ?? 0), 0).toFixed(2)} lv
          </p>
        </div>
      </div>

      {/* Counts List */}
      <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-100">
          <h2 className="font-semibold text-surface-900">Stock Count History</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-surface-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Count #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Location</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Items</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Variances</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-surface-500 uppercase">Value</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-surface-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {counts.map(count => (
                <tr key={count.id} className="hover:bg-surface-50">
                  <td className="px-4 py-3 font-medium text-surface-900">{count.count_number}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${getTypeColor(count.type)}`}>
                      {count.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-surface-600">{count.location}</td>
                  <td className="px-4 py-3 text-center font-medium">{count.items_count}</td>
                  <td className="px-4 py-3 text-center">
                    {count.variance_count > 0 ? (
                      <span className="px-2 py-0.5 bg-error-100 text-error-700 rounded font-medium">{count.variance_count}</span>
                    ) : (
                      <span className="text-surface-400">-</span>
                    )}
                  </td>
                  <td className={`px-4 py-3 text-right font-medium ${(count.variance_value ?? 0) < 0 ? 'text-error-600' : (count.variance_value ?? 0) > 0 ? 'text-success-600' : 'text-surface-600'}`}>
                    {(count.variance_value ?? 0) !== 0 ? `${(count.variance_value ?? 0) > 0 ? '+' : ''}${count.variance_value.toFixed(2)} lv` : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${getStatusColor(count.status)}`}>
                      {count.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-surface-500">
                    {new Date(count.started_at).toLocaleDateString('bg-BG', { day: 'numeric', month: 'short' })}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {count.status === 'in_progress' && (
                      <button
                        onClick={() => { setActiveCount(count); loadCountItems(count.id); setShowCountModal(true); }}
                        className="px-3 py-1 bg-primary-50 text-primary-600 rounded text-sm font-medium hover:bg-primary-100"
                      >
                        Continue
                      </button>
                    )}
                    {count.status === 'pending_review' && (
                      <button
                        onClick={() => handleApproveCount(count.id)}
                        className="px-3 py-1 bg-success-50 text-success-600 rounded text-sm font-medium hover:bg-success-100"
                      >
                        Approve
                      </button>
                    )}
                    {(count.status === 'approved' || count.status === 'rejected') && (
                      <button className="px-3 py-1 bg-surface-50 text-surface-600 rounded text-sm font-medium hover:bg-surface-100">
                        View
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* New Count Modal */}
      {showNewCountModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900">Start New Stock Count</h2>
              <button onClick={() => setShowNewCountModal(false)} className="p-1 rounded hover:bg-surface-100">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-2">Count Type</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['full', 'partial', 'spot'] as const).map(type => (
                    <button
                      key={type}
                      onClick={() => setNewCount(prev => ({ ...prev, type }))}
                      className={`p-3 rounded-lg border-2 text-center transition-colors ${
                        newCount.type === type
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-surface-200 hover:border-surface-300'
                      }`}
                    >
                      <span className="text-lg block mb-1">
                        {type === 'full' && '📋'}
                        {type === 'partial' && '📝'}
                        {type === 'spot' && '🔍'}
                      </span>
                      <span className="text-sm font-medium capitalize">{type}</span>
                      <p className="text-xs text-surface-500 mt-1">
                        {type === 'full' && 'All items'}
                        {type === 'partial' && 'By location'}
                        {type === 'spot' && 'Random check'}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Location</label>
                <select
                  value={newCount.location}
                  onChange={e => setNewCount(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select location...</option>
                  {locations.map(loc => (
                    <option key={loc} value={loc}>{loc}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-100 flex justify-end gap-3">
              <button
                onClick={() => setShowNewCountModal(false)}
                className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg font-medium hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                onClick={handleStartCount}
                className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600"
              >
                Start Count
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Count Modal */}
      {showCountModal && activeCount && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-surface-900">{activeCount.count_number}</h2>
                <p className="text-sm text-surface-500">{activeCount.location} - {activeCount.type} count</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-sm text-surface-500">Progress</p>
                  <p className="font-bold text-surface-900">{countedItems} / {filteredItems.length}</p>
                </div>
                <button onClick={() => setShowCountModal(false)} className="p-1 rounded hover:bg-surface-100">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-4 border-b border-surface-100 flex items-center gap-4">
              <input
                type="text"
                placeholder="Search items..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="flex-1 px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <select
                value={categoryFilter}
                onChange={e => setCategoryFilter(e.target.value)}
                className="px-3 py-2 border border-surface-200 rounded-lg"
              >
                <option value="all">All Categories</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
            <div className="overflow-y-auto max-h-[50vh]">
              <table className="w-full">
                <thead className="bg-surface-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Item</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">System Qty</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Counted Qty</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Variance</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-surface-500 uppercase">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {filteredItems.map(item => (
                    <tr key={item.id} className={item.variance && item.variance !== 0 ? 'bg-error-50' : ''}>
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-surface-900">{item.name}</p>
                          <p className="text-xs text-surface-500">{item.sku} - {item.category}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="px-2 py-1 bg-surface-100 rounded font-medium">{item.system_quantity} {item.unit}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <input
                          type="number"
                          value={item.counted_quantity ?? ''}
                          onChange={e => handleUpdateCount(item.id, Number(e.target.value))}
                          placeholder="Enter count"
                          min={0}
                          step={0.1}
                          className="w-24 px-2 py-1 border border-surface-200 rounded text-center focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        {item.variance !== null ? (
                          <span className={`px-2 py-1 rounded font-medium ${
                            item.variance === 0 ? 'bg-success-100 text-success-700' :
                            item.variance < 0 ? 'bg-error-100 text-error-700' :
                            'bg-warning-100 text-warning-700'
                          }`}>
                            {item.variance > 0 ? '+' : ''}{item.variance} {item.unit}
                          </span>
                        ) : (
                          <span className="text-surface-400">-</span>
                        )}
                      </td>
                      <td className={`px-4 py-3 text-right font-medium ${
                        item.variance_cost && item.variance_cost < 0 ? 'text-error-600' :
                        item.variance_cost && item.variance_cost > 0 ? 'text-success-600' : ''
                      }`}>
                        {item.variance_cost != null ? `${item.variance_cost > 0 ? '+' : ''}${item.variance_cost.toFixed(2)} lv` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 border-t border-surface-100 flex items-center justify-between">
              <div>
                {itemsWithVariance.length > 0 && (
                  <p className="text-sm text-error-600">
                    {itemsWithVariance.length} variance(s) detected: {itemsWithVariance.reduce((sum, i) => sum + (i.variance_cost || 0), 0).toFixed(2)} lv
                  </p>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowCountModal(false)}
                  className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg font-medium hover:bg-surface-200"
                >
                  Save & Exit
                </button>
                <button
                  onClick={handleCompleteCount}
                  disabled={countedItems < filteredItems.length}
                  className="px-4 py-2 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600 disabled:opacity-50"
                >
                  Complete Count
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
