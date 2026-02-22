'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface TrainingSession {
  session_id: string;
  staff_id: number;
  staff_name: string;
  started_at: string;
  ended_at?: string;
  orders_created: number;
  payments_processed: number;
  errors_made: number;
  score?: number;
  status: string;
}

interface TrainingConfig {
  enabled: boolean;
  require_pin: boolean;
  training_pin?: string;
  auto_end_minutes: number;
  show_hints: boolean;
  allow_void_practice: boolean;
  allow_discount_practice: boolean;
  allow_refund_practice: boolean;
}

const STATUS_BADGES: Record<string, { label: string; bg: string; text: string }> = {
  active: { label: 'Active', bg: 'bg-green-100', text: 'text-green-800' },
  completed: { label: 'Completed', bg: 'bg-blue-100', text: 'text-blue-800' },
  expired: { label: 'Expired', bg: 'bg-surface-100', text: 'text-surface-600' },
};

export default function TrainingModePage() {
  const [config, setConfig] = useState<TrainingConfig>({
    enabled: false,
    require_pin: true,
    training_pin: '0000',
    auto_end_minutes: 60,
    show_hints: true,
    allow_void_practice: true,
    allow_discount_practice: true,
    allow_refund_practice: false,
  });
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [activeSessions, setActiveSessions] = useState<TrainingSession[]>([]);
  const [stats, setStats] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [, setLoading] = useState(true);
  const [, setError] = useState<string | null>(null);
  const [showStartModal, setShowStartModal] = useState(false);
  const [newSessionStaffId, setNewSessionStaffId] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'sessions' | 'settings'>('overview');

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, sessionsRes, activeRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/training/config`, { credentials: 'include', headers: getAuthHeaders() }),
        fetch(`${API_URL}/training/sessions?limit=20`, { credentials: 'include', headers: getAuthHeaders() }),
        fetch(`${API_URL}/training/sessions/active`, { credentials: 'include', headers: getAuthHeaders() }),
        fetch(`${API_URL}/training/stats`, { credentials: 'include', headers: getAuthHeaders() }),
      ]);

      if (configRes.ok) {
        const data = await configRes.json();
        setConfig(prev => ({ ...prev, ...data }));
      }
      if (sessionsRes.ok) {
        const data = await sessionsRes.json();
        setSessions(data);
      }
      if (activeRes.ok) {
        const data = await activeRes.json();
        setActiveSessions(data);
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load training mode data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/training/config`, {
        credentials: 'include',
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(config),
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error saving config:', error);
    } finally {
      setSaving(false);
    }
  };

  const startSession = async () => {
    try {
      const res = await fetch(`${API_URL}/training/sessions`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ staff_id: parseInt(newSessionStaffId) }),
      });
      if (res.ok) {
        loadData();
        setShowStartModal(false);
        setNewSessionStaffId('');
      }
    } catch (error) {
      console.error('Error starting session:', error);
    }
  };

  const endSession = async (sessionId: string) => {
    try {
      const res = await fetch(`${API_URL}/training/sessions/${sessionId}/end`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error ending session:', error);
    }
  };

  const getStatusBadge = (status: string) => STATUS_BADGES[status] || STATUS_BADGES.completed;

  const getScoreColor = (score?: number) => {
    if (!score) return 'text-surface-500';
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <div className="bg-white border-b border-surface-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/settings" className="p-2 rounded-lg hover:bg-surface-100">
                <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <span className="text-xl">🎓</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-surface-900">Training Mode</h1>
                  <p className="text-sm text-surface-500">Sandbox environment for staff practice</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${config.enabled ? 'bg-green-100 text-green-800' : 'bg-surface-100 text-surface-600'}`}>
                <div className={`w-2 h-2 rounded-full ${config.enabled ? 'bg-green-500' : 'bg-surface-400'}`}></div>
                <span className="text-sm font-medium">{config.enabled ? 'Enabled' : 'Disabled'}</span>
              </div>
              <button
                onClick={() => setShowStartModal(true)}
                disabled={!config.enabled}
                className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
              >
                Start Training Session
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'overview', label: 'Overview', icon: '📊' },
            { id: 'sessions', label: 'Sessions', icon: '📋' },
            { id: 'settings', label: 'Settings', icon: '⚙️' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                activeTab === tab.id
                  ? 'bg-amber-500 text-gray-900'
                  : 'bg-white text-surface-600 hover:bg-surface-100'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl p-4 border border-surface-200">
                <div className="text-3xl font-bold text-green-600">{activeSessions.length}</div>
                <div className="text-sm text-surface-500">Active Sessions</div>
              </div>
              <div className="bg-white rounded-xl p-4 border border-surface-200">
                <div className="text-3xl font-bold text-surface-900">{stats.total_sessions || 0}</div>
                <div className="text-sm text-surface-500">Total Sessions</div>
              </div>
              <div className="bg-white rounded-xl p-4 border border-surface-200">
                <div className="text-3xl font-bold text-purple-600">{stats.avg_score || 0}%</div>
                <div className="text-sm text-surface-500">Average Score</div>
              </div>
              <div className="bg-white rounded-xl p-4 border border-surface-200">
                <div className="text-3xl font-bold text-amber-600">{stats.total_practice_orders || 0}</div>
                <div className="text-sm text-surface-500">Practice Orders</div>
              </div>
            </div>

            {/* Active Sessions */}
            {activeSessions.length > 0 && (
              <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
                <div className="p-4 border-b border-surface-100 bg-green-50">
                  <h3 className="font-semibold text-green-800 flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    Active Training Sessions
                  </h3>
                </div>
                <div className="divide-y divide-surface-100">
                  {activeSessions.map((session) => (
                    <div key={session.session_id} className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                          <span className="text-lg">👤</span>
                        </div>
                        <div>
                          <div className="font-medium text-surface-900">{session.staff_name}</div>
                          <div className="text-sm text-surface-500">
                            Started {new Date(session.started_at).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <div className="text-xl font-bold text-surface-900">{session.orders_created}</div>
                          <div className="text-xs text-surface-500">Orders</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xl font-bold text-surface-900">{session.payments_processed}</div>
                          <div className="text-xs text-surface-500">Payments</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xl font-bold text-red-600">{session.errors_made}</div>
                          <div className="text-xs text-surface-500">Errors</div>
                        </div>
                        <button
                          onClick={() => endSession(session.session_id)}
                          className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
                        >
                          End Session
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Training Features */}
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Training Mode Features</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-surface-50 rounded-lg">
                  <div className="text-2xl mb-2">📝</div>
                  <h4 className="font-medium text-surface-900">Practice Orders</h4>
                  <p className="text-sm text-surface-500">Create orders without affecting real data or inventory</p>
                </div>
                <div className="p-4 bg-surface-50 rounded-lg">
                  <div className="text-2xl mb-2">💳</div>
                  <h4 className="font-medium text-surface-900">Simulated Payments</h4>
                  <p className="text-sm text-surface-500">Process fake payments to learn the payment flow</p>
                </div>
                <div className="p-4 bg-surface-50 rounded-lg">
                  <div className="text-2xl mb-2">📊</div>
                  <h4 className="font-medium text-surface-900">Performance Tracking</h4>
                  <p className="text-sm text-surface-500">Track speed and accuracy with detailed scoring</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Staff</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Duration</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-surface-700">Orders</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-surface-700">Payments</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-surface-700">Errors</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-surface-700">Score</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Status</th>
                </tr>
              </thead>
              <tbody>
                {sessions.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-surface-500">
                      No training sessions yet. Start one to begin tracking.
                    </td>
                  </tr>
                ) : (
                  sessions.map((session) => {
                    const status = getStatusBadge(session.status);
                    const duration = session.ended_at
                      ? Math.round((new Date(session.ended_at).getTime() - new Date(session.started_at).getTime()) / 60000)
                      : null;
                    return (
                      <tr key={session.session_id} className="border-t border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <div className="font-medium text-surface-900">{session.staff_name}</div>
                        </td>
                        <td className="px-4 py-3 text-surface-600">
                          {new Date(session.started_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-surface-600">
                          {duration ? `${duration} min` : '-'}
                        </td>
                        <td className="px-4 py-3 text-center text-surface-900">{session.orders_created}</td>
                        <td className="px-4 py-3 text-center text-surface-900">{session.payments_processed}</td>
                        <td className="px-4 py-3 text-center text-red-600">{session.errors_made}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`font-bold ${getScoreColor(session.score)}`}>
                            {session.score ? `${session.score}%` : '-'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                            {status.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="font-semibold text-surface-900">Enable Training Mode</h3>
                  <p className="text-sm text-surface-500">Allow staff to practice in a sandbox environment</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.enabled}
                    onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-surface-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div>
                </label>
              </div>

              <div className="space-y-4 pt-4 border-t border-surface-100">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-surface-900">Require PIN to enter</div>
                    <div className="text-sm text-surface-500">Staff must enter PIN to start training</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.require_pin}
                    onChange={(e) => setConfig({ ...config, require_pin: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                </div>

                {config.require_pin && (
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Training PIN</label>
                    <input
                      type="text"
                      value={config.training_pin}
                      onChange={(e) => setConfig({ ...config, training_pin: e.target.value })}
                      className="w-32 px-3 py-2 border border-surface-200 rounded-lg font-mono text-center tracking-widest"
                      maxLength={6}
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Auto-end after (minutes)</label>
                  <input
                    type="number"
                    value={config.auto_end_minutes}
                    onChange={(e) => setConfig({ ...config, auto_end_minutes: parseInt(e.target.value) || 60 })}
                    className="w-32 px-3 py-2 border border-surface-200 rounded-lg"
                    min={15}
                    max={480}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-surface-900">Show helpful hints</div>
                    <div className="text-sm text-surface-500">Display tips during training</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.show_hints}
                    onChange={(e) => setConfig({ ...config, show_hints: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Practice Features</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-surface-900">Void practice</div>
                    <div className="text-sm text-surface-500">Allow voiding items in training</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.allow_void_practice}
                    onChange={(e) => setConfig({ ...config, allow_void_practice: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-surface-900">Discount practice</div>
                    <div className="text-sm text-surface-500">Allow applying discounts in training</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.allow_discount_practice}
                    onChange={(e) => setConfig({ ...config, allow_discount_practice: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-surface-900">Refund practice</div>
                    <div className="text-sm text-surface-500">Allow processing refunds in training</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={config.allow_refund_practice}
                    onChange={(e) => setConfig({ ...config, allow_refund_practice: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={saveConfig}
                disabled={saving}
                className="px-6 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Start Session Modal */}
      <AnimatePresence>
        {showStartModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-md w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Start Training Session</h2>
              </div>
              <div className="p-6">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Staff ID</label>
                  <input
                    type="number"
                    value={newSessionStaffId}
                    onChange={(e) => setNewSessionStaffId(e.target.value)}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Enter staff ID"
                  />
                </div>
                <div className="mt-4 p-4 bg-purple-50 rounded-lg">
                  <p className="text-sm text-purple-800">
                    Training sessions create a sandbox where orders and payments don&apos;t affect real data.
                  </p>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
                <button
                  onClick={() => setShowStartModal(false)}
                  className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={startSession}
                  disabled={!newSessionStaffId}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
                >
                  Start Session
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
