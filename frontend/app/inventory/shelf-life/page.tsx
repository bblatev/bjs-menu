'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface ShelfLifeItem {
  id: number;
  product_name: string;
  product_id: number;
  category: string;
  batch_id: string;
  received_date: string;
  expiry_date: string;
  days_remaining: number;
  quantity: number;
  unit: string;
  storage_location: string;
  cost_per_unit: number;
  status: 'fresh' | 'use_soon' | 'expiring' | 'expired' | 'discarded';
}

interface ExpiringItem {
  id: number;
  product_name: string;
  batch_id: string;
  expiry_date: string;
  days_remaining: number;
  quantity: number;
  unit: string;
  estimated_waste_cost: number;
  fifo_recommendation: string;
}

interface WastePrediction {
  items_at_risk: number;
  estimated_waste_cost: number;
  by_category: { category: string; units: number; cost: number; confidence: number }[];
  recommendation: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const statusConfig: Record<string, { bg: string; border: string; text: string; label: string }> = {
  fresh: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', label: 'Fresh' },
  use_soon: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', label: 'Use Soon' },
  expiring: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', label: 'Expiring' },
  expired: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', label: 'Expired' },
  discarded: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-500', label: 'Discarded' },
};

const getDaysColor = (days: number): string => {
  if (days <= 0) return 'text-red-600 font-bold';
  if (days <= 1) return 'text-orange-600 font-bold';
  if (days <= 3) return 'text-yellow-600 font-semibold';
  if (days <= 7) return 'text-yellow-500';
  return 'text-green-600';
};

const formatCurrency = (v: number) =>
  `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// ── Component ───────────────────────────────────────────────────────────────

export default function ShelfLifePage() {
  const [items, setItems] = useState<ShelfLifeItem[]>([]);
  const [expiring, setExpiring] = useState<ExpiringItem[]>([]);
  const [prediction, setPrediction] = useState<WastePrediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [itemsData, expiringData, predictionData] = await Promise.allSettled([
        api.get<ShelfLifeItem[]>('/inventory/shelf-life'),
        api.get<ExpiringItem[]>('/inventory/expiring-soon'),
        api.get<WastePrediction>('/inventory/shelf-life/waste-prediction'),
      ]);
      if (itemsData.status === 'fulfilled') setItems(itemsData.value);
      if (expiringData.status === 'fulfilled') setExpiring(expiringData.value);
      if (predictionData.status === 'fulfilled') setPrediction(predictionData.value);

      if (itemsData.status === 'rejected') {
        throw itemsData.reason;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load shelf life data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const discardItem = async (id: number) => {
    try {
      await api.post(`/inventory/shelf-life/${id}/discard`);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to discard item');
    }
  };

  const filteredItems = items.filter(item => {
    const matchesFilter = filter === 'all' || item.status === filter;
    const matchesSearch = !searchTerm ||
      item.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.category || '').toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const statusCounts: Record<string, number> = {
    fresh: items.filter(i => i.status === 'fresh').length,
    use_soon: items.filter(i => i.status === 'use_soon').length,
    expiring: items.filter(i => i.status === 'expiring').length,
    expired: items.filter(i => i.status === 'expired').length,
  };

  const totalWasteCost = expiring.reduce((sum, e) => sum + (e.estimated_waste_cost || 0), 0);

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading shelf life data...</p>
        </div>
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Shelf Life Tracker</h1>
            <p className="text-gray-500 mt-1">Monitor expiry dates, reduce waste, and follow FIFO</p>
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Search items..."
            className="px-4 py-2 border border-gray-200 rounded-lg text-gray-700 bg-gray-50 w-64"
          />
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Status Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {(Object.entries(statusCounts) as [string, number][]).map(([status, count]) => {
            const config = statusConfig[status] || statusConfig.fresh;
            return (
              <button
                key={status}
                onClick={() => setFilter(filter === status ? 'all' : status)}
                className={`rounded-xl border p-4 text-left transition-all ${
                  filter === status ? `${config.bg} ${config.border} ring-2 ring-current ${config.text}` : 'bg-white border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="text-sm text-gray-500">{config.label}</div>
                <div className="text-2xl font-bold text-gray-900">{count}</div>
              </button>
            );
          })}
          <div className="rounded-xl border border-red-200 bg-red-50 p-4">
            <div className="text-sm text-red-600">Est. Waste Cost</div>
            <div className="text-2xl font-bold text-red-900">{formatCurrency(totalWasteCost)}</div>
          </div>
        </div>

        {/* Waste Prediction Alert */}
        {prediction && prediction.items_at_risk > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-xl p-5 mb-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="text-3xl font-bold text-orange-600">{prediction.items_at_risk}</div>
                <div>
                  <div className="font-semibold text-orange-900">Items at risk of expiring this week</div>
                  <div className="text-sm text-orange-700">{prediction.recommendation}</div>
                  {prediction.estimated_waste_cost > 0 && (
                    <div className="text-sm font-medium text-orange-800 mt-1">
                      Potential waste: {formatCurrency(prediction.estimated_waste_cost)}
                    </div>
                  )}
                </div>
              </div>
            </div>
            {/* Category Breakdown */}
            {prediction.by_category && prediction.by_category.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
                {prediction.by_category.map(cat => (
                  <div key={cat.category} className="bg-white rounded-lg border border-orange-100 p-3">
                    <div className="font-medium text-gray-900 text-sm">{cat.category}</div>
                    <div className="flex justify-between text-sm mt-1">
                      <span className="text-gray-500">{cat.units} units</span>
                      <span className="text-red-600 font-medium">{formatCurrency(cat.cost)}</span>
                    </div>
                    <div className="mt-1.5">
                      <div className="h-1.5 bg-orange-100 rounded-full overflow-hidden">
                        <div className="h-full bg-orange-500 rounded-full" style={{ width: `${cat.confidence * 100}%` }} />
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">{(cat.confidence * 100).toFixed(0)}% confidence</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Items Expiring Soon + FIFO Recommendations */}
        {expiring.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Expiring Soon */}
            <div className="bg-red-50 border border-red-200 rounded-xl p-5">
              <h2 className="text-lg font-bold text-red-900 mb-3">
                Expiring Soon ({expiring.length} items)
              </h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {expiring.map(item => (
                  <div key={item.id} className="flex items-center justify-between bg-white rounded-lg p-3 border border-red-100">
                    <div>
                      <span className="font-medium text-gray-900">{item.product_name}</span>
                      <div className="text-xs text-gray-500">Batch: {item.batch_id}</div>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className={getDaysColor(item.days_remaining)}>
                        {item.days_remaining <= 0 ? 'EXPIRED' : `${item.days_remaining}d`}
                      </span>
                      <span className="text-gray-500">{item.quantity} {item.unit}</span>
                      <span className="text-red-600 font-medium">{formatCurrency(item.estimated_waste_cost)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* FIFO Recommendations */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
              <h2 className="text-lg font-bold text-blue-900 mb-3">FIFO Recommendations</h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {expiring.filter(e => e.fifo_recommendation).length > 0 ? (
                  expiring.filter(e => e.fifo_recommendation).map(item => (
                    <div key={item.id} className="flex items-start gap-3 bg-white rounded-lg p-3 border border-blue-100">
                      <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-1.5" />
                      <div>
                        <div className="font-medium text-gray-900 text-sm">{item.product_name}</div>
                        <div className="text-sm text-blue-700 mt-0.5">{item.fifo_recommendation}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-6 text-blue-600 text-sm">
                    All items are following FIFO order correctly.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-4">
          {['all', 'fresh', 'use_soon', 'expiring', 'expired', 'discarded'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === f ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {f === 'all' ? 'All' : (statusConfig[f]?.label || f.replace('_', ' '))}
            </button>
          ))}
        </div>

        {/* Items Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Product</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Category</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Location</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Qty</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Received</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Expires</th>
                <th className="text-center px-4 py-3 text-sm font-medium text-gray-600">Days Left</th>
                <th className="text-center px-4 py-3 text-sm font-medium text-gray-600">Status</th>
                <th className="text-right px-4 py-3 text-sm font-medium text-gray-600">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map(item => {
                const config = statusConfig[item.status] || statusConfig.fresh;
                return (
                  <tr key={item.id} className={`border-b hover:bg-gray-50 ${item.status === 'expired' || item.status === 'discarded' ? 'opacity-60' : ''}`}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{item.product_name}</div>
                      {item.batch_id && <div className="text-xs text-gray-500">Batch: {item.batch_id}</div>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.category || '--'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.storage_location || '--'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.quantity} {item.unit}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.received_date}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.expiry_date}</td>
                    <td className={`px-4 py-3 text-center text-sm ${getDaysColor(item.days_remaining)}`}>
                      {item.days_remaining <= 0 ? 'EXPIRED' : item.days_remaining}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text} ${config.border} border`}>
                        {config.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {item.status !== 'discarded' && (
                        <button
                          onClick={() => discardItem(item.id)}
                          className="text-sm text-red-600 hover:text-red-800 font-medium"
                        >
                          Discard
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filteredItems.length === 0 && (
            <div className="p-8 text-center text-gray-500">No items match the current filter.</div>
          )}
        </div>
      </div>
    </div>
  );
}
