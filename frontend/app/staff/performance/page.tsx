'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface StaffMember {
  id: number;
  name: string;
  role: string;
  avatar_initials: string;
  hired_date: string;
  status: 'active' | 'on_leave' | 'inactive';
}

interface PerformanceMetrics {
  staff_id: number;
  period: string;
  sales_amount: number;
  orders_count: number;
  avg_ticket: number;
  items_sold: number;
  tips_received: number;
  customer_rating: number;
  reviews_count: number;
  hours_worked: number;
  sales_per_hour: number;
  late_arrivals: number;
  absences: number;
  upsell_rate: number;
  table_turnover: number;
  comps_given: number;
  voids_processed: number;
}

interface PerformanceGoal {
  id: number;
  metric: string;
  target: number;
  current: number;
  unit: string;
  period: string;
}

interface LeaderboardEntry {
  rank: number;
  staff: StaffMember;
  metrics: PerformanceMetrics;
  change: number;
}

export default function StaffPerformancePage() {
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [selectedStaff, setSelectedStaff] = useState<number | null>(null);
  const [selectedMetrics, setSelectedMetrics] = useState<PerformanceMetrics | null>(null);
  const [period, setPeriod] = useState<'today' | 'week' | 'month' | 'quarter'>('month');
  const [sortBy, setSortBy] = useState<'sales' | 'rating' | 'efficiency' | 'tips'>('sales');
  const [showGoalsModal, setShowGoalsModal] = useState(false);

  const [loading, setLoading] = useState(true);
  const [goals, setGoals] = useState<{
    metric: string;
    value: number;
    unit: string;
  }[]>([
    { metric: 'Minimum Sales per Shift', value: 500, unit: '$' },
    { metric: 'Target Upsell Rate', value: 25, unit: '%' },
    { metric: 'Minimum Customer Rating', value: 4.5, unit: '' },
    { metric: 'Max Late Arrivals per Month', value: 2, unit: '' },
  ]);

  useEffect(() => {
    loadPerformanceData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, sortBy]);

  const loadPerformanceData = async () => {
    setLoading(true);
    try {
      await Promise.all([loadStaff(), loadLeaderboard(), loadGoals()]);
    } catch (err) {
      console.error('Failed to load performance data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadStaff = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/staff`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setStaff(data.map((s: any) => ({
          id: s.id,
          name: s.full_name,
          role: s.role,
          avatar_initials: s.full_name.split(' ').map((n: string) => n[0]).join('').toUpperCase(),
          hired_date: s.created_at,
          status: s.active ? 'active' : 'inactive',
        })));
      }
    } catch (error) {
      console.error('Error loading staff:', error);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/staff/performance/leaderboard?period=${period}&sort_by=${sortBy}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setLeaderboard(data);
      }
    } catch (error) {
      console.error('Error loading leaderboard:', error);
    }
  };

  const loadGoals = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/staff/performance/goals`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          setGoals(data);
        }
      }
    } catch (error) {
      console.error('Error loading goals:', error);
    }
  };

  const saveGoals = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/staff/performance/goals`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(goals),
        }
      );

      if (response.ok) {
        setShowGoalsModal(false);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save goals');
      }
    } catch (error) {
      console.error('Error saving goals:', error);
      toast.error('Failed to save goals');
    }
  };

  const getRankBadge = (rank: number) => {
    if (rank === 1) return { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: '🥇' };
    if (rank === 2) return { bg: 'bg-gray-100', text: 'text-gray-700', icon: '🥈' };
    if (rank === 3) return { bg: 'bg-amber-100', text: 'text-amber-700', icon: '🥉' };
    return { bg: 'bg-surface-100', text: 'text-surface-700', icon: `#${rank}` };
  };

  const getRatingColor = (rating: number) => {
    if (rating >= 4.5) return 'text-success-600';
    if (rating >= 4.0) return 'text-primary-600';
    if (rating >= 3.5) return 'text-warning-600';
    return 'text-error-600';
  };

  const totalSales = leaderboard.reduce((sum, e) => sum + e.metrics.sales_amount, 0);
  const totalTips = leaderboard.reduce((sum, e) => sum + e.metrics.tips_received, 0);
  const avgRating = leaderboard.reduce((sum, e) => sum + e.metrics.customer_rating, 0) / leaderboard.length;
  const topPerformer = leaderboard[0];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/staff" className="p-2 hover:bg-surface-100 rounded-lg transition-colors">
            <svg className="w-5 h-5 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Staff Performance</h1>
            <p className="text-surface-600 mt-1">Track sales, ratings & productivity metrics</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as typeof period)}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
          </select>
          <button
            onClick={() => setShowGoalsModal(true)}
            className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Set Goals
          </button>
          <Link
            href="/staff/tips"
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Tips Manager
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Total Sales</p>
          <p className="text-xl font-bold text-surface-900">${totalSales.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Total Tips</p>
          <p className="text-xl font-bold text-success-600">${totalTips.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Avg Rating</p>
          <p className={`text-xl font-bold ${getRatingColor(avgRating)}`}>
            {(avgRating ?? 0).toFixed(1)} <span className="text-yellow-500">★</span>
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Active Staff</p>
          <p className="text-xl font-bold text-surface-900">{staff.filter(s => s.status === 'active').length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Top Performer</p>
          <p className="text-xl font-bold text-primary-600">{topPerformer?.staff.name.split(' ')[0]}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Avg Sales/Hour</p>
          <p className="text-xl font-bold text-surface-900">
            ${((leaderboard.filter(l => l.metrics.sales_per_hour > 0).reduce((s, l) => s + l.metrics.sales_per_hour, 0) / leaderboard.filter(l => l.metrics.sales_per_hour > 0).length) ?? 0).toFixed(2)}
          </p>
        </div>
      </div>

      {/* Leaderboard */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm mb-6">
        <div className="p-4 border-b border-surface-200 flex items-center justify-between">
          <h2 className="font-semibold text-surface-900">Performance Leaderboard</h2>
          <div className="flex items-center gap-2">
            {[
              { key: 'sales', label: 'Sales' },
              { key: 'rating', label: 'Rating' },
              { key: 'efficiency', label: 'Efficiency' },
              { key: 'tips', label: 'Tips' },
            ].map((sort) => (
              <button
                key={sort.key}
                onClick={() => setSortBy(sort.key as typeof sortBy)}
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  sortBy === sort.key
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-surface-600 hover:bg-surface-100'
                }`}
              >
                {sort.label}
              </button>
            ))}
          </div>
        </div>
        <div className="divide-y divide-surface-100">
          {leaderboard.map((entry) => {
            const rankBadge = getRankBadge(entry.rank);
            const m = entry.metrics;

            return (
              <div
                key={entry.staff.id}
                onClick={() => {
                  setSelectedStaff(entry.staff.id);
                  setSelectedMetrics(entry.metrics);
                }}
                className="p-4 hover:bg-surface-50 cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  {/* Rank */}
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${rankBadge.bg} ${rankBadge.text}`}>
                    {entry.rank <= 3 ? rankBadge.icon : entry.rank}
                  </div>

                  {/* Avatar & Name */}
                  <div className="flex items-center gap-3 w-48">
                    <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center font-semibold text-primary-700">
                      {entry.staff.avatar_initials}
                    </div>
                    <div>
                      <p className="font-medium text-surface-900">{entry.staff.name}</p>
                      <p className="text-sm text-surface-500">{entry.staff.role}</p>
                    </div>
                  </div>

                  {/* Metrics Grid */}
                  <div className="flex-1 grid grid-cols-6 gap-4">
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Sales</p>
                      <p className="font-bold text-surface-900">${m.sales_amount.toLocaleString()}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Orders</p>
                      <p className="font-bold text-surface-900">{m.orders_count}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Avg Ticket</p>
                      <p className="font-bold text-surface-900">${(m.avg_ticket ?? 0).toFixed(2)}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Tips</p>
                      <p className="font-bold text-success-600">${m.tips_received}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Rating</p>
                      <p className={`font-bold ${getRatingColor(m.customer_rating)}`}>
                        {(m.customer_rating ?? 0).toFixed(1)} ★
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Sales/Hour</p>
                      <p className="font-bold text-primary-600">${(m.sales_per_hour ?? 0).toFixed(2)}</p>
                    </div>
                  </div>

                  {/* Trend */}
                  <div className="w-16 text-right">
                    {entry.change > 0 && <span className="text-success-600">↑ {entry.change}</span>}
                    {entry.change < 0 && <span className="text-error-600">↓ {Math.abs(entry.change)}</span>}
                    {entry.change === 0 && <span className="text-surface-400">—</span>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Performance Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attendance & Punctuality */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Attendance & Punctuality</h3>
          <div className="space-y-4">
            {leaderboard.slice(0, 5).map((entry) => (
              <div key={entry.staff.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-sm font-semibold text-primary-700">
                    {entry.staff.avatar_initials}
                  </div>
                  <span className="font-medium text-surface-900">{entry.staff.name}</span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className={`${entry.metrics.late_arrivals === 0 ? 'text-success-600' : 'text-warning-600'}`}>
                    {entry.metrics.late_arrivals} late
                  </span>
                  <span className={`${entry.metrics.absences === 0 ? 'text-success-600' : 'text-error-600'}`}>
                    {entry.metrics.absences} absent
                  </span>
                  <span className="text-surface-500">{entry.metrics.hours_worked}h worked</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upselling Performance */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Upselling Performance</h3>
          <div className="space-y-4">
            {leaderboard
              .filter(e => e.metrics.upsell_rate > 0)
              .sort((a, b) => b.metrics.upsell_rate - a.metrics.upsell_rate)
              .map((entry) => (
                <div key={entry.staff.id}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-sm font-semibold text-primary-700">
                        {entry.staff.avatar_initials}
                      </div>
                      <span className="font-medium text-surface-900">{entry.staff.name}</span>
                    </div>
                    <span className="font-bold text-primary-600">{entry.metrics.upsell_rate}%</span>
                  </div>
                  <div className="ml-11 h-2 bg-surface-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full"
                      style={{ width: `${(entry.metrics.upsell_rate / 35) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Customer Reviews */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Customer Reviews</h3>
          <div className="space-y-4">
            {leaderboard
              .sort((a, b) => b.metrics.reviews_count - a.metrics.reviews_count)
              .slice(0, 5)
              .map((entry) => (
                <div key={entry.staff.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-sm font-semibold text-primary-700">
                      {entry.staff.avatar_initials}
                    </div>
                    <div>
                      <p className="font-medium text-surface-900">{entry.staff.name}</p>
                      <p className="text-sm text-surface-500">{entry.metrics.reviews_count} reviews</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <span
                        key={star}
                        className={`text-lg ${star <= Math.round(entry.metrics.customer_rating) ? 'text-yellow-400' : 'text-surface-300'}`}
                      >
                        ★
                      </span>
                    ))}
                    <span className="ml-2 font-bold text-surface-900">{(entry.metrics.customer_rating ?? 0).toFixed(1)}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Issues & Flags */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Comps & Voids Tracking</h3>
          <div className="space-y-4">
            {leaderboard
              .filter(e => e.metrics.comps_given > 0 || e.metrics.voids_processed > 0)
              .sort((a, b) => (b.metrics.comps_given + b.metrics.voids_processed) - (a.metrics.comps_given + a.metrics.voids_processed))
              .map((entry) => (
                <div key={entry.staff.id} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-sm font-semibold text-primary-700">
                      {entry.staff.avatar_initials}
                    </div>
                    <span className="font-medium text-surface-900">{entry.staff.name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Comps</p>
                      <p className={`font-bold ${entry.metrics.comps_given > 5 ? 'text-warning-600' : 'text-surface-900'}`}>
                        {entry.metrics.comps_given}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-surface-500">Voids</p>
                      <p className={`font-bold ${entry.metrics.voids_processed > 4 ? 'text-error-600' : 'text-surface-900'}`}>
                        {entry.metrics.voids_processed}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Goals Modal */}
      {showGoalsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-lg mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">Performance Goals</h2>
              <p className="text-surface-600 mt-1">Set targets for your team</p>
            </div>
            <div className="p-6 space-y-4">
              {goals.map((goal, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-surface-700">{goal.metric}</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={goal.value}
                      onChange={(e) => {
                        const newGoals = [...goals];
                        newGoals[index].value = parseFloat(e.target.value) || 0;
                        setGoals(newGoals);
                      }}
                      className="w-20 px-3 py-1 border border-surface-300 rounded-lg text-right focus:ring-2 focus:ring-primary-500"
                    />
                    <span className="text-surface-500 w-6">{goal.unit}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowGoalsModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={saveGoals}
                className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
              >
                Save Goals
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
