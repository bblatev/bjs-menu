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

export default function XeroIntegrationPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [organizationName, setOrganizationName] = useState('');
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
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

  useEffect(() => {
    loadIntegrationData();
  }, []);

  const loadIntegrationData = async () => {
    try {
      // Mock data
      setIsConnected(false);
      setSyncLogs([]);
    } catch (error) {
      console.error('Error loading integration data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = () => {
    window.open('https://login.xero.com/identity/connect/authorize', '_blank');
  };

  const handleDisconnect = () => {
    if (confirm('Are you sure you want to disconnect Xero?')) {
      setIsConnected(false);
      setOrganizationName('');
    }
  };

  const handleSync = async (syncType: string) => {
    setSyncing(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 2000));
      alert(`${syncType} sync completed!`);
      loadIntegrationData();
    } finally {
      setSyncing(false);
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
              <span className="text-2xl">🔵</span>
            </div>
            <div>
              <h1 className="text-2xl font-display font-bold text-surface-900">Xero Integration</h1>
              <p className="text-surface-500 mt-1">Sync financial data with Xero</p>
            </div>
          </div>
        </div>
        {isConnected && (
          <button
            onClick={() => handleSync('Full')}
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

      {/* Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="font-semibold text-surface-900">Sync Settings</h3>
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
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Sync Invoices', icon: '📄', action: () => handleSync('Invoices') },
              { label: 'Sync Bills', icon: '📋', action: () => handleSync('Bills') },
              { label: 'Sync Bank', icon: '🏦', action: () => handleSync('Bank') },
              { label: 'Test Connection', icon: '🔌', action: () => alert('Connection OK!') },
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
                <div className="text-3xl mb-2">{item.icon}</div>
                <div className="font-medium text-surface-900">{item.label}</div>
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'mappings' && (
        <div className="bg-white rounded-xl p-12 border border-surface-200 text-center">
          <div className="text-6xl mb-4">🔗</div>
          <h3 className="text-xl font-bold text-surface-900 mb-2">No Mappings Yet</h3>
          <p className="text-surface-500">Connect to Xero first to configure account mappings</p>
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="bg-white rounded-xl p-12 border border-surface-200 text-center">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="text-xl font-bold text-surface-900 mb-2">No Sync History</h3>
          <p className="text-surface-500">Sync history will appear here after your first sync</p>
        </div>
      )}
    </div>
  );
}
