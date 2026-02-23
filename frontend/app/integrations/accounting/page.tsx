"use client";

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Integration {
  type: string;
  name: string;
  description: string;
  auth_type: string;
  features: string[];
}

interface ConnectedIntegration {
  key: string;
  type: string;
  class: string;
}


export default function AccountingIntegrationsPage() {
  const [available, setAvailable] = useState<Integration[]>([]);
  const [connected, setConnected] = useState<ConnectedIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [availData, connData] = await Promise.all([
        api.get<any>('/integrations/accounting/available'),
        api.get<any>('/integrations/accounting/status'),
      ]);
      setAvailable(availData.integrations || []);
      setConnected(connData.integrations || []);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectIntegration = async (type: string) => {
    setConnecting(type);

    try {
      await api.post('/integrations/accounting/connect', {
        integration_type: type,
        // TODO: Replace with form inputs for real credentials
        client_id: '',
        client_secret: '',
        access_token: '',
        tenant_id: ''
      });
      await fetchData();
      toast.success('Integration connected successfully!');
    } catch {
      // Connection failed
    } finally {
      setConnecting(null);
    }
  };

  const disconnectIntegration = async (type: string) => {
    try {
      await api.del(`/integrations/accounting/${type}`);
      await fetchData();
    } catch {
      // Disconnect failed
    }
  };

  const getIntegrationLogo = (type: string) => {
    switch (type) {
      case 'quickbooks': return '📗';
      case 'xero': return '🔵';
      case 'sage': return '🌿';
      case 'microinvest': return '💼';
      default: return '📊';
    }
  };

  const isConnected = (type: string) => connected.some(c => c.type === type);

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Accounting Integrations</h1>
          <p className="text-surface-500 mt-1">Connect your accounting software for automatic sync</p>
        </div>

        {loading ? (
          <div className="p-8 text-center">Loading...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {available.map((integration, idx) => {
              const connected = isConnected(integration.type);
              return (
                <motion.div
                  key={integration.type}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`bg-white rounded-xl shadow-sm border p-6 ${connected ? 'border-green-300 bg-green-50' : ''}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                      <span className="text-4xl">{getIntegrationLogo(integration.type)}</span>
                      <div>
                        <h3 className="text-lg font-semibold text-surface-900">{integration.name}</h3>
                        <p className="text-sm text-surface-500">{integration.description}</p>
                      </div>
                    </div>
                    {connected && (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                        Connected
                      </span>
                    )}
                  </div>

                  <div className="mt-4">
                    <div className="text-sm text-surface-500 mb-2">Features:</div>
                    <div className="flex flex-wrap gap-2">
                      {integration.features.map(feature => (
                        <span key={feature} className="px-2 py-1 bg-surface-100 text-surface-700 text-xs rounded">
                          {feature.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 flex gap-2">
                    {connected ? (
                      <>
                        <button
                          onClick={() => disconnectIntegration(integration.type)}
                          className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                        >
                          Disconnect
                        </button>
                        <button className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200">
                          Settings
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => connectIntegration(integration.type)}
                        disabled={connecting === integration.type}
                        className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                      >
                        {connecting === integration.type ? 'Connecting...' : 'Connect'}
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Export Section */}
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-lg font-semibold mb-4">Manual Export</h2>
          <p className="text-sm text-surface-500 mb-4">Export data manually to your accounting system</p>
          <div className="flex gap-4">
            <button className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200">
              Export Sales
            </button>
            <button className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200">
              Export Purchases
            </button>
            <button className="px-4 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200">
              Export Inventory
            </button>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
