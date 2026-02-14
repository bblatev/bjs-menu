'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button, Input, Card, CardBody, Badge } from '@/components/ui';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Integration {
  id: string;
  name: string;
  category: string;
  description: string;
  popular: boolean;
  status: 'connected' | 'available';
}

interface Category {
  id: string;
  name: string;
  count: number;
}

export default function SettingsIntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showPopularOnly, setShowPopularOnly] = useState(false);

  // Hardware settings
  const [hardwareDevices, setHardwareDevices] = useState([]);
  const [showHardwareModal, setShowHardwareModal] = useState(false);

  // Webhook settings
  const [webhooks, setWebhooks] = useState<{
    enabled: boolean;
    endpoints: Array<{ url: string; events: string[] }>;
    retry_attempts: number;
    timeout_seconds: number;
  }>({
    enabled: false,
    endpoints: [],
    retry_attempts: 3,
    timeout_seconds: 30,
  });

  // API Keys
  const [apiKeys, setApiKeys] = useState<Array<{ id: string; name: string; key: string; created_at: string }>>([]);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);

  // Connect integration modal
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [connectIntegrationId, setConnectIntegrationId] = useState<string | null>(null);
  const [connectCredentials, setConnectCredentials] = useState('');

  // Create API key modal
  const [showCreateApiKeyModal, setShowCreateApiKeyModal] = useState(false);
  const [newApiKeyName, setNewApiKeyName] = useState('');

  // Multi-location sync
  const [multiLocationSync, setMultiLocationSync] = useState({
    enabled: false,
    sync_menu: true,
    sync_prices: true,
    sync_inventory: false,
    sync_employees: false,
    sync_promotions: true,
    sync_frequency: 'realtime',
    master_location_id: null,
    linked_locations: [],
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      // Load integrations
      const integrationsRes = await fetch(`${API_URL}/integrations/integrations`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (integrationsRes.ok) {
        const data = await integrationsRes.json();
        setIntegrations(data.integrations || []);
      }

      // Load categories
      const categoriesRes = await fetch(`${API_URL}/integrations/integrations/categories`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategories(data.categories || []);
      }

      // Load hardware devices
      const hardwareRes = await fetch(`${API_URL}/integrations/hardware/devices`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (hardwareRes.ok) {
        const data = await hardwareRes.json();
        setHardwareDevices(data.devices || []);
      }

      // Load webhooks
      const webhooksRes = await fetch(`${API_URL}/integrations/webhooks`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (webhooksRes.ok) {
        const data = await webhooksRes.json();
        setWebhooks({
          enabled: data?.enabled ?? false,
          endpoints: data?.endpoints || [],
          retry_attempts: data?.retry_attempts ?? 3,
          timeout_seconds: data?.timeout_seconds ?? 30,
        });
      }

      // Load API keys
      const apiKeysRes = await fetch(`${API_URL}/integrations/api-keys`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (apiKeysRes.ok) {
        const data = await apiKeysRes.json();
        setApiKeys(data.keys || []);
      }

      // Load multi-location sync settings
      const syncRes = await fetch(`${API_URL}/integrations/multi-location/sync-settings`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (syncRes.ok) {
        const data = await syncRes.json();
        setMultiLocationSync({
          enabled: data?.enabled ?? false,
          sync_menu: data?.sync_menu ?? true,
          sync_prices: data?.sync_prices ?? true,
          sync_inventory: data?.sync_inventory ?? false,
          sync_employees: data?.sync_employees ?? false,
          sync_promotions: data?.sync_promotions ?? true,
          sync_frequency: data?.sync_frequency ?? 'realtime',
          master_location_id: data?.master_location_id ?? null,
          linked_locations: data?.linked_locations || [],
        });
      }
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const connectIntegration = (integrationId: string) => {
    setConnectIntegrationId(integrationId);
    setConnectCredentials('');
    setShowConnectModal(true);
  };

  const handleConfirmConnect = async () => {
    if (!connectIntegrationId || !connectCredentials) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/integrations/integrations/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          integration_id: connectIntegrationId,
          credentials: { api_key: connectCredentials },
          settings: {},
        }),
      });

      if (response.ok) {
        toast.success('Integration connected successfully!');
        loadData();
      } else {
        toast.error('Failed to connect integration');
      }
    } catch (err) {
      console.error('Error connecting integration:', err);
      toast.error('Error connecting integration');
    } finally {
      setShowConnectModal(false);
      setConnectIntegrationId(null);
      setConnectCredentials('');
    }
  };

  const disconnectIntegration = async (integrationId: string) => {
    if (!confirm('Are you sure you want to disconnect this integration?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/integrations/integrations/${integrationId}/disconnect`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        toast.success('Integration disconnected');
        loadData();
      }
    } catch (err) {
      console.error('Error disconnecting integration:', err);
    }
  };

  const saveWebhooks = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/integrations/webhooks`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(webhooks),
      });

      if (response.ok) {
        toast.success('Webhook settings saved!');
      }
    } catch (err) {
      console.error('Error saving webhooks:', err);
      toast.error('Failed to save webhooks');
    } finally {
      setSaving(false);
    }
  };

  const createApiKey = () => {
    setNewApiKeyName('');
    setShowCreateApiKeyModal(true);
  };

  const handleConfirmCreateApiKey = async () => {
    if (!newApiKeyName) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/integrations/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newApiKeyName,
          permissions: ['read', 'write'],
        }),
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(`API Key created: ${data.api_key}\n\nSave this key securely, it won't be shown again.`);
        loadData();
      }
    } catch (err) {
      console.error('Error creating API key:', err);
    } finally {
      setShowCreateApiKeyModal(false);
      setNewApiKeyName('');
    }
  };

  const revokeApiKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return;

    try {
      const token = localStorage.getItem('access_token');
      await fetch(`${API_URL}/integrations/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      loadData();
    } catch (err) {
      console.error('Error revoking API key:', err);
    }
  };

  const saveMultiLocationSync = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_URL}/integrations/multi-location/sync-settings`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(multiLocationSync),
        }
      );

      if (response.ok) {
        toast.success('Multi-location sync settings saved!');
      }
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const filteredIntegrations = integrations.filter((integration) => {
    if (selectedCategory && integration.category !== selectedCategory) return false;
    if (showPopularOnly && !integration.popular) return false;
    if (searchQuery && !integration.name.toLowerCase().includes(searchQuery.toLowerCase()))
      return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/settings" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Integrations</h1>
            <p className="text-surface-500 mt-1">Connect 200+ third-party services and platforms</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link href="/settings">
            <Button variant="secondary">Cancel</Button>
          </Link>
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardBody>
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <Input
                placeholder="Search integrations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showPopularOnly}
                onChange={(e) => setShowPopularOnly(e.target.checked)}
                className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-surface-900">Popular only</span>
            </label>
          </div>

          <div className="mt-4 flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedCategory === null
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
              }`}
            >
              All Categories
            </button>
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                }`}
              >
                {category.name} ({category.count})
              </button>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* Integrations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredIntegrations.map((integration) => (
          <Card key={integration.id}>
            <CardBody>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold text-surface-900">{integration.name}</h3>
                  <p className="text-xs text-surface-500 capitalize">{(integration.category || '').replace('_', ' ')}</p>
                </div>
                {integration.popular && <Badge variant="primary">Popular</Badge>}
              </div>
              <p className="text-sm text-surface-600 mb-4">{integration.description}</p>
              <div className="flex gap-2">
                {integration.status === 'connected' ? (
                  <>
                    <Badge variant="success" dot>Connected</Badge>
                    <button
                      onClick={() => disconnectIntegration(integration.id)}
                      className="ml-auto text-sm text-red-600 hover:text-red-700"
                    >
                      Disconnect
                    </button>
                  </>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => connectIntegration(integration.id)}
                    className="ml-auto"
                  >
                    Connect
                  </Button>
                )}
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Hardware Devices */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-surface-900">Hardware Devices</h2>
            <Button size="sm" onClick={() => setShowHardwareModal(true)}>Add Device</Button>
          </div>
          <div className="space-y-2">
            {hardwareDevices.length === 0 ? (
              <p className="text-sm text-surface-500">No hardware devices configured</p>
            ) : (
              hardwareDevices.map((device: any) => (
                <div key={device.device_id} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-surface-900">{device.device_id}</p>
                    <p className="text-xs text-surface-500 capitalize">{device.device_type} - {device.connection_type}</p>
                  </div>
                  <Badge variant={device.enabled ? 'success' : 'neutral'}>
                    {device.enabled ? 'Online' : 'Offline'}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </CardBody>
      </Card>

      {/* Webhooks */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-surface-900">Webhooks</h2>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={webhooks.enabled}
                onChange={(e) => setWebhooks({ ...webhooks, enabled: e.target.checked })}
                className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-surface-900">Enable Webhooks</span>
            </label>
          </div>
          {webhooks.enabled && (
            <>
              <div className="space-y-3 mb-4">
                {(webhooks.endpoints || []).map((endpoint: any, index: number) => (
                  <div key={index} className="p-3 bg-surface-50 rounded-lg">
                    <Input
                      label="Endpoint URL"
                      value={endpoint.url}
                      onChange={(e) => {
                        const newEndpoints = [...webhooks.endpoints];
                        newEndpoints[index] = { ...endpoint, url: e.target.value };
                        setWebhooks({ ...webhooks, endpoints: newEndpoints });
                      }}
                      placeholder="https://your-server.com/webhook"
                    />
                  </div>
                ))}
              </div>
              <Button onClick={saveWebhooks} isLoading={saving}>
                Save Webhook Settings
              </Button>
            </>
          )}
        </CardBody>
      </Card>

      {/* API Keys */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-surface-900">API Keys</h2>
            <Button size="sm" onClick={createApiKey}>Create API Key</Button>
          </div>
          <div className="space-y-2">
            {apiKeys.length === 0 ? (
              <p className="text-sm text-surface-500">No API keys created</p>
            ) : (
              apiKeys.map((key: any) => (
                <div key={key.id} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-surface-900">{key.name}</p>
                    <p className="text-xs text-surface-500 font-mono">{key.key_preview}</p>
                  </div>
                  <button
                    onClick={() => revokeApiKey(key.id)}
                    className="text-sm text-red-600 hover:text-red-700"
                  >
                    Revoke
                  </button>
                </div>
              ))
            )}
          </div>
        </CardBody>
      </Card>

      {/* Multi-Location Sync */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-surface-900">Multi-Location Sync</h2>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={multiLocationSync.enabled}
                onChange={(e) => setMultiLocationSync({ ...multiLocationSync, enabled: e.target.checked })}
                className="w-5 h-5 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-surface-900">Enable Sync</span>
            </label>
          </div>
          {multiLocationSync.enabled && (
            <>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={multiLocationSync.sync_menu}
                    onChange={(e) => setMultiLocationSync({ ...multiLocationSync, sync_menu: e.target.checked })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Sync Menu</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={multiLocationSync.sync_prices}
                    onChange={(e) => setMultiLocationSync({ ...multiLocationSync, sync_prices: e.target.checked })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Sync Prices</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={multiLocationSync.sync_inventory}
                    onChange={(e) => setMultiLocationSync({ ...multiLocationSync, sync_inventory: e.target.checked })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Sync Inventory</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={multiLocationSync.sync_promotions}
                    onChange={(e) => setMultiLocationSync({ ...multiLocationSync, sync_promotions: e.target.checked })}
                    className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-surface-900">Sync Promotions</span>
                </label>
              </div>
              <Button onClick={saveMultiLocationSync} isLoading={saving}>
                Save Sync Settings
              </Button>
            </>
          )}
        </CardBody>
      </Card>

      {/* Connect Integration Modal */}
      {showConnectModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => { setShowConnectModal(false); setConnectIntegrationId(null); setConnectCredentials(''); }}
        >
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-md mx-4"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-surface-900 mb-4">Connect Integration</h3>
            <p className="text-sm text-surface-500 mb-4">Enter API key or credentials for {connectIntegrationId}.</p>
            <input
              type="text"
              autoFocus
              value={connectCredentials}
              onChange={(e) => setConnectCredentials(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && connectCredentials) handleConfirmConnect();
                if (e.key === 'Escape') { setShowConnectModal(false); setConnectIntegrationId(null); setConnectCredentials(''); }
              }}
              placeholder="API key / credentials"
              className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setShowConnectModal(false); setConnectIntegrationId(null); setConnectCredentials(''); }}
                className="flex-1 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmConnect}
                disabled={!connectCredentials}
                className="flex-1 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Connect
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create API Key Modal */}
      {showCreateApiKeyModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => { setShowCreateApiKeyModal(false); setNewApiKeyName(''); }}
        >
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-md mx-4"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-surface-900 mb-4">Create API Key</h3>
            <input
              type="text"
              autoFocus
              value={newApiKeyName}
              onChange={(e) => setNewApiKeyName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && newApiKeyName) handleConfirmCreateApiKey();
                if (e.key === 'Escape') { setShowCreateApiKeyModal(false); setNewApiKeyName(''); }
              }}
              placeholder="API key name"
              className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setShowCreateApiKeyModal(false); setNewApiKeyName(''); }}
                className="flex-1 py-2 bg-surface-100 text-surface-700 rounded-lg hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmCreateApiKey}
                disabled={!newApiKeyName}
                className="flex-1 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
