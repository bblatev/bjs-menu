'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface PMSConnection {
  id: number;
  provider: string;
  provider_name: string;
  property_name: string;
  status: 'connected' | 'disconnected' | 'error';
  last_sync?: string;
  settings: {
    auto_sync_guests: boolean;
    allow_room_charges: boolean;
    sync_fb_credits: boolean;
    sync_packages: boolean;
  };
}

interface HotelGuest {
  id: number;
  external_guest_id: string;
  first_name: string;
  last_name: string;
  room_number: string;
  check_in_date: string;
  check_out_date: string;
  vip_status?: string;
  fb_credit_balance: number;
  total_charges: number;
}

interface RoomCharge {
  id: number;
  guest_name: string;
  room_number: string;
  amount: number;
  description: string;
  status: 'pending' | 'posted' | 'voided' | 'failed';
  created_at: string;
}

const PMS_PROVIDERS = [
  { id: 'opera', name: 'Oracle Opera', icon: '🏛️', description: 'Enterprise hotel management system' },
  { id: 'mews', name: 'Mews', icon: '🌟', description: 'Modern cloud-native PMS' },
  { id: 'cloudbeds', name: 'Cloudbeds', icon: '☁️', description: 'All-in-one hospitality platform' },
  { id: 'protel', name: 'Protel', icon: '🏨', description: 'Industry-leading PMS' },
  { id: 'clock', name: 'Clock PMS+', icon: '⏰', description: 'Next-gen property management' },
  { id: 'stayntouch', name: 'StayNTouch', icon: '📱', description: 'Mobile-first PMS' },
  { id: 'apaleo', name: 'Apaleo', icon: '🔌', description: 'API-first platform' },
  { id: 'guestline', name: 'Guestline', icon: '👤', description: 'Cloud hospitality software' },
  { id: 'infor', name: 'Infor HMS', icon: '📊', description: 'Enterprise management' },
  { id: 'roommaster', name: 'RoomMaster', icon: '🔑', description: 'Flexible PMS solution' },
];

export default function HotelPMSPage() {
  const [connection, setConnection] = useState<PMSConnection | null>(null);
  const [guests, setGuests] = useState<HotelGuest[]>([]);
  const [charges, setCharges] = useState<RoomCharge[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'guests' | 'charges' | 'settings'>('overview');
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [showChargeModal, setShowChargeModal] = useState(false);
  const [newCharge, setNewCharge] = useState({ guest_id: '', amount: '', description: '' });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const headers = getAuthHeaders();

      // Load connection
      const connRes = await fetch(`${API_URL}/enterprise/hotel-pms/connection`, { headers });
      if (connRes.ok) {
        const data = await connRes.json();
        setConnection(data);
      }

      // Load guests
      const guestsRes = await fetch(`${API_URL}/enterprise/hotel-pms/guests`, { headers });
      if (guestsRes.ok) {
        const data = await guestsRes.json();
        setGuests(data);
      }

      // Load charges
      const chargesRes = await fetch(`${API_URL}/enterprise/hotel-pms/charges`, { headers });
      if (chargesRes.ok) {
        const data = await chargesRes.json();
        setCharges(data);
      }
    } catch (error) {
      console.error('Error loading hotel PMS data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    if (!selectedProvider) return;

    try {
      const response = await fetch(`${API_URL}/enterprise/hotel-pms/connect`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          provider: selectedProvider,
          config: {
            api_key: '',
            property_id: ''
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        setConnection(data);
      } else {
        console.error('Failed to connect PMS:', response.status);
      }

      setShowConnectModal(false);
      setSelectedProvider(null);
    } catch (error) {
      console.error('Error connecting:', error);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect from the PMS?')) return;

    try {
      await fetch(`${API_URL}/enterprise/hotel-pms/disconnect`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      setConnection(null);
    } catch (error) {
      console.error('Error disconnecting:', error);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await fetch(`${API_URL}/enterprise/hotel-pms/sync-guests`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      await loadData();
    } catch (error) {
      console.error('Error syncing:', error);
    } finally {
      setSyncing(false);
    }
  };

  const handlePostCharge = async () => {
    if (!newCharge.guest_id || !newCharge.amount) return;

    try {
      const response = await fetch(`${API_URL}/enterprise/hotel-pms/charges`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          guest_id: parseInt(newCharge.guest_id),
          amount: parseFloat(newCharge.amount),
          description: newCharge.description
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCharges(prev => [data, ...prev]);
      }

      setShowChargeModal(false);
      setNewCharge({ guest_id: '', amount: '', description: '' });
    } catch (error) {
      console.error('Error posting charge:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'bg-green-100 text-green-700';
      case 'posted': return 'bg-green-100 text-green-700';
      case 'pending': return 'bg-amber-100 text-amber-700';
      case 'error': return 'bg-red-100 text-red-700';
      case 'voided': return 'bg-gray-100 text-gray-700';
      case 'failed': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-amber-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-surface-900">Hotel PMS Integration</h1>
          <p className="text-surface-500 mt-1">Connect with hotel property management systems</p>
        </div>
        {connection && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleSync}
              disabled={syncing}
              className="px-4 py-2 border border-surface-200 rounded-lg hover:bg-surface-50 flex items-center gap-2 disabled:opacity-50"
            >
              {syncing ? (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-amber-500 border-t-transparent"></div>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              )}
              Sync Now
            </button>
            <button
              onClick={() => setShowChargeModal(true)}
              className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Post Room Charge
            </button>
          </div>
        )}
      </div>

      {/* Connection Status */}
      {!connection ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl border border-surface-200 p-8 text-center"
        >
          <div className="text-5xl mb-4">🏨</div>
          <h2 className="text-xl font-bold text-surface-900 mb-2">Connect Your Hotel PMS</h2>
          <p className="text-surface-500 mb-6 max-w-md mx-auto">
            Integrate with your hotel&apos;s property management system to enable room charges, guest sync, and F&amp;B credits.
          </p>
          <button
            onClick={() => setShowConnectModal(true)}
            className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 font-medium"
          >
            Connect PMS
          </button>
        </motion.div>
      ) : (
        <>
          {/* Connection Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl border border-green-200 bg-green-50/50 p-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-xl bg-green-100 flex items-center justify-center text-2xl">
                  {PMS_PROVIDERS.find(p => p.id === connection.provider)?.icon || '🏨'}
                </div>
                <div>
                  <div className="font-semibold text-surface-900">{connection.provider_name}</div>
                  <div className="text-sm text-surface-600">{connection.property_name}</div>
                  {connection.last_sync && (
                    <div className="text-xs text-surface-500">
                      Last sync: {new Date(connection.last_sync).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(connection.status)}`}>
                  {connection.status === 'connected' && (
                    <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                  )}
                  Connected
                </span>
                <button
                  onClick={handleDisconnect}
                  className="px-4 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50"
                >
                  Disconnect
                </button>
              </div>
            </div>
          </motion.div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Active Guests', value: guests.length, icon: '👤', color: 'blue' },
              { label: 'Today\'s Charges', value: `$${(charges.filter(c => c.status !== 'voided').reduce((sum, c) => sum + c.amount, 0) ?? 0).toFixed(2)}`, icon: '💰', color: 'green' },
              { label: 'Pending Charges', value: charges.filter(c => c.status === 'pending').length, icon: '⏳', color: 'amber' },
              { label: 'F&B Credits', value: `$${(guests.reduce((sum, g) => sum + g.fb_credit_balance, 0) ?? 0).toFixed(2)}`, icon: '🎫', color: 'purple' },
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-xl border border-surface-200 p-4"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{stat.icon}</span>
                  <div>
                    <div className="text-2xl font-bold text-surface-900">{stat.value}</div>
                    <div className="text-sm text-surface-500">{stat.label}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Tabs */}
          <div className="border-b border-surface-200">
            <div className="flex gap-4">
              {[
                { id: 'overview', label: 'Overview', icon: '📊' },
                { id: 'guests', label: 'Hotel Guests', icon: '👥' },
                { id: 'charges', label: 'Room Charges', icon: '💳' },
                { id: 'settings', label: 'Settings', icon: '⚙️' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-4 py-2 border-b-2 -mb-px transition-colors flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'border-amber-500 text-amber-600'
                      : 'border-transparent text-surface-500 hover:text-surface-700'
                  }`}
                >
                  <span>{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
                <div className="p-4 border-b border-surface-100">
                  <h3 className="font-semibold text-surface-900">Recent Charges</h3>
                </div>
                <div className="divide-y divide-surface-100">
                  {charges.slice(0, 5).map((charge) => (
                    <div key={charge.id} className="p-4 flex items-center justify-between">
                      <div>
                        <div className="font-medium text-surface-900">{charge.guest_name}</div>
                        <div className="text-sm text-surface-500">Room {charge.room_number} • {charge.description}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-surface-900">${(charge.amount ?? 0).toFixed(2)}</div>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${getStatusColor(charge.status)}`}>
                          {charge.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
                <div className="p-4 border-b border-surface-100">
                  <h3 className="font-semibold text-surface-900">VIP Guests</h3>
                </div>
                <div className="divide-y divide-surface-100">
                  {guests.filter(g => g.vip_status).map((guest) => (
                    <div key={guest.id} className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-lg">
                          ⭐
                        </div>
                        <div>
                          <div className="font-medium text-surface-900">{guest.first_name} {guest.last_name}</div>
                          <div className="text-sm text-surface-500">Room {guest.room_number}</div>
                        </div>
                      </div>
                      <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">
                        {guest.vip_status}
                      </span>
                    </div>
                  ))}
                  {guests.filter(g => g.vip_status).length === 0 && (
                    <div className="p-8 text-center text-surface-500">No VIP guests currently</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Guests Tab */}
          {activeTab === 'guests' && (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Guest</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Room</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Check-in/out</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">VIP Status</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">F&B Credit</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Total Charges</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {guests.map((guest) => (
                    <tr key={guest.id} className="hover:bg-surface-50">
                      <td className="px-6 py-4">
                        <div className="font-medium text-surface-900">{guest.first_name} {guest.last_name}</div>
                        <div className="text-xs text-surface-500">ID: {guest.external_guest_id}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 bg-surface-100 rounded-lg font-mono">{guest.room_number}</span>
                      </td>
                      <td className="px-6 py-4 text-sm text-surface-600">
                        <div>{guest.check_in_date}</div>
                        <div className="text-surface-400">to {guest.check_out_date}</div>
                      </td>
                      <td className="px-6 py-4">
                        {guest.vip_status ? (
                          <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">
                            {guest.vip_status}
                          </span>
                        ) : (
                          <span className="text-surface-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {guest.fb_credit_balance > 0 ? (
                          <span className="text-green-600 font-medium">${(guest.fb_credit_balance ?? 0).toFixed(2)}</span>
                        ) : (
                          <span className="text-surface-400">$0.00</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-surface-900">
                        ${(guest.total_charges ?? 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Charges Tab */}
          {activeTab === 'charges' && (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Time</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Guest</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Room</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Description</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Amount</th>
                    <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {charges.map((charge) => (
                    <tr key={charge.id} className="hover:bg-surface-50">
                      <td className="px-6 py-4 text-sm text-surface-600">
                        {new Date(charge.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-medium text-surface-900">{charge.guest_name}</td>
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 bg-surface-100 rounded-lg font-mono">{charge.room_number}</span>
                      </td>
                      <td className="px-6 py-4 text-surface-600">{charge.description}</td>
                      <td className="px-6 py-4 text-right font-semibold text-surface-900">
                        ${(charge.amount ?? 0).toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(charge.status)}`}>
                          {charge.status.charAt(0).toUpperCase() + charge.status.slice(1)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div className="bg-white rounded-xl border border-surface-200 p-6">
              <h3 className="font-semibold text-surface-900 mb-4">Integration Settings</h3>
              <div className="space-y-4">
                {[
                  { key: 'auto_sync_guests', label: 'Auto-sync Guests', description: 'Automatically sync guest data from the PMS' },
                  { key: 'allow_room_charges', label: 'Allow Room Charges', description: 'Enable posting charges to guest rooms' },
                  { key: 'sync_fb_credits', label: 'Sync F&B Credits', description: 'Sync food & beverage credits from hotel packages' },
                  { key: 'sync_packages', label: 'Sync Packages', description: 'Import hotel packages with meal plans' },
                ].map((setting) => (
                  <label
                    key={setting.key}
                    className="flex items-center justify-between p-4 bg-surface-50 rounded-xl cursor-pointer"
                  >
                    <div>
                      <div className="font-medium text-surface-900">{setting.label}</div>
                      <div className="text-sm text-surface-500">{setting.description}</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={connection.settings[setting.key as keyof typeof connection.settings]}
                      onChange={() => {
                        setConnection({
                          ...connection,
                          settings: {
                            ...connection.settings,
                            [setting.key]: !connection.settings[setting.key as keyof typeof connection.settings]
                          }
                        });
                      }}
                      className="w-5 h-5 rounded text-amber-500"
                    />
                  </label>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Connect Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowConnectModal(false)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-surface-100">
              <h2 className="text-xl font-bold text-surface-900">Select Your PMS Provider</h2>
              <p className="text-surface-500 mt-1">Choose the property management system your hotel uses</p>
            </div>
            <div className="p-6 overflow-y-auto max-h-[50vh]">
              <div className="grid grid-cols-2 gap-3">
                {PMS_PROVIDERS.map((provider) => (
                  <button
                    key={provider.id}
                    onClick={() => setSelectedProvider(provider.id)}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      selectedProvider === provider.id
                        ? 'border-amber-500 bg-amber-50'
                        : 'border-surface-200 hover:border-amber-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{provider.icon}</span>
                      <div>
                        <div className="font-medium text-surface-900">{provider.name}</div>
                        <div className="text-xs text-surface-500">{provider.description}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
            <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
              <button
                onClick={() => setShowConnectModal(false)}
                className="px-6 py-2 border border-surface-200 rounded-lg hover:bg-surface-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConnect}
                disabled={!selectedProvider}
                className="px-6 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
              >
                Connect
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Post Charge Modal */}
      {showChargeModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowChargeModal(false)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-surface-100">
              <h2 className="text-xl font-bold text-surface-900">Post Room Charge</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-surface-600 mb-1">Select Guest</label>
                <select
                  value={newCharge.guest_id}
                  onChange={(e) => setNewCharge({ ...newCharge, guest_id: e.target.value })}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                >
                  <option value="">Choose a guest...</option>
                  {guests.map((guest) => (
                    <option key={guest.id} value={guest.id}>
                      {guest.first_name} {guest.last_name} - Room {guest.room_number}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-surface-600 mb-1">Amount</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">$</span>
                  <input
                    type="number"
                    step="0.01"
                    value={newCharge.amount}
                    onChange={(e) => setNewCharge({ ...newCharge, amount: e.target.value })}
                    className="w-full pl-8 pr-3 py-2 border border-surface-200 rounded-lg"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-surface-600 mb-1">Description</label>
                <input
                  type="text"
                  value={newCharge.description}
                  onChange={(e) => setNewCharge({ ...newCharge, description: e.target.value })}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                  placeholder="e.g., Dinner - Restaurant"
                />
              </div>
            </div>
            <div className="p-6 border-t border-surface-100 flex justify-end gap-3">
              <button
                onClick={() => setShowChargeModal(false)}
                className="px-6 py-2 border border-surface-200 rounded-lg hover:bg-surface-50"
              >
                Cancel
              </button>
              <button
                onClick={handlePostCharge}
                disabled={!newCharge.guest_id || !newCharge.amount}
                className="px-6 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
              >
                Post Charge
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
