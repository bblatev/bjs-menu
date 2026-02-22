'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface SyncLog {
  id: number;
  sync_type: string;
  records_synced: number;
  status: 'success' | 'partial' | 'failed';
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

interface AccountMapping {
  id: number;
  local_category: string;
  xero_account_code: string;
  xero_account_name: string | null;
  sync_direction: string;
  is_active: boolean;
}

export default function XeroIntegrationPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [organizationName, setOrganizationName] = useState('');
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [mappings, setMappings] = useState<AccountMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'mappings' | 'logs'>('overview');
  const [settings, setSettings] = useState({
    sync_invoices: true,
    sync_bills: true,
    sync_bank_transactions: true,
    sync_contacts: false,
    auto_sync_enabled: false,
    sync_frequency: 'daily',
  });

  const loadIntegrationData = useCallback(async () => {
    const headers = getAuthHeaders();
    try {
      const [statusRes, logsRes, mappingsRes] = await Promise.all([
        fetch(`${API_URL}/xero/status`, { credentials: 'include', headers }),
        fetch(`${API_URL}/xero/sync-logs`, { credentials: 'include', headers }),
        fetch(`${API_URL}/xero/mappings`, { credentials: 'include', headers }),
      ]);

      const status = await statusRes.json();
      setIsConnected(status.connected || false);
      setOrganizationName(status.organization_name || '');
      setLastSyncTime(status.last_sync || null);
      if (status.sync_enabled !== undefined) {
        setSettings(prev => ({ ...prev, auto_sync_enabled: status.sync_enabled }));
      }

      const logs = await logsRes.json();
      setSyncLogs(Array.isArray(logs) ? logs : []);

      const maps = await mappingsRes.json();
      setMappings(Array.isArray(maps) ? maps : []);
    } catch (error) {
      console.error('Error loading integration data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIntegrationData();
  }, [loadIntegrationData]);

  const handleConnect = async () => {
    const headers = getAuthHeaders();
    try {
      const res = await fetch(`${API_URL}/xero/connect`, {
        credentials: 'include',
        method: 'POST',
        headers,
        body: JSON.stringify({ redirect_uri: `${window.location.origin}/integrations/xero/callback` }),
      });
      const data = await res.json();
      if (data.auth_url) {
        window.open(data.auth_url, '_blank');
      }
    } catch (error) {
      console.error('Connect error:', error);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect Xero?')) return;
    const headers = getAuthHeaders();
    try {
      await fetch(`${API_URL}/xero/disconnect`, {
        credentials: 'include',
        method: 'POST',
        headers,
        body: JSON.stringify({ confirm: true }),
      });
      setIsConnected(false);
      setOrganizationName('');
      loadIntegrationData();
    } catch (error) {
      console.error('Disconnect error:', error);
    }
  };

  const handleSync = async (syncType: string) => {
    setSyncing(true);
    const headers = getAuthHeaders();
    try {
      const res = await fetch(`${API_URL}/xero/sync`, {
        credentials: 'include',
        method: 'POST',
        headers,
        body: JSON.stringify({ sync_type: syncType.toLowerCase() }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        loadIntegrationData();
      }
    } catch (error) {
      console.error('Sync error:', error);
    } finally {
      setSyncing(false);
    }
  };

  const saveSettings = async () => {
    const headers = getAuthHeaders();
    try {
      await fetch(`${API_URL}/xero/settings`, {
        credentials: 'include',
        method: 'PUT',
        headers,
        body: JSON.stringify(settings),
      });
    } catch (error) {
      console.error('Settings save error:', error);
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
        <div className="flex items-center gap-4">
          <Link href="/settings/integrations" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
              <span className="text-2xl">X</span>
            </div>
            <div>
              <h1 className="text-2xl font-display font-bold text-surface-900">Xero Integration</h1>
              <p className="text-surface-500 mt-1">Sync financial data with Xero</p>
            </div>
          </div>
        </div>
        {isConnected && (
          <button
            onClick={() => handleSync('all')}
            disabled={syncing}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
        )}
      </div>

      {/* Connection Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-xl p-6 border ${
          isConnected ? 'bg-blue-50 border-blue-200' : 'bg-surface-50 border-surface-200'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-4 h-4 rounded-full ${isConnected ? 'bg-blue-500' : 'bg-gray-300'}`}></div>
            <div>
              <div className="font-semibold text-surface-900">
                {isConnected ? 'Connected' : 'Not Connected'}
              </div>
              {isConnected && organizationName && (
                <div className="text-sm text-surface-600">{organizationName}</div>
              )}
              {lastSyncTime && (
                <div className="text-xs text-surface-400 mt-1">Last sync: {new Date(lastSyncTime).toLocaleString()}</div>
              )}
            </div>
          </div>
          {isConnected ? (
            <button
              onClick={handleDisconnect}
              className="px-4 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50"
            >
              Disconnect
            </button>
          ) : (
            <button
              onClick={handleConnect}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Connect to Xero
            </button>
          )}
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="border-b border-surface-200">
        <div className="flex gap-4">
          {(['overview', 'mappings', 'logs'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-surface-500 hover:text-surface-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100 flex items-center justify-between">
              <h3 className="font-semibold text-surface-900">Sync Settings</h3>
              <button onClick={saveSettings} className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600">
                Save Settings
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {[
                  { key: 'sync_invoices', label: 'Invoices', desc: 'Sync sales invoices to Xero' },
                  { key: 'sync_bills', label: 'Bills', desc: 'Sync purchase bills to Xero' },
                  { key: 'sync_bank_transactions', label: 'Bank Transactions', desc: 'Sync bank feeds' },
                  { key: 'sync_contacts', label: 'Contacts', desc: 'Sync customers and suppliers' },
                ].map((item) => (
                  <label key={item.key} className="flex items-center gap-3 p-3 bg-surface-50 rounded-lg">
                    <input
                      type="checkbox"
                      checked={settings[item.key as keyof typeof settings] as boolean}
                      onChange={(e) => setSettings({ ...settings, [item.key]: e.target.checked })}
                      className="w-5 h-5 rounded text-amber-500"
                    />
                    <div>
                      <div className="font-medium text-surface-900">{item.label}</div>
                      <div className="text-xs text-surface-500">{item.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
              <div className="flex items-center gap-4 pt-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={settings.auto_sync_enabled}
                    onChange={(e) => setSettings({ ...settings, auto_sync_enabled: e.target.checked })}
                    className="w-5 h-5 rounded text-amber-500"
                  />
                  <span className="text-sm font-medium text-surface-900">Auto-sync</span>
                </label>
                <select
                  value={settings.sync_frequency}
                  onChange={(e) => setSettings({ ...settings, sync_frequency: e.target.value })}
                  className="px-3 py-1.5 border border-surface-200 rounded-lg text-sm"
                >
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Sync Invoices', icon: 'INV', action: () => handleSync('invoices') },
              { label: 'Sync Bills', icon: 'BIL', action: () => handleSync('bills') },
              { label: 'Sync Contacts', icon: 'CON', action: () => handleSync('contacts') },
              { label: 'Sync All', icon: 'ALL', action: () => handleSync('all') },
            ].map((item, index) => (
              <motion.button
                key={item.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onClick={item.action}
                disabled={!isConnected || syncing}
                className="p-4 bg-white rounded-xl border border-surface-200 hover:border-amber-300 hover:shadow-md transition-all disabled:opacity-50"
              >
                <div className="text-xl font-bold mb-2 text-amber-600">{item.icon}</div>
                <div className="font-medium text-surface-900 text-sm">{item.label}</div>
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Mappings Tab */}
      {activeTab === 'mappings' && (
        <div className="space-y-4">
          {mappings.length === 0 ? (
            <div className="bg-white rounded-xl p-12 border border-surface-200 text-center">
              <div className="text-4xl mb-4">&#128279;</div>
              <h3 className="text-xl font-bold text-surface-900 mb-2">No Mappings Yet</h3>
              <p className="text-surface-500">Connect to Xero first to configure account mappings</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <div className="p-4 border-b border-surface-100">
                <h3 className="font-semibold text-surface-900">Account Mappings ({mappings.length})</h3>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Local Category</th>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Xero Account</th>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Account Name</th>
                    <th className="text-center px-4 py-3 font-medium text-surface-600">Direction</th>
                    <th className="text-center px-4 py-3 font-medium text-surface-600">Active</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {mappings.map((m) => (
                    <tr key={m.id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{m.local_category}</td>
                      <td className="px-4 py-3 font-mono text-surface-600">{m.xero_account_code}</td>
                      <td className="px-4 py-3 text-surface-600">{m.xero_account_name || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                          m.sync_direction === 'both' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                        }`}>
                          {m.sync_direction}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`w-2 h-2 rounded-full inline-block ${m.is_active ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="space-y-4">
          {syncLogs.length === 0 ? (
            <div className="bg-white rounded-xl p-12 border border-surface-200 text-center">
              <div className="text-4xl mb-4">&#128202;</div>
              <h3 className="text-xl font-bold text-surface-900 mb-2">No Sync History</h3>
              <p className="text-surface-500">Sync history will appear here after your first sync</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <div className="p-4 border-b border-surface-100">
                <h3 className="font-semibold text-surface-900">Sync History ({syncLogs.length})</h3>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Type</th>
                    <th className="text-center px-4 py-3 font-medium text-surface-600">Status</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Records</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Started</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Completed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {syncLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900 capitalize">{log.sync_type}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                          log.status === 'success' ? 'bg-green-100 text-green-800' :
                          log.status === 'partial' ? 'bg-amber-100 text-amber-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {log.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{log.records_synced}</td>
                      <td className="px-4 py-3 text-right text-xs text-surface-500">{new Date(log.started_at).toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-xs text-surface-500">{log.completed_at ? new Date(log.completed_at).toLocaleString() : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
