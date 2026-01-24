'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

interface Webhook {
  id: number;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  secret_key: string;
  created_at: string;
  last_triggered?: string;
  success_count: number;
  failure_count: number;
}

interface WebhookDelivery {
  id: number;
  webhook_id: number;
  event_type: string;
  payload_size: number;
  response_status: number;
  response_time_ms: number;
  status: 'success' | 'failed' | 'pending';
  created_at: string;
  error_message?: string;
}

const AVAILABLE_EVENTS = [
  { value: 'order.created', label: 'Order Created', category: 'Orders' },
  { value: 'order.updated', label: 'Order Updated', category: 'Orders' },
  { value: 'order.completed', label: 'Order Completed', category: 'Orders' },
  { value: 'order.cancelled', label: 'Order Cancelled', category: 'Orders' },
  { value: 'payment.received', label: 'Payment Received', category: 'Payments' },
  { value: 'payment.refunded', label: 'Payment Refunded', category: 'Payments' },
  { value: 'inventory.low_stock', label: 'Low Stock Alert', category: 'Inventory' },
  { value: 'inventory.updated', label: 'Inventory Updated', category: 'Inventory' },
  { value: 'customer.created', label: 'Customer Created', category: 'Customers' },
  { value: 'reservation.created', label: 'Reservation Created', category: 'Reservations' },
  { value: 'reservation.cancelled', label: 'Reservation Cancelled', category: 'Reservations' },
];

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showDeliveriesModal, setShowDeliveriesModal] = useState(false);
  const [selectedWebhook, setSelectedWebhook] = useState<Webhook | null>(null);
  const [editingWebhook, setEditingWebhook] = useState<Webhook | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    events: [] as string[],
  });

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    try {
      const token = localStorage.getItem('access_token');
      // Mock data
      setWebhooks([
        {
          id: 1,
          name: 'Order Notification',
          url: 'https://example.com/webhooks/orders',
          events: ['order.created', 'order.completed'],
          is_active: true,
          secret_key: 'whsec_xxxx...xxxx',
          created_at: '2024-12-01',
          last_triggered: '2024-12-28T15:30:00',
          success_count: 152,
          failure_count: 3,
        },
        {
          id: 2,
          name: 'Inventory Alerts',
          url: 'https://slack.com/webhooks/inventory',
          events: ['inventory.low_stock'],
          is_active: true,
          secret_key: 'whsec_yyyy...yyyy',
          created_at: '2024-12-15',
          last_triggered: '2024-12-27T08:00:00',
          success_count: 28,
          failure_count: 0,
        },
      ]);
    } catch (error) {
      console.error('Error loading webhooks:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const token = localStorage.getItem('access_token');
      // Would call API
      const newWebhook: Webhook = {
        id: webhooks.length + 1,
        name: formData.name,
        url: formData.url,
        events: formData.events,
        is_active: true,
        secret_key: 'whsec_' + Math.random().toString(36).substring(7),
        created_at: new Date().toISOString().split('T')[0],
        success_count: 0,
        failure_count: 0,
      };
      setWebhooks([...webhooks, newWebhook]);
      setShowModal(false);
      resetForm();
    } catch (error) {
      console.error('Error creating webhook:', error);
    }
  };

  const handleToggleActive = async (id: number) => {
    setWebhooks(webhooks.map(wh =>
      wh.id === id ? { ...wh, is_active: !wh.is_active } : wh
    ));
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this webhook?')) return;
    setWebhooks(webhooks.filter(wh => wh.id !== id));
  };

  const handleTestWebhook = async (webhook: Webhook) => {
    alert(`Sending test event to ${webhook.url}...`);
    // Would call API to send test
  };

  const viewDeliveries = (webhook: Webhook) => {
    setSelectedWebhook(webhook);
    // Mock deliveries
    setDeliveries([
      { id: 1, webhook_id: webhook.id, event_type: 'order.created', payload_size: 1240, response_status: 200, response_time_ms: 145, status: 'success', created_at: '2024-12-28T15:30:00' },
      { id: 2, webhook_id: webhook.id, event_type: 'order.completed', payload_size: 980, response_status: 200, response_time_ms: 98, status: 'success', created_at: '2024-12-28T15:25:00' },
      { id: 3, webhook_id: webhook.id, event_type: 'order.created', payload_size: 1100, response_status: 500, response_time_ms: 2500, status: 'failed', created_at: '2024-12-28T14:00:00', error_message: 'Connection timeout' },
    ]);
    setShowDeliveriesModal(true);
  };

  const resetForm = () => {
    setFormData({ name: '', url: '', events: [] });
    setEditingWebhook(null);
  };

  const toggleEvent = (event: string) => {
    if (formData.events.includes(event)) {
      setFormData({ ...formData, events: formData.events.filter(e => e !== event) });
    } else {
      setFormData({ ...formData, events: [...formData.events, event] });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-700';
      case 'failed': return 'bg-red-100 text-red-700';
      case 'pending': return 'bg-yellow-100 text-yellow-700';
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
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Webhooks</h1>
            <p className="text-surface-500 mt-1">Receive real-time notifications for system events</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Webhook
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">🔗</div>
          <div className="text-2xl font-bold text-surface-900">{webhooks.length}</div>
          <div className="text-sm text-surface-500">Total Webhooks</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">✅</div>
          <div className="text-2xl font-bold text-green-600">{webhooks.filter(w => w.is_active).length}</div>
          <div className="text-sm text-surface-500">Active</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">📤</div>
          <div className="text-2xl font-bold text-blue-600">
            {webhooks.reduce((sum, w) => sum + w.success_count, 0)}
          </div>
          <div className="text-sm text-surface-500">Successful Deliveries</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="text-3xl mb-2">❌</div>
          <div className="text-2xl font-bold text-red-600">
            {webhooks.reduce((sum, w) => sum + w.failure_count, 0)}
          </div>
          <div className="text-sm text-surface-500">Failed Deliveries</div>
        </motion.div>
      </div>

      {/* Webhooks List */}
      <div className="space-y-4">
        {webhooks.map((webhook, index) => (
          <motion.div
            key={webhook.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="bg-white rounded-xl p-6 border border-surface-200"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-bold text-surface-900">{webhook.name}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    webhook.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {webhook.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-surface-600 mb-3">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  <code className="bg-surface-100 px-2 py-0.5 rounded">{webhook.url}</code>
                </div>
                <div className="flex flex-wrap gap-2 mb-3">
                  {webhook.events.map((event) => (
                    <span key={event} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                      {event}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-4 text-xs text-surface-500">
                  <span>Created: {webhook.created_at}</span>
                  {webhook.last_triggered && (
                    <span>Last triggered: {new Date(webhook.last_triggered).toLocaleString()}</span>
                  )}
                  <span className="text-green-600">{webhook.success_count} successful</span>
                  {webhook.failure_count > 0 && (
                    <span className="text-red-600">{webhook.failure_count} failed</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => viewDeliveries(webhook)}
                  className="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg"
                  title="View Deliveries"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </button>
                <button
                  onClick={() => handleTestWebhook(webhook)}
                  className="p-2 text-surface-400 hover:text-surface-600 hover:bg-surface-100 rounded-lg"
                  title="Send Test"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </button>
                <button
                  onClick={() => handleToggleActive(webhook.id)}
                  className={`p-2 rounded-lg ${
                    webhook.is_active
                      ? 'text-green-600 hover:bg-green-50'
                      : 'text-gray-400 hover:bg-gray-100'
                  }`}
                  title={webhook.is_active ? 'Disable' : 'Enable'}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={
                      webhook.is_active
                        ? "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        : "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                    } />
                  </svg>
                </button>
                <button
                  onClick={() => handleDelete(webhook.id)}
                  className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                  title="Delete"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </motion.div>
        ))}

        {webhooks.length === 0 && (
          <div className="bg-white rounded-xl p-12 text-center border border-surface-200">
            <div className="text-6xl mb-4">🔗</div>
            <h3 className="text-xl font-bold text-surface-900 mb-2">No Webhooks</h3>
            <p className="text-surface-500 mb-4">Create a webhook to receive real-time event notifications</p>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
            >
              Add Webhook
            </button>
          </div>
        )}
      </div>

      {/* Create Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Create Webhook</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Webhook Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Order Notifications"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Endpoint URL</label>
                  <input
                    type="url"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="https://your-server.com/webhooks"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-2">Events to Listen</label>
                  <div className="space-y-3">
                    {['Orders', 'Payments', 'Inventory', 'Customers', 'Reservations'].map((category) => (
                      <div key={category}>
                        <div className="text-xs font-semibold text-surface-500 uppercase mb-2">{category}</div>
                        <div className="flex flex-wrap gap-2">
                          {AVAILABLE_EVENTS.filter(e => e.category === category).map((event) => (
                            <button
                              key={event.value}
                              type="button"
                              onClick={() => toggleEvent(event.value)}
                              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                                formData.events.includes(event.value)
                                  ? 'bg-amber-500 text-gray-900'
                                  : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                              }`}
                            >
                              {event.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={!formData.name || !formData.url || formData.events.length === 0}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 disabled:opacity-50"
                >
                  Create Webhook
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Deliveries Modal */}
      <AnimatePresence>
        {showDeliveriesModal && selectedWebhook && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">{selectedWebhook.name} - Deliveries</h2>
              </div>
              <div className="p-6">
                <table className="w-full">
                  <thead className="bg-surface-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-surface-600">Event</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-surface-600">Time</th>
                      <th className="px-4 py-2 text-center text-xs font-semibold text-surface-600">Status</th>
                      <th className="px-4 py-2 text-right text-xs font-semibold text-surface-600">Response</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-100">
                    {deliveries.map((delivery) => (
                      <tr key={delivery.id} className="hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                            {delivery.event_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-surface-600">
                          {new Date(delivery.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(delivery.status)}`}>
                            {delivery.response_status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-sm text-surface-600">
                          {delivery.response_time_ms}ms
                          {delivery.error_message && (
                            <div className="text-xs text-red-600">{delivery.error_message}</div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-6 border-t border-surface-100">
                <button
                  onClick={() => setShowDeliveriesModal(false)}
                  className="w-full px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
