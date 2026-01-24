'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

interface SyncLog {
  id: number;
  sync_type: string;
  records_synced: number;
  status: 'success' | 'partial' | 'failed';
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

interface MappingItem {
  id: number;
  entity_type: string;
  local_id: number;
  local_name: string;
  external_id: string;
  external_name: string;
  last_synced?: string;
}

export default function QuickBooksIntegrationPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [companyName, setCompanyName] = useState('');
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [mappings, setMappings] = useState<MappingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'mappings' | 'logs'>('overview');
  const [settings, setSettings] = useState({
    sync_sales: true,
    sync_purchases: true,
    sync_inventory: true,
    sync_customers: false,
    sync_vendors: true,
    auto_sync_enabled: false,
    sync_frequency: 'daily',
  });

  useEffect(() => {
    loadIntegrationData();
  }, []);

  const loadIntegrationData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      // Mock data - would come from API
      setIsConnected(false);
      setSyncLogs([
        {
          id: 1,
          sync_type: 'Sales',
          records_synced: 45,
          status: 'success',
          started_at: '2024-12-28T10:30:00',
          completed_at: '2024-12-28T10:32:15',
        },
        {
          id: 2,
          sync_type: 'Purchases',
          records_synced: 12,
          status: 'success',
          started_at: '2024-12-28T10:32:20',
          completed_at: '2024-12-28T10:33:05',
        },
      ]);
      setMappings([
        { id: 1, entity_type: 'revenue_account', local_id: 1, local_name: 'Sales Revenue', external_id: '1001', external_name: 'Sales Income', last_synced: '2024-12-28' },
        { id: 2, entity_type: 'expense_account', local_id: 2, local_name: 'Food Cost', external_id: '5001', external_name: 'Cost of Goods Sold', last_synced: '2024-12-28' },
      ]);
    } catch (error) {
      console.error('Error loading integration data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = () => {
    // Would redirect to QuickBooks OAuth
    window.open('https://appcenter.intuit.com/connect/oauth2', '_blank');
  };

  const handleDisconnect = () => {
    if (confirm('Are you sure you want to disconnect QuickBooks? This will stop all automatic syncing.')) {
      setIsConnected(false);
      setCompanyName('');
    }
  };

  const handleSync = async (syncType: string) => {
    setSyncing(true);
    try {
      // Would call API
      await new Promise(resolve => setTimeout(resolve, 2000));
      alert(`${syncType} sync completed successfully!`);
      loadIntegrationData();
    } catch (error) {
      console.error('Sync error:', error);
    } finally {
      setSyncing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-700';
      case 'partial': return 'bg-yellow-100 text-yellow-700';
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
        <div className="flex items-center gap-4">
          <Link href="/settings/integrations" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center">
              <span className="text-2xl">📗</span>
            </div>
            <div>
              <h1 className="text-2xl font-display font-bold text-surface-900">QuickBooks Integration</h1>
              <p className="text-surface-500 mt-1">Sync financial data with QuickBooks Online</p>
            </div>
          </div>
        </div>
        {isConnected && (
          <button
            onClick={() => handleSync('Full')}
            disabled={syncing}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {syncing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-900 border-t-transparent"></div>
                Syncing...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync Now
              </>
            )}
          </button>
        )}
      </div>

      {/* Connection Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-xl p-6 border ${
          isConnected ? 'bg-green-50 border-green-200' : 'bg-surface-50 border-surface-200'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-4 h-4 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-300'}`}></div>
            <div>
              <div className="font-semibold text-surface-900">
                {isConnected ? 'Connected' : 'Not Connected'}
              </div>
              {isConnected && companyName && (
                <div className="text-sm text-surface-600">{companyName}</div>
              )}
              {lastSyncTime && (
                <div className="text-xs text-surface-500">Last synced: {lastSyncTime}</div>
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
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
            >
              Connect to QuickBooks
            </button>
          )}
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="border-b border-surface-200">
        <div className="flex gap-4">
          {['overview', 'mappings', 'logs'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
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
          {/* Sync Settings */}
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="font-semibold text-surface-900">Sync Settings</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <label className="flex items-center gap-3 p-3 bg-surface-50 rounded-lg">
                  <input
                    type="checkbox"
                    checked={settings.sync_sales}
                    onChange={(e) => setSettings({ ...settings, sync_sales: e.target.checked })}
                    className="w-5 h-5 rounded text-amber-500"
                  />
                  <div>
                    <div className="font-medium text-surface-900">Sales & Invoices</div>
                    <div className="text-xs text-surface-500">Sync sales data to QuickBooks</div>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 bg-surface-50 rounded-lg">
                  <input
                    type="checkbox"
                    checked={settings.sync_purchases}
                    onChange={(e) => setSettings({ ...settings, sync_purchases: e.target.checked })}
                    className="w-5 h-5 rounded text-amber-500"
                  />
                  <div>
                    <div className="font-medium text-surface-900">Purchases & Bills</div>
                    <div className="text-xs text-surface-500">Sync purchase orders and expenses</div>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 bg-surface-50 rounded-lg">
                  <input
                    type="checkbox"
                    checked={settings.sync_inventory}
                    onChange={(e) => setSettings({ ...settings, sync_inventory: e.target.checked })}
                    className="w-5 h-5 rounded text-amber-500"
                  />
                  <div>
                    <div className="font-medium text-surface-900">Inventory</div>
                    <div className="text-xs text-surface-500">Sync inventory levels</div>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 bg-surface-50 rounded-lg">
                  <input
                    type="checkbox"
                    checked={settings.sync_vendors}
                    onChange={(e) => setSettings({ ...settings, sync_vendors: e.target.checked })}
                    className="w-5 h-5 rounded text-amber-500"
                  />
                  <div>
                    <div className="font-medium text-surface-900">Vendors</div>
                    <div className="text-xs text-surface-500">Sync supplier information</div>
                  </div>
                </label>
              </div>

              <div className="pt-4 border-t border-surface-100">
                <label className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                  <div>
                    <div className="font-medium text-surface-900">Automatic Sync</div>
                    <div className="text-xs text-surface-500">Automatically sync data on schedule</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <select
                      value={settings.sync_frequency}
                      onChange={(e) => setSettings({ ...settings, sync_frequency: e.target.value })}
                      className="px-3 py-1 border border-surface-200 rounded-lg text-sm"
                      disabled={!settings.auto_sync_enabled}
                    >
                      <option value="hourly">Hourly</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                    </select>
                    <input
                      type="checkbox"
                      checked={settings.auto_sync_enabled}
                      onChange={(e) => setSettings({ ...settings, auto_sync_enabled: e.target.checked })}
                      className="w-5 h-5 rounded text-amber-500"
                    />
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Sync Sales', icon: '💰', action: () => handleSync('Sales') },
              { label: 'Sync Purchases', icon: '🛒', action: () => handleSync('Purchases') },
              { label: 'Sync Inventory', icon: '📦', action: () => handleSync('Inventory') },
              { label: 'Test Connection', icon: '🔌', action: () => alert('Connection test successful!') },
            ].map((item, index) => (
              <motion.button
                key={item.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onClick={item.action}
                disabled={!isConnected || syncing}
                className="p-4 bg-white rounded-xl border border-surface-200 hover:border-amber-300 hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="text-3xl mb-2">{item.icon}</div>
                <div className="font-medium text-surface-900">{item.label}</div>
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Mappings Tab */}
      {activeTab === 'mappings' && (
        <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
          <div className="p-4 border-b border-surface-100 flex items-center justify-between">
            <h3 className="font-semibold text-surface-900">Account Mappings</h3>
            <button className="px-3 py-1 bg-amber-100 text-amber-700 rounded-lg text-sm hover:bg-amber-200">
              + Add Mapping
            </button>
          </div>
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">V99 Account</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">QuickBooks Account</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Last Synced</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {mappings.map((mapping) => (
                <tr key={mapping.id} className="hover:bg-surface-50">
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                      {mapping.entity_type.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-medium text-surface-900">{mapping.local_name}</div>
                    <div className="text-xs text-surface-500">ID: {mapping.local_id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-medium text-surface-900">{mapping.external_name}</div>
                    <div className="text-xs text-surface-500">ID: {mapping.external_id}</div>
                  </td>
                  <td className="px-6 py-4 text-surface-600">{mapping.last_synced || '-'}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-surface-400 hover:text-surface-600 p-1">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Logs Tab */}
      {activeTab === 'logs' && (
        <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
          <div className="p-4 border-b border-surface-100">
            <h3 className="font-semibold text-surface-900">Sync History</h3>
          </div>
          <div className="divide-y divide-surface-100">
            {syncLogs.map((log) => (
              <div key={log.id} className="p-4 flex items-center justify-between hover:bg-surface-50">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                  <div>
                    <div className="font-medium text-surface-900">{log.sync_type} Sync</div>
                    <div className="text-sm text-surface-500">
                      {log.records_synced} records synced
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-sm text-surface-600">
                      {new Date(log.started_at).toLocaleString()}
                    </div>
                    {log.error_message && (
                      <div className="text-xs text-red-600">{log.error_message}</div>
                    )}
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(log.status)}`}>
                    {log.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
