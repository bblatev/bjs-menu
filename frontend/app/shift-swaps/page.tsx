'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface ShiftSwap {
  id: number;
  shift_id: number;
  original_owner: string;
  original_owner_id: number;
  date: string;
  start_time: string;
  end_time: string;
  role: string;
  reason: string;
  status: 'pending' | 'accepted' | 'approved' | 'rejected';
  claimed_by: string | null;
  claimed_by_id: number | null;
  manager_note: string | null;
  created_at: string;
  updated_at: string;
}

interface NewSwapForm {
  shift_id: string;
  reason: string;
}

// ── Constants ───────────────────────────────────────────────────────────────

const STATUS_BADGES: Record<string, { classes: string; label: string }> = {
  pending: { classes: 'bg-yellow-100 text-yellow-700', label: 'Pending' },
  accepted: { classes: 'bg-blue-100 text-blue-700', label: 'Accepted' },
  approved: { classes: 'bg-green-100 text-green-700', label: 'Approved' },
  rejected: { classes: 'bg-red-100 text-red-700', label: 'Rejected' },
};

// ── Component ───────────────────────────────────────────────────────────────

export default function ShiftSwapsPage() {
  const [swaps, setSwaps] = useState<ShiftSwap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // View / Filters
  const [activeTab, setActiveTab] = useState<'available' | 'my_requests' | 'manager'>('available');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRole, setFilterRole] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');

  // Swap creation
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [swapForm, setSwapForm] = useState<NewSwapForm>({
    shift_id: '',
    reason: '',
  });

  // Actions
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  // Simulated current user (in real app this comes from auth context)
  const currentUserId = 1;
  const _isManager = true;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ShiftSwap[]>('/staff/shift-swaps?venue_id=1');
      setSwaps(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load shift swaps');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const createSwap = async () => {
    if (!swapForm.shift_id || !swapForm.reason.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.post('/staff/shift-swaps', {
        shift_id: parseInt(swapForm.shift_id),
        reason: swapForm.reason,
      });
      setShowCreateModal(false);
      setSwapForm({ shift_id: '', reason: '' });
      setSuccessMsg('Shift swap request created');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create swap request');
    } finally {
      setCreating(false);
    }
  };

  const acceptSwap = async (swapId: number) => {
    setActionLoading(swapId);
    setError(null);
    try {
      await api.put(`/staff/shift-swaps/${swapId}/accept`);
      setSuccessMsg('Shift swap accepted');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept swap');
    } finally {
      setActionLoading(null);
    }
  };

  const approveSwap = async (swapId: number) => {
    setActionLoading(swapId);
    setError(null);
    try {
      await api.put(`/staff/shift-swaps/${swapId}/accept`);
      setSuccessMsg('Shift swap approved by manager');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve swap');
    } finally {
      setActionLoading(null);
    }
  };

  const rejectSwap = async (swapId: number) => {
    setActionLoading(swapId);
    setError(null);
    try {
      await api.put(`/staff/shift-swaps/${swapId}/accept`);
      setSuccessMsg('Shift swap rejected');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject swap');
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr: string): string => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const formatTime = (timeStr: string): string => {
    try {
      if (timeStr.includes('T')) {
        const d = new Date(timeStr);
        return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      }
      return timeStr;
    } catch {
      return timeStr;
    }
  };

  // Filter logic based on tab
  const getFilteredSwaps = (): ShiftSwap[] => {
    let filtered = swaps;

    // Tab-based filtering
    if (activeTab === 'available') {
      filtered = filtered.filter((s) => s.status === 'pending' && s.original_owner_id !== currentUserId);
    } else if (activeTab === 'my_requests') {
      filtered = filtered.filter((s) => s.original_owner_id === currentUserId);
    } else if (activeTab === 'manager') {
      filtered = filtered.filter((s) => s.status === 'accepted');
    }

    // Role filter
    if (filterRole !== 'all') {
      filtered = filtered.filter((s) => s.role.toLowerCase() === filterRole.toLowerCase());
    }

    // Status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter((s) => s.status === filterStatus);
    }

    // Search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.original_owner.toLowerCase().includes(q) ||
          s.role.toLowerCase().includes(q) ||
          s.reason.toLowerCase().includes(q) ||
          (s.claimed_by && s.claimed_by.toLowerCase().includes(q))
      );
    }

    return filtered;
  };

  // Extract unique roles
  const uniqueRoles = Array.from(new Set(swaps.map((s) => s.role)));

  const filteredSwaps = getFilteredSwaps();

  // Counts
  const availableCount = swaps.filter((s) => s.status === 'pending' && s.original_owner_id !== currentUserId).length;
  const myRequestsCount = swaps.filter((s) => s.original_owner_id === currentUserId).length;
  const needsApprovalCount = swaps.filter((s) => s.status === 'accepted').length;

  // ── Loading ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading shift swaps...</p>
        </div>
      </div>
    );
  }

  if (error && swaps.length === 0) {
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Shift Swap Marketplace</h1>
            <p className="text-gray-500 mt-1">Request, claim, and manage shift swaps with your team</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Request Swap
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
            {successMsg}
            <button onClick={() => setSuccessMsg(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Total Swaps</p>
            <p className="text-2xl font-bold text-gray-900">{swaps.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Available</p>
            <p className="text-2xl font-bold text-yellow-600">{availableCount}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Needs Approval</p>
            <p className="text-2xl font-bold text-blue-600">{needsApprovalCount}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <p className="text-sm text-gray-500">Approved</p>
            <p className="text-2xl font-bold text-green-600">
              {swaps.filter((s) => s.status === 'approved').length}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          <button
            onClick={() => setActiveTab('available')}
            className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'available'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Available Shifts
            {availableCount > 0 && (
              <span className="ml-2 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded-full text-xs">
                {availableCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('my_requests')}
            className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'my_requests'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            My Requests
            {myRequestsCount > 0 && (
              <span className="ml-2 px-1.5 py-0.5 bg-gray-200 text-gray-700 rounded-full text-xs">
                {myRequestsCount}
              </span>
            )}
          </button>
          {_isManager && (
            <button
              onClick={() => setActiveTab('manager')}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'manager'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Manager Approval
              {needsApprovalCount > 0 && (
                <span className="ml-2 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
                  {needsApprovalCount}
                </span>
              )}
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, role, or reason..."
            className="flex-1 min-w-[200px] px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <select
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="all">All Roles</option>
            {uniqueRoles.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          {activeTab === 'my_requests' && (
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="accepted">Accepted</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          )}
        </div>

        {/* Swap Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSwaps.length === 0 ? (
            <div className="col-span-full text-center py-12 text-gray-500">
              {activeTab === 'available'
                ? 'No shifts available for swapping right now.'
                : activeTab === 'my_requests'
                ? 'You have no swap requests.'
                : 'No swaps awaiting manager approval.'}
            </div>
          ) : (
            filteredSwaps.map((swap) => {
              const badge = STATUS_BADGES[swap.status] || STATUS_BADGES.pending;
              const isActionLoading = actionLoading === swap.id;
              return (
                <div
                  key={swap.id}
                  className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 hover:shadow-md transition-shadow"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900">{swap.original_owner}</h3>
                      <p className="text-sm text-gray-500">{swap.role}</p>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.classes}`}>
                      {badge.label}
                    </span>
                  </div>

                  {/* Date / Time */}
                  <div className="bg-gray-50 rounded-lg p-3 mb-3">
                    <div className="flex items-center gap-2 mb-1">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-900">{formatDate(swap.date)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-sm text-gray-700">
                        {formatTime(swap.start_time)} - {formatTime(swap.end_time)}
                      </span>
                    </div>
                  </div>

                  {/* Reason */}
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-0.5">Reason:</p>
                    <p className="text-sm text-gray-700">{swap.reason}</p>
                  </div>

                  {/* Claimed By */}
                  {swap.claimed_by && (
                    <div className="mb-3 px-3 py-2 bg-blue-50 rounded-lg">
                      <p className="text-xs text-blue-700">
                        Claimed by: <span className="font-medium">{swap.claimed_by}</span>
                      </p>
                    </div>
                  )}

                  {/* Manager Note */}
                  {swap.manager_note && (
                    <div className="mb-3 px-3 py-2 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-600">
                        Manager note: <span className="italic">{swap.manager_note}</span>
                      </p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="pt-3 border-t border-gray-100">
                    {/* Available tab: Claim button */}
                    {activeTab === 'available' && swap.status === 'pending' && (
                      <button
                        onClick={() => acceptSwap(swap.id)}
                        disabled={isActionLoading}
                        className="w-full py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 text-sm"
                      >
                        {isActionLoading ? (
                          <span className="flex items-center justify-center gap-2">
                            <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                            Claiming...
                          </span>
                        ) : (
                          'Claim This Shift'
                        )}
                      </button>
                    )}

                    {/* My requests tab: status info */}
                    {activeTab === 'my_requests' && (
                      <div className="text-xs text-gray-500 text-center">
                        {swap.status === 'pending' && 'Waiting for someone to claim...'}
                        {swap.status === 'accepted' && `Claimed by ${swap.claimed_by || 'someone'} - awaiting manager approval`}
                        {swap.status === 'approved' && 'Swap approved! Shift has been transferred.'}
                        {swap.status === 'rejected' && 'Swap was rejected by manager.'}
                      </div>
                    )}

                    {/* Manager tab: approve/reject */}
                    {activeTab === 'manager' && swap.status === 'accepted' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => rejectSwap(swap.id)}
                          disabled={isActionLoading}
                          className="flex-1 py-2 bg-white border border-red-300 text-red-700 rounded-lg font-medium hover:bg-red-50 transition-colors disabled:opacity-50 text-sm"
                        >
                          Reject
                        </button>
                        <button
                          onClick={() => approveSwap(swap.id)}
                          disabled={isActionLoading}
                          className="flex-1 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 text-sm"
                        >
                          {isActionLoading ? 'Processing...' : 'Approve'}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Timestamp */}
                  <div className="mt-2 text-right">
                    <span className="text-xs text-gray-400">
                      Posted {formatDate(swap.created_at)}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Create Swap Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-xl font-bold text-gray-900">Request Shift Swap</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                  aria-label="Close"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Shift ID</label>
                  <input
                    type="number"
                    value={swapForm.shift_id}
                    onChange={(e) => setSwapForm({ ...swapForm, shift_id: e.target.value })}
                    placeholder="Enter shift ID to swap"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  <p className="text-xs text-gray-400 mt-1">Find your shift ID from the Shifts page</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
                  <textarea
                    value={swapForm.reason}
                    onChange={(e) => setSwapForm({ ...swapForm, reason: e.target.value })}
                    placeholder="Why do you need to swap this shift?"
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white resize-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={createSwap}
                  disabled={creating || !swapForm.shift_id || !swapForm.reason.trim()}
                  className="flex-1 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50"
                >
                  {creating ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
