'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface GoogleReserveConfig {
  merchant_id: string;
  service_id: string;
  api_key: string;
  is_enabled: boolean;
  auto_confirm: boolean;
  sync_availability: boolean;
  max_party_size: number;
  min_lead_time_hours: number;
  max_lead_time_days: number;
  last_sync?: string;
}

interface Booking {
  booking_id: string;
  google_booking_id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  party_size: number;
  booking_date: string;
  booking_time: string;
  status: string;
  created_at: string;
  confirmed_at?: string;
}

const STATUS_BADGES: Record<string, { label: string; bg: string; text: string }> = {
  pending: { label: 'Pending', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  confirmed: { label: 'Confirmed', bg: 'bg-green-100', text: 'text-green-800' },
  cancelled: { label: 'Cancelled', bg: 'bg-red-100', text: 'text-red-800' },
  completed: { label: 'Completed', bg: 'bg-surface-100', text: 'text-surface-600' },
  no_show: { label: 'No Show', bg: 'bg-orange-100', text: 'text-orange-800' },
};

export default function GoogleReservePage() {
  const [config, setConfig] = useState<GoogleReserveConfig>({
    merchant_id: '',
    service_id: '',
    api_key: '',
    is_enabled: false,
    auto_confirm: true,
    sync_availability: true,
    max_party_size: 10,
    min_lead_time_hours: 2,
    max_lead_time_days: 30,
  });
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [stats, setStats] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<'bookings' | 'settings'>('bookings');
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, bookingsRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/google-reserve/config`),
        fetch(`${API_URL}/google-reserve/bookings?limit=20`),
        fetch(`${API_URL}/google-reserve/stats`),
      ]);

      if (configRes.ok) {
        const data = await configRes.json();
        setConfig(prev => ({ ...prev, ...data }));
      }
      if (bookingsRes.ok) {
        const data = await bookingsRes.json();
        setBookings(data);
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load Google Reserve data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/google-reserve/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        loadData();
        setShowConfigModal(false);
      }
    } catch (error) {
      console.error('Error saving config:', error);
    } finally {
      setSaving(false);
    }
  };

  const syncAvailability = async () => {
    setSyncing(true);
    try {
      const res = await fetch(`${API_URL}/google-reserve/sync`, { method: 'POST' });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error syncing:', error);
    } finally {
      setSyncing(false);
    }
  };

  const updateBookingStatus = async (bookingId: string, status: string) => {
    try {
      const res = await fetch(`${API_URL}/google-reserve/bookings/${bookingId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error updating status:', error);
    }
  };

  const getStatusBadge = (status: string) => STATUS_BADGES[status] || STATUS_BADGES.pending;

  const todayBookings = bookings.filter(b =>
    b.booking_date === new Date().toISOString().split('T')[0]
  );

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <div className="bg-white border-b border-surface-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/integrations" className="p-2 rounded-lg hover:bg-surface-100">
                <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white border border-surface-200 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-surface-900">Reserve with Google</h1>
                  <p className="text-sm text-surface-500">Google Maps booking integration</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${config.is_enabled ? 'bg-green-100 text-green-800' : 'bg-surface-100 text-surface-600'}`}>
                <div className={`w-2 h-2 rounded-full ${config.is_enabled ? 'bg-green-500' : 'bg-surface-400'}`}></div>
                <span className="text-sm font-medium">{config.is_enabled ? 'Connected' : 'Disconnected'}</span>
              </div>
              <button
                onClick={syncAvailability}
                disabled={syncing || !config.is_enabled}
                className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg disabled:opacity-50 flex items-center gap-2"
              >
                <svg className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync
              </button>
              <button
                onClick={() => setShowConfigModal(true)}
                className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
              >
                Settings
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-surface-900">{todayBookings.length}</div>
            <div className="text-sm text-surface-500">Today&apos;s Bookings</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-green-600">
              {todayBookings.filter(b => b.status === 'confirmed').length}
            </div>
            <div className="text-sm text-surface-500">Confirmed</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-yellow-600">
              {todayBookings.filter(b => b.status === 'pending').length}
            </div>
            <div className="text-sm text-surface-500">Pending</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-blue-600">{stats.total_this_month || 0}</div>
            <div className="text-sm text-surface-500">This Month</div>
          </div>
        </div>

        {/* How it Works */}
        {!config.is_enabled && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
            <h3 className="font-semibold text-blue-900 mb-3">How Reserve with Google Works</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-blue-800">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">1</div>
                <div>
                  <div className="font-medium">Customer finds you on Google</div>
                  <div className="text-blue-600">Via Google Maps or Search</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">2</div>
                <div>
                  <div className="font-medium">Books directly from Google</div>
                  <div className="text-blue-600">No app download required</div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">3</div>
                <div>
                  <div className="font-medium">Booking syncs to your POS</div>
                  <div className="text-blue-600">Real-time availability</div>
                </div>
              </div>
            </div>
            <button
              onClick={() => setShowConfigModal(true)}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Connect Google Reserve
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'bookings', label: 'Bookings', icon: '📅' },
            { id: 'settings', label: 'Availability Settings', icon: '⚙️' },
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

        {/* Bookings Tab */}
        {activeTab === 'bookings' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Guest</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Date & Time</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Party</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Source</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {bookings.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-surface-500">
                      No bookings from Google Reserve yet.
                      {!config.is_enabled && ' Connect your account to start receiving bookings.'}
                    </td>
                  </tr>
                ) : (
                  bookings.map((booking) => {
                    const status = getStatusBadge(booking.status);
                    return (
                      <tr key={booking.booking_id} className="border-t border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <div className="font-medium text-surface-900">{booking.customer_name}</div>
                          <div className="text-xs text-surface-500">{booking.customer_phone}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-surface-900">{booking.booking_date}</div>
                          <div className="text-sm text-surface-500">{booking.booking_time}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1">
                            <span>👥</span>
                            <span className="text-surface-700">{booking.party_size}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1 text-sm">
                            <svg className="w-4 h-4" viewBox="0 0 24 24">
                              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            Google
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={booking.status}
                            onChange={(e) => updateBookingStatus(booking.booking_id, e.target.value)}
                            className="px-2 py-1 text-sm border border-surface-200 rounded"
                          >
                            <option value="pending">Pending</option>
                            <option value="confirmed">Confirmed</option>
                            <option value="cancelled">Cancelled</option>
                            <option value="completed">Completed</option>
                            <option value="no_show">No Show</option>
                          </select>
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
              <h3 className="font-semibold text-surface-900 mb-4">Booking Rules</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Max Party Size</label>
                  <input
                    type="number"
                    value={config.max_party_size}
                    onChange={(e) => setConfig({ ...config, max_party_size: parseInt(e.target.value) || 10 })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    min={1}
                    max={50}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Min Lead Time (hours)</label>
                  <input
                    type="number"
                    value={config.min_lead_time_hours}
                    onChange={(e) => setConfig({ ...config, min_lead_time_hours: parseInt(e.target.value) || 2 })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    min={0}
                    max={72}
                  />
                  <p className="text-xs text-surface-500 mt-1">Minimum hours before reservation</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Max Lead Time (days)</label>
                  <input
                    type="number"
                    value={config.max_lead_time_days}
                    onChange={(e) => setConfig({ ...config, max_lead_time_days: parseInt(e.target.value) || 30 })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    min={1}
                    max={365}
                  />
                  <p className="text-xs text-surface-500 mt-1">How far ahead customers can book</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Automation</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-surface-900">Auto-confirm bookings</div>
                    <div className="text-sm text-surface-500">Automatically confirm incoming reservations</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.auto_confirm}
                      onChange={(e) => setConfig({ ...config, auto_confirm: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-surface-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-surface-900">Sync availability</div>
                    <div className="text-sm text-surface-500">Push table availability to Google every 15 minutes</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.sync_availability}
                      onChange={(e) => setConfig({ ...config, sync_availability: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-surface-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div>
                  </label>
                </div>
              </div>
              {config.last_sync && (
                <p className="text-sm text-surface-500 mt-4">
                  Last synced: {new Date(config.last_sync).toLocaleString()}
                </p>
              )}
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

      {/* Config Modal */}
      <AnimatePresence>
        {showConfigModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Google Reserve Settings</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Merchant ID</label>
                  <input
                    type="text"
                    value={config.merchant_id}
                    onChange={(e) => setConfig({ ...config, merchant_id: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Your Google Merchant ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Service ID</label>
                  <input
                    type="text"
                    value={config.service_id}
                    onChange={(e) => setConfig({ ...config, service_id: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Reservation service ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">API Key</label>
                  <input
                    type="password"
                    value={config.api_key}
                    onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Your API Key"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_enabled"
                    checked={config.is_enabled}
                    onChange={(e) => setConfig({ ...config, is_enabled: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                  <label htmlFor="is_enabled" className="text-sm text-surface-700">Enable Google Reserve integration</label>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
                <button
                  onClick={() => setShowConfigModal(false)}
                  className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={saveConfig}
                  disabled={saving}
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
