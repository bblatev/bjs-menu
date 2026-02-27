'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface PrimeCostData {
  venue_id: number;
  venue_name: string;
  period: string;
  food_cost_pct: number;
  labor_cost_pct: number;
  prime_cost_pct: number;
  food_cost_amount: number;
  labor_cost_amount: number;
  prime_cost_amount: number;
  total_revenue: number;
  target_food_cost_pct: number;
  target_labor_cost_pct: number;
  target_prime_cost_pct: number;
  daily_trend: DailyPrimeCost[];
  alerts: PrimeCostAlert[];
}

interface DailyPrimeCost {
  date: string;
  food_cost_pct: number;
  labor_cost_pct: number;
  prime_cost_pct: number;
  revenue: number;
}

interface PrimeCostAlert {
  id: string;
  type: 'food_cost' | 'labor_cost' | 'prime_cost';
  severity: 'warning' | 'critical';
  message: string;
  current_value: number;
  target_value: number;
  date: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const formatCurrency = (v: number) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const formatPct = (v: number) => `${v.toFixed(1)}%`;

const getStatusColor = (current: number, target: number): string => {
  const diff = current - target;
  if (diff <= 0) return 'text-green-600';
  if (diff <= 2) return 'text-yellow-600';
  return 'text-red-600';
};

const getBarColor = (current: number, target: number): string => {
  const diff = current - target;
  if (diff <= 0) return 'bg-green-500';
  if (diff <= 2) return 'bg-yellow-500';
  return 'bg-red-500';
};

// ── Component ───────────────────────────────────────────────────────────────

export default function PrimeCostPage() {
  const [data, setData] = useState<PrimeCostData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [venueId, setVenueId] = useState(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<PrimeCostData>(`/financial/prime-cost?venue_id=${venueId}`);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prime cost data');
    } finally {
      setLoading(false);
    }
  }, [venueId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const maxTrendValue = data?.daily_trend
    ? Math.max(...data.daily_trend.map(d => d.prime_cost_pct), 1)
    : 100;

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading prime cost data...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={loadData} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Prime Cost Monitoring</h1>
            <p className="text-gray-500 mt-1">{data.venue_name} -- {data.period}</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Venue:
            <select
              value={venueId}
              onChange={e => setVenueId(parseInt(e.target.value))}
              className="px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-700"
            >
              <option value={1}>Main Location</option>
              <option value={2}>Branch 2</option>
              <option value={3}>Branch 3</option>
            </select>
            </label>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Prime Cost Formula Banner */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-6 mb-8">
          <div className="flex items-center justify-center gap-4 flex-wrap text-center">
            <div className="px-6 py-4 bg-white rounded-lg shadow-sm border border-blue-100">
              <div className="text-sm text-gray-500">Food Cost %</div>
              <div className={`text-3xl font-bold ${getStatusColor(data.food_cost_pct, data.target_food_cost_pct)}`}>
                {formatPct(data.food_cost_pct)}
              </div>
              <div className="text-xs text-gray-400">Target: {formatPct(data.target_food_cost_pct)}</div>
            </div>
            <div className="text-3xl font-bold text-gray-400">+</div>
            <div className="px-6 py-4 bg-white rounded-lg shadow-sm border border-blue-100">
              <div className="text-sm text-gray-500">Labor Cost %</div>
              <div className={`text-3xl font-bold ${getStatusColor(data.labor_cost_pct, data.target_labor_cost_pct)}`}>
                {formatPct(data.labor_cost_pct)}
              </div>
              <div className="text-xs text-gray-400">Target: {formatPct(data.target_labor_cost_pct)}</div>
            </div>
            <div className="text-3xl font-bold text-gray-400">=</div>
            <div className="px-8 py-4 bg-white rounded-lg shadow-sm border-2 border-indigo-300">
              <div className="text-sm text-gray-500 font-semibold">Prime Cost %</div>
              <div className={`text-4xl font-bold ${getStatusColor(data.prime_cost_pct, data.target_prime_cost_pct)}`}>
                {formatPct(data.prime_cost_pct)}
              </div>
              <div className="text-xs text-gray-400">Target: {formatPct(data.target_prime_cost_pct)}</div>
            </div>
          </div>
        </div>

        {/* Detail Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[
            { label: 'Food Cost', amount: data.food_cost_amount, pct: data.food_cost_pct, target: data.target_food_cost_pct, color: 'orange' },
            { label: 'Labor Cost', amount: data.labor_cost_amount, pct: data.labor_cost_pct, target: data.target_labor_cost_pct, color: 'blue' },
            { label: 'Total Revenue', amount: data.total_revenue, pct: 100, target: 100, color: 'green' },
          ].map(item => (
            <div key={item.label} className="bg-gray-50 rounded-xl border border-gray-200 p-5">
              <div className="text-sm text-gray-500 font-medium">{item.label}</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(item.amount)}</div>
              {item.label !== 'Total Revenue' && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{formatPct(item.pct)}</span>
                    <span>Target: {formatPct(item.target)}</span>
                  </div>
                  <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${getBarColor(item.pct, item.target)}`}
                      style={{ width: `${Math.min(item.pct * 1.5, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Daily Trend */}
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Daily Prime Cost Trend</h2>
          <div className="flex items-end gap-2 h-56">
            {data.daily_trend.map((day, idx) => {
              const foodHeight = (day.food_cost_pct / maxTrendValue) * 100;
              const laborHeight = (day.labor_cost_pct / maxTrendValue) * 100;
              const isOverTarget = day.prime_cost_pct > data.target_prime_cost_pct;
              const shortDate = day.date.split('-').slice(1).join('/');

              return (
                <div key={idx} className="flex-1 flex flex-col items-center group">
                  <div className="text-xs text-gray-500 mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {formatPct(day.prime_cost_pct)}
                  </div>
                  <div className="w-full flex flex-col justify-end" style={{ height: '180px' }}>
                    <div
                      className="w-full bg-blue-400 rounded-t"
                      style={{ height: `${laborHeight}%`, minHeight: '2px' }}
                      title={`Labor: ${formatPct(day.labor_cost_pct)}`}
                    />
                    <div
                      className="w-full bg-orange-400"
                      style={{ height: `${foodHeight}%`, minHeight: '2px' }}
                      title={`Food: ${formatPct(day.food_cost_pct)}`}
                    />
                  </div>
                  {isOverTarget && (
                    <div className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1" title="Over target" />
                  )}
                  <span className="text-xs text-gray-500 mt-1">{shortDate}</span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-orange-400 rounded" />
              <span className="text-gray-600 text-sm">Food Cost</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-400 rounded" />
              <span className="text-gray-600 text-sm">Labor Cost</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full" />
              <span className="text-gray-600 text-sm">Over Target</span>
            </div>
          </div>
        </div>

        {/* Alerts */}
        {data.alerts.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Alerts</h2>
            <div className="space-y-3">
              {data.alerts.map(alert => (
                <div
                  key={alert.id}
                  className={`rounded-lg border p-4 flex items-start gap-3 ${
                    alert.severity === 'critical'
                      ? 'bg-red-50 border-red-200 text-red-800'
                      : 'bg-yellow-50 border-yellow-200 text-yellow-800'
                  }`}
                >
                  <span className="text-xl flex-shrink-0">
                    {alert.severity === 'critical' ? '&#9888;' : '&#9888;'}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium">{alert.message}</div>
                    <div className="text-sm mt-1 opacity-80">
                      Current: {formatPct(alert.current_value)} | Target: {formatPct(alert.target_value)} | {alert.date}
                    </div>
                  </div>
                  <span className="px-2 py-1 rounded text-xs font-bold uppercase">
                    {alert.severity}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
