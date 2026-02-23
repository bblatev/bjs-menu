'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface PLMetric {
  label: string;
  value: number;
  previous_value: number;
  change_pct: number;
  trend: 'up' | 'down' | 'flat';
  sparkline: number[];
}

interface RealtimePL {
  venue_id: number;
  venue_name: string;
  period: string;
  last_updated: string;
  revenue: PLMetric;
  cogs: PLMetric;
  labor_cost: PLMetric;
  prime_cost_pct: PLMetric;
  net_profit: PLMetric;
  gross_profit: PLMetric;
  operating_expenses: PLMetric;
  food_cost_pct: number;
  beverage_cost_pct: number;
  labor_cost_pct: number;
  revenue_by_channel: { channel: string; amount: number; pct: number }[];
  hourly_revenue: { hour: string; amount: number }[];
}

// ============ COMPONENT ============

export default function RealtimePLPage() {
  const [data, setData] = useState<RealtimePL | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [venueId, _setVenueId] = useState(1);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchPL = useCallback(async () => {
    try {
      const result = await api.get<RealtimePL>(`/financial/realtime-pl?venue_id=${venueId}`);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load P&L data');
    } finally {
      setLoading(false);
    }
  }, [venueId]);

  useEffect(() => {
    fetchPL();
  }, [fetchPL]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchPL, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchPL]);

  const formatCurrency = (val: number) =>
    `$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const formatPct = (val: number) => `${val.toFixed(1)}%`;

  const getTrendIcon = (trend: 'up' | 'down' | 'flat') => {
    if (trend === 'up') return { arrow: '\u2191', color: 'text-green-600' };
    if (trend === 'down') return { arrow: '\u2193', color: 'text-red-600' };
    return { arrow: '\u2192', color: 'text-surface-500' };
  };

  const renderSparkline = (data: number[], color: string) => {
    if (!data || data.length < 2) return null;
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const width = 120;
    const height = 32;
    const points = data
      .map((v, i) => `${(i / (data.length - 1)) * width},${height - ((v - min) / range) * height}`)
      .join(' ');

    return (
      <svg width={width} height={height} className="ml-auto">
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  };

  const renderMetricCard = (
    metric: PLMetric,
    icon: string,
    gradientFrom: string,
    gradientTo: string,
    borderColor: string,
    sparkColor: string,
    isPercentage?: boolean,
    invertTrend?: boolean
  ) => {
    const trendInfo = getTrendIcon(metric.trend);
    const isPositiveChange = invertTrend ? metric.change_pct < 0 : metric.change_pct > 0;
    const changeColor = isPositiveChange ? 'text-green-600' : metric.change_pct === 0 ? 'text-surface-500' : 'text-red-600';

    return (
      <div className={`bg-gradient-to-br ${gradientFrom} ${gradientTo} rounded-2xl p-6 border ${borderColor}`}>
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-sm font-medium text-surface-600">{metric.label}</p>
            <p className="text-3xl font-bold text-surface-900 mt-1">
              {isPercentage ? formatPct(metric.value) : formatCurrency(metric.value)}
            </p>
          </div>
          <span className="text-2xl">{icon}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className={`flex items-center gap-1 text-sm font-medium ${changeColor}`}>
            <span>{trendInfo.arrow}</span>
            <span>{Math.abs(metric.change_pct).toFixed(1)}%</span>
            <span className="text-surface-400 font-normal ml-1">vs prev</span>
          </div>
          {renderSparkline(metric.sparkline, sparkColor)}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading real-time P&L...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📉</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">P&L Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchPL}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/financial-management" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-surface-900">Real-Time P&L Dashboard</h1>
          <p className="text-surface-500 mt-1">
            {data.venue_name} &middot; {data.period} &middot; Updated {new Date(data.last_updated).toLocaleTimeString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-surface-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 rounded text-primary-600"
            />
            Auto-refresh (30s)
          </label>
          <button
            onClick={fetchPL}
            className="px-4 py-2 border border-surface-300 rounded-lg hover:bg-surface-50 transition-colors text-sm font-medium"
          >
            Refresh Now
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {renderMetricCard(data.revenue, '💰', 'from-green-50', 'to-emerald-50', 'border-green-200', '#16a34a')}
        {renderMetricCard(data.cogs, '📦', 'from-orange-50', 'to-amber-50', 'border-orange-200', '#ea580c', false, true)}
        {renderMetricCard(data.labor_cost, '👥', 'from-blue-50', 'to-indigo-50', 'border-blue-200', '#2563eb', false, true)}
        {renderMetricCard(data.prime_cost_pct, '🎯', 'from-purple-50', 'to-violet-50', 'border-purple-200', '#7c3aed', true, true)}
        {renderMetricCard(data.gross_profit, '📈', 'from-teal-50', 'to-cyan-50', 'border-teal-200', '#0d9488')}
        {renderMetricCard(data.net_profit, '🏆', 'from-yellow-50', 'to-amber-50', 'border-yellow-200', '#ca8a04')}
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cost Breakdown */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-surface-900 mb-4">Cost Breakdown</h3>
          <div className="space-y-4">
            {[
              { label: 'Food Cost', value: data.food_cost_pct, target: 30, color: 'bg-orange-500' },
              { label: 'Beverage Cost', value: data.beverage_cost_pct, target: 22, color: 'bg-purple-500' },
              { label: 'Labor Cost', value: data.labor_cost_pct, target: 30, color: 'bg-blue-500' },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-surface-600">{item.label}</span>
                  <span className={`font-bold ${item.value > item.target ? 'text-red-600' : 'text-green-600'}`}>
                    {item.value.toFixed(1)}%
                  </span>
                </div>
                <div className="h-3 bg-surface-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${item.color} transition-all duration-500`}
                    style={{ width: `${Math.min(item.value * 2, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-surface-400 mt-1">Target: {item.target}%</p>
              </div>
            ))}
            <div className="pt-3 border-t border-surface-100">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-surface-700">Prime Cost %</span>
                <span className={`font-bold ${data.prime_cost_pct.value > 65 ? 'text-red-600' : 'text-green-600'}`}>
                  {data.prime_cost_pct.value.toFixed(1)}%
                </span>
              </div>
              <p className="text-xs text-surface-400 mt-1">Target: under 65%</p>
            </div>
          </div>
        </div>

        {/* Revenue by Channel */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-surface-900 mb-4">Revenue by Channel</h3>
          <div className="space-y-3">
            {data.revenue_by_channel.map((ch) => (
              <div key={ch.channel}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-surface-700 capitalize">{ch.channel}</span>
                  <span className="font-medium text-surface-900">{formatCurrency(ch.amount)}</span>
                </div>
                <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full"
                    style={{ width: `${ch.pct}%` }}
                  />
                </div>
                <p className="text-xs text-surface-400 mt-0.5">{ch.pct.toFixed(1)}% of total</p>
              </div>
            ))}
          </div>
        </div>

        {/* Hourly Revenue */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-surface-900 mb-4">Hourly Revenue</h3>
          <div className="flex items-end justify-between h-48 gap-1">
            {data.hourly_revenue.map((hr) => {
              const maxAmt = Math.max(...data.hourly_revenue.map((h) => h.amount), 1);
              const pct = (hr.amount / maxAmt) * 100;
              return (
                <div key={hr.hour} className="flex flex-col items-center flex-1 h-full justify-end">
                  <div
                    className="w-full bg-gradient-to-t from-primary-500 to-primary-300 rounded-t transition-all duration-300"
                    style={{ height: `${pct}%`, minHeight: hr.amount > 0 ? '4px' : '0' }}
                    title={`${hr.hour}: ${formatCurrency(hr.amount)}`}
                  />
                  <span className="text-[10px] text-surface-400 mt-1 rotate-[-45deg] origin-center">
                    {hr.hour}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Operating Expenses */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-surface-900">Operating Expenses</h3>
            <p className="text-sm text-surface-500 mt-1">Total overhead and operational costs</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-surface-900">{formatCurrency(data.operating_expenses.value)}</p>
            <p className={`text-sm font-medium ${data.operating_expenses.change_pct <= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {data.operating_expenses.change_pct > 0 ? '+' : ''}{data.operating_expenses.change_pct.toFixed(1)}% vs previous period
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
