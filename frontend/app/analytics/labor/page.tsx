'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface LaborVsRevenueData {
  venue_id: number;
  venue_name: string;
  period: string;
  summary: {
    total_labor_cost: number;
    total_revenue: number;
    labor_percentage: number;
    target_labor_pct: number;
    total_overtime_hours: number;
    overtime_cost: number;
    avg_hourly_cost: number;
    efficiency_score: number;
  };
  daily_trend: DailyLaborData[];
  department_breakdown: DepartmentData[];
  overtime_by_staff: OvertimeEntry[];
}

interface DailyLaborData {
  date: string;
  labor_cost: number;
  revenue: number;
  labor_pct: number;
  overtime_hours: number;
}

interface DepartmentData {
  department: string;
  labor_cost: number;
  revenue_attributed: number;
  labor_pct: number;
  headcount: number;
  avg_hourly_rate: number;
  hours_worked: number;
}

interface OvertimeEntry {
  staff_name: string;
  department: string;
  regular_hours: number;
  overtime_hours: number;
  overtime_cost: number;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const formatCurrency = (v: number) =>
  `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const formatCurrencyShort = (v: number) => {
  if (v >= 1000) return `$${(v / 1000).toFixed(1)}k`;
  return `$${v.toFixed(0)}`;
};

const formatPct = (v: number) => `${v.toFixed(1)}%`;

const laborPctColor = (pct: number, target: number): string => {
  if (pct <= target) return 'text-green-600';
  if (pct <= target + 3) return 'text-yellow-600';
  return 'text-red-600';
};

const laborPctBarColor = (pct: number, target: number): string => {
  if (pct <= target) return 'bg-green-500';
  if (pct <= target + 3) return 'bg-yellow-500';
  return 'bg-red-500';
};

// ── Component ───────────────────────────────────────────────────────────────

export default function LaborAnalyticsPage() {
  const [data, setData] = useState<LaborVsRevenueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [venueId, setVenueId] = useState(1);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<LaborVsRevenueData>(
        `/analytics/labor-vs-revenue?venue_id=${venueId}`
      );
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load labor analytics');
    } finally {
      setLoading(false);
    }
  }, [venueId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading labor vs revenue data...</p>
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

  const maxDailyValue = Math.max(
    ...data.daily_trend.map(d => Math.max(d.labor_cost, d.revenue)),
    1
  );

  const totalDeptLabor = data.department_breakdown.reduce((s, d) => s + d.labor_cost, 0) || 1;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Labor vs Revenue Analytics</h1>
            <p className="text-gray-500 mt-1">{data.venue_name} -- {data.period}</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Venue:</label>
            <select
              value={venueId}
              onChange={e => setVenueId(parseInt(e.target.value))}
              className="px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-700"
            >
              <option value={1}>Main Location</option>
              <option value={2}>Branch 2</option>
              <option value={3}>Branch 3</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
            <div className="text-sm text-blue-600 font-medium">Total Revenue</div>
            <div className="text-2xl font-bold text-blue-900 mt-1">{formatCurrency(data.summary.total_revenue)}</div>
          </div>
          <div className="bg-orange-50 rounded-xl p-5 border border-orange-100">
            <div className="text-sm text-orange-600 font-medium">Total Labor Cost</div>
            <div className="text-2xl font-bold text-orange-900 mt-1">{formatCurrency(data.summary.total_labor_cost)}</div>
          </div>
          <div className={`rounded-xl p-5 border ${
            data.summary.labor_percentage <= data.summary.target_labor_pct
              ? 'bg-green-50 border-green-100'
              : 'bg-red-50 border-red-100'
          }`}>
            <div className="text-sm font-medium text-gray-600">Labor %</div>
            <div className={`text-2xl font-bold mt-1 ${laborPctColor(data.summary.labor_percentage, data.summary.target_labor_pct)}`}>
              {formatPct(data.summary.labor_percentage)}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">Target: {formatPct(data.summary.target_labor_pct)}</div>
          </div>
          <div className="bg-purple-50 rounded-xl p-5 border border-purple-100">
            <div className="text-sm text-purple-600 font-medium">Overtime</div>
            <div className="text-2xl font-bold text-purple-900 mt-1">{data.summary.total_overtime_hours.toFixed(1)}h</div>
            <div className="text-xs text-purple-500 mt-0.5">{formatCurrency(data.summary.overtime_cost)} cost</div>
          </div>
        </div>

        {/* Side-by-Side: Labor $ vs Revenue $ */}
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Daily Labor vs Revenue</h2>
          <div className="flex items-end gap-1 h-56">
            {data.daily_trend.map((day, idx) => {
              const revenueHeight = (day.revenue / maxDailyValue) * 100;
              const laborHeight = (day.labor_cost / maxDailyValue) * 100;
              const shortDate = day.date.split('-').slice(1).join('/');

              return (
                <div key={idx} className="flex-1 flex flex-col items-center group">
                  <div className="w-full flex gap-0.5 items-end" style={{ height: '200px' }}>
                    {/* Revenue bar */}
                    <div
                      className="flex-1 bg-blue-400 rounded-t transition-all group-hover:bg-blue-500"
                      style={{ height: `${revenueHeight}%`, minHeight: '2px' }}
                      title={`Revenue: ${formatCurrency(day.revenue)}`}
                    />
                    {/* Labor bar */}
                    <div
                      className="flex-1 bg-orange-400 rounded-t transition-all group-hover:bg-orange-500"
                      style={{ height: `${laborHeight}%`, minHeight: '2px' }}
                      title={`Labor: ${formatCurrency(day.labor_cost)}`}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {formatPct(day.labor_pct)}
                  </div>
                  <span className="text-xs text-gray-400">{shortDate}</span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-3 bg-blue-400 rounded" />
              <span className="text-gray-600 text-sm">Revenue</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-3 bg-orange-400 rounded" />
              <span className="text-gray-600 text-sm">Labor Cost</span>
            </div>
          </div>
        </div>

        {/* Labor % Trend */}
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Labor % Trend</h2>
            <span className="text-sm text-gray-500">
              Target: {formatPct(data.summary.target_labor_pct)}
            </span>
          </div>
          <div className="flex items-end gap-2 h-40">
            {data.daily_trend.map((day, idx) => {
              const maxPct = Math.max(...data.daily_trend.map(d => d.labor_pct), 1);
              const height = (day.labor_pct / maxPct) * 100;
              const shortDate = day.date.split('-').slice(1).join('/');
              const barColor = laborPctBarColor(day.labor_pct, data.summary.target_labor_pct);

              return (
                <div key={idx} className="flex-1 flex flex-col items-center group">
                  <div className="text-xs font-medium text-gray-600 mb-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {formatPct(day.labor_pct)}
                  </div>
                  <div
                    className={`w-full rounded-t ${barColor} transition-all group-hover:opacity-80`}
                    style={{ height: `${height}%`, minHeight: '2px' }}
                    title={`${day.date}: ${formatPct(day.labor_pct)}`}
                  />
                  <span className="text-xs text-gray-400 mt-1">{shortDate}</span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-center gap-4 mt-4 text-sm">
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-green-500 rounded" /> Under target</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-yellow-500 rounded" /> Near target</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-red-500 rounded" /> Over target</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Department Breakdown */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Department Breakdown</h2>
            <div className="space-y-4">
              {data.department_breakdown.map((dept, idx) => {
                const pctOfTotal = (dept.labor_cost / totalDeptLabor) * 100;
                return (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-1">
                      <div>
                        <span className="font-medium text-gray-900">{dept.department}</span>
                        <span className="text-xs text-gray-500 ml-2">{dept.headcount} staff</span>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-gray-900">{formatCurrency(dept.labor_cost)}</span>
                        <span className={`ml-2 text-sm ${laborPctColor(dept.labor_pct, data.summary.target_labor_pct)}`}>
                          ({formatPct(dept.labor_pct)})
                        </span>
                      </div>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all"
                        style={{ width: `${pctOfTotal}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>{dept.hours_worked.toFixed(0)}h worked</span>
                      <span>{formatCurrency(dept.avg_hourly_rate)}/hr avg</span>
                      <span>Revenue: {formatCurrencyShort(dept.revenue_attributed)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Overtime Tracking */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Overtime Tracking</h2>
              <span className="text-sm font-medium text-purple-600">
                {data.summary.total_overtime_hours.toFixed(1)}h total
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Staff</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Dept</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Regular</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">OT Hours</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">OT Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {data.overtime_by_staff.map((entry, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{entry.staff_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{entry.department}</td>
                      <td className="px-4 py-3 text-sm text-right text-gray-600">{entry.regular_hours.toFixed(1)}h</td>
                      <td className={`px-4 py-3 text-sm text-right font-medium ${
                        entry.overtime_hours > 10 ? 'text-red-600' : entry.overtime_hours > 5 ? 'text-yellow-600' : 'text-gray-900'
                      }`}>
                        {entry.overtime_hours.toFixed(1)}h
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-purple-600">
                        {formatCurrency(entry.overtime_cost)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.overtime_by_staff.length === 0 && (
              <div className="text-center py-8 text-gray-500">No overtime recorded this period.</div>
            )}
          </div>
        </div>

        {/* Efficiency Insight */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-6">
          <div className="flex items-start gap-4">
            <div className="flex-1">
              <h3 className="font-semibold text-blue-900 mb-2">Labor Efficiency Score</h3>
              <div className="flex items-center gap-4 mb-2">
                <div className="text-4xl font-bold text-blue-700">{data.summary.efficiency_score}%</div>
                <div className="flex-1">
                  <div className="h-3 bg-blue-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        data.summary.efficiency_score >= 90 ? 'bg-green-500' :
                        data.summary.efficiency_score >= 75 ? 'bg-blue-500' :
                        'bg-yellow-500'
                      }`}
                      style={{ width: `${data.summary.efficiency_score}%` }}
                    />
                  </div>
                </div>
              </div>
              <p className="text-sm text-blue-700 leading-relaxed">
                Avg hourly cost: {formatCurrency(data.summary.avg_hourly_cost)} per employee.
                Overtime accounts for {formatCurrency(data.summary.overtime_cost)} ({data.summary.total_overtime_hours.toFixed(1)}h) of total labor cost.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
