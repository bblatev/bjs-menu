'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Reservation {
  reservation_id: string;
  opentable_id: string;
  guest_name: string;
  guest_email: string;
  guest_phone: string;
  party_size: number;
  reservation_date: string;
  reservation_time: string;
  status: string;
  special_requests: string;
  occasion?: string;
  high_chair: number;
  table_id?: string;
  created_at: string;
  synced_at?: string;
}

interface Guest {
  guest_id: string;
  opentable_guest_id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  visit_count: number;
  no_show_count: number;
  vip_status: boolean;
}

interface IntegrationConfig {
  restaurant_id: string;
  api_key: string;
  webhook_secret: string;
  webhook_url: string;
  sync_enabled: boolean;
  last_sync?: string;
}

const STATUS_BADGES: Record<string, { label: string; bg: string; text: string }> = {
  pending: { label: 'Pending', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  confirmed: { label: 'Confirmed', bg: 'bg-blue-100', text: 'text-blue-800' },
  seated: { label: 'Seated', bg: 'bg-green-100', text: 'text-green-800' },
  completed: { label: 'Completed', bg: 'bg-surface-100', text: 'text-surface-600' },
  cancelled: { label: 'Cancelled', bg: 'bg-red-100', text: 'text-red-800' },
  no_show: { label: 'No Show', bg: 'bg-orange-100', text: 'text-orange-800' },
};

export default function OpenTableIntegrationPage() {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [guests, setGuests] = useState<Guest[]>([]);
  const [config, setConfig] = useState<IntegrationConfig>({
    restaurant_id: '',
    api_key: '',
    webhook_secret: '',
    webhook_url: `${typeof window !== 'undefined' ? window.location.origin : ''}/api/v1/opentable/webhook`,
    sync_enabled: false,
  });
  const [activeTab, setActiveTab] = useState<'reservations' | 'guests' | 'settings'>('reservations');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [stats, setStats] = useState<any>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [reservationsRes, guestsRes, statsRes, configRes] = await Promise.all([
        fetch(`${API_URL}/opentable/reservations`),
        fetch(`${API_URL}/opentable/guests`),
        fetch(`${API_URL}/opentable/stats`),
        fetch(`${API_URL}/opentable/config`),
      ]);

      if (reservationsRes.ok) {
        const data = await reservationsRes.json();
        setReservations(data);
      }
      if (guestsRes.ok) {
        const data = await guestsRes.json();
        setGuests(data);
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
      if (configRes.ok) {
        const data = await configRes.json();
        setConfig(prev => ({ ...prev, ...data }));
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load OpenTable data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const syncNow = async () => {
    setSyncing(true);
    try {
      const res = await fetch(`${API_URL}/opentable/sync`, { method: 'POST' });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error syncing:', error);
    } finally {
      setSyncing(false);
    }
  };

  const updateReservationStatus = async (reservationId: string, status: string) => {
    try {
      const res = await fetch(`${API_URL}/opentable/reservations/${reservationId}/status`, {
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

  const saveConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/opentable/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        setShowConfigModal(false);
        loadData();
      }
    } catch (error) {
      console.error('Error saving config:', error);
    }
  };

  const getStatusBadge = (status: string) => STATUS_BADGES[status] || STATUS_BADGES.pending;

  const todayReservations = reservations.filter(r =>
    r.reservation_date === new Date().toISOString().split('T')[0]
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
                <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                  <span className="text-xl">🍽️</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-surface-900">OpenTable Integration</h1>
                  <p className="text-sm text-surface-500">Reservation sync and guest management</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${config.sync_enabled ? 'bg-green-100 text-green-800' : 'bg-surface-100 text-surface-600'}`}>
                <div className={`w-2 h-2 rounded-full ${config.sync_enabled ? 'bg-green-500' : 'bg-surface-400'}`}></div>
                <span className="text-sm font-medium">{config.sync_enabled ? 'Connected' : 'Disconnected'}</span>
              </div>
              <button
                onClick={syncNow}
                disabled={syncing || !config.sync_enabled}
                className="px-4 py-2 text-surface-600 hover:bg-surface-100 rounded-lg disabled:opacity-50 flex items-center gap-2"
              >
                <svg className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync Now
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

      {/* Stats */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-surface-900">{todayReservations.length}</div>
            <div className="text-sm text-surface-500">Today&apos;s Reservations</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-blue-600">
              {todayReservations.filter(r => r.status === 'confirmed').length}
            </div>
            <div className="text-sm text-surface-500">Confirmed</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-green-600">
              {todayReservations.filter(r => r.status === 'seated').length}
            </div>
            <div className="text-sm text-surface-500">Seated</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-surface-200">
            <div className="text-3xl font-bold text-purple-600">{guests.filter(g => g.vip_status).length}</div>
            <div className="text-sm text-surface-500">VIP Guests</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'reservations', label: 'Reservations', icon: '📅' },
            { id: 'guests', label: 'Guest Profiles', icon: '👥' },
            { id: 'settings', label: 'Availability', icon: '⏰' },
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

        {/* Reservations Tab */}
        {activeTab === 'reservations' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100 flex items-center justify-between">
              <h3 className="font-semibold text-surface-900">Recent Reservations</h3>
              <span className="text-sm text-surface-500">{reservations.length} total</span>
            </div>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[700px]">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Guest</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Date & Time</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Party</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Special Requests</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reservations.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-surface-500">
                      No reservations synced yet. Connect your OpenTable account to get started.
                    </td>
                  </tr>
                ) : (
                  reservations.map((res) => {
                    const status = getStatusBadge(res.status);
                    return (
                      <tr key={res.reservation_id} className="border-t border-surface-100 hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <div className="font-medium text-surface-900">{res.guest_name}</div>
                          <div className="text-xs text-surface-500">{res.guest_phone}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-surface-900">{res.reservation_date}</div>
                          <div className="text-sm text-surface-500">{res.reservation_time}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1">
                            <span>👥</span>
                            <span className="text-surface-700">{res.party_size}</span>
                            {res.high_chair > 0 && (
                              <span className="ml-2 text-xs text-surface-500">+{res.high_chair} high chair</span>
                            )}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-sm text-surface-600 max-w-xs truncate">
                            {res.special_requests || '-'}
                          </div>
                          {res.occasion && (
                            <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">
                              {res.occasion}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={res.status}
                            onChange={(e) => updateReservationStatus(res.reservation_id, e.target.value)}
                            className="px-2 py-1 text-sm border border-surface-200 rounded"
                          >
                            <option value="pending">Pending</option>
                            <option value="confirmed">Confirmed</option>
                            <option value="seated">Seated</option>
                            <option value="completed">Completed</option>
                            <option value="cancelled">Cancelled</option>
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
          </div>
        )}

        {/* Guests Tab */}
        {activeTab === 'guests' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="font-semibold text-surface-900">Guest Profiles from OpenTable</h3>
            </div>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Guest</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Contact</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Visits</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">No Shows</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700">Status</th>
                </tr>
              </thead>
              <tbody>
                {guests.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center text-surface-500">
                      No guest profiles synced yet.
                    </td>
                  </tr>
                ) : (
                  guests.map((guest) => (
                    <tr key={guest.guest_id} className="border-t border-surface-100 hover:bg-surface-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-surface-100 rounded-full flex items-center justify-center">
                            <span className="text-surface-600 font-medium">
                              {guest.first_name[0]}{guest.last_name[0]}
                            </span>
                          </div>
                          <div>
                            <div className="font-medium text-surface-900">
                              {guest.first_name} {guest.last_name}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-surface-600">{guest.email}</div>
                        <div className="text-xs text-surface-500">{guest.phone || '-'}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-medium text-surface-900">{guest.visit_count}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={guest.no_show_count > 0 ? 'text-red-600 font-medium' : 'text-surface-500'}>
                          {guest.no_show_count}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {guest.vip_status ? (
                          <span className="px-2 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-medium flex items-center gap-1 w-fit">
                            <span>⭐</span> VIP
                          </span>
                        ) : (
                          <span className="text-surface-500 text-sm">Regular</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            </div>
          </div>
        )}

        {/* Availability Tab */}
        {activeTab === 'settings' && (
          <div className="bg-white rounded-xl border border-surface-200 p-6">
            <h3 className="font-semibold text-surface-900 mb-4">Availability Sync</h3>
            <p className="text-surface-500 mb-6">
              Push your table availability to OpenTable to keep your booking calendar in sync.
            </p>
            <div className="bg-surface-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-surface-900">Auto-sync availability</div>
                  <div className="text-sm text-surface-500">
                    Automatically push availability updates every 15 minutes
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.sync_enabled}
                    onChange={(e) => setConfig({ ...config, sync_enabled: e.target.checked })}
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
                <h2 className="text-xl font-bold text-surface-900">OpenTable Settings</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Restaurant ID</label>
                  <input
                    type="text"
                    value={config.restaurant_id}
                    onChange={(e) => setConfig({ ...config, restaurant_id: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Your OpenTable Restaurant ID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">API Key</label>
                  <input
                    type="password"
                    value={config.api_key}
                    onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="Your OpenTable API Key"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Webhook Secret</label>
                  <input
                    type="password"
                    value={config.webhook_secret}
                    onChange={(e) => setConfig({ ...config, webhook_secret: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="For verifying webhook signatures"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Webhook URL</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={config.webhook_url}
                      readOnly
                      className="flex-1 px-3 py-2 border border-surface-200 rounded-lg bg-surface-50 font-mono text-sm"
                    />
                    <button
                      onClick={() => navigator.clipboard.writeText(config.webhook_url)}
                      className="px-3 py-2 bg-surface-100 hover:bg-surface-200 rounded-lg"
                    >
                      Copy
                    </button>
                  </div>
                  <p className="text-xs text-surface-500 mt-1">
                    Add this URL to your OpenTable webhook settings
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="sync_enabled"
                    checked={config.sync_enabled}
                    onChange={(e) => setConfig({ ...config, sync_enabled: e.target.checked })}
                    className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                  />
                  <label htmlFor="sync_enabled" className="text-sm text-surface-700">Enable sync</label>
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
                  className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Save Settings
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
