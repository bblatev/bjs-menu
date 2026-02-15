'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface WasteRecord {
  id: number;
  item_id: number;
  item_name: string;
  sku: string;
  quantity: number;
  unit: string;
  reason: 'expired' | 'spoiled' | 'damaged' | 'overproduction' | 'customer_return' | 'spillage' | 'theft' | 'other';
  cost: number;
  recorded_by: string;
  recorded_at: string;
  notes?: string;
  batch_number?: string;
}

interface WasteStats {
  totalWasteToday: number;
  totalWasteWeek: number;
  totalWasteMonth: number;
  topWastedItem: string;
  wastePercentage: number;
  costSaved: number;
}

interface WasteInsight {
  id: string;
  type: 'expiration' | 'overproduction' | 'compliance' | 'general';
  title: string;
  message: string;
  icon: string;
}

const WASTE_REASONS = [
  { value: 'expired', label: 'Expired', icon: '📅', color: 'bg-warning-100 text-warning-700' },
  { value: 'spoiled', label: 'Spoiled', icon: '🦠', color: 'bg-error-100 text-error-700' },
  { value: 'damaged', label: 'Damaged', icon: '💔', color: 'bg-error-100 text-error-700' },
  { value: 'overproduction', label: 'Overproduction', icon: '📦', color: 'bg-primary-100 text-primary-700' },
  { value: 'customer_return', label: 'Customer Return', icon: '↩️', color: 'bg-accent-100 text-accent-700' },
  { value: 'spillage', label: 'Spillage', icon: '💧', color: 'bg-primary-100 text-primary-700' },
  { value: 'theft', label: 'Theft/Shrinkage', icon: '🚨', color: 'bg-error-100 text-error-700' },
  { value: 'other', label: 'Other', icon: '📝', color: 'bg-surface-100 text-surface-700' },
];

export default function WasteManagementPage() {
  const [records, setRecords] = useState<WasteRecord[]>([]);
  const [stats, setStats] = useState<WasteStats | null>(null);
  const [insights, setInsights] = useState<WasteInsight[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [dateFilter, setDateFilter] = useState<'today' | 'week' | 'month' | 'all'>('week');
  const [reasonFilter, setReasonFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const [newRecord, setNewRecord] = useState({
    item_name: '',
    sku: '',
    quantity: 1,
    unit: 'kg',
    reason: 'expired' as WasteRecord['reason'],
    cost_per_unit: 0,
    notes: '',
    batch_number: '',
  });

  const [stockItems, setStockItems] = useState<{id: number; name: string; sku: string; unit: string; cost_per_unit: number}[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const token = localStorage.getItem('access_token');
    try {
      // Load waste records
      const recordsRes = await fetch(`${API_URL}/stock/waste/records`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (recordsRes.ok) {
        const data = await recordsRes.json();
        setRecords(data);
      }

      // Load waste stats
      const statsRes = await fetch(`${API_URL}/stock/waste/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats({
          totalWasteToday: data.total_waste_today,
          totalWasteWeek: data.total_waste_week,
          totalWasteMonth: data.total_waste_month,
          topWastedItem: data.top_wasted_item || 'N/A',
          wastePercentage: 0,
          costSaved: 0,
        });
      }

      // Load stock items for the dropdown
      const stockRes = await fetch(`${API_URL}/stock`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (stockRes.ok) {
        const data = await stockRes.json();
        setStockItems(data.map((s: any) => ({
          id: s.id,
          name: typeof s.name === 'object' ? (s.name?.bg || s.name?.en || 'Item') : (s.name || 'Item'),
          sku: s.sku || '',
          unit: s.unit || 'units',
          cost_per_unit: s.cost_per_unit || 0
        })));
      }

      // Load waste insights
      const insightsRes = await fetch(`${API_URL}/stock/waste/insights`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (insightsRes.ok) {
        const data = await insightsRes.json();
        setInsights(data.map((i: any) => ({
          id: String(i.id),
          type: i.insight_type || i.type || 'general',
          title: i.title || '',
          message: i.message || i.description || '',
          icon: i.icon || (i.type === 'expiration' ? '📅' : i.type === 'overproduction' ? '📊' : i.type === 'compliance' ? '✓' : '💡'),
        })));
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const [selectedStockItemId, setSelectedStockItemId] = useState<number>(0);

  const handleRecordWaste = async () => {
    if (!selectedStockItemId || newRecord.quantity <= 0) {
      toast.error('Please select an item and enter quantity');
      return;
    }

    const token = localStorage.getItem('access_token');
    try {
      const params = new URLSearchParams({
        stock_item_id: selectedStockItemId.toString(),
        quantity: newRecord.quantity.toString(),
        reason: newRecord.reason,
      });

      if (newRecord.notes) params.append('notes', newRecord.notes);
      if (newRecord.batch_number) params.append('batch_number', newRecord.batch_number);

      const res = await fetch(`${API_URL}/stock/waste/records?${params.toString()}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to record waste');
      }

      setNewRecord({ item_name: '', sku: '', quantity: 1, unit: 'kg', reason: 'expired', cost_per_unit: 0, notes: '', batch_number: '' });
      setSelectedStockItemId(0);
      setShowModal(false);
      loadData();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      toast.error(message);
    }
  };

  const getReasonInfo = (reason: string) => WASTE_REASONS.find(r => r.value === reason) || WASTE_REASONS[7];

  const filteredRecords = records.filter(record => {
    // Date filter
    const recordDate = new Date(record.recorded_at);
    const now = new Date();
    if (dateFilter === 'today' && recordDate.toDateString() !== now.toDateString()) return false;
    if (dateFilter === 'week' && (now.getTime() - recordDate.getTime()) > 7 * 24 * 3600000) return false;
    if (dateFilter === 'month' && (now.getTime() - recordDate.getTime()) > 30 * 24 * 3600000) return false;

    // Reason filter
    if (reasonFilter !== 'all' && record.reason !== reasonFilter) return false;

    // Search filter
    if (searchQuery && !record.item_name.toLowerCase().includes(searchQuery.toLowerCase())) return false;

    return true;
  });

  const totalFilteredCost = filteredRecords.reduce((sum, r) => sum + r.cost, 0);

  const wasteByReason = WASTE_REASONS.map(reason => ({
    ...reason,
    count: records.filter(r => r.reason === reason.value).length,
    cost: records.filter(r => r.reason === reason.value).reduce((sum, r) => sum + r.cost, 0),
  })).filter(r => r.count > 0).sort((a, b) => b.cost - a.cost);

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
            <h1 className="text-2xl font-display font-bold text-surface-900">Waste Management</h1>
            <p className="text-surface-500 mt-1">Track and analyze inventory waste</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-error-500 text-white rounded-lg font-medium hover:bg-error-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Record Waste
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-6 gap-4">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Today</p>
            <p className="text-2xl font-display font-bold text-error-600 mt-1">{(stats.totalWasteToday || 0).toFixed(2)} lv</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">This Week</p>
            <p className="text-2xl font-display font-bold text-warning-600 mt-1">{(stats.totalWasteWeek || 0).toFixed(2)} lv</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">This Month</p>
            <p className="text-2xl font-display font-bold text-surface-900 mt-1">{(stats.totalWasteMonth || 0).toFixed(2)} lv</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Waste %</p>
            <p className="text-2xl font-display font-bold text-primary-600 mt-1">{stats.wastePercentage}%</p>
            <p className="text-xs text-surface-500">of COGS</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Top Wasted</p>
            <p className="text-lg font-display font-bold text-surface-900 mt-1">{stats.topWastedItem}</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Cost Saved</p>
            <p className="text-2xl font-display font-bold text-success-600 mt-1">{(stats.costSaved || 0).toFixed(2)} lv</p>
            <p className="text-xs text-surface-500">vs last month</p>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Waste by Reason Chart */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100">
            <h2 className="font-semibold text-surface-900">Waste by Reason</h2>
          </div>
          <div className="p-4 space-y-3">
            {wasteByReason.map(reason => (
              <div key={reason.value} className="flex items-center gap-3">
                <span className="text-xl">{reason.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-surface-900">{reason.label}</span>
                    <span className="text-sm text-surface-500">{(reason.cost || 0).toFixed(2)} lv ({reason.count})</span>
                  </div>
                  <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-error-500 rounded-full"
                      style={{ width: `${stats && stats.totalWasteMonth > 0 ? (reason.cost / stats.totalWasteMonth) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Waste Records Table */}
        <div className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between gap-4">
            <h2 className="font-semibold text-surface-900">Waste Records</h2>
            <div className="flex items-center gap-2">
              <select
                value={dateFilter}
                onChange={e => setDateFilter(e.target.value as any)}
                className="px-3 py-1.5 border border-surface-200 rounded-lg text-sm"
              >
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
                <option value="all">All Time</option>
              </select>
              <select
                value={reasonFilter}
                onChange={e => setReasonFilter(e.target.value)}
                className="px-3 py-1.5 border border-surface-200 rounded-lg text-sm"
              >
                <option value="all">All Reasons</option>
                {WASTE_REASONS.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="px-3 py-1.5 border border-surface-200 rounded-lg text-sm w-40"
              />
            </div>
          </div>
          <div className="overflow-x-auto max-h-96">
            <table className="w-full">
              <thead className="bg-surface-50 sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Item</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Qty</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Reason</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-surface-500 uppercase">Cost</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Recorded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {filteredRecords.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-surface-500">No records found</td>
                  </tr>
                ) : (
                  filteredRecords.map(record => {
                    const reasonInfo = getReasonInfo(record.reason);
                    return (
                      <tr key={record.id} className="hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-medium text-surface-900">{record.item_name}</p>
                            <p className="text-xs text-surface-500">{record.sku}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center font-medium">
                          {record.quantity} {record.unit}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${reasonInfo.color}`}>
                            {reasonInfo.icon} {reasonInfo.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-medium text-error-600">
                          -{(record.cost || 0).toFixed(2)} lv
                        </td>
                        <td className="px-4 py-3 text-sm text-surface-500">
                          <div>{record.recorded_by}</div>
                          <div className="text-xs">{new Date(record.recorded_at).toLocaleString('bg-BG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
              <tfoot className="bg-surface-50 border-t border-surface-200">
                <tr>
                  <td colSpan={3} className="px-4 py-3 font-medium text-surface-900">
                    Total ({filteredRecords.length} records)
                  </td>
                  <td className="px-4 py-3 text-right font-bold text-error-600">
                    -{(totalFilteredCost || 0).toFixed(2)} lv
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>

      {/* Waste Reduction Insights */}
      {insights.length > 0 && (
        <div className="bg-gradient-to-r from-warning-50 to-error-50 rounded-2xl p-6 border border-warning-100">
          <h2 className="font-semibold text-surface-900 mb-4">Waste Reduction Insights</h2>
          <div className="grid grid-cols-3 gap-4">
            {insights.slice(0, 3).map((insight) => (
              <div key={insight.id} className="bg-white/80 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{insight.icon}</span>
                  <span className="font-medium text-surface-900">{insight.title}</span>
                </div>
                <p className="text-sm text-surface-600">
                  {insight.message}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Record Waste Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-surface-900">Record Waste</h2>
              <button onClick={() => setShowModal(false)} className="p-1 rounded hover:bg-surface-100">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Stock Item *</label>
                <select
                  value={selectedStockItemId}
                  onChange={e => {
                    const itemId = Number(e.target.value);
                    setSelectedStockItemId(itemId);
                    const item = stockItems.find(i => i.id === itemId);
                    if (item) {
                      setNewRecord(prev => ({
                        ...prev,
                        item_name: item.name,
                        sku: item.sku,
                        unit: item.unit,
                        cost_per_unit: item.cost_per_unit
                      }));
                    }
                  }}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value={0}>Select stock item...</option>
                  {stockItems.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.name} ({item.sku}) - {item.unit}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Batch # (optional)</label>
                <input
                  type="text"
                  value={newRecord.batch_number}
                  onChange={e => setNewRecord(prev => ({ ...prev, batch_number: e.target.value }))}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Enter batch number if known"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Quantity *</label>
                  <input
                    type="number"
                    value={newRecord.quantity}
                    onChange={e => setNewRecord(prev => ({ ...prev, quantity: Number(e.target.value) }))}
                    min={0.1}
                    step={0.1}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Unit</label>
                  <input
                    type="text"
                    value={newRecord.unit}
                    readOnly
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg bg-surface-50 text-surface-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Cost/Unit</label>
                  <input
                    type="number"
                    value={newRecord.cost_per_unit}
                    onChange={e => setNewRecord(prev => ({ ...prev, cost_per_unit: Number(e.target.value) }))}
                    min={0}
                    step={0.01}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-2">Reason *</label>
                <div className="grid grid-cols-4 gap-2">
                  {WASTE_REASONS.map(reason => (
                    <button
                      key={reason.value}
                      onClick={() => setNewRecord(prev => ({ ...prev, reason: reason.value as any }))}
                      className={`p-2 rounded-lg border-2 text-center transition-colors ${
                        newRecord.reason === reason.value
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-surface-200 hover:border-surface-300'
                      }`}
                    >
                      <span className="text-xl block">{reason.icon}</span>
                      <span className="text-xs">{reason.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Notes</label>
                <textarea
                  value={newRecord.notes}
                  onChange={e => setNewRecord(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                  placeholder="Optional notes..."
                />
              </div>
              {newRecord.quantity > 0 && newRecord.cost_per_unit > 0 && (
                <div className="p-3 bg-error-50 rounded-lg">
                  <p className="text-sm text-error-700">
                    Total waste cost: <span className="font-bold">{((newRecord.quantity * newRecord.cost_per_unit) || 0).toFixed(2)} lv</span>
                  </p>
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t border-surface-100 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg font-medium hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                onClick={handleRecordWaste}
                disabled={!selectedStockItemId || newRecord.quantity <= 0}
                className="px-4 py-2 bg-error-500 text-white rounded-lg font-medium hover:bg-error-600 disabled:opacity-50"
              >
                Record Waste
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
