'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface AgingItem {
  id: number;
  name: string;
  sku: string;
  category: string;
  batch_number: string;
  received_date: string;
  expiry_date: string;
  days_in_stock: number;
  days_until_expiry: number;
  quantity: number;
  unit: string;
  cost_per_unit: number;
  total_value: number;
  turnover_rate: number;
  avg_days_to_sell: number;
  aging_bucket: '0-7' | '8-14' | '15-30' | '31-60' | '60+';
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  location: string;
}

interface AgingStats {
  total_items: number;
  total_value_at_risk: number;
  critical_items: number;
  avg_days_in_stock: number;
  slow_movers: number;
  items_expiring_7_days: number;
  items_expiring_30_days: number;
  fifo_violations: number;
}

interface AgingBucket {
  bucket: string;
  count: number;
  value: number;
  percentage: number;
}

export default function StockAgingPage() {
  const [items, setItems] = useState<AgingItem[]>([]);
  const [stats, setStats] = useState<AgingStats | null>(null);
  const [buckets, setBuckets] = useState<AgingBucket[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [sortBy, setSortBy] = useState<'days_in_stock' | 'days_until_expiry' | 'total_value' | 'turnover_rate'>('days_until_expiry');


  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/stock/aging`, {
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        const data = await response.json();
        setItems(data.items || []);
        setBuckets(data.buckets || []);
        if (data.stats) {
          setStats(data.stats);
        } else {
          calculateStats(data.items || []);
        }
      } else {
        console.error('Failed to load aging data:', response.status);
      }
    } catch (err) {
      console.error('Failed to fetch aging data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateStats = (data: AgingItem[]) => {
    setStats({
      total_items: data.length,
      total_value_at_risk: data.filter(i => i.risk_level === 'high' || i.risk_level === 'critical').reduce((sum, i) => sum + i.total_value, 0),
      critical_items: data.filter(i => i.risk_level === 'critical').length,
      avg_days_in_stock: data.reduce((sum, i) => sum + i.days_in_stock, 0) / data.length,
      slow_movers: data.filter(i => i.turnover_rate < 0.5).length,
      items_expiring_7_days: data.filter(i => i.days_until_expiry <= 7).length,
      items_expiring_30_days: data.filter(i => i.days_until_expiry <= 30).length,
      fifo_violations: data.filter(i => i.days_in_stock > i.avg_days_to_sell * 2).length,
    });
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical': return 'bg-error-100 text-error-700 border-error-300';
      case 'high': return 'bg-warning-100 text-warning-700 border-warning-300';
      case 'medium': return 'bg-primary-100 text-primary-700 border-primary-300';
      default: return 'bg-success-100 text-success-700 border-success-300';
    }
  };

  const getExpiryColor = (days: number) => {
    if (days <= 3) return 'text-error-600';
    if (days <= 7) return 'text-warning-600';
    if (days <= 14) return 'text-primary-600';
    return 'text-success-600';
  };

  const filteredItems = items
    .filter(item => categoryFilter === 'all' || item.category === categoryFilter)
    .filter(item => riskFilter === 'all' || item.risk_level === riskFilter)
    .sort((a, b) => {
      switch (sortBy) {
        case 'days_in_stock': return b.days_in_stock - a.days_in_stock;
        case 'days_until_expiry': return a.days_until_expiry - b.days_until_expiry;
        case 'total_value': return b.total_value - a.total_value;
        case 'turnover_rate': return a.turnover_rate - b.turnover_rate;
        default: return 0;
      }
    });

  const categories = [...new Set(items.map(i => i.category))];

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading stock aging data...</p>
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
            <h1 className="text-2xl font-bold text-surface-900">Stock Aging Analytics</h1>
            <p className="text-surface-600 mt-1">Monitor inventory age, turnover rates and expiry risks</p>
          </div>
        </div>
        <button className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export Report
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Total Items</p>
            <p className="text-2xl font-bold text-surface-900">{stats.total_items}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-error-200 shadow-sm">
            <p className="text-sm text-surface-500">Value at Risk</p>
            <p className="text-2xl font-bold text-error-600">${(stats.total_value_at_risk || 0).toFixed(0)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Critical Items</p>
            <p className="text-2xl font-bold text-error-600">{stats.critical_items}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Avg Days in Stock</p>
            <p className="text-2xl font-bold text-surface-900">{(stats.avg_days_in_stock || 0).toFixed(1)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Slow Movers</p>
            <p className="text-2xl font-bold text-warning-600">{stats.slow_movers}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Expiring 7d</p>
            <p className="text-2xl font-bold text-error-600">{stats.items_expiring_7_days}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Expiring 30d</p>
            <p className="text-2xl font-bold text-warning-600">{stats.items_expiring_30_days}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">FIFO Violations</p>
            <p className="text-2xl font-bold text-error-600">{stats.fifo_violations}</p>
          </div>
        </div>
      )}

      {/* Aging Buckets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Stock Age Distribution</h3>
          <div className="space-y-3">
            {buckets.map((bucket, idx) => (
              <div key={idx}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-surface-700">{bucket.bucket}</span>
                  <span className="text-sm text-surface-600">{bucket.count} items • ${(bucket.value || 0).toFixed(0)}</span>
                </div>
                <div className="h-4 bg-surface-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      idx === 0 ? 'bg-success-500' :
                      idx === 1 ? 'bg-primary-500' :
                      idx === 2 ? 'bg-yellow-500' :
                      idx === 3 ? 'bg-warning-500' :
                      'bg-error-500'
                    }`}
                    style={{ width: `${bucket.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Turnover Analysis</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-success-50 rounded-lg">
              <div>
                <p className="font-medium text-success-900">Fast Movers</p>
                <p className="text-sm text-success-700">Turnover &gt; 1.0</p>
              </div>
              <span className="text-2xl font-bold text-success-600">{items.filter(i => i.turnover_rate > 1.0).length}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-primary-50 rounded-lg">
              <div>
                <p className="font-medium text-primary-900">Normal</p>
                <p className="text-sm text-primary-700">Turnover 0.5-1.0</p>
              </div>
              <span className="text-2xl font-bold text-primary-600">{items.filter(i => i.turnover_rate >= 0.5 && i.turnover_rate <= 1.0).length}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-warning-50 rounded-lg">
              <div>
                <p className="font-medium text-warning-900">Slow Movers</p>
                <p className="text-sm text-warning-700">Turnover &lt; 0.5</p>
              </div>
              <span className="text-2xl font-bold text-warning-600">{items.filter(i => i.turnover_rate < 0.5).length}</span>
            </div>
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
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Risk Levels</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="days_until_expiry">Sort by Expiry (Soonest)</option>
          <option value="days_in_stock">Sort by Age (Oldest)</option>
          <option value="total_value">Sort by Value (Highest)</option>
          <option value="turnover_rate">Sort by Turnover (Slowest)</option>
        </select>
      </div>

      {/* Items Table */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Item</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Batch</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Days in Stock</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Days to Expiry</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Quantity</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Value</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Turnover</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Risk</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredItems.map((item) => (
                <tr key={item.id} className={`hover:bg-surface-50 ${item.risk_level === 'critical' ? 'bg-error-50' : ''}`}>
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-surface-900">{item.name}</p>
                      <p className="text-sm text-surface-500">{item.sku} • {item.location}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm text-surface-700">{item.batch_number}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-medium ${item.days_in_stock > item.avg_days_to_sell * 2 ? 'text-error-600' : 'text-surface-900'}`}>
                      {item.days_in_stock} days
                    </span>
                    <p className="text-xs text-surface-500">avg: {item.avg_days_to_sell}d</p>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-bold ${getExpiryColor(item.days_until_expiry)}`}>
                      {item.days_until_expiry} days
                    </span>
                    <p className="text-xs text-surface-500">{item.expiry_date}</p>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-surface-900">{item.quantity} {item.unit}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="font-medium text-surface-900">${(item.total_value || 0).toFixed(2)}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-medium ${
                      item.turnover_rate > 1.0 ? 'text-success-600' :
                      item.turnover_rate >= 0.5 ? 'text-primary-600' :
                      'text-warning-600'
                    }`}>
                      {(item.turnover_rate || 0).toFixed(2)}x
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getRiskColor(item.risk_level)}`}>
                      {item.risk_level.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {item.risk_level === 'critical' && (
                        <button className="px-3 py-1 bg-error-100 text-error-700 rounded-lg text-sm hover:bg-error-200">
                          Use Now
                        </button>
                      )}
                      <button className="px-3 py-1 bg-surface-100 text-surface-700 rounded-lg text-sm hover:bg-surface-200">
                        Transfer
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* FIFO Alert */}
      {stats && stats.fifo_violations > 0 && (
        <div className="mt-6 bg-warning-50 border border-warning-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-warning-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <h4 className="font-semibold text-warning-900">FIFO Violations Detected</h4>
              <p className="text-sm text-warning-700 mt-1">
                {stats.fifo_violations} items have been in stock longer than their typical sell-through time.
                Review these items to ensure older inventory is being used first.
              </p>
              <button className="mt-2 text-sm font-medium text-warning-800 hover:text-warning-900">
                View FIFO Report →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
