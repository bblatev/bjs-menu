'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface SpillageRecord {
  id: number;
  date: string;
  item_name: string;
  item_category: string;
  quantity: number;
  unit: string;
  cost: number;
  reason: 'spillage' | 'breakage' | 'over_pour' | 'comp' | 'expired' | 'other';
  bartender_id: number;
  bartender_name: string;
  notes?: string;
  approved_by?: string;
}

interface VarianceItem {
  id: number;
  item_name: string;
  category: string;
  expected_usage: number;
  actual_usage: number;
  variance: number;
  variance_percentage: number;
  variance_cost: number;
  status: 'ok' | 'warning' | 'critical';
}

interface SpillageStats {
  total_spillage_cost: number;
  total_breakage_cost: number;
  total_variance_cost: number;
  spillage_percentage: number;
  top_wasted_item: string;
  worst_bartender?: string;
  improvement_vs_last: number;
}

const REASONS = {
  spillage: { label: 'Spillage', color: 'bg-blue-500' },
  breakage: { label: 'Breakage', color: 'bg-red-500' },
  over_pour: { label: 'Over Pour', color: 'bg-yellow-500' },
  comp: { label: 'Comp', color: 'bg-purple-500' },
  expired: { label: 'Expired', color: 'bg-orange-500' },
  other: { label: 'Other', color: 'bg-gray-500' },
};

export default function SpillagePage() {
  const [records, setRecords] = useState<SpillageRecord[]>([]);
  const [variances, setVariances] = useState<VarianceItem[]>([]);
  const [stats, setStats] = useState<SpillageStats | null>(null);
  const [activeTab, setActiveTab] = useState<'spillage' | 'variance'>('spillage');
  const [period, setPeriod] = useState<'today' | 'week' | 'month'>('week');
  const [showAddModal, setShowAddModal] = useState(false);
  const [reasonFilter, setReasonFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    item_name: '',
    item_category: 'spirits',
    quantity: 1,
    unit: 'oz',
    reason: 'spillage' as SpillageRecord['reason'],
    notes: '',
  });

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, reasonFilter]);

  const loadData = async () => {
    setLoading(true);
    const headers = getAuthHeaders();

    try {
      // Fetch all data in parallel
      const [recordsRes, variancesRes, statsRes] = await Promise.allSettled([
        fetch(`${API_URL}/bar/spillage/records?period=${period}&reason_filter=${reasonFilter}`, { headers }),
        fetch(`${API_URL}/bar/spillage/variance`, { headers }),
        fetch(`${API_URL}/bar/spillage/stats?period=${period}`, { headers })
      ]);

      // Process records
      if (recordsRes.status === 'fulfilled' && recordsRes.value.ok) {
        const data = await recordsRes.value.json();
        if (Array.isArray(data)) {
          // Normalize API response to match component interface
          const reasonMap: Record<string, SpillageRecord['reason']> = {
            'spoilage': 'spillage', 'spillage': 'spillage', 'breakage': 'breakage',
            'over_pour': 'over_pour', 'comp': 'comp', 'expired': 'expired',
          };
          setRecords(data.map((r: Record<string, unknown>, idx: number) => ({
            id: Number(r.id) || idx,
            date: typeof r.timestamp === 'string' ? (r.timestamp as string).split('T')[0] : (r.date as string) || '',
            item_name: (r.item_name || r.item || 'Unknown') as string,
            item_category: (r.item_category || r.category || 'General') as string,
            quantity: Number(r.quantity) || 0,
            unit: (r.unit || 'pcs') as string,
            cost: Number(r.cost) || 0,
            reason: reasonMap[String(r.reason).toLowerCase()] || 'other',
            bartender_id: Number(r.bartender_id) || 0,
            bartender_name: (r.bartender_name || r.recorded_by || 'Staff') as string,
            notes: (r.notes || '') as string,
            approved_by: (r.approved_by || undefined) as string | undefined,
          })));
        }
      } else {
        // Fallback data
        const mockRecords: SpillageRecord[] = [
          { id: 1, date: '2024-12-24', item_name: 'Grey Goose Vodka', item_category: 'Spirits', quantity: 2, unit: 'oz', cost: 4.50, reason: 'spillage', bartender_id: 3, bartender_name: 'Elena Georgieva', notes: 'Slipped while pouring' },
          { id: 2, date: '2024-12-24', item_name: 'Margarita Glass', item_category: 'Glassware', quantity: 1, unit: 'pc', cost: 8.00, reason: 'breakage', bartender_id: 5, bartender_name: 'Alex Nikolov' },
          { id: 3, date: '2024-12-23', item_name: 'Jack Daniels', item_category: 'Spirits', quantity: 1.5, unit: 'oz', cost: 2.25, reason: 'over_pour', bartender_id: 3, bartender_name: 'Elena Georgieva' },
        ];
        let filtered = mockRecords;
        if (reasonFilter !== 'all') {
          filtered = filtered.filter(r => r.reason === reasonFilter);
        }
        setRecords(filtered);
      }

      // Process variances
      if (variancesRes.status === 'fulfilled' && variancesRes.value.ok) {
        const data = await variancesRes.value.json();
        if (Array.isArray(data)) {
          setVariances(data);
        }
      } else {
        setVariances([
          { id: 1, item_name: 'Grey Goose Vodka', category: 'Spirits', expected_usage: 120, actual_usage: 135, variance: -15, variance_percentage: -12.5, variance_cost: -33.75, status: 'critical' },
          { id: 2, item_name: 'Jack Daniels', category: 'Spirits', expected_usage: 95, actual_usage: 102, variance: -7, variance_percentage: -7.4, variance_cost: -10.50, status: 'warning' },
        ]);
      }

      // Process stats
      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        const data = await statsRes.value.json();
        setStats(data);
      } else {
        setStats({
          total_spillage_cost: 15.75,
          total_breakage_cost: 20.00,
          total_variance_cost: 82.75,
          spillage_percentage: 1.8,
          top_wasted_item: 'Grey Goose Vodka',
          worst_bartender: undefined,
          improvement_vs_last: 12,
        });
      }

      setError(null);
    } catch (err) {
      console.error('Failed to fetch spillage data:', err);
      setError('Failed to load spillage data. Showing default values.');
      // Set fallback data
      setStats({
        total_spillage_cost: 15.75,
        total_breakage_cost: 20.00,
        total_variance_cost: 82.75,
        spillage_percentage: 1.8,
        top_wasted_item: 'Grey Goose Vodka',
        worst_bartender: undefined,
        improvement_vs_last: 12,
      });
    } finally {
      setLoading(false);
    }
  };

  const addSpillage = () => {
    // In real app, would call API
    setShowAddModal(false);
    setFormData({
      item_name: '',
      item_category: 'spirits',
      quantity: 1,
      unit: 'oz',
      reason: 'spillage',
      notes: '',
    });
    loadData();
  };

  const getStatusColor = (status: VarianceItem['status']) => {
    switch (status) {
      case 'ok': return 'text-green-400';
      case 'warning': return 'text-yellow-400';
      case 'critical': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const groupByReason = () => {
    const groups: Record<string, number> = {};
    records.forEach(r => {
      groups[r.reason] = (groups[r.reason] || 0) + r.cost;
    });
    return groups;
  };

  const groupByBartender = () => {
    const groups: Record<string, number> = {};
    records.forEach(r => {
      groups[r.bartender_name] = (groups[r.bartender_name] || 0) + r.cost;
    });
    return Object.entries(groups).sort((a, b) => b[1] - a[1]);
  };

  const totalSpillage = records.reduce((sum, r) => sum + r.cost, 0);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-white p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-400">Loading spillage data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800">
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/bar" className="p-2 hover:bg-gray-100 rounded-lg">
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-3xl font-display text-primary">Spillage & Variance</h1>
            <p className="text-gray-400">Track waste and inventory discrepancies</p>
          </div>
        </div>
        <div className="flex gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as typeof period)}
            className="px-4 py-2 bg-secondary border border-gray-300 rounded-lg text-gray-900"
          >
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
          </select>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary/80"
          >
            + Log Spillage
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Spillage Cost</div>
            <div className="text-2xl font-bold text-blue-400">${stats.total_spillage_cost.toFixed(2)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Breakage Cost</div>
            <div className="text-2xl font-bold text-red-400">${stats.total_breakage_cost.toFixed(2)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Variance Cost</div>
            <div className="text-2xl font-bold text-yellow-400">${stats.total_variance_cost.toFixed(2)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Spillage %</div>
            <div className="text-2xl font-bold text-purple-400">{stats.spillage_percentage}%</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Total Waste</div>
            <div className="text-2xl font-bold text-gray-900">${totalSpillage.toFixed(2)}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">Top Wasted</div>
            <div className="text-lg font-bold text-orange-400 truncate">{stats.top_wasted_item}</div>
          </div>
          <div className="bg-secondary rounded-lg p-4">
            <div className="text-gray-400 text-xs">vs Last Period</div>
            <div className={`text-2xl font-bold ${stats.improvement_vs_last > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {stats.improvement_vs_last > 0 ? '-' : '+'}{Math.abs(stats.improvement_vs_last)}%
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('spillage')}
          className={`px-4 py-2 rounded-lg transition ${
            activeTab === 'spillage' ? 'bg-primary text-white' : 'bg-secondary text-gray-300 hover:bg-gray-100'
          }`}
        >
          Spillage Log
        </button>
        <button
          onClick={() => setActiveTab('variance')}
          className={`px-4 py-2 rounded-lg transition ${
            activeTab === 'variance' ? 'bg-primary text-white' : 'bg-secondary text-gray-300 hover:bg-gray-100'
          }`}
        >
          Inventory Variance
        </button>
      </div>

      {activeTab === 'spillage' && (
        <>
          {/* Reason Filter */}
          <div className="flex flex-wrap gap-2 mb-6">
            <button
              onClick={() => setReasonFilter('all')}
              className={`px-3 py-1 rounded text-sm ${
                reasonFilter === 'all' ? 'bg-primary text-white' : 'bg-secondary text-gray-300'
              }`}
            >
              All
            </button>
            {Object.entries(REASONS).map(([key, value]) => (
              <button
                key={key}
                onClick={() => setReasonFilter(key)}
                className={`px-3 py-1 rounded text-sm flex items-center gap-1 ${
                  reasonFilter === key ? `${value.color} text-white` : 'bg-secondary text-gray-300'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${value.color}`} />
                {value.label}
              </button>
            ))}
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Spillage Records */}
            <div className="lg:col-span-2 bg-secondary rounded-lg">
              <div className="p-4 border-b border-gray-300">
                <h3 className="text-gray-900 font-semibold">Spillage Log ({records.length} records)</h3>
              </div>
              <div className="divide-y divide-gray-700 max-h-[500px] overflow-y-auto">
                {records.map((record) => (
                  <div key={record.id} className="p-4 hover:bg-gray-100/50">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded text-xs text-gray-900 ${REASONS[record.reason].color}`}>
                          {REASONS[record.reason].label}
                        </span>
                        <span className="text-gray-900 font-semibold">{record.item_name}</span>
                      </div>
                      <span className="text-red-400 font-bold">-${record.cost.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <div className="text-gray-400">
                        {record.quantity} {record.unit} • {record.item_category}
                      </div>
                      <div className="text-gray-400">
                        {record.bartender_name} • {record.date}
                      </div>
                    </div>
                    {record.notes && (
                      <p className="text-gray-500 text-sm mt-2 italic">{record.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Analytics Sidebar */}
            <div className="space-y-6">
              {/* By Reason */}
              <div className="bg-secondary rounded-lg p-4">
                <h3 className="text-gray-900 font-semibold mb-4">Cost by Reason</h3>
                <div className="space-y-3">
                  {Object.entries(groupByReason()).map(([reason, cost]) => (
                    <div key={reason}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-gray-300 text-sm flex items-center gap-2">
                          <span className={`w-3 h-3 rounded ${REASONS[reason as keyof typeof REASONS]?.color || 'bg-gray-500'}`} />
                          {REASONS[reason as keyof typeof REASONS]?.label || reason}
                        </span>
                        <span className="text-gray-900 font-bold">${cost.toFixed(2)}</span>
                      </div>
                      <div className="h-2 bg-white rounded-full overflow-hidden">
                        <div
                          className={`h-full ${REASONS[reason as keyof typeof REASONS]?.color || 'bg-gray-500'}`}
                          style={{ width: `${(cost / totalSpillage) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* By Bartender */}
              <div className="bg-secondary rounded-lg p-4">
                <h3 className="text-gray-900 font-semibold mb-4">Cost by Bartender</h3>
                <div className="space-y-3">
                  {groupByBartender().map(([name, cost]) => (
                    <div key={name} className="flex items-center justify-between">
                      <span className="text-gray-300">{name}</span>
                      <span className="text-red-400 font-bold">${cost.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {activeTab === 'variance' && (
        <div className="bg-secondary rounded-lg overflow-hidden">
          <div className="p-4 border-b border-gray-300 flex items-center justify-between">
            <h3 className="text-gray-900 font-semibold">Inventory Variance Report</h3>
            <span className="text-gray-400 text-sm">Expected vs Actual Usage (oz/units)</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-white text-gray-400 text-sm">
                <tr>
                  <th className="p-3 text-left">Item</th>
                  <th className="p-3 text-left">Category</th>
                  <th className="p-3 text-right">Expected</th>
                  <th className="p-3 text-right">Actual</th>
                  <th className="p-3 text-right">Variance</th>
                  <th className="p-3 text-right">Variance %</th>
                  <th className="p-3 text-right">Cost Impact</th>
                  <th className="p-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {variances.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-100/50">
                    <td className="p-3 text-gray-900 font-medium">{item.item_name}</td>
                    <td className="p-3 text-gray-400">{item.category}</td>
                    <td className="p-3 text-right text-gray-300">{item.expected_usage}</td>
                    <td className="p-3 text-right text-gray-300">{item.actual_usage}</td>
                    <td className={`p-3 text-right font-bold ${item.variance < 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {item.variance > 0 ? '+' : ''}{item.variance}
                    </td>
                    <td className={`p-3 text-right font-bold ${item.variance_percentage < 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {item.variance_percentage > 0 ? '+' : ''}{item.variance_percentage.toFixed(1)}%
                    </td>
                    <td className={`p-3 text-right font-bold ${item.variance_cost < 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {item.variance_cost > 0 ? '+' : ''}${item.variance_cost.toFixed(2)}
                    </td>
                    <td className="p-3 text-center">
                      <span className={`inline-flex items-center gap-1 ${getStatusColor(item.status)}`}>
                        <span className={`w-2 h-2 rounded-full ${
                          item.status === 'ok' ? 'bg-green-400' :
                          item.status === 'warning' ? 'bg-yellow-400' : 'bg-red-400'
                        }`} />
                        {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-white">
                <tr>
                  <td colSpan={6} className="p-3 text-right text-gray-900 font-bold">Total Variance Cost:</td>
                  <td className="p-3 text-right text-red-400 font-bold text-lg">
                    ${variances.reduce((sum, v) => sum + v.variance_cost, 0).toFixed(2)}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Add Spillage Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
          <div className="bg-secondary rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Log Spillage</h2>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="text-gray-400 hover:text-gray-900 text-2xl"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-1">Item Name</label>
                  <input
                    type="text"
                    value={formData.item_name}
                    onChange={(e) => setFormData({ ...formData, item_name: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    placeholder="e.g., Grey Goose Vodka"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Category</label>
                    <select
                      value={formData.item_category}
                      onChange={(e) => setFormData({ ...formData, item_category: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      <option value="spirits">Spirits</option>
                      <option value="beer">Beer</option>
                      <option value="wine">Wine</option>
                      <option value="cocktails">Cocktails</option>
                      <option value="glassware">Glassware</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Reason</label>
                    <select
                      value={formData.reason}
                      onChange={(e) => setFormData({ ...formData, reason: e.target.value as SpillageRecord['reason'] })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      {Object.entries(REASONS).map(([key, value]) => (
                        <option key={key} value={key}>{value.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-1">Quantity</label>
                    <input
                      type="number"
                      step="0.5"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-1">Unit</label>
                    <select
                      value={formData.unit}
                      onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                      className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    >
                      <option value="oz">Ounces (oz)</option>
                      <option value="ml">Milliliters (ml)</option>
                      <option value="btl">Bottles</option>
                      <option value="pc">Pieces</option>
                      <option value="drink">Drinks</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Notes</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                    rows={2}
                    placeholder="What happened?"
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  onClick={addSpillage}
                  disabled={!formData.item_name}
                  className="flex-1 px-4 py-3 bg-primary text-gray-900 rounded-lg hover:bg-primary/80 disabled:opacity-50"
                >
                  Log Spillage
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
