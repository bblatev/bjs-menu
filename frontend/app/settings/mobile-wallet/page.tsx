'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface WalletConfig {
  apple_pay_enabled: boolean;
  google_pay_enabled: boolean;
  merchant_name: string;
  merchant_country: string;
  supported_networks: string[];
  require_billing_address: boolean;
  require_shipping_address: boolean;
}

interface PaymentSession {
  session_id: string;
  order_id: string;
  amount: number;
  currency: string;
  wallet_type: string;
  status: string;
  created_at: string;
  completed_at?: string;
}

const CARD_NETWORKS = [
  { id: 'visa', name: 'Visa', icon: '💳' },
  { id: 'mastercard', name: 'Mastercard', icon: '💳' },
  { id: 'amex', name: 'American Express', icon: '💳' },
  { id: 'discover', name: 'Discover', icon: '💳' },
  { id: 'jcb', name: 'JCB', icon: '💳' },
];

const COUNTRIES = [
  { code: 'US', name: 'United States' },
  { code: 'CA', name: 'Canada' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'AU', name: 'Australia' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'ES', name: 'Spain' },
  { code: 'IT', name: 'Italy' },
  { code: 'BG', name: 'Bulgaria' },
];

const STATUS_BADGES: Record<string, { label: string; bg: string; text: string }> = {
  pending: { label: 'Pending', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  authorized: { label: 'Authorized', bg: 'bg-blue-100', text: 'text-blue-800' },
  completed: { label: 'Completed', bg: 'bg-green-100', text: 'text-green-800' },
  failed: { label: 'Failed', bg: 'bg-red-100', text: 'text-red-800' },
  cancelled: { label: 'Cancelled', bg: 'bg-surface-100', text: 'text-surface-600' },
};

export default function MobileWalletPage() {
  const [config, setConfig] = useState<WalletConfig>({
    apple_pay_enabled: false,
    google_pay_enabled: false,
    merchant_name: '',
    merchant_country: 'US',
    supported_networks: ['visa', 'mastercard'],
    require_billing_address: false,
    require_shipping_address: false,
  });
  const [sessions, setSessions] = useState<PaymentSession[]>([]);
  const [stats, setStats] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'config' | 'transactions'>('config');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, sessionsRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/mobile-wallet/config`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/mobile-wallet/payments?limit=20`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/mobile-wallet/stats`, { headers: getAuthHeaders() }),
      ]);

      if (configRes.ok) {
        const data = await configRes.json();
        setConfig(prev => ({ ...prev, ...data }));
      }
      if (sessionsRes.ok) {
        const data = await sessionsRes.json();
        setSessions(data);
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load mobile wallet settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/mobile-wallet/config`, {
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

  const toggleNetwork = (networkId: string) => {
    setConfig(prev => ({
      ...prev,
      supported_networks: prev.supported_networks.includes(networkId)
        ? prev.supported_networks.filter(n => n !== networkId)
        : [...prev.supported_networks, networkId],
    }));
  };

  const getStatusBadge = (status: string) => STATUS_BADGES[status] || STATUS_BADGES.pending;

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
                <h1 className="text-2xl font-bold text-surface-900">Mobile Wallet Payments</h1>
                <p className="text-sm text-surface-500">Apple Pay & Google Pay configuration</p>
              </div>
            </div>
            <button
              onClick={saveConfig}
              disabled={saving}
              className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gray-900 rounded-lg">
                <span className="text-xl"></span>
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900">{stats.apple_pay_count || 0}</div>
                <div className="text-sm text-surface-500">Apple Pay Today</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-white border border-surface-200 rounded-lg">
                <span className="text-xl">G</span>
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900">{stats.google_pay_count || 0}</div>
                <div className="text-sm text-surface-500">Google Pay Today</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-2xl font-bold text-green-600">
              ${((stats.total_volume || 0) / 100).toLocaleString()}
            </div>
            <div className="text-sm text-surface-500">Total Volume Today</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-2xl font-bold text-surface-900">{stats.success_rate || 0}%</div>
            <div className="text-sm text-surface-500">Success Rate</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'config', label: 'Configuration', icon: '⚙️' },
            { id: 'transactions', label: 'Transactions', icon: '📋' },
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

        {/* Config Tab */}
        {activeTab === 'config' && (
          <div className="space-y-6">
            {/* Wallet Toggles */}
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Payment Methods</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Apple Pay */}
                <div
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    config.apple_pay_enabled
                      ? 'border-gray-900 bg-gray-50'
                      : 'border-surface-200 hover:border-surface-300'
                  }`}
                  onClick={() => setConfig({ ...config, apple_pay_enabled: !config.apple_pay_enabled })}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-gray-900 rounded-xl flex items-center justify-center text-white text-xl">

                      </div>
                      <div>
                        <div className="font-semibold text-surface-900">Apple Pay</div>
                        <div className="text-sm text-surface-500">iOS devices & Safari</div>
                      </div>
                    </div>
                    <div className={`w-12 h-6 rounded-full transition-colors ${
                      config.apple_pay_enabled ? 'bg-green-500' : 'bg-surface-200'
                    }`}>
                      <div className={`w-5 h-5 bg-white rounded-full shadow-sm transition-transform mt-0.5 ${
                        config.apple_pay_enabled ? 'translate-x-6 ml-0.5' : 'translate-x-0.5'
                      }`}></div>
                    </div>
                  </div>
                  {config.apple_pay_enabled && (
                    <div className="text-xs text-green-600 flex items-center gap-1">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Enabled
                    </div>
                  )}
                </div>

                {/* Google Pay */}
                <div
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    config.google_pay_enabled
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-surface-200 hover:border-surface-300'
                  }`}
                  onClick={() => setConfig({ ...config, google_pay_enabled: !config.google_pay_enabled })}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-white border border-surface-200 rounded-xl flex items-center justify-center">
                        <span className="text-xl font-bold text-blue-500">G</span>
                      </div>
                      <div>
                        <div className="font-semibold text-surface-900">Google Pay</div>
                        <div className="text-sm text-surface-500">Android & Chrome</div>
                      </div>
                    </div>
                    <div className={`w-12 h-6 rounded-full transition-colors ${
                      config.google_pay_enabled ? 'bg-green-500' : 'bg-surface-200'
                    }`}>
                      <div className={`w-5 h-5 bg-white rounded-full shadow-sm transition-transform mt-0.5 ${
                        config.google_pay_enabled ? 'translate-x-6 ml-0.5' : 'translate-x-0.5'
                      }`}></div>
                    </div>
                  </div>
                  {config.google_pay_enabled && (
                    <div className="text-xs text-green-600 flex items-center gap-1">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Enabled
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Merchant Settings */}
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Merchant Settings</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Merchant Name</label>
                  <input
                    type="text"
                    value={config.merchant_name}
                    onChange={(e) => setConfig({ ...config, merchant_name: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Your Restaurant Name"
                  />
                  <p className="text-xs text-surface-500 mt-1">Shown on payment sheets</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Country</label>
                  <select
                    value={config.merchant_country}
                    onChange={(e) => setConfig({ ...config, merchant_country: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                  >
                    {COUNTRIES.map((c) => (
                      <option key={c.code} value={c.code}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Card Networks */}
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Accepted Card Networks</h3>
              <div className="flex flex-wrap gap-2">
                {CARD_NETWORKS.map((network) => (
                  <button
                    key={network.id}
                    onClick={() => toggleNetwork(network.id)}
                    className={`px-4 py-2 rounded-lg border-2 flex items-center gap-2 transition-colors ${
                      config.supported_networks.includes(network.id)
                        ? 'border-amber-500 bg-amber-50 text-amber-800'
                        : 'border-surface-200 text-surface-600 hover:border-surface-300'
                    }`}
                  >
                    <span>{network.icon}</span>
                    <span>{network.name}</span>
                    {config.supported_networks.includes(network.id) && (
                      <svg className="w-4 h-4 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Additional Options */}
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Additional Options</h3>
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.require_billing_address}
                    onChange={(e) => setConfig({ ...config, require_billing_address: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                  <div>
                    <div className="font-medium text-surface-900">Require Billing Address</div>
                    <div className="text-sm text-surface-500">Request billing address during checkout</div>
                  </div>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.require_shipping_address}
                    onChange={(e) => setConfig({ ...config, require_shipping_address: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                  <div>
                    <div className="font-medium text-surface-900">Require Shipping Address</div>
                    <div className="text-sm text-surface-500">For delivery orders</div>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Session</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Order</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Wallet</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-surface-700">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Time</th>
                </tr>
              </thead>
              <tbody>
                {sessions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-surface-500">
                      No mobile wallet transactions yet.
                    </td>
                  </tr>
                ) : (
                  sessions.map((session) => {
                    const status = getStatusBadge(session.status);
                    return (
                      <tr key={session.session_id} className="border-t border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <code className="text-xs font-mono text-surface-600">
                            {session.session_id.substring(0, 12)}...
                          </code>
                        </td>
                        <td className="px-4 py-3 text-surface-900">{session.order_id}</td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-2">
                            {session.wallet_type === 'apple_pay' ? (
                              <>
                                <span className="w-6 h-6 bg-gray-900 rounded flex items-center justify-center text-white text-xs"></span>
                                <span>Apple Pay</span>
                              </>
                            ) : (
                              <>
                                <span className="w-6 h-6 bg-white border border-surface-200 rounded flex items-center justify-center text-blue-500 text-xs font-bold">G</span>
                                <span>Google Pay</span>
                              </>
                            )}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right font-medium text-surface-900">
                          ${((session.amount / 100) ?? 0).toFixed(2)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-surface-500">
                          {new Date(session.created_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
