'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface PourRecord {
  id: number;
  bartender_name: string;
  drink_name: string;
  spirit_type: string;
  expected_oz: number;
  actual_oz: number;
  variance_pct: number;
  timestamp: string;
  status: 'within_tolerance' | 'over' | 'under';
}

interface PourStats {
  total_pours_today: number;
  avg_variance_pct: number;
  overpour_cost: number;
  accuracy_rate: number;
  total_pours_week: number;
  most_accurate_bartender: string;
  least_accurate_bartender: string;
  top_overpoured_spirit: string;
}

interface BartenderOption {
  id: number;
  name: string;
}

// ── Constants ───────────────────────────────────────────────────────────────

const SPIRIT_TYPES = [
  'All',
  'Vodka',
  'Gin',
  'Rum',
  'Tequila',
  'Whiskey',
  'Bourbon',
  'Scotch',
  'Brandy',
  'Liqueur',
  'Other',
];

// ── Component ───────────────────────────────────────────────────────────────

export default function PourTrackingPage() {
  const [records, setRecords] = useState<PourRecord[]>([]);
  const [stats, setStats] = useState<PourStats | null>(null);
  const [bartenders, setBartenders] = useState<BartenderOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterBartender, setFilterBartender] = useState<string>('all');
  const [filterSpirit, setFilterSpirit] = useState<string>('All');
  const [filterDateFrom, setFilterDateFrom] = useState<string>('');
  const [filterDateTo, setFilterDateTo] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ venue_id: '1' });
      if (filterBartender !== 'all') params.append('bartender', filterBartender);
      if (filterSpirit !== 'All') params.append('spirit_type', filterSpirit);
      if (filterDateFrom) params.append('date_from', filterDateFrom);
      if (filterDateTo) params.append('date_to', filterDateTo);

      const [recordsData, statsData] = await Promise.all([
        api.get<PourRecord[]>(`/bar/pour-records?${params.toString()}`),
        api.get<PourStats>('/bar/pour-stats?venue_id=1'),
      ]);

      setRecords(Array.isArray(recordsData) ? recordsData : []);
      setStats(statsData);

      // Extract unique bartenders for filter
      if (Array.isArray(recordsData)) {
        const uniqueNames = Array.from(new Set(recordsData.map((r) => r.bartender_name)));
        setBartenders(uniqueNames.map((name, idx) => ({ id: idx + 1, name })));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pour tracking data');
    } finally {
      setLoading(false);
    }
  }, [filterBartender, filterSpirit, filterDateFrom, filterDateTo]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Client-side search filter
  const filteredRecords = records.filter((r) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.bartender_name.toLowerCase().includes(q) ||
      r.drink_name.toLowerCase().includes(q) ||
      r.spirit_type.toLowerCase().includes(q)
    );
  });

  const getVarianceColor = (status: string, variancePct: number): string => {
    if (status === 'within_tolerance') return 'text-green-600 bg-green-50';
    if (variancePct > 0) return 'text-red-600 bg-red-50';
    return 'text-orange-600 bg-orange-50';
  };

  const getVarianceBadge = (status: string): { label: string; classes: string } => {
    switch (status) {
      case 'within_tolerance':
        return { label: 'OK', classes: 'bg-green-100 text-green-700' };
      case 'over':
        return { label: 'Over', classes: 'bg-red-100 text-red-700' };
      case 'under':
        return { label: 'Under', classes: 'bg-orange-100 text-orange-700' };
      default:
        return { label: status, classes: 'bg-gray-100 text-gray-700' };
    }
  };

  const formatTimestamp = (ts: string): string => {
    try {
      const date = new Date(ts);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return ts;
    }
  };

  // ── Loading ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading pour tracking data...</p>
        </div>
      </div>
    );
  }

  if (error && records.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Pour Tracking &amp; Variance Analysis</h1>
          <p className="text-gray-500 mt-1">Monitor bartender pour accuracy, track variances, and control costs</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {/* Summary Cards */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-500">Total Pours Today</span>
                <span className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 text-lg font-bold">
                  #
                </span>
              </div>
              <p className="text-3xl font-bold text-gray-900">{stats.total_pours_today}</p>
              <p className="text-sm text-gray-500 mt-1">{stats.total_pours_week} this week</p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-500">Avg Variance</span>
                <span className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold ${
                  Math.abs(stats.avg_variance_pct) <= 5
                    ? 'bg-green-50 text-green-600'
                    : 'bg-red-50 text-red-600'
                }`}>
                  %
                </span>
              </div>
              <p className={`text-3xl font-bold ${
                Math.abs(stats.avg_variance_pct) <= 5 ? 'text-green-600' : 'text-red-600'
              }`}>
                {stats.avg_variance_pct > 0 ? '+' : ''}{stats.avg_variance_pct.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500 mt-1">Target: within +/- 5%</p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-500">Overpour Cost</span>
                <span className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center text-red-600 text-lg font-bold">
                  $
                </span>
              </div>
              <p className="text-3xl font-bold text-red-600">${stats.overpour_cost.toFixed(2)}</p>
              <p className="text-sm text-gray-500 mt-1">Lost revenue from overpouring</p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-500">Accuracy Rate</span>
                <span className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold ${
                  stats.accuracy_rate >= 90
                    ? 'bg-green-50 text-green-600'
                    : stats.accuracy_rate >= 75
                    ? 'bg-yellow-50 text-yellow-600'
                    : 'bg-red-50 text-red-600'
                }`}>
                  A
                </span>
              </div>
              <p className={`text-3xl font-bold ${
                stats.accuracy_rate >= 90
                  ? 'text-green-600'
                  : stats.accuracy_rate >= 75
                  ? 'text-yellow-600'
                  : 'text-red-600'
              }`}>
                {stats.accuracy_rate.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-500 mt-1">Pours within tolerance</p>
            </div>
          </div>
        )}

        {/* Insights Row */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <p className="text-sm text-green-700 font-medium">Most Accurate Bartender</p>
              <p className="text-lg font-bold text-green-900 mt-1">{stats.most_accurate_bartender || 'N/A'}</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <p className="text-sm text-red-700 font-medium">Needs Improvement</p>
              <p className="text-lg font-bold text-red-900 mt-1">{stats.least_accurate_bartender || 'N/A'}</p>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
              <p className="text-sm text-orange-700 font-medium">Top Overpoured Spirit</p>
              <p className="text-lg font-bold text-orange-900 mt-1">{stats.top_overpoured_spirit || 'N/A'}</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex flex-wrap items-end gap-4">
            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Search
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search bartender, drink, spirit..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              </label>
            </div>

            {/* Bartender Filter */}
            <div className="min-w-[160px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Bartender
              <select
                value={filterBartender}
                onChange={(e) => setFilterBartender(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Bartenders</option>
                {bartenders.map((b) => (
                  <option key={b.id} value={b.name}>{b.name}</option>
                ))}
              </select>
              </label>
            </div>

            {/* Spirit Type Filter */}
            <div className="min-w-[140px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Spirit Type
              <select
                value={filterSpirit}
                onChange={(e) => setFilterSpirit(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                {SPIRIT_TYPES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              </label>
            </div>

            {/* Date Range */}
            <div className="min-w-[140px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">From
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              </label>
            </div>
            <div className="min-w-[140px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">To
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              </label>
            </div>

            {/* Reset Button */}
            <div>
              <button
                onClick={() => {
                  setFilterBartender('all');
                  setFilterSpirit('All');
                  setFilterDateFrom('');
                  setFilterDateTo('');
                  setSearchQuery('');
                }}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors text-sm"
              >
                Reset Filters
              </button>
            </div>
          </div>
        </div>

        {/* Pour Records Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">
              Pour Records
              <span className="ml-2 text-sm font-normal text-gray-500">
                ({filteredRecords.length} record{filteredRecords.length !== 1 ? 's' : ''})
              </span>
            </h2>
            <button
              onClick={loadData}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
            >
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Bartender
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Drink / Spirit
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Expected (oz)
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actual (oz)
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Variance
                  </th>
                  <th className="px-5 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Timestamp
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredRecords.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-12 text-center text-gray-500">
                      No pour records found matching your filters.
                    </td>
                  </tr>
                ) : (
                  filteredRecords.map((record) => {
                    const badge = getVarianceBadge(record.status);
                    const varianceClasses = getVarianceColor(record.status, record.variance_pct);
                    return (
                      <tr key={record.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-sm">
                              {record.bartender_name.charAt(0).toUpperCase()}
                            </div>
                            <span className="font-medium text-gray-900">{record.bartender_name}</span>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <div>
                            <p className="font-medium text-gray-900">{record.drink_name}</p>
                            <p className="text-sm text-gray-500">{record.spirit_type}</p>
                          </div>
                        </td>
                        <td className="px-5 py-3 text-right font-mono text-gray-900">
                          {record.expected_oz.toFixed(2)}
                        </td>
                        <td className="px-5 py-3 text-right font-mono text-gray-900">
                          {record.actual_oz.toFixed(2)}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <span className={`inline-flex items-center px-2 py-1 rounded-md text-sm font-medium ${varianceClasses}`}>
                            {record.variance_pct > 0 ? '+' : ''}{record.variance_pct.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-5 py-3 text-center">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.classes}`}>
                            {badge.label}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right text-sm text-gray-500">
                          {formatTimestamp(record.timestamp)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
