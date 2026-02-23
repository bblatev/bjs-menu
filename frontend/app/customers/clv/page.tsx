'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface TopCustomer {
  id: number;
  name: string;
  email: string;
  total_revenue: number;
  visit_count: number;
  avg_order_value: number;
  clv: number;
  last_visit: string;
  tier: string;
}

interface CLVSegment {
  segment: string;
  customer_count: number;
  avg_clv: number;
  total_clv: number;
  avg_frequency: number;
  avg_order_value: number;
  churn_risk: number;
  color: string;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function CustomerCLVPage() {
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [segments, setSegments] = useState<CLVSegment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'clv' | 'total_revenue' | 'visit_count'>('clv');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [topData, segmentData] = await Promise.all([
        api.get<TopCustomer[]>('/customers/clv/top'),
        api.get<CLVSegment[]>('/customers/clv/segments'),
      ]);
      setTopCustomers(topData);
      setSegments(segmentData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load CLV data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortDir(prev => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(column);
      setSortDir('desc');
    }
  };

  const sortedCustomers = [...topCustomers].sort((a, b) => {
    const multiplier = sortDir === 'desc' ? -1 : 1;
    return (a[sortBy] - b[sortBy]) * multiplier;
  });

  const formatCurrency = (v: number) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const totalCLV = segments.reduce((sum, s) => sum + s.total_clv, 0);
  const maxSegmentCLV = Math.max(...segments.map(s => s.avg_clv), 1);

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading customer lifetime value data...</p>
        </div>
      </div>
    );
  }

  if (error && topCustomers.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
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
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Customer Lifetime Value</h1>
          <p className="text-gray-500 mt-1">Understand the long-term value of your customer base</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-indigo-50 rounded-xl p-5 border border-indigo-100">
            <div className="text-sm text-indigo-600 font-medium">Total CLV</div>
            <div className="text-2xl font-bold text-indigo-900 mt-1">{formatCurrency(totalCLV)}</div>
          </div>
          <div className="bg-green-50 rounded-xl p-5 border border-green-100">
            <div className="text-sm text-green-600 font-medium">Top Customer CLV</div>
            <div className="text-2xl font-bold text-green-900 mt-1">
              {topCustomers.length > 0 ? formatCurrency(Math.max(...topCustomers.map(c => c.clv))) : '$0.00'}
            </div>
          </div>
          <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
            <div className="text-sm text-blue-600 font-medium">Segments</div>
            <div className="text-2xl font-bold text-blue-900 mt-1">{segments.length}</div>
          </div>
          <div className="bg-purple-50 rounded-xl p-5 border border-purple-100">
            <div className="text-sm text-purple-600 font-medium">Total Customers</div>
            <div className="text-2xl font-bold text-purple-900 mt-1">
              {segments.reduce((sum, s) => sum + s.customer_count, 0).toLocaleString()}
            </div>
          </div>
        </div>

        {/* CLV Distribution Chart */}
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">CLV by Segment</h2>
          <div className="space-y-4">
            {segments.map(seg => (
              <div key={seg.segment}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: seg.color || '#6366f1' }} />
                    <span className="font-medium text-gray-900">{seg.segment}</span>
                    <span className="text-sm text-gray-500">({seg.customer_count} customers)</span>
                  </div>
                  <span className="font-semibold text-gray-900">{formatCurrency(seg.avg_clv)} avg</span>
                </div>
                <div className="h-6 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(seg.avg_clv / maxSegmentCLV) * 100}%`,
                      backgroundColor: seg.color || '#6366f1',
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Avg Order: {formatCurrency(seg.avg_order_value)}</span>
                  <span>Frequency: {seg.avg_frequency.toFixed(1)}/mo</span>
                  <span>Churn Risk: {(seg.churn_risk * 100).toFixed(0)}%</span>
                  <span>Total: {formatCurrency(seg.total_clv)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Segment Breakdown Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
          {segments.map(seg => (
            <div key={seg.segment} className="rounded-xl border border-gray-200 p-4 bg-white shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: seg.color || '#6366f1' }} />
                <h3 className="font-semibold text-gray-900">{seg.segment}</h3>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-gray-500">Customers</div>
                  <div className="font-bold text-gray-900">{seg.customer_count.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-gray-500">Avg CLV</div>
                  <div className="font-bold text-gray-900">{formatCurrency(seg.avg_clv)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Frequency</div>
                  <div className="font-bold text-gray-900">{seg.avg_frequency.toFixed(1)}/mo</div>
                </div>
                <div>
                  <div className="text-gray-500">Churn Risk</div>
                  <div className={`font-bold ${seg.churn_risk > 0.5 ? 'text-red-600' : seg.churn_risk > 0.3 ? 'text-yellow-600' : 'text-green-600'}`}>
                    {(seg.churn_risk * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Top Customers Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">Top Customers</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">#</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Customer</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Tier</th>
                  <th
                    className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase cursor-pointer hover:text-gray-700"
                    onClick={() => handleSort('clv')}
                  >
                    CLV {sortBy === 'clv' && (sortDir === 'desc' ? '&#9660;' : '&#9650;')}
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase cursor-pointer hover:text-gray-700"
                    onClick={() => handleSort('total_revenue')}
                  >
                    Revenue {sortBy === 'total_revenue' && (sortDir === 'desc' ? '&#9660;' : '&#9650;')}
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase cursor-pointer hover:text-gray-700"
                    onClick={() => handleSort('visit_count')}
                  >
                    Visits {sortBy === 'visit_count' && (sortDir === 'desc' ? '&#9660;' : '&#9650;')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Avg Order</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Last Visit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {sortedCustomers.map((c, idx) => (
                  <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 text-sm text-gray-500">{idx + 1}</td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{c.name}</div>
                      <div className="text-xs text-gray-500">{c.email}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        c.tier === 'platinum' ? 'bg-purple-100 text-purple-800' :
                        c.tier === 'gold' ? 'bg-yellow-100 text-yellow-800' :
                        c.tier === 'silver' ? 'bg-gray-200 text-gray-800' :
                        'bg-amber-100 text-amber-800'
                      }`}>
                        {c.tier}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right font-bold text-indigo-600">{formatCurrency(c.clv)}</td>
                    <td className="px-6 py-4 text-right text-gray-900">{formatCurrency(c.total_revenue)}</td>
                    <td className="px-6 py-4 text-right text-gray-900">{c.visit_count}</td>
                    <td className="px-6 py-4 text-right text-gray-900">{formatCurrency(c.avg_order_value)}</td>
                    <td className="px-6 py-4 text-right text-gray-500 text-sm">{c.last_visit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {topCustomers.length === 0 && (
            <div className="text-center py-12 text-gray-500">No customer data available.</div>
          )}
        </div>
      </div>
    </div>
  );
}
