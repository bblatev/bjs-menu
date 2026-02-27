'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface HourlySlot {
  hour: string;
  expected_covers: number;
  forecasted_revenue: number;
  required_staff: number;
  scheduled_staff: number;
  staffing_gap: number;
}

interface RoleBreakdown {
  role: string;
  required: number;
  scheduled: number;
  gap: number;
  hourly_rate: number;
  total_cost: number;
}

interface ScheduleSummary {
  total_hours: number;
  total_labor_cost: number;
  labor_percentage: number;
  efficiency_score: number;
}

interface DemandSchedule {
  id: number;
  date: string;
  venue_id: number;
  total_forecasted_revenue: number;
  total_labor_cost: number;
  labor_percentage: number;
  total_required_staff: number;
  total_scheduled_staff: number;
  overall_gap: number;
  hourly_slots: HourlySlot[];
  role_breakdown: RoleBreakdown[];
  recommendations: string[];
  summary: ScheduleSummary;
}

interface DemandScheduleResponse {
  schedules: DemandSchedule[];
  week_summary: {
    avg_labor_pct: number;
    total_revenue: number;
    total_labor_cost: number;
    total_hours: number;
    avg_efficiency_score: number;
    understaffed_slots: number;
    overstaffed_slots: number;
  };
}

// ============ COMPONENT ============

export default function DemandSchedulingPage() {
  const [data, setData] = useState<DemandScheduleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);

  const [targetLaborPct, setTargetLaborPct] = useState(30);
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [viewMode, setViewMode] = useState<'forecast' | 'schedule' | 'split'>('split');
  const [searchStaff, setSearchStaff] = useState('');

  const fetchSchedule = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<DemandScheduleResponse>(
        `/staff-scheduling/demand-schedule?venue_id=1&target_labor_pct=${targetLaborPct}`
      );
      setData(result);
      setSelectedDayIndex(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load demand schedule');
    } finally {
      setLoading(false);
    }
  }, [targetLaborPct]);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  const handleApplySchedule = async (scheduleId: number) => {
    setApplying(true);
    setApplySuccess(null);
    try {
      await api.post('/staff-scheduling/demand-schedule/apply', {
        schedule_id: scheduleId,
        venue_id: 1,
      });
      setApplySuccess(`Schedule for ${selectedDay?.date || 'selected day'} applied successfully.`);
      setTimeout(() => setApplySuccess(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply schedule');
    } finally {
      setApplying(false);
    }
  };

  const selectedDay = data?.schedules[selectedDayIndex] ?? null;

  const getGapColor = (gap: number) => {
    if (gap === 0) return 'text-green-700 bg-green-50 border-green-200';
    if (gap > 0) return 'text-blue-700 bg-blue-50 border-blue-200';
    return 'text-red-700 bg-red-50 border-red-200';
  };

  const getGapBarColor = (gap: number) => {
    if (gap === 0) return 'bg-green-500';
    if (gap > 0) return 'bg-blue-400';
    return 'bg-red-400';
  };

  const getLaborPctColor = (pct: number) => {
    if (pct >= 25 && pct <= 35) return 'text-green-600';
    if (pct < 25) return 'text-blue-600';
    return 'text-red-600';
  };

  const getEfficiencyColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-yellow-600';
    return 'text-red-600';
  };

  // ---- Loading ----
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Generating demand-based schedule...</p>
        </div>
      </div>
    );
  }

  // ---- Error ----
  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load Schedule</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchSchedule}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-full">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/staff" className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">AI Demand-Based Scheduling</h1>
          <p className="text-gray-500 mt-1">Optimize staffing levels against forecasted demand</p>
        </div>
        <div className="flex gap-2">
          {(['forecast', 'split', 'schedule'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
                viewMode === mode
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {mode === 'split' ? 'Side-by-Side' : mode}
            </button>
          ))}
        </div>
      </div>

      {/* Labor Cost Slider */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex flex-col md:flex-row md:items-end gap-6">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Labor Cost %:{' '}
              <span className={`text-lg font-bold ${getLaborPctColor(targetLaborPct)}`}>
                {targetLaborPct}%
              </span>
            <input
              type="range"
              min={15}
              max={50}
              value={targetLaborPct}
              onChange={(e) => setTargetLaborPct(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            </label>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>15%</span>
              <span className="text-green-600 font-semibold px-2 py-0.5 bg-green-50 rounded">25-35% optimal range</span>
              <span>50%</span>
            </div>
          </div>
          <div className="flex-shrink-0">
            <input
              type="text"
              placeholder="Search staff..."
              value={searchStaff}
              onChange={(e) => setSearchStaff(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
          <button
            onClick={fetchSchedule}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex-shrink-0"
          >
            Recalculate
          </button>
        </div>
      </div>

      {/* Success / Error banners */}
      {applySuccess && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800 text-sm flex items-center gap-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {applySuccess}
        </div>
      )}

      {error && data && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
      )}

      {/* Summary Cards */}
      {data?.week_summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Total Hours</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{data.week_summary.total_hours.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Labor Cost</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">${data.week_summary.total_labor_cost.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Labor %</p>
            <p className={`text-2xl font-bold mt-1 ${getLaborPctColor(data.week_summary.avg_labor_pct)}`}>
              {data.week_summary.avg_labor_pct.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Efficiency</p>
            <p className={`text-2xl font-bold mt-1 ${getEfficiencyColor(data.week_summary.avg_efficiency_score)}`}>
              {data.week_summary.avg_efficiency_score.toFixed(0)}%
            </p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Revenue</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">${data.week_summary.total_revenue.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Understaffed</p>
            <p className="text-2xl font-bold text-red-600 mt-1">{data.week_summary.understaffed_slots}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Overstaffed</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{data.week_summary.overstaffed_slots}</p>
          </div>
        </div>
      )}

      {/* Day Selector Tabs */}
      {data?.schedules && data.schedules.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {data.schedules.map((schedule, idx) => {
            const date = new Date(schedule.date + 'T00:00:00');
            const isSelected = selectedDayIndex === idx;
            return (
              <button
                key={schedule.date}
                onClick={() => setSelectedDayIndex(idx)}
                className={`flex-shrink-0 px-4 py-3 rounded-xl border transition-colors text-center min-w-[100px] ${
                  isSelected
                    ? 'bg-blue-600 text-white border-blue-600 shadow-md'
                    : 'bg-white text-gray-700 border-gray-200 hover:border-blue-300'
                }`}
              >
                <div className="text-xs font-medium">
                  {date.toLocaleDateString('en-US', { weekday: 'short' })}
                </div>
                <div className="text-lg font-bold">
                  {date.toLocaleDateString('en-US', { day: 'numeric' })}
                </div>
                <div className={`text-xs font-medium ${isSelected ? 'text-blue-100' : getLaborPctColor(schedule.labor_percentage)}`}>
                  {schedule.labor_percentage.toFixed(0)}% labor
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Selected Day: Forecast vs Schedule */}
      {selectedDay && (
        <div className={`grid gap-6 ${viewMode === 'split' ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
          {/* Forecast Panel */}
          {(viewMode === 'forecast' || viewMode === 'split') && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Forecast - {new Date(selectedDay.date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
                </h3>
                <span className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-xs font-medium">
                  AI Generated
                </span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-3 text-xs font-medium text-gray-500 px-2">
                  <span className="w-14">Hour</span>
                  <span className="flex-1">Expected Covers</span>
                  <span className="w-20 text-right">Covers</span>
                  <span className="w-20 text-right">Revenue</span>
                </div>
                {selectedDay.hourly_slots.map((slot) => {
                  const maxCovers = Math.max(...selectedDay.hourly_slots.map((s) => s.expected_covers), 1);
                  return (
                    <div key={slot.hour} className="flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-gray-50">
                      <span className="text-sm font-medium text-gray-600 w-14 flex-shrink-0">{slot.hour}</span>
                      <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-purple-400 rounded-full transition-all"
                          style={{ width: `${(slot.expected_covers / maxCovers) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-700 w-20 text-right font-medium">{slot.expected_covers}</span>
                      <span className="text-xs text-gray-500 w-20 text-right">${slot.forecasted_revenue.toLocaleString()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Schedule Panel */}
          {(viewMode === 'schedule' || viewMode === 'split') && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Staffing Schedule</h3>
                <button
                  onClick={() => handleApplySchedule(selectedDay.id)}
                  disabled={applying}
                  className="px-4 py-1.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {applying ? 'Applying...' : 'Apply Schedule'}
                </button>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-3 text-xs font-medium text-gray-500 px-2">
                  <span className="w-14">Hour</span>
                  <span className="flex-1">Staffing (Required vs Scheduled)</span>
                  <span className="w-16 text-center">Req</span>
                  <span className="w-16 text-center">Sched</span>
                  <span className="w-16 text-center">Gap</span>
                </div>
                {selectedDay.hourly_slots.map((slot) => {
                  const maxStaff = Math.max(...selectedDay.hourly_slots.map((s) => Math.max(s.required_staff, s.scheduled_staff)), 1);
                  return (
                    <div key={slot.hour} className="flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-gray-50">
                      <span className="text-sm font-medium text-gray-600 w-14 flex-shrink-0">{slot.hour}</span>
                      <div className="flex-1 space-y-1">
                        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${(slot.required_staff / maxStaff) * 100}%` }}
                          />
                        </div>
                        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${getGapBarColor(slot.staffing_gap)}`}
                            style={{ width: `${(slot.scheduled_staff / maxStaff) * 100}%` }}
                          />
                        </div>
                      </div>
                      <span className="text-xs text-gray-600 w-16 text-center">{slot.required_staff}</span>
                      <span className="text-xs text-gray-600 w-16 text-center">{slot.scheduled_staff}</span>
                      <span className={`text-xs font-medium w-16 text-center px-2 py-0.5 rounded border ${getGapColor(slot.staffing_gap)}`}>
                        {slot.staffing_gap > 0 ? `+${slot.staffing_gap}` : slot.staffing_gap}
                      </span>
                    </div>
                  );
                })}
              </div>
              {/* Legend */}
              <div className="flex items-center gap-6 mt-4 pt-4 border-t border-gray-100 text-xs text-gray-500">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-blue-500"></span> Required
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-green-500"></span> On Target
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-400"></span> Under
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-blue-400"></span> Over
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Role Breakdown + Summary + Recommendations */}
      {selectedDay && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Role Breakdown Table */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Role Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-2 text-gray-500 font-medium">Role</th>
                    <th className="text-center py-3 px-2 text-gray-500 font-medium">Required</th>
                    <th className="text-center py-3 px-2 text-gray-500 font-medium">Scheduled</th>
                    <th className="text-center py-3 px-2 text-gray-500 font-medium">Gap</th>
                    <th className="text-right py-3 px-2 text-gray-500 font-medium">Rate/hr</th>
                    <th className="text-right py-3 px-2 text-gray-500 font-medium">Total Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedDay.role_breakdown
                    .filter((r) => !searchStaff || r.role.toLowerCase().includes(searchStaff.toLowerCase()))
                    .map((role) => (
                      <tr key={role.role} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-2 font-medium text-gray-900 capitalize">{role.role}</td>
                        <td className="py-3 px-2 text-center text-gray-700">{role.required}</td>
                        <td className="py-3 px-2 text-center text-gray-700">{role.scheduled}</td>
                        <td className="py-3 px-2 text-center">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${getGapColor(role.gap)}`}>
                            {role.gap > 0 ? `+${role.gap}` : role.gap}
                          </span>
                        </td>
                        <td className="py-3 px-2 text-right text-gray-700">${role.hourly_rate.toFixed(2)}</td>
                        <td className="py-3 px-2 text-right text-gray-700 font-medium">${role.total_cost.toLocaleString()}</td>
                      </tr>
                    ))}
                </tbody>
                <tfoot>
                  <tr className="font-semibold bg-gray-50">
                    <td className="py-3 px-2 text-gray-900">Total</td>
                    <td className="py-3 px-2 text-center">{selectedDay.total_required_staff}</td>
                    <td className="py-3 px-2 text-center">{selectedDay.total_scheduled_staff}</td>
                    <td className="py-3 px-2 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${getGapColor(selectedDay.overall_gap)}`}>
                        {selectedDay.overall_gap > 0 ? `+${selectedDay.overall_gap}` : selectedDay.overall_gap}
                      </span>
                    </td>
                    <td className="py-3 px-2"></td>
                    <td className="py-3 px-2 text-right">${selectedDay.total_labor_cost.toLocaleString()}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Day Summary + Recommendations */}
          <div className="space-y-6">
            {/* Day Summary Card */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Day Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Total Hours</span>
                  <span className="font-bold text-gray-900">{selectedDay.summary.total_hours.toLocaleString()}h</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Labor Cost</span>
                  <span className="font-bold text-gray-900">${selectedDay.summary.total_labor_cost.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Forecasted Revenue</span>
                  <span className="font-bold text-gray-900">${selectedDay.total_forecasted_revenue.toLocaleString()}</span>
                </div>
                <div className="h-px bg-gray-100 my-2"></div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Labor %</span>
                  <span className={`text-lg font-bold ${getLaborPctColor(selectedDay.summary.labor_percentage)}`}>
                    {selectedDay.summary.labor_percentage.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Efficiency Score</span>
                  <span className={`text-lg font-bold ${getEfficiencyColor(selectedDay.summary.efficiency_score)}`}>
                    {selectedDay.summary.efficiency_score.toFixed(0)}%
                  </span>
                </div>
                {/* Labor % visual bar */}
                <div className="mt-2">
                  <div className="h-3 bg-gray-100 rounded-full overflow-hidden relative">
                    {/* Optimal zone marker */}
                    <div
                      className="absolute h-full bg-green-100 border-l border-r border-green-300"
                      style={{ left: '25%', width: '20%' }}
                    />
                    <div
                      className={`h-full rounded-full relative z-10 ${
                        selectedDay.summary.labor_percentage >= 25 && selectedDay.summary.labor_percentage <= 35
                          ? 'bg-green-500'
                          : selectedDay.summary.labor_percentage > 35
                          ? 'bg-red-500'
                          : 'bg-blue-500'
                      }`}
                      style={{ width: `${Math.min(selectedDay.summary.labor_percentage, 50) * 2}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                    <span>0%</span>
                    <span>25%</span>
                    <span>35%</span>
                    <span>50%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Recommendations */}
            {selectedDay.recommendations.length > 0 && (
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-6">
                <h4 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI Recommendations
                </h4>
                <ul className="space-y-2">
                  {selectedDay.recommendations.map((rec, i) => (
                    <li key={i} className="text-sm text-blue-800 flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {data?.schedules.length === 0 && (
        <div className="text-center py-16">
          <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-lg text-gray-500">No schedule data available</p>
          <p className="text-sm text-gray-400 mt-1">Adjust the labor target and try again</p>
        </div>
      )}
    </div>
  );
}
