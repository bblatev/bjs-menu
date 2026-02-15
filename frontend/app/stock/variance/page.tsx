'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface VarianceRecord {
  id: number;
  item_name: string;
  sku: string;
  category: string;
  expected_quantity: number;
  actual_quantity: number;
  variance_quantity: number;
  variance_percentage: number;
  variance_cost: number;
  unit: string;
  root_cause: string;
  root_cause_category: 'theft' | 'waste' | 'data_error' | 'supplier' | 'over_portion' | 'unknown';
  date: string;
  count_id: number;
  investigated: boolean;
  resolution: string;
  investigated_by: string;
}

interface VarianceStats {
  total_variance_cost: number;
  total_positive_variance: number;
  total_negative_variance: number;
  variance_percentage: number;
  items_with_variance: number;
  top_variance_category: string;
  avg_variance_per_item: number;
  investigated_count: number;
  uninvestigated_count: number;
}

interface TrendData {
  period: string;
  variance_cost: number;
  variance_percentage: number;
}

const ROOT_CAUSES = {
  theft: { label: 'Theft/Shrinkage', color: 'bg-error-500', icon: '🚨' },
  waste: { label: 'Waste/Spoilage', color: 'bg-orange-500', icon: '🗑️' },
  data_error: { label: 'Data Entry Error', color: 'bg-blue-500', icon: '📝' },
  supplier: { label: 'Supplier Short', color: 'bg-purple-500', icon: '📦' },
  over_portion: { label: 'Over Portioning', color: 'bg-yellow-500', icon: '🍽️' },
  unknown: { label: 'Unknown', color: 'bg-gray-500', icon: '❓' },
};

export default function VarianceAnalysisPage() {
  const [records, setRecords] = useState<VarianceRecord[]>([]);
  const [stats, setStats] = useState<VarianceStats | null>(null);
  const [trends, setTrends] = useState<TrendData[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'week' | 'month' | 'quarter'>('month');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [showOnlyUninvestigated, setShowOnlyUninvestigated] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<VarianceRecord | null>(null);
  const [showInvestigateModal, setShowInvestigateModal] = useState(false);


  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/stock/variance/analysis?period=${period}`, {
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        const data = await response.json();
        setRecords(data.records || []);
        setTrends(data.trends || []);
        if (data.stats) {
          setStats(data.stats);
        } else {
          calculateStats(data.records || []);
        }
      } else {
        console.error('Failed to load variance data:', response.status);
      }
    } catch (err) {
      console.error('Failed to fetch variance data:', err);
    } finally {
      setLoading(false);
    }
  }, [period]);

  const calculateStats = (data: VarianceRecord[]) => {
    const totalVarianceCost = data.reduce((sum, r) => sum + r.variance_cost, 0);
    const positiveVariance = data.filter(r => r.variance_cost > 0).reduce((sum, r) => sum + r.variance_cost, 0);
    const negativeVariance = data.filter(r => r.variance_cost < 0).reduce((sum, r) => sum + r.variance_cost, 0);
    const totalExpected = data.reduce((sum, r) => sum + (r.expected_quantity * (r.variance_cost / r.variance_quantity || 0)), 0);

    const categoryCounts: Record<string, number> = {};
    data.forEach(r => {
      categoryCounts[r.root_cause_category] = (categoryCounts[r.root_cause_category] || 0) + Math.abs(r.variance_cost);
    });
    const topCategory = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'unknown';

    setStats({
      total_variance_cost: totalVarianceCost,
      total_positive_variance: positiveVariance,
      total_negative_variance: negativeVariance,
      variance_percentage: totalExpected !== 0 ? (totalVarianceCost / totalExpected) * 100 : 0,
      items_with_variance: data.length,
      top_variance_category: ROOT_CAUSES[topCategory as keyof typeof ROOT_CAUSES]?.label || 'Unknown',
      avg_variance_per_item: totalVarianceCost / data.length,
      investigated_count: data.filter(r => r.investigated).length,
      uninvestigated_count: data.filter(r => !r.investigated).length,
    });
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredRecords = records
    .filter(r => categoryFilter === 'all' || r.category === categoryFilter)
    .filter(r => !showOnlyUninvestigated || !r.investigated);

  const categories = [...new Set(records.map(r => r.category))];

  const varianceByCause = Object.entries(ROOT_CAUSES).map(([key, value]) => {
    const total = records
      .filter(r => r.root_cause_category === key)
      .reduce((sum, r) => sum + Math.abs(r.variance_cost), 0);
    return { key, ...value, total };
  }).filter(c => c.total > 0).sort((a, b) => b.total - a.total);

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading variance analysis...</p>
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
            <h1 className="text-2xl font-bold text-surface-900">Variance Analysis & Root Cause</h1>
            <p className="text-surface-600 mt-1">Identify, investigate and resolve inventory discrepancies</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as typeof period)}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
          </select>
          <button className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export Report
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Total Variance</p>
            <p className={`text-2xl font-bold ${stats.total_variance_cost < 0 ? 'text-error-600' : 'text-success-600'}`}>
              ${(Math.abs(stats.total_variance_cost) ?? 0).toFixed(2)}
            </p>
            <p className="text-xs text-surface-500">{stats.total_variance_cost < 0 ? 'Loss' : 'Gain'}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Items with Variance</p>
            <p className="text-2xl font-bold text-surface-900">{stats.items_with_variance}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Uninvestigated</p>
            <p className="text-2xl font-bold text-warning-600">{stats.uninvestigated_count}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Top Cause</p>
            <p className="text-lg font-bold text-surface-900">{stats.top_variance_category}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Avg per Item</p>
            <p className={`text-2xl font-bold ${stats.avg_variance_per_item < 0 ? 'text-error-600' : 'text-success-600'}`}>
              ${(Math.abs(stats.avg_variance_per_item) ?? 0).toFixed(2)}
            </p>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Variance by Root Cause */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Variance by Root Cause</h3>
          <div className="space-y-3">
            {varianceByCause.map((cause) => (
              <div key={cause.key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-surface-700 flex items-center gap-2">
                    <span>{cause.icon}</span> {cause.label}
                  </span>
                  <span className="text-sm font-medium text-error-600">${(cause.total ?? 0).toFixed(2)}</span>
                </div>
                <div className="h-3 bg-surface-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${cause.color} rounded-full`}
                    style={{ width: `${(cause.total / varianceByCause[0].total) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Variance Trend */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Variance Trend</h3>
          <div className="flex items-end justify-between h-40 gap-4">
            {trends.map((t, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center">
                <div className="w-full flex flex-col items-center justify-end h-32">
                  <div
                    className={`w-full rounded-t ${t.variance_cost < 0 ? 'bg-error-500' : 'bg-success-500'}`}
                    style={{ height: `${(Math.abs(t.variance_cost) / 600) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-surface-500 mt-2">{t.period}</span>
                <span className={`text-xs font-medium ${t.variance_cost < 0 ? 'text-error-600' : 'text-success-600'}`}>
                  ${(Math.abs(t.variance_cost) ?? 0).toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
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
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showOnlyUninvestigated}
            onChange={(e) => setShowOnlyUninvestigated(e.target.checked)}
            className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
          />
          <span className="text-sm text-surface-700">Show only uninvestigated</span>
        </label>
        <div className="flex-1" />
        <span className="text-sm text-surface-500">{filteredRecords.length} records</span>
      </div>

      {/* Records Table */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Item</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Expected</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Actual</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Variance</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Cost Impact</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Root Cause</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Status</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredRecords.map((record) => (
                <tr key={record.id} className="hover:bg-surface-50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-surface-900">{record.item_name}</p>
                      <p className="text-sm text-surface-500">{record.sku} • {record.category}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-surface-700">{record.expected_quantity} {record.unit}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-surface-700">{record.actual_quantity} {record.unit}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-medium ${record.variance_quantity < 0 ? 'text-error-600' : 'text-success-600'}`}>
                      {record.variance_quantity > 0 ? '+' : ''}{record.variance_quantity} ({(record.variance_percentage ?? 0).toFixed(1)}%)
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-bold ${record.variance_cost < 0 ? 'text-error-600' : 'text-success-600'}`}>
                      {record.variance_cost < 0 ? '-' : '+'}${(Math.abs(record.variance_cost) ?? 0).toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${ROOT_CAUSES[record.root_cause_category].color} text-white`}>
                      {ROOT_CAUSES[record.root_cause_category].icon} {ROOT_CAUSES[record.root_cause_category].label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {record.investigated ? (
                      <span className="inline-flex items-center gap-1 text-success-600">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        Resolved
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-warning-600">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        Pending
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => {
                        setSelectedRecord(record);
                        setShowInvestigateModal(true);
                      }}
                      className="px-3 py-1 bg-primary-100 text-primary-700 rounded-lg text-sm hover:bg-primary-200"
                    >
                      {record.investigated ? 'View' : 'Investigate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Investigate Modal */}
      {showInvestigateModal && selectedRecord && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-2xl mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">
                {selectedRecord.investigated ? 'Variance Details' : 'Investigate Variance'} - {selectedRecord.item_name}
              </h2>
            </div>
            <div className="p-6 space-y-4">
              {/* Variance Summary */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-surface-50 p-4 rounded-lg text-center">
                  <p className="text-sm text-surface-500">Expected</p>
                  <p className="text-xl font-bold text-surface-900">{selectedRecord.expected_quantity} {selectedRecord.unit}</p>
                </div>
                <div className="bg-surface-50 p-4 rounded-lg text-center">
                  <p className="text-sm text-surface-500">Actual</p>
                  <p className="text-xl font-bold text-surface-900">{selectedRecord.actual_quantity} {selectedRecord.unit}</p>
                </div>
                <div className={`p-4 rounded-lg text-center ${selectedRecord.variance_cost < 0 ? 'bg-error-50' : 'bg-success-50'}`}>
                  <p className="text-sm text-surface-500">Cost Impact</p>
                  <p className={`text-xl font-bold ${selectedRecord.variance_cost < 0 ? 'text-error-600' : 'text-success-600'}`}>
                    ${(Math.abs(selectedRecord.variance_cost) ?? 0).toFixed(2)}
                  </p>
                </div>
              </div>

              {/* Root Cause Selection */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-2">Root Cause Category</label>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(ROOT_CAUSES).map(([key, value]) => (
                    <button
                      key={key}
                      className={`p-3 rounded-lg border-2 text-left transition-colors ${
                        selectedRecord.root_cause_category === key
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-surface-200 hover:border-surface-300'
                      }`}
                    >
                      <span className="text-lg">{value.icon}</span>
                      <span className="text-sm font-medium ml-2">{value.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Root Cause Details */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Root Cause Details</label>
                <textarea
                  rows={3}
                  defaultValue={selectedRecord.root_cause}
                  placeholder="Describe the root cause of this variance..."
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {/* Resolution */}
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Resolution / Corrective Action</label>
                <textarea
                  rows={3}
                  defaultValue={selectedRecord.resolution}
                  placeholder="What actions were taken to resolve this and prevent recurrence..."
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {selectedRecord.investigated && (
                <div className="bg-success-50 p-4 rounded-lg">
                  <p className="text-sm text-success-700">
                    <strong>Investigated by:</strong> {selectedRecord.investigated_by} on {selectedRecord.date}
                  </p>
                </div>
              )}
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowInvestigateModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Close
              </button>
              {!selectedRecord.investigated && (
                <button
                  onClick={() => {
                    setShowInvestigateModal(false);
                    toast.success('Variance investigation saved');
                  }}
                  className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
                >
                  Save Investigation
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
