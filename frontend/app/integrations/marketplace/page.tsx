'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

interface Integration {
  id: string;
  name: string;
  description: string;
  category: string;
  logo_url?: string;
  pricing_type: string;
  monthly_cost?: number;
  is_popular: boolean;
  is_new: boolean;
  features: string[];
  supported_regions: string[];
}

interface ConnectedIntegration {
  id: number;
  integration_id: string;
  integration_name: string;
  status: 'active' | 'inactive' | 'error';
  connected_at: string;
  last_sync?: string;
}

const CATEGORIES = [
  { id: 'all', name: 'All Integrations', icon: '🔗' },
  { id: 'accounting', name: 'Accounting', icon: '📊' },
  { id: 'payment', name: 'Payments', icon: '💳' },
  { id: 'delivery', name: 'Delivery', icon: '🚚' },
  { id: 'reservation', name: 'Reservations', icon: '📅' },
  { id: 'loyalty', name: 'Loyalty & Marketing', icon: '⭐' },
  { id: 'hr', name: 'HR & Payroll', icon: '👥' },
  { id: 'hotel', name: 'Hotel PMS', icon: '🏨' },
  { id: 'inventory', name: 'Inventory', icon: '📦' },
  { id: 'analytics', name: 'Analytics', icon: '📈' },
  { id: 'ecommerce', name: 'E-commerce', icon: '🛒' },
];

export default function IntegrationMarketplacePage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [connectedIntegrations, setConnectedIntegrations] = useState<ConnectedIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [showConnectedOnly, setShowConnectedOnly] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState<Integration | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('access_token');

      // Load all integrations
      const integrationsRes = await fetch('/api/v1/enterprise/integrations/marketplace', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (integrationsRes.ok) {
        const data = await integrationsRes.json();
        setIntegrations(data);
      } else {
        // Mock data for demo
        setIntegrations(getMockIntegrations());
      }

      // Load connected integrations
      const connectedRes = await fetch('/api/v1/enterprise/integrations/connected', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (connectedRes.ok) {
        const data = await connectedRes.json();
        setConnectedIntegrations(data);
      }
    } catch (error) {
      console.error('Error loading integrations:', error);
      setIntegrations(getMockIntegrations());
    } finally {
      setLoading(false);
    }
  };

  const getMockIntegrations = (): Integration[] => [
    { id: 'quickbooks', name: 'QuickBooks Online', description: 'Sync sales, expenses, and inventory with QuickBooks', category: 'accounting', pricing_type: 'free', is_popular: true, is_new: false, features: ['Auto-sync sales', 'Expense tracking', 'Invoice generation'], supported_regions: ['US', 'CA', 'UK', 'AU'] },
    { id: 'xero', name: 'Xero', description: 'Cloud accounting integration for seamless bookkeeping', category: 'accounting', pricing_type: 'free', is_popular: true, is_new: false, features: ['Bank reconciliation', 'P&L reports', 'Tax compliance'], supported_regions: ['Global'] },
    { id: 'stripe', name: 'Stripe', description: 'Accept payments online and in-person', category: 'payment', pricing_type: 'free', is_popular: true, is_new: false, features: ['Card payments', 'Apple Pay', 'Google Pay', 'Recurring billing'], supported_regions: ['Global'] },
    { id: 'doordash', name: 'DoorDash', description: 'Receive and manage DoorDash delivery orders', category: 'delivery', pricing_type: 'free', is_popular: true, is_new: false, features: ['Auto-accept orders', 'Menu sync', 'Driver tracking'], supported_regions: ['US', 'CA', 'AU'] },
    { id: 'uber_eats', name: 'Uber Eats', description: 'Integrate Uber Eats orders directly into your POS', category: 'delivery', pricing_type: 'free', is_popular: true, is_new: false, features: ['Real-time orders', 'Menu management', 'Analytics'], supported_regions: ['Global'] },
    { id: 'opentable', name: 'OpenTable', description: 'Sync reservations from OpenTable', category: 'reservation', pricing_type: 'paid', monthly_cost: 39, is_popular: true, is_new: false, features: ['Auto table assignment', 'Guest profiles', 'Waitlist sync'], supported_regions: ['Global'] },
    { id: 'mailchimp', name: 'Mailchimp', description: 'Email marketing automation', category: 'loyalty', pricing_type: 'free', is_popular: true, is_new: false, features: ['Customer segments', 'Campaign automation', 'Analytics'], supported_regions: ['Global'] },
    { id: 'gusto', name: 'Gusto', description: 'Payroll and HR management', category: 'hr', pricing_type: 'paid', monthly_cost: 49, is_popular: false, is_new: true, features: ['Payroll sync', 'Time tracking', 'Benefits'], supported_regions: ['US'] },
    { id: 'opera', name: 'Oracle Opera', description: 'Hotel property management integration', category: 'hotel', pricing_type: 'enterprise', is_popular: false, is_new: true, features: ['Room charges', 'Guest sync', 'F&B credits'], supported_regions: ['Global'] },
    { id: 'mews', name: 'Mews', description: 'Modern hotel PMS integration', category: 'hotel', pricing_type: 'paid', monthly_cost: 99, is_popular: false, is_new: true, features: ['Real-time sync', 'Room service', 'Package billing'], supported_regions: ['Global'] },
    { id: 'marketman', name: 'MarketMan', description: 'Advanced inventory management', category: 'inventory', pricing_type: 'paid', monthly_cost: 79, is_popular: false, is_new: false, features: ['Recipe costing', 'Purchase orders', 'Waste tracking'], supported_regions: ['Global'] },
    { id: 'google_analytics', name: 'Google Analytics 4', description: 'Track customer behavior and conversions', category: 'analytics', pricing_type: 'free', is_popular: true, is_new: false, features: ['Event tracking', 'Conversion funnels', 'Audience insights'], supported_regions: ['Global'] },
  ];

  const handleConnect = async (integration: Integration) => {
    setConnecting(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/enterprise/integrations/${integration.id}/connect`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ config: {} })
      });

      if (response.ok) {
        alert(`Successfully connected to ${integration.name}!`);
        loadData();
        setSelectedIntegration(null);
      } else {
        // Demo mode - simulate success
        setConnectedIntegrations(prev => [...prev, {
          id: Date.now(),
          integration_id: integration.id,
          integration_name: integration.name,
          status: 'active',
          connected_at: new Date().toISOString()
        }]);
        setSelectedIntegration(null);
      }
    } catch (error) {
      console.error('Error connecting:', error);
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async (connectionId: number) => {
    if (!confirm('Are you sure you want to disconnect this integration?')) return;

    try {
      const token = localStorage.getItem('access_token');
      await fetch(`/api/v1/enterprise/integrations/connections/${connectionId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setConnectedIntegrations(prev => prev.filter(c => c.id !== connectionId));
    } catch (error) {
      console.error('Error disconnecting:', error);
      setConnectedIntegrations(prev => prev.filter(c => c.id !== connectionId));
    }
  };

  const filteredIntegrations = integrations.filter(integration => {
    const matchesCategory = selectedCategory === 'all' || integration.category === selectedCategory;
    const matchesSearch = integration.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         integration.description.toLowerCase().includes(searchTerm.toLowerCase());
    const connectedIds = connectedIntegrations.map(c => c.integration_id);
    const matchesConnected = !showConnectedOnly || connectedIds.includes(integration.id);
    return matchesCategory && matchesSearch && matchesConnected;
  });

  const isConnected = (integrationId: string) =>
    connectedIntegrations.some(c => c.integration_id === integrationId);

  const getConnection = (integrationId: string) =>
    connectedIntegrations.find(c => c.integration_id === integrationId);

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
          <h1 className="text-2xl font-display font-bold text-surface-900">Integration Marketplace</h1>
          <p className="text-surface-500 mt-1">Connect your favorite tools and services</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-sm text-surface-600">
            <span className="font-semibold text-amber-600">{connectedIntegrations.length}</span> connected
          </div>
          <div className="text-sm text-surface-600">
            <span className="font-semibold">{integrations.length}</span> available
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Connected', value: connectedIntegrations.length, icon: '🔗', color: 'green' },
          { label: 'Active', value: connectedIntegrations.filter(c => c.status === 'active').length, icon: '✅', color: 'blue' },
          { label: 'Errors', value: connectedIntegrations.filter(c => c.status === 'error').length, icon: '⚠️', color: 'red' },
          { label: 'Available', value: integrations.length - connectedIntegrations.length, icon: '📦', color: 'amber' },
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

      {/* Search and Filters */}
      <div className="bg-white rounded-xl border border-surface-200 p-4">
        <div className="flex items-center gap-4">
          <div className="relative flex-1">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search integrations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-surface-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500"
            />
          </div>
          <label className="flex items-center gap-2 px-4 py-2 bg-surface-50 rounded-lg cursor-pointer">
            <input
              type="checkbox"
              checked={showConnectedOnly}
              onChange={(e) => setShowConnectedOnly(e.target.checked)}
              className="w-4 h-4 rounded text-amber-500"
            />
            <span className="text-sm text-surface-700">Connected only</span>
          </label>
        </div>
      </div>

      {/* Categories */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {CATEGORIES.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl whitespace-nowrap transition-all ${
              selectedCategory === category.id
                ? 'bg-amber-500 text-gray-900'
                : 'bg-white border border-surface-200 text-surface-700 hover:border-amber-300'
            }`}
          >
            <span>{category.icon}</span>
            <span className="text-sm font-medium">{category.name}</span>
          </button>
        ))}
      </div>

      {/* Integrations Grid */}
      <div className="grid grid-cols-3 gap-4">
        {filteredIntegrations.map((integration, index) => {
          const connected = isConnected(integration.id);
          const connection = getConnection(integration.id);

          return (
            <motion.div
              key={integration.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`bg-white rounded-xl border overflow-hidden hover:shadow-lg transition-all cursor-pointer ${
                connected ? 'border-green-300 bg-green-50/50' : 'border-surface-200 hover:border-amber-300'
              }`}
              onClick={() => setSelectedIntegration(integration)}
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-surface-100 flex items-center justify-center text-2xl">
                      {integration.logo_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img src={integration.logo_url} alt={integration.name} className="w-8 h-8" />
                      ) : (
                        getIntegrationIcon(integration.category)
                      )}
                    </div>
                    <div>
                      <div className="font-semibold text-surface-900">{integration.name}</div>
                      <div className="text-xs text-surface-500 capitalize">{integration.category}</div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {integration.is_new && (
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">New</span>
                    )}
                    {integration.is_popular && (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full">Popular</span>
                    )}
                  </div>
                </div>

                <p className="text-sm text-surface-600 mb-3 line-clamp-2">{integration.description}</p>

                <div className="flex items-center justify-between">
                  <div className="text-sm">
                    {integration.pricing_type === 'free' && (
                      <span className="text-green-600 font-medium">Free</span>
                    )}
                    {integration.pricing_type === 'paid' && integration.monthly_cost && (
                      <span className="text-surface-600">${integration.monthly_cost}/mo</span>
                    )}
                    {integration.pricing_type === 'enterprise' && (
                      <span className="text-purple-600 font-medium">Enterprise</span>
                    )}
                  </div>
                  {connected ? (
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Connected
                    </span>
                  ) : (
                    <span className="text-amber-600 text-sm font-medium">Connect →</span>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {filteredIntegrations.length === 0 && (
        <div className="text-center py-12 text-surface-500">
          <div className="text-4xl mb-4">🔍</div>
          <div className="font-medium">No integrations found</div>
          <div className="text-sm">Try adjusting your search or filters</div>
        </div>
      )}

      {/* Integration Detail Modal */}
      {selectedIntegration && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelectedIntegration(null)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl w-full max-w-lg overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-start gap-4 mb-4">
                <div className="w-16 h-16 rounded-xl bg-surface-100 flex items-center justify-center text-3xl">
                  {getIntegrationIcon(selectedIntegration.category)}
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-bold text-surface-900">{selectedIntegration.name}</h2>
                  <p className="text-surface-500 capitalize">{selectedIntegration.category}</p>
                </div>
                <button onClick={() => setSelectedIntegration(null)} className="p-2 hover:bg-surface-100 rounded-lg">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <p className="text-surface-600 mb-6">{selectedIntegration.description}</p>

              <div className="mb-6">
                <h3 className="font-semibold text-surface-900 mb-2">Features</h3>
                <ul className="space-y-2">
                  {selectedIntegration.features.map((feature, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-surface-600">
                      <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mb-6">
                <h3 className="font-semibold text-surface-900 mb-2">Supported Regions</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedIntegration.supported_regions.map((region, i) => (
                    <span key={i} className="px-2 py-1 bg-surface-100 text-surface-600 text-xs rounded-full">
                      {region}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-surface-100">
                <div>
                  {selectedIntegration.pricing_type === 'free' && (
                    <span className="text-green-600 font-semibold">Free to use</span>
                  )}
                  {selectedIntegration.pricing_type === 'paid' && selectedIntegration.monthly_cost && (
                    <span className="text-surface-900 font-semibold">${selectedIntegration.monthly_cost}/month</span>
                  )}
                  {selectedIntegration.pricing_type === 'enterprise' && (
                    <span className="text-purple-600 font-semibold">Contact Sales</span>
                  )}
                </div>
                {isConnected(selectedIntegration.id) ? (
                  <button
                    onClick={() => {
                      const conn = getConnection(selectedIntegration.id);
                      if (conn) handleDisconnect(conn.id);
                    }}
                    className="px-6 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50"
                  >
                    Disconnect
                  </button>
                ) : (
                  <button
                    onClick={() => handleConnect(selectedIntegration)}
                    disabled={connecting}
                    className="px-6 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
                  >
                    {connecting ? 'Connecting...' : 'Connect'}
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

function getIntegrationIcon(category: string): string {
  const icons: Record<string, string> = {
    accounting: '📊',
    payment: '💳',
    delivery: '🚚',
    reservation: '📅',
    loyalty: '⭐',
    hr: '👥',
    hotel: '🏨',
    inventory: '📦',
    analytics: '📈',
    ecommerce: '🛒',
  };
  return icons[category] || '🔗';
}
