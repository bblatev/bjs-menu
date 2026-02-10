'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

interface AutoReorderRule {
  id: number;
  stock_item_id: number;
  stock_item_name: string;
  reorder_point: number;
  par_level: number;
  preferred_supplier_id: number;
  preferred_supplier_name: string;
  trigger_type: 'below_reorder_point' | 'below_par_level' | 'scheduled';
  min_order_quantity?: number;
  max_order_quantity?: number;
  order_multiple?: number;
  lead_time_days: number;
  requires_approval: boolean;
  auto_approve_below_amount?: number;
  notify_on_trigger: boolean;
  is_active: boolean;
  last_triggered?: string;
  current_quantity: number;
}

interface ReorderLog {
  id: number;
  rule_id: number;
  stock_item_name: string;
  triggered_at: string;
  quantity_ordered: number;
  estimated_cost: number;
  status: 'pending' | 'approved' | 'rejected' | 'ordered' | 'received';
  purchase_order_id?: number;
}

export default function AutoReorderPage() {
  const [rules, setRules] = useState<AutoReorderRule[]>([]);
  const [logs, setLogs] = useState<ReorderLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<AutoReorderRule | null>(null);
  const [showExecuteConfirm, setShowExecuteConfirm] = useState(false);
  const [formData, setFormData] = useState({
    stock_item_id: '',
    reorder_point: '',
    par_level: '',
    preferred_supplier_id: '',
    trigger_type: 'below_reorder_point',
    min_order_quantity: '',
    max_order_quantity: '',
    order_multiple: '',
    lead_time_days: '1',
    requires_approval: true,
    auto_approve_below_amount: '',
    notify_on_trigger: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('access_token');

      // Load rules
      const rulesResponse = await fetch(`${API_URL}/inventory-complete/auto-reorder/rules`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (rulesResponse.ok) {
        setRules(await rulesResponse.json());
      }

      // Load history
      const logsResponse = await fetch(`${API_URL}/inventory-complete/auto-reorder/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (logsResponse.ok) {
        setLogs(await logsResponse.json());
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/inventory-complete/auto-reorder/rules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...formData,
          stock_item_id: parseInt(formData.stock_item_id),
          reorder_point: parseFloat(formData.reorder_point),
          par_level: parseFloat(formData.par_level),
          preferred_supplier_id: parseInt(formData.preferred_supplier_id),
          min_order_quantity: formData.min_order_quantity ? parseFloat(formData.min_order_quantity) : null,
          max_order_quantity: formData.max_order_quantity ? parseFloat(formData.max_order_quantity) : null,
          order_multiple: formData.order_multiple ? parseFloat(formData.order_multiple) : null,
          lead_time_days: parseInt(formData.lead_time_days),
          auto_approve_below_amount: formData.auto_approve_below_amount ? parseFloat(formData.auto_approve_below_amount) : null,
        }),
      });
      if (response.ok) {
        loadData();
        setShowModal(false);
        resetForm();
      } else {
        const error = await response.json();
        alert(error.detail || 'Error creating rule');
      }
    } catch (error) {
      console.error('Error creating rule:', error);
    }
  };

  const handleToggleActive = async (ruleId: number, isActive: boolean) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/inventory-complete/auto-reorder/rules/${ruleId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !isActive }),
      });
      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error toggling rule:', error);
    }
  };

  const handleDelete = async (ruleId: number) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/inventory-complete/auto-reorder/rules/${ruleId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error deleting rule:', error);
    }
  };

  const executeAutoReorder = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/inventory-complete/auto-reorder/execute`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const result = await response.json();
        alert(`Auto-reorder executed: ${result.purchase_orders_created || 0} POs created`);
        loadData();
      }
    } catch (error) {
      console.error('Error executing auto-reorder:', error);
    }
    setShowExecuteConfirm(false);
  };

  const resetForm = () => {
    setFormData({
      stock_item_id: '',
      reorder_point: '',
      par_level: '',
      preferred_supplier_id: '',
      trigger_type: 'below_reorder_point',
      min_order_quantity: '',
      max_order_quantity: '',
      order_multiple: '',
      lead_time_days: '1',
      requires_approval: true,
      auto_approve_below_amount: '',
      notify_on_trigger: true,
    });
    setEditingRule(null);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-blue-100 text-blue-700',
      rejected: 'bg-red-100 text-red-700',
      ordered: 'bg-purple-100 text-purple-700',
      received: 'bg-green-100 text-green-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  // Stats
  const activeRules = rules.filter(r => r.is_active).length;
  const triggeredToday = logs.filter(l => new Date(l.triggered_at).toDateString() === new Date().toDateString()).length;
  const belowReorderPoint = rules.filter(r => r.current_quantity <= r.reorder_point).length;

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
          <Link href="/stock" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Auto-Reorder</h1>
            <p className="text-surface-500 mt-1">Automatic purchase order generation</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowExecuteConfirm(true)}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Run Now
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Rule
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <span className="text-xl">✅</span>
            </div>
            <span className="text-sm text-surface-500">Active Rules</span>
          </div>
          <div className="text-2xl font-bold text-green-600">{activeRules}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
              <span className="text-xl">⚠️</span>
            </div>
            <span className="text-sm text-surface-500">Below Reorder Point</span>
          </div>
          <div className="text-2xl font-bold text-red-600">{belowReorderPoint}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <span className="text-xl">📦</span>
            </div>
            <span className="text-sm text-surface-500">Triggered Today</span>
          </div>
          <div className="text-2xl font-bold text-blue-600">{triggeredToday}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
              <span className="text-xl">📋</span>
            </div>
            <span className="text-sm text-surface-500">Total Rules</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{rules.length}</div>
        </motion.div>
      </div>

      {/* Rules Table */}
      <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
        <div className="p-4 border-b border-surface-100">
          <h3 className="font-semibold text-surface-900">Reorder Rules</h3>
        </div>
        <table className="w-full">
          <thead className="bg-surface-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Item</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Supplier</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Current Qty</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Reorder Point</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Par Level</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Lead Time</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {rules.map((rule, index) => {
              const needsReorder = rule.current_quantity <= rule.reorder_point;
              return (
                <motion.tr
                  key={rule.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className={`hover:bg-surface-50 ${needsReorder ? 'bg-red-50' : ''}`}
                >
                  <td className="px-6 py-4">
                    <div className="font-medium text-surface-900">{rule.stock_item_name}</div>
                    <div className="text-xs text-surface-500">{(rule.trigger_type || '').replace(/_/g, ' ')}</div>
                  </td>
                  <td className="px-6 py-4 text-surface-600">{rule.preferred_supplier_name}</td>
                  <td className="px-6 py-4 text-center">
                    <span className={`font-medium ${needsReorder ? 'text-red-600' : 'text-surface-900'}`}>
                      {rule.current_quantity}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center text-surface-600">{rule.reorder_point}</td>
                  <td className="px-6 py-4 text-center text-surface-600">{rule.par_level}</td>
                  <td className="px-6 py-4 text-center text-surface-600">{rule.lead_time_days}d</td>
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() => handleToggleActive(rule.id, rule.is_active)}
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        rule.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {rule.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => {}}
                        className="p-1 text-surface-400 hover:text-surface-600 rounded"
                        title="Edit"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id)}
                        className="p-1 text-red-400 hover:text-red-600 rounded"
                        title="Delete"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </motion.tr>
              );
            })}
            {rules.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-surface-500">
                  No auto-reorder rules configured
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Recent Triggers */}
      <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
        <div className="p-4 border-b border-surface-100">
          <h3 className="font-semibold text-surface-900">Recent Triggers</h3>
        </div>
        <div className="divide-y divide-surface-100">
          {logs.slice(0, 10).map((log, index) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.02 }}
              className="p-4 flex items-center justify-between hover:bg-surface-50"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
                  <span className="text-xl">📦</span>
                </div>
                <div>
                  <div className="font-medium text-surface-900">{log.stock_item_name}</div>
                  <div className="text-sm text-surface-500">
                    Qty: {log.quantity_ordered} • Est. Cost: {formatCurrency(log.estimated_cost)}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-sm text-surface-600">{formatDate(log.triggered_at)}</div>
                  {log.purchase_order_id && (
                    <div className="text-xs text-surface-500">PO #{log.purchase_order_id}</div>
                  )}
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(log.status)}`}>
                  {log.status}
                </span>
              </div>
            </motion.div>
          ))}
          {logs.length === 0 && (
            <div className="p-12 text-center text-surface-500">
              No reorder triggers yet
            </div>
          )}
        </div>
      </div>

      {/* Create Rule Modal */}
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
                <h2 className="text-xl font-bold text-surface-900">Create Auto-Reorder Rule</h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Stock Item</label>
                    <select
                      value={formData.stock_item_id}
                      onChange={(e) => setFormData({ ...formData, stock_item_id: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="">Select item...</option>
                      {/* Would be populated from API */}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Preferred Supplier</label>
                    <select
                      value={formData.preferred_supplier_id}
                      onChange={(e) => setFormData({ ...formData, preferred_supplier_id: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="">Select supplier...</option>
                      {/* Would be populated from API */}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Reorder Point</label>
                    <input
                      type="number"
                      value={formData.reorder_point}
                      onChange={(e) => setFormData({ ...formData, reorder_point: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="Trigger level"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Par Level</label>
                    <input
                      type="number"
                      value={formData.par_level}
                      onChange={(e) => setFormData({ ...formData, par_level: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="Target level"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Lead Time (days)</label>
                    <input
                      type="number"
                      value={formData.lead_time_days}
                      onChange={(e) => setFormData({ ...formData, lead_time_days: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Trigger Type</label>
                  <select
                    value={formData.trigger_type}
                    onChange={(e) => setFormData({ ...formData, trigger_type: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                  >
                    <option value="below_reorder_point">Below Reorder Point</option>
                    <option value="below_par_level">Below Par Level</option>
                    <option value="scheduled">Scheduled</option>
                  </select>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Min Order Qty</label>
                    <input
                      type="number"
                      value={formData.min_order_quantity}
                      onChange={(e) => setFormData({ ...formData, min_order_quantity: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="Optional"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Max Order Qty</label>
                    <input
                      type="number"
                      value={formData.max_order_quantity}
                      onChange={(e) => setFormData({ ...formData, max_order_quantity: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="Optional"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Order Multiple</label>
                    <input
                      type="number"
                      value={formData.order_multiple}
                      onChange={(e) => setFormData({ ...formData, order_multiple: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="e.g., 12 for cases"
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.requires_approval}
                      onChange={(e) => setFormData({ ...formData, requires_approval: e.target.checked })}
                      className="w-4 h-4 rounded text-amber-500"
                    />
                    <span className="text-sm text-surface-700">Requires manager approval</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.notify_on_trigger}
                      onChange={(e) => setFormData({ ...formData, notify_on_trigger: e.target.checked })}
                      className="w-4 h-4 rounded text-amber-500"
                    />
                    <span className="text-sm text-surface-700">Send notification when triggered</span>
                  </label>
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
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Create Rule
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Execute Confirmation Modal */}
      <AnimatePresence>
        {showExecuteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-md w-full"
            >
              <div className="p-6">
                <div className="text-center">
                  <div className="text-6xl mb-4">🔄</div>
                  <h3 className="text-xl font-bold text-surface-900 mb-2">Run Auto-Reorder Check</h3>
                  <p className="text-surface-500 mb-6">
                    This will check all active rules and create purchase orders for items below their reorder points.
                  </p>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowExecuteConfirm(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={executeAutoReorder}
                  className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                >
                  Run Now
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
