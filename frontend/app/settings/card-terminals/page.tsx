'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Terminal {
  terminal_id: string;
  stripe_terminal_id?: string;
  name: string;
  terminal_type: string;
  serial_number?: string;
  location_id?: string;
  venue_id?: number;
  status: string;
  ip_address?: string;
  firmware_version?: string;
  last_seen?: string;
  registered_at: string;
}

interface TerminalType {
  id: string;
  name: string;
  description: string;
  features: string[];
}

interface Payment {
  payment_id: string;
  terminal_id: string;
  order_id: string;
  amount: number;
  currency: string;
  status: string;
  entry_mode?: string;
  card_brand?: string;
  card_last4?: string;
  cardholder_name?: string;
  auth_code?: string;
  receipt_url?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

const STATUS_BADGES = {
  online: { label: 'Online', bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-500' },
  offline: { label: 'Offline', bg: 'bg-surface-100', text: 'text-surface-600', dot: 'bg-surface-400' },
  busy: { label: 'Busy', bg: 'bg-amber-100', text: 'text-amber-800', dot: 'bg-amber-500' },
  error: { label: 'Error', bg: 'bg-red-100', text: 'text-red-800', dot: 'bg-red-500' },
};

const PAYMENT_STATUS_BADGES = {
  pending: { label: 'Pending', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  processing: { label: 'Processing', bg: 'bg-blue-100', text: 'text-blue-800' },
  completed: { label: 'Completed', bg: 'bg-green-100', text: 'text-green-800' },
  failed: { label: 'Failed', bg: 'bg-red-100', text: 'text-red-800' },
  canceled: { label: 'Canceled', bg: 'bg-surface-100', text: 'text-surface-600' },
};

const ENTRY_MODE_ICONS = {
  chip: '💳',
  contactless: '📶',
  swipe: '🔄',
  manual: '⌨️',
};

export default function CardTerminalsPage() {
  const [terminals, setTerminals] = useState<Terminal[]>([]);
  const [terminalTypes, setTerminalTypes] = useState<TerminalType[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [stats, setStats] = useState<any>({});
  const [showAddModal, setShowAddModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedTerminal, setSelectedTerminal] = useState<Terminal | null>(null);
  const [activeTab, setActiveTab] = useState<'terminals' | 'payments'>('terminals');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newTerminal, setNewTerminal] = useState({
    name: '',
    terminal_type: 'stripe_s700',
    registration_code: '',
  });

  const [testPayment, setTestPayment] = useState({
    terminal_id: '',
    order_id: `ORD-${Date.now()}`,
    amount: 1000,
  });

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [terminalsRes, typesRes, paymentsRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/card-terminals/terminals`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/card-terminals/terminal-types`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/card-terminals/payments?limit=20`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/card-terminals/stats`, { headers: getAuthHeaders() }),
      ]);

      if (terminalsRes.ok) {
        const data = await terminalsRes.json();
        setTerminals(data);
      }
      if (typesRes.ok) {
        const data = await typesRes.json();
        setTerminalTypes(data.types || []);
      }
      if (paymentsRes.ok) {
        const data = await paymentsRes.json();
        setPayments(data);
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load card terminal data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const registerTerminal = async () => {
    try {
      const res = await fetch(`${API_URL}/card-terminals/terminals`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(newTerminal),
      });

      if (res.ok) {
        loadData();
        setShowAddModal(false);
        setNewTerminal({ name: '', terminal_type: 'stripe_s700', registration_code: '' });
      }
    } catch (error) {
      console.error('Error registering terminal:', error);
    }
  };

  const deleteTerminal = async (terminalId: string) => {
    if (!confirm('Are you sure you want to delete this terminal?')) return;
    try {
      const res = await fetch(`${API_URL}/card-terminals/terminals/${terminalId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error deleting terminal:', error);
    }
  };

  const createTestPayment = async () => {
    try {
      const res = await fetch(`${API_URL}/card-terminals/payments`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(testPayment),
      });

      if (res.ok) {
        loadData();
        setShowPaymentModal(false);
        toast.success('Payment created! Present card to terminal.');
      }
    } catch (error) {
      console.error('Error creating payment:', error);
    }
  };

  const displayMessage = async (terminalId: string, message: string) => {
    try {
      await fetch(`${API_URL}/card-terminals/terminals/${terminalId}/display`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message }),
      });
    } catch (error) {
      console.error('Error displaying message:', error);
    }
  };

  const clearDisplay = async (terminalId: string) => {
    try {
      await fetch(`${API_URL}/card-terminals/terminals/${terminalId}/clear`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
    } catch (error) {
      console.error('Error clearing display:', error);
    }
  };

  const getTerminalType = (typeId: string) => terminalTypes.find(t => t.id === typeId);
  const getStatusBadge = (status: string) => STATUS_BADGES[status as keyof typeof STATUS_BADGES] || STATUS_BADGES.offline;
  const getPaymentStatusBadge = (status: string) => PAYMENT_STATUS_BADGES[status as keyof typeof PAYMENT_STATUS_BADGES] || PAYMENT_STATUS_BADGES.pending;

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
              <div>
                <h1 className="text-2xl font-bold text-surface-900">Card Terminals</h1>
                <p className="text-sm text-surface-500">Manage EMV card readers and payments</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  setTestPayment({ ...testPayment, terminal_id: terminals[0]?.terminal_id || '' });
                  setShowPaymentModal(true);
                }}
                disabled={terminals.length === 0}
                className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg disabled:opacity-50"
              >
                Test Payment
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Terminal
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Loading and Error States */}
      {loading && <PageLoading message="Loading card terminals..." />}

      {error && !loading && (
        <div className="max-w-7xl mx-auto px-6 py-6">
          <ErrorAlert message={error} onRetry={loadData} />
        </div>
      )}

      {/* Stats */}
      {!loading && !error && <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 rounded-lg">
                <span className="text-2xl">💳</span>
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900">{terminals.length}</div>
                <div className="text-sm text-surface-500">Total Terminals</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-100 rounded-lg">
                <span className="text-2xl">🟢</span>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {terminals.filter(t => t.status === 'online').length}
                </div>
                <div className="text-sm text-surface-500">Online</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-amber-100 rounded-lg">
                <span className="text-2xl">💵</span>
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900">
                  ${((stats.total_amount || 0) / 100).toLocaleString()}
                </div>
                <div className="text-sm text-surface-500">Today&apos;s Volume</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-100 rounded-lg">
                <span className="text-2xl">📶</span>
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900">{stats.transactions_today || 0}</div>
                <div className="text-sm text-surface-500">Transactions Today</div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'terminals', label: 'Terminals', icon: '💳' },
            { id: 'payments', label: 'Recent Payments', icon: '📋' },
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

        {/* Terminals Tab */}
        {activeTab === 'terminals' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {terminals.length === 0 ? (
              <div className="col-span-full bg-white rounded-xl p-12 border border-surface-200 text-center">
                <div className="text-6xl mb-4">💳</div>
                <h3 className="text-xl font-semibold text-surface-900 mb-2">No Terminals Registered</h3>
                <p className="text-surface-500 mb-6">Add your first card terminal to start accepting payments.</p>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Add Terminal
                </button>
              </div>
            ) : (
              terminals.map((terminal) => {
                const type = getTerminalType(terminal.terminal_type);
                const status = getStatusBadge(terminal.status);
                return (
                  <motion.div
                    key={terminal.terminal_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white rounded-xl border border-surface-200 overflow-hidden"
                  >
                    <div className="p-4 border-b border-surface-100">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 bg-surface-100 rounded-lg flex items-center justify-center text-2xl">
                            💳
                          </div>
                          <div>
                            <h3 className="font-semibold text-surface-900">{terminal.name}</h3>
                            <p className="text-sm text-surface-500">{type?.name || terminal.terminal_type}</p>
                          </div>
                        </div>
                        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full ${status.bg}`}>
                          <div className={`w-2 h-2 rounded-full ${status.dot}`}></div>
                          <span className={`text-xs font-medium ${status.text}`}>{status.label}</span>
                        </div>
                      </div>
                    </div>
                    <div className="p-4 space-y-2 text-sm">
                      {terminal.serial_number && (
                        <div className="flex justify-between">
                          <span className="text-surface-500">Serial</span>
                          <span className="font-mono text-surface-700">{terminal.serial_number}</span>
                        </div>
                      )}
                      {terminal.ip_address && (
                        <div className="flex justify-between">
                          <span className="text-surface-500">IP Address</span>
                          <span className="font-mono text-surface-700">{terminal.ip_address}</span>
                        </div>
                      )}
                      {terminal.firmware_version && (
                        <div className="flex justify-between">
                          <span className="text-surface-500">Firmware</span>
                          <span className="text-surface-700">{terminal.firmware_version}</span>
                        </div>
                      )}
                      {terminal.last_seen && (
                        <div className="flex justify-between">
                          <span className="text-surface-500">Last Seen</span>
                          <span className="text-surface-700">
                            {new Date(terminal.last_seen).toLocaleString()}
                          </span>
                        </div>
                      )}
                      {type?.features && (
                        <div className="flex gap-1 mt-2 pt-2 border-t border-surface-100">
                          {type.features.map((feature) => (
                            <span
                              key={feature}
                              className="px-2 py-0.5 bg-surface-100 rounded text-xs text-surface-600"
                            >
                              {feature}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="p-3 bg-surface-50 border-t border-surface-100 flex gap-2">
                      <button
                        onClick={() => displayMessage(terminal.terminal_id, 'Welcome!')}
                        className="flex-1 px-3 py-1.5 text-sm bg-white border border-surface-200 rounded-lg hover:bg-surface-100"
                      >
                        Test Display
                      </button>
                      <button
                        onClick={() => clearDisplay(terminal.terminal_id)}
                        className="px-3 py-1.5 text-sm bg-white border border-surface-200 rounded-lg hover:bg-surface-100"
                      >
                        Clear
                      </button>
                      <button
                        onClick={() => deleteTerminal(terminal.terminal_id)}
                        className="px-3 py-1.5 text-sm text-red-600 bg-white border border-surface-200 rounded-lg hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        )}

        {/* Payments Tab */}
        {activeTab === 'payments' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden overflow-x-auto">
            <table className="w-full min-w-[700px]">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Payment ID</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Terminal</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Method</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Card</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-surface-700">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Time</th>
                </tr>
              </thead>
              <tbody>
                {payments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-surface-500">
                      No payments yet
                    </td>
                  </tr>
                ) : (
                  payments.map((payment) => {
                    const terminal = terminals.find(t => t.terminal_id === payment.terminal_id);
                    const status = getPaymentStatusBadge(payment.status);
                    const entryIcon = ENTRY_MODE_ICONS[payment.entry_mode as keyof typeof ENTRY_MODE_ICONS] || '💳';
                    return (
                      <tr key={payment.payment_id} className="border-t border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <code className="text-xs font-mono text-surface-600">
                            {payment.payment_id.substring(0, 12)}...
                          </code>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-surface-900">{terminal?.name || 'Unknown'}</span>
                        </td>
                        <td className="px-4 py-3">
                          {payment.entry_mode && (
                            <span className="flex items-center gap-1">
                              <span>{entryIcon}</span>
                              <span className="text-surface-600 capitalize">{payment.entry_mode}</span>
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {payment.card_brand && payment.card_last4 && (
                            <span className="text-surface-600">
                              {payment.card_brand} ****{payment.card_last4}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-medium text-surface-900">
                          ${(payment.amount / 100).toFixed(2)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-surface-500">
                          {new Date(payment.created_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>}

      {/* Add Terminal Modal */}
      <AnimatePresence>
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Register New Terminal</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Terminal Name</label>
                  <input
                    type="text"
                    value={newTerminal.name}
                    onChange={(e) => setNewTerminal({ ...newTerminal, name: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Front Counter #1"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Terminal Type</label>
                  <div className="space-y-2">
                    {terminalTypes.map((type) => (
                      <button
                        key={type.id}
                        type="button"
                        onClick={() => setNewTerminal({ ...newTerminal, terminal_type: type.id })}
                        className={`w-full p-3 rounded-lg border-2 text-left transition-colors ${
                          newTerminal.terminal_type === type.id
                            ? 'border-amber-500 bg-amber-50'
                            : 'border-surface-200 hover:border-surface-300'
                        }`}
                      >
                        <div className="font-medium text-surface-900">{type.name}</div>
                        <div className="text-sm text-surface-500">{type.description}</div>
                        <div className="flex gap-1 mt-2">
                          {type.features.map((feature) => (
                            <span
                              key={feature}
                              className="px-2 py-0.5 bg-surface-100 rounded text-xs text-surface-600"
                            >
                              {feature}
                            </span>
                          ))}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Registration Code</label>
                  <input
                    type="text"
                    value={newTerminal.registration_code}
                    onChange={(e) => setNewTerminal({ ...newTerminal, registration_code: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500 font-mono"
                    placeholder="Enter code from terminal screen"
                  />
                  <p className="text-xs text-surface-500 mt-1">
                    The registration code is displayed on the terminal during setup
                  </p>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={registerTerminal}
                  disabled={!newTerminal.name}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
                >
                  Register Terminal
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Test Payment Modal */}
      <AnimatePresence>
        {showPaymentModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-md w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Create Test Payment</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Terminal</label>
                  <select
                    value={testPayment.terminal_id}
                    onChange={(e) => setTestPayment({ ...testPayment, terminal_id: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                  >
                    {terminals.map((t) => (
                      <option key={t.terminal_id} value={t.terminal_id}>{t.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Amount</label>
                  <div className="relative">
                    <span className="absolute left-3 top-2 text-surface-500">$</span>
                    <input
                      type="number"
                      value={(testPayment.amount / 100).toFixed(2)}
                      onChange={(e) => setTestPayment({ ...testPayment, amount: Math.round(parseFloat(e.target.value) * 100) || 0 })}
                      className="w-full pl-7 pr-3 py-2 border border-surface-200 rounded-lg"
                      step="0.01"
                      min="0.01"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Order ID</label>
                  <input
                    type="text"
                    value={testPayment.order_id}
                    onChange={(e) => setTestPayment({ ...testPayment, order_id: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg font-mono"
                  />
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
                <button
                  onClick={() => setShowPaymentModal(false)}
                  className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={createTestPayment}
                  disabled={!testPayment.terminal_id || testPayment.amount <= 0}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
                >
                  Create Payment
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
