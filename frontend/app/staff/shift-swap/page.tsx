'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

// ── Types ───────────────────────────────────────────────────────────────────

interface ShiftSwap {
  id: number;
  requester_name: string;
  requester_id: number;
  original_shift_date: string;
  original_shift_time: string;
  original_role: string;
  target_shift_date: string;
  target_shift_time: string;
  target_staff_name: string | null;
  target_staff_id: number | null;
  reason: string;
  status: 'open' | 'pending' | 'approved' | 'rejected';
  created_at: string;
}

interface SwapFormData {
  original_shift_date: string;
  original_shift_time: string;
  original_role: string;
  target_shift_date: string;
  target_shift_time: string;
  target_staff_id: number | null;
  reason: string;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function ShiftSwapPage() {
  const [swaps, setSwaps] = useState<ShiftSwap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'marketplace' | 'pending' | 'create'>('marketplace');
  const [submitting, setSubmitting] = useState(false);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  const [form, setForm] = useState<SwapFormData>({
    original_shift_date: '',
    original_shift_time: '',
    original_role: '',
    target_shift_date: '',
    target_shift_time: '',
    target_staff_id: null,
    reason: '',
  });

  const loadSwaps = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ShiftSwap[]>('/staff/shift-swaps');
      setSwaps(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load shift swaps');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSwaps();
  }, [loadSwaps]);

  const createSwapRequest = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const newSwap = await api.post<ShiftSwap>('/staff/shift-swaps', form);
      setSwaps(prev => [newSwap, ...prev]);
      setForm({
        original_shift_date: '',
        original_shift_time: '',
        original_role: '',
        target_shift_date: '',
        target_shift_time: '',
        target_staff_id: null,
        reason: '',
      });
      setActiveTab('marketplace');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create swap request');
    } finally {
      setSubmitting(false);
    }
  };

  const approveSwap = async (id: number) => {
    setApprovingId(id);
    setError(null);
    try {
      await api.put(`/staff/shift-swaps/${id}/approve`);
      setSwaps(prev => prev.map(s => s.id === id ? { ...s, status: 'approved' as const } : s));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve swap');
    } finally {
      setApprovingId(null);
    }
  };

  const rejectSwap = async (id: number) => {
    setApprovingId(id);
    setError(null);
    try {
      await api.put(`/staff/shift-swaps/${id}/approve`, { action: 'reject' });
      setSwaps(prev => prev.map(s => s.id === id ? { ...s, status: 'rejected' as const } : s));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject swap');
    } finally {
      setApprovingId(null);
    }
  };

  const marketplace = swaps.filter(s => s.status === 'open');
  const pending = swaps.filter(s => s.status === 'pending');

  const statusBadge = (status: ShiftSwap['status']) => {
    const styles: Record<string, string> = {
      open: 'bg-blue-100 text-blue-800',
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-500">Loading shift swaps...</p>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Shift Swap Marketplace</h1>
          <p className="text-gray-500 mt-1">Find, request, and manage shift swaps with your team</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-bold">&times;</button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          {[
            { key: 'marketplace' as const, label: 'Available Swaps', count: marketplace.length },
            { key: 'pending' as const, label: 'Pending Approvals', count: pending.length },
            { key: 'create' as const, label: 'Request Swap', count: 0 },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Marketplace Tab */}
        {activeTab === 'marketplace' && (
          <div className="space-y-4">
            {marketplace.length === 0 ? (
              <div className="text-center py-16 text-gray-500">
                <div className="text-5xl mb-4">&#128260;</div>
                <h3 className="text-lg font-medium text-gray-700 mb-1">No available swaps</h3>
                <p>Be the first to post a shift swap request.</p>
              </div>
            ) : (
              marketplace.map(swap => (
                <div key={swap.id} className="bg-gray-50 rounded-lg border border-gray-200 p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-semibold text-gray-900">{swap.requester_name}</span>
                        {statusBadge(swap.status)}
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="text-gray-500 mb-1">Giving Up</div>
                          <div className="font-medium text-gray-900">{swap.original_shift_date}</div>
                          <div className="text-gray-600">{swap.original_shift_time} -- {swap.original_role}</div>
                        </div>
                        <div>
                          <div className="text-gray-500 mb-1">Looking For</div>
                          <div className="font-medium text-gray-900">{swap.target_shift_date || 'Any date'}</div>
                          <div className="text-gray-600">{swap.target_shift_time || 'Any time'}</div>
                        </div>
                      </div>
                      {swap.reason && (
                        <p className="mt-3 text-sm text-gray-600 italic">&quot;{swap.reason}&quot;</p>
                      )}
                    </div>
                    <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium">
                      Offer Swap
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Pending Tab */}
        {activeTab === 'pending' && (
          <div className="space-y-4">
            {pending.length === 0 ? (
              <div className="text-center py-16 text-gray-500">
                <div className="text-5xl mb-4">&#9989;</div>
                <h3 className="text-lg font-medium text-gray-700 mb-1">No pending approvals</h3>
                <p>All swap requests have been processed.</p>
              </div>
            ) : (
              pending.map(swap => (
                <div key={swap.id} className="bg-yellow-50 rounded-lg border border-yellow-200 p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-semibold text-gray-900">{swap.requester_name}</span>
                        <span className="text-gray-400">&#8596;</span>
                        <span className="font-semibold text-gray-900">{swap.target_staff_name || 'Unassigned'}</span>
                        {statusBadge(swap.status)}
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="text-gray-500 mb-1">Original Shift</div>
                          <div className="font-medium text-gray-900">{swap.original_shift_date}</div>
                          <div className="text-gray-600">{swap.original_shift_time}</div>
                        </div>
                        <div>
                          <div className="text-gray-500 mb-1">Swapped Shift</div>
                          <div className="font-medium text-gray-900">{swap.target_shift_date}</div>
                          <div className="text-gray-600">{swap.target_shift_time}</div>
                        </div>
                      </div>
                      {swap.reason && (
                        <p className="mt-3 text-sm text-gray-600 italic">&quot;{swap.reason}&quot;</p>
                      )}
                    </div>
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => approveSwap(swap.id)}
                        disabled={approvingId === swap.id}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50"
                      >
                        {approvingId === swap.id ? 'Processing...' : 'Approve'}
                      </button>
                      <button
                        onClick={() => rejectSwap(swap.id)}
                        disabled={approvingId === swap.id}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Create Tab */}
        {activeTab === 'create' && (
          <div className="max-w-lg mx-auto">
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Request a Shift Swap</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Your Shift Date
                  <input
                    type="date"
                    value={form.original_shift_date}
                    onChange={e => setForm({ ...form, original_shift_date: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Your Shift Time
                  <input
                    type="text"
                    value={form.original_shift_time}
                    onChange={e => setForm({ ...form, original_shift_time: e.target.value })}
                    placeholder="e.g., 9:00 AM - 5:00 PM"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Role / Position
                  <input
                    type="text"
                    value={form.original_role}
                    onChange={e => setForm({ ...form, original_role: e.target.value })}
                    placeholder="e.g., Server, Cook, Host"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                  </label>
                </div>
                <hr className="border-gray-200" />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Swap Date (optional)
                  <input
                    type="date"
                    value={form.target_shift_date}
                    onChange={e => setForm({ ...form, target_shift_date: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Swap Time (optional)
                  <input
                    type="text"
                    value={form.target_shift_time}
                    onChange={e => setForm({ ...form, target_shift_time: e.target.value })}
                    placeholder="e.g., Any, Morning, Evening"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reason
                  <textarea
                    value={form.reason}
                    onChange={e => setForm({ ...form, reason: e.target.value })}
                    rows={3}
                    placeholder="Why do you need this swap?"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 bg-white resize-none"
                  />
                  </label>
                </div>
                <button
                  onClick={createSwapRequest}
                  disabled={submitting || !form.original_shift_date || !form.original_shift_time}
                  className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Submitting...' : 'Post Swap Request'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
