'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface PourAccuracy {
  overall_accuracy_pct: number;
  target_accuracy_pct: number;
  total_pours: number;
  accurate_pours: number;
  over_pours: number;
  under_pours: number;
  total_variance_oz: number;
  total_variance_cost: number;
  accuracy_trend: number[];
  accuracy_by_bartender: {
    name: string;
    accuracy_pct: number;
    total_pours: number;
    variance_cost: number;
  }[];
  accuracy_by_shift: {
    shift: string;
    accuracy_pct: number;
    pours: number;
  }[];
}

interface PourVariance {
  products: {
    id: number;
    name: string;
    category: string;
    expected_oz: number;
    actual_avg_oz: number;
    variance_oz: number;
    variance_pct: number;
    cost_per_oz: number;
    cost_impact: number;
    pour_count: number;
    trend: 'improving' | 'worsening' | 'stable';
  }[];
  total_cost_impact: number;
  period: string;
}

// ============ COMPONENT ============

export default function PourTrackingPage() {
  const [accuracy, setAccuracy] = useState<PourAccuracy | null>(null);
  const [variance, setVariance] = useState<PourVariance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'cost_impact' | 'variance_pct' | 'name'>('cost_impact');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [accRes, varRes] = await Promise.all([
        api.get<PourAccuracy>('/bar/pour-accuracy'),
        api.get<PourVariance>('/bar/pour-variance'),
      ]);
      setAccuracy(accRes);
      setVariance(varRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pour data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getAccuracyColor = (pct: number) => {
    if (pct >= 95) return 'text-green-600';
    if (pct >= 90) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getAccuracyBg = (pct: number) => {
    if (pct >= 95) return 'bg-green-500';
    if (pct >= 90) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return { symbol: '\u2191', color: 'text-green-600' };
      case 'worsening': return { symbol: '\u2193', color: 'text-red-600' };
      default: return { symbol: '\u2192', color: 'text-surface-500' };
    }
  };

  const sortedProducts = variance?.products
    .slice()
    .sort((a, b) => {
      switch (sortBy) {
        case 'cost_impact': return Math.abs(b.cost_impact) - Math.abs(a.cost_impact);
        case 'variance_pct': return Math.abs(b.variance_pct) - Math.abs(a.variance_pct);
        case 'name': return a.name.localeCompare(b.name);
        default: return 0;
      }
    }) || [];

  const renderSparkline = (data: number[]) => {
    if (!data || data.length < 2) return null;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const w = 160;
    const h = 40;
    const points = data
      .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`)
      .join(' ');

    return (
      <svg width={w} height={h}>
        <polyline
          points={points}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading pour data...</p>
        </div>
      </div>
    );
  }

  if (error && !accuracy) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🍺</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Pour Data Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchData}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/bar" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-surface-900">Pour Accuracy Dashboard</h1>
          <p className="text-surface-500 mt-1">
            Monitor pour precision, variance, and cost impact
            {variance?.period && ` - ${variance.period}`}
          </p>
        </div>
      </div>

      {/* Top Stats */}
      {accuracy && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm col-span-2">
            <p className="text-sm text-surface-500">Overall Accuracy</p>
            <div className="flex items-end gap-2">
              <p className={`text-4xl font-bold ${getAccuracyColor(accuracy.overall_accuracy_pct)}`}>
                {accuracy.overall_accuracy_pct.toFixed(1)}%
              </p>
              <p className="text-sm text-surface-400 mb-1">/ {accuracy.target_accuracy_pct}% target</p>
            </div>
            <div className="mt-2 h-2 bg-surface-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${getAccuracyBg(accuracy.overall_accuracy_pct)}`}
                style={{ width: `${accuracy.overall_accuracy_pct}%` }}
              />
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Total Pours</p>
            <p className="text-2xl font-bold text-surface-900">{accuracy.total_pours.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Over Pours</p>
            <p className="text-2xl font-bold text-orange-600">{accuracy.over_pours}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Under Pours</p>
            <p className="text-2xl font-bold text-blue-600">{accuracy.under_pours}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Cost Impact</p>
            <p className={`text-2xl font-bold ${accuracy.total_variance_cost > 0 ? 'text-red-600' : 'text-green-600'}`}>
              ${Math.abs(accuracy.total_variance_cost).toFixed(2)}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Accuracy Trend */}
        {accuracy && (
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-surface-900 mb-4">Accuracy Trend</h3>
            <div className="flex items-center justify-center">
              {renderSparkline(accuracy.accuracy_trend)}
            </div>
            <p className="text-xs text-surface-400 text-center mt-2">Last 30 days</p>
          </div>
        )}

        {/* By Bartender */}
        {accuracy && (
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-surface-900 mb-4">By Bartender</h3>
            <div className="space-y-3">
              {accuracy.accuracy_by_bartender.map((bt) => (
                <div key={bt.name} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium text-surface-900 truncate">{bt.name}</span>
                      <span className={`font-bold ${getAccuracyColor(bt.accuracy_pct)}`}>
                        {bt.accuracy_pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${getAccuracyBg(bt.accuracy_pct)}`}
                        style={{ width: `${bt.accuracy_pct}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-surface-400 mt-0.5">
                      <span>{bt.total_pours} pours</span>
                      <span className={bt.variance_cost > 0 ? 'text-red-500' : 'text-green-500'}>
                        ${Math.abs(bt.variance_cost).toFixed(2)} impact
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* By Shift */}
        {accuracy && (
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-surface-900 mb-4">By Shift</h3>
            <div className="space-y-4">
              {accuracy.accuracy_by_shift.map((shift) => (
                <div key={shift.shift}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-surface-700 capitalize">{shift.shift}</span>
                    <span className={`font-bold ${getAccuracyColor(shift.accuracy_pct)}`}>
                      {shift.accuracy_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-3 bg-surface-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${getAccuracyBg(shift.accuracy_pct)}`}
                      style={{ width: `${shift.accuracy_pct}%` }}
                    />
                  </div>
                  <p className="text-xs text-surface-400 mt-0.5">{shift.pours} pours</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Variance Report */}
      {variance && (
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-surface-100 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-surface-900">Variance Report by Product</h3>
              <p className="text-sm text-surface-500">
                Total cost impact: <span className={`font-bold ${variance.total_cost_impact > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  ${Math.abs(variance.total_cost_impact).toFixed(2)}
                </span>
              </p>
            </div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="px-3 py-1.5 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
            >
              <option value="cost_impact">Sort by Cost Impact</option>
              <option value="variance_pct">Sort by Variance %</option>
              <option value="name">Sort by Name</option>
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-surface-600">Product</th>
                  <th className="px-4 py-3 text-left font-medium text-surface-600">Category</th>
                  <th className="px-4 py-3 text-right font-medium text-surface-600">Expected (oz)</th>
                  <th className="px-4 py-3 text-right font-medium text-surface-600">Actual Avg (oz)</th>
                  <th className="px-4 py-3 text-right font-medium text-surface-600">Variance</th>
                  <th className="px-4 py-3 text-right font-medium text-surface-600">Cost Impact</th>
                  <th className="px-4 py-3 text-right font-medium text-surface-600">Pours</th>
                  <th className="px-4 py-3 text-center font-medium text-surface-600">Trend</th>
                </tr>
              </thead>
              <tbody>
                {sortedProducts.map((product) => {
                  const trend = getTrendIcon(product.trend);
                  return (
                    <tr key={product.id} className="border-t border-surface-100 hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{product.name}</td>
                      <td className="px-4 py-3 text-surface-600 capitalize">{product.category}</td>
                      <td className="px-4 py-3 text-right text-surface-700">{product.expected_oz.toFixed(1)}</td>
                      <td className="px-4 py-3 text-right text-surface-700">{product.actual_avg_oz.toFixed(1)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-medium ${product.variance_oz > 0 ? 'text-red-600' : product.variance_oz < 0 ? 'text-blue-600' : 'text-green-600'}`}>
                          {product.variance_oz > 0 ? '+' : ''}{product.variance_oz.toFixed(2)} oz
                        </span>
                        <span className="text-xs text-surface-400 ml-1">
                          ({product.variance_pct > 0 ? '+' : ''}{product.variance_pct.toFixed(1)}%)
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-bold ${product.cost_impact > 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {product.cost_impact > 0 ? '-' : '+'}${Math.abs(product.cost_impact).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-surface-700">{product.pour_count}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-bold ${trend.color}`}>{trend.symbol}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
