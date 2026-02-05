'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

interface TipPool {
  id: number;
  date: string;
  shift: 'morning' | 'afternoon' | 'evening' | 'night';
  total_tips_cash: number;
  total_tips_card: number;
  total_tips: number;
  participants: number;
  distribution_method: 'equal' | 'hours' | 'points' | 'custom';
  status: 'pending' | 'distributed' | 'paid';
  distributed_at?: string;
  distributions: TipDistribution[];
}

interface TipDistribution {
  staff_id: number;
  staff_name: string;
  role: string;
  hours_worked: number;
  points: number;
  share_percentage: number;
  amount: number;
  paid: boolean;
}

interface TipStats {
  totalTipsToday: number;
  totalTipsWeek: number;
  totalTipsMonth: number;
  avgTipPerHour: number;
  pendingDistribution: number;
  topEarner: string;
}

const DISTRIBUTION_METHODS = [
  { value: 'equal', label: 'Equal Split', description: 'Tips divided equally among all staff' },
  { value: 'hours', label: 'By Hours', description: 'Tips distributed based on hours worked' },
  { value: 'points', label: 'Point System', description: 'Tips distributed by role-based points' },
  { value: 'custom', label: 'Custom', description: 'Manually set distribution percentages' },
];

const ROLE_POINTS: Record<string, number> = {
  'Server': 10,
  'Bartender': 10,
  'Host': 6,
  'Busser': 5,
  'Food Runner': 5,
  'Manager': 8,
};

export default function TipsManagerPage() {
  const [pools, setPools] = useState<TipPool[]>([]);
  const [stats, setStats] = useState<TipStats | null>(null);
  const [selectedPool, setSelectedPool] = useState<TipPool | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showDistributeModal, setShowDistributeModal] = useState(false);
  const [dateRange, setDateRange] = useState<'today' | 'week' | 'month'>('week');
  const [viewMode, setViewMode] = useState<'pools' | 'individual'>('pools');

  const [newPool, setNewPool] = useState({
    date: new Date().toISOString().split('T')[0],
    shift: 'evening' as TipPool['shift'],
    tips_cash: 0,
    tips_card: 0,
    distribution_method: 'hours' as TipPool['distribution_method'],
  });

  const [loading, setLoading] = useState(true);
  const [individualEarnings, setIndividualEarnings] = useState<{
    id: number;
    name: string;
    role: string;
    hours: number;
    earned: number;
    pending: number;
    paid: number;
  }[]>([]);

  useEffect(() => {
    loadTipPools();
    loadTipStats();
    loadIndividualEarnings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const loadTipPools = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/tips/pools?range=${dateRange}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setPools(data);
      }
    } catch (error) {
      console.error('Error loading tip pools:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTipStats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/tips/stats?range=${dateRange}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error loading tip stats:', error);
    }
  };

  const loadIndividualEarnings = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/tips/earnings?range=${dateRange}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setIndividualEarnings(data);
      }
    } catch (error) {
      console.error('Error loading individual earnings:', error);
    }
  };

  const getStatusColor = (status: TipPool['status']) => {
    switch (status) {
      case 'pending': return 'bg-warning-100 text-warning-700 border-warning-300';
      case 'distributed': return 'bg-primary-100 text-primary-700 border-primary-300';
      case 'paid': return 'bg-success-100 text-success-700 border-success-300';
    }
  };

  const getShiftColor = (shift: TipPool['shift']) => {
    switch (shift) {
      case 'morning': return 'bg-amber-100 text-amber-700';
      case 'afternoon': return 'bg-orange-100 text-orange-700';
      case 'evening': return 'bg-purple-100 text-purple-700';
      case 'night': return 'bg-indigo-100 text-indigo-700';
    }
  };

  const handleAddPool = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/tips/pools`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            date: newPool.date,
            shift: newPool.shift,
            total_tips_cash: newPool.tips_cash,
            total_tips_card: newPool.tips_card,
            distribution_method: newPool.distribution_method,
          }),
        }
      );

      if (response.ok) {
        setShowAddModal(false);
        setNewPool({
          date: new Date().toISOString().split('T')[0],
          shift: 'evening',
          tips_cash: 0,
          tips_card: 0,
          distribution_method: 'hours',
        });
        loadTipPools();
        loadTipStats();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create tip pool');
      }
    } catch (error) {
      console.error('Error creating tip pool:', error);
      alert('Failed to create tip pool');
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/staff/performance" className="p-2 hover:bg-surface-100 rounded-lg transition-colors">
            <svg className="w-5 h-5 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Tips Manager</h1>
            <p className="text-surface-600 mt-1">Track, pool & distribute tips fairly</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value as typeof dateRange)}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
          </select>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Tip Pool
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">Today</p>
            <p className="text-xl font-bold text-surface-900">${stats.totalTipsToday.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">This Week</p>
            <p className="text-xl font-bold text-surface-900">${stats.totalTipsWeek.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">This Month</p>
            <p className="text-xl font-bold text-surface-900">${stats.totalTipsMonth.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">Avg per Hour</p>
            <p className="text-xl font-bold text-primary-600">${stats.avgTipPerHour.toFixed(2)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-warning-200 shadow-sm bg-warning-50">
            <p className="text-xs text-warning-600 uppercase">Pending</p>
            <p className="text-xl font-bold text-warning-700">${stats.pendingDistribution.toLocaleString()}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-xs text-surface-500 uppercase">Top Earner</p>
            <p className="text-xl font-bold text-success-600">{stats.topEarner.split(' ')[0]}</p>
          </div>
        </div>
      )}

      {/* View Toggle */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => setViewMode('pools')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            viewMode === 'pools' ? 'bg-primary-600 text-white' : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
          }`}
        >
          Tip Pools
        </button>
        <button
          onClick={() => setViewMode('individual')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            viewMode === 'individual' ? 'bg-primary-600 text-white' : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
          }`}
        >
          Individual Earnings
        </button>
      </div>

      {viewMode === 'pools' ? (
        /* Tip Pools View */
        <div className="space-y-4">
          {pools.map((pool) => (
            <div
              key={pool.id}
              className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden"
            >
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-surface-900">
                      {new Date(pool.date).getDate()}
                    </p>
                    <p className="text-sm text-surface-500">
                      {new Date(pool.date).toLocaleDateString('en', { month: 'short' })}
                    </p>
                  </div>
                  <div className="h-12 w-px bg-surface-200" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getShiftColor(pool.shift)}`}>
                        {pool.shift.charAt(0).toUpperCase() + pool.shift.slice(1)}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(pool.status)}`}>
                        {pool.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-surface-500 mt-1">
                      {pool.participants} staff • {DISTRIBUTION_METHODS.find(m => m.value === pool.distribution_method)?.label}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-sm text-surface-500">Cash</p>
                    <p className="font-bold text-surface-900">${pool.total_tips_cash}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-surface-500">Card</p>
                    <p className="font-bold text-surface-900">${pool.total_tips_card}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-surface-500">Total</p>
                    <p className="text-2xl font-bold text-success-600">${pool.total_tips}</p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedPool(pool);
                      setShowDistributeModal(true);
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium ${
                      pool.status === 'pending'
                        ? 'bg-primary-600 text-gray-900 hover:bg-primary-700'
                        : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                    }`}
                  >
                    {pool.status === 'pending' ? 'Distribute' : 'View'}
                  </button>
                </div>
              </div>

              {/* Distribution Preview */}
              {pool.distributions.length > 0 && (
                <div className="border-t border-surface-200 p-4 bg-surface-50">
                  <div className="flex items-center gap-4 overflow-x-auto pb-2">
                    {pool.distributions.map((dist) => (
                      <div
                        key={dist.staff_id}
                        className="flex-shrink-0 flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-surface-200"
                      >
                        <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-xs font-semibold text-primary-700">
                          {dist.staff_name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-surface-900">{dist.staff_name.split(' ')[0]}</p>
                          <p className="text-xs text-surface-500">{dist.hours_worked}h</p>
                        </div>
                        <div className="text-right ml-2">
                          <p className="font-bold text-success-600">${dist.amount}</p>
                          <p className="text-xs text-surface-500">{dist.share_percentage.toFixed(1)}%</p>
                        </div>
                        {dist.paid && (
                          <span className="text-success-500 text-sm">✓</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        /* Individual Earnings View */
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-surface-200">
            <h2 className="font-semibold text-surface-900">Individual Tip Earnings</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Staff</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Role</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Hours</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Tips Earned</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Per Hour</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Pending</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Paid</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {individualEarnings.map((staff) => (
                  <tr key={staff.id} className="hover:bg-surface-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-sm font-semibold text-primary-700">
                          {staff.name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <span className="font-medium text-surface-900">{staff.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-1 bg-surface-100 text-surface-700 rounded text-sm">
                        {staff.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-surface-700">{staff.hours}h</td>
                    <td className="px-4 py-3 text-right font-bold text-surface-900">${staff.earned}</td>
                    <td className="px-4 py-3 text-right text-primary-600">
                      ${staff.hours > 0 ? (staff.earned / staff.hours).toFixed(2) : '0.00'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {staff.pending > 0 ? (
                        <span className="text-warning-600">${staff.pending}</span>
                      ) : (
                        <span className="text-surface-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-success-600">${staff.paid}</td>
                  </tr>
                ))}
                {individualEarnings.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-surface-500">
                      No earnings data available for this period
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Pool Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-lg mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">Add Tip Pool</h2>
              <p className="text-surface-600 mt-1">Record tips for a shift</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Date</label>
                  <input
                    type="date"
                    value={newPool.date}
                    onChange={(e) => setNewPool({ ...newPool, date: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Shift</label>
                  <select
                    value={newPool.shift}
                    onChange={(e) => setNewPool({ ...newPool, shift: e.target.value as TipPool['shift'] })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="morning">Morning</option>
                    <option value="afternoon">Afternoon</option>
                    <option value="evening">Evening</option>
                    <option value="night">Night</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Cash Tips ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newPool.tips_cash || ''}
                    onChange={(e) => setNewPool({ ...newPool, tips_cash: parseFloat(e.target.value) || 0 })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Card Tips ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newPool.tips_card || ''}
                    onChange={(e) => setNewPool({ ...newPool, tips_card: parseFloat(e.target.value) || 0 })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-2">Distribution Method</label>
                <div className="space-y-2">
                  {DISTRIBUTION_METHODS.map((method) => (
                    <label
                      key={method.value}
                      className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                        newPool.distribution_method === method.value
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-surface-200 hover:bg-surface-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="distribution_method"
                        value={method.value}
                        checked={newPool.distribution_method === method.value}
                        onChange={(e) => setNewPool({ ...newPool, distribution_method: e.target.value as TipPool['distribution_method'] })}
                        className="text-primary-600 focus:ring-primary-500"
                      />
                      <div className="ml-3">
                        <p className="font-medium text-surface-900">{method.label}</p>
                        <p className="text-sm text-surface-500">{method.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
              {(newPool.tips_cash > 0 || newPool.tips_card > 0) && (
                <div className="bg-success-50 rounded-lg p-4 text-center">
                  <p className="text-sm text-success-600">Total Tips</p>
                  <p className="text-2xl font-bold text-success-700">
                    ${(newPool.tips_cash + newPool.tips_card).toFixed(2)}
                  </p>
                </div>
              )}
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleAddPool}
                disabled={newPool.tips_cash === 0 && newPool.tips_card === 0}
                className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Pool
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Distribution Modal */}
      {showDistributeModal && selectedPool && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-2xl mx-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">
                Distribute Tips - {new Date(selectedPool.date).toLocaleDateString()} {selectedPool.shift}
              </h2>
              <p className="text-surface-600 mt-1">
                Total: ${selectedPool.total_tips} • Method: {DISTRIBUTION_METHODS.find(m => m.value === selectedPool.distribution_method)?.label}
              </p>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {selectedPool.distributions.map((dist, index) => (
                  <div key={dist.staff_id} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center text-sm font-semibold text-primary-700">
                        {dist.staff_name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <p className="font-medium text-surface-900">{dist.staff_name}</p>
                        <p className="text-sm text-surface-500">{dist.role} • {dist.hours_worked}h • {dist.points} pts</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm text-surface-500">Share</p>
                        <p className="font-medium">{dist.share_percentage.toFixed(1)}%</p>
                      </div>
                      <div className="text-right w-24">
                        <p className="text-sm text-surface-500">Amount</p>
                        <input
                          type="number"
                          value={dist.amount}
                          className="w-full px-2 py-1 text-right border border-surface-300 rounded focus:ring-2 focus:ring-primary-500 font-bold"
                        />
                      </div>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={dist.paid}
                          className="rounded text-success-600 focus:ring-success-500"
                        />
                        <span className="text-sm text-surface-600">Paid</span>
                      </label>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 p-4 bg-primary-50 rounded-lg flex items-center justify-between">
                <span className="font-semibold text-primary-900">Total Distribution</span>
                <span className="text-2xl font-bold text-primary-700">
                  ${selectedPool.distributions.reduce((s, d) => s + d.amount, 0)}
                </span>
              </div>
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowDistributeModal(false);
                  setSelectedPool(null);
                }}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              {selectedPool.status === 'pending' && (
                <button className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700">
                  Confirm Distribution
                </button>
              )}
              {selectedPool.status === 'distributed' && (
                <button className="px-4 py-2 bg-success-600 text-gray-900 rounded-lg hover:bg-success-700">
                  Mark All Paid
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
