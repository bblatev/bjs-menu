'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Budget {
  id: number;
  name: string;
  budget_type: 'monthly' | 'quarterly' | 'annual' | 'project';
  period_start: string;
  period_end: string;
  total_amount: number;
  spent_amount: number;
  status: 'draft' | 'active' | 'completed';
}

interface BudgetVariance {
  budget_id: number;
  budget_name: string;
  period: { start: string; end: string };
  total_budgeted: number;
  total_actual: number;
  total_variance: number;
  variance_percentage: number;
  line_items: {
    category: string;
    budgeted: number;
    actual: number;
    variance: number;
    percentage: number;
  }[];
}

interface BudgetLineItem {
  account_id?: number;
  category?: string;
  amount: number;
}

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [variance, setVariance] = useState<BudgetVariance | null>(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showVarianceModal, setShowVarianceModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [formData, setFormData] = useState({
    name: '',
    budget_type: 'monthly' as const,
    period_start: '',
    period_end: '',
    line_items: [{ category: '', amount: 0 }] as BudgetLineItem[],
  });

  useEffect(() => {
    loadBudgets();
  }, []);

  const loadBudgets = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/budgets`, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setBudgets(data);
      }
    } catch (error) {
      console.error('Error loading budgets:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadVariance = async (budgetId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/budget-variance/${budgetId}`, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setVariance(data);
        setShowVarianceModal(true);
      }
    } catch (error) {
      console.error('Error loading variance:', error);
    }
  };

  const handleCreate = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/budgets`, {
        credentials: 'include',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });
      if (response.ok) {
        loadBudgets();
        setShowModal(false);
        resetForm();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error creating budget');
      }
    } catch (error) {
      console.error('Error creating budget:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      budget_type: 'monthly',
      period_start: '',
      period_end: '',
      line_items: [{ category: '', amount: 0 }],
    });
  };

  const addLineItem = () => {
    setFormData({
      ...formData,
      line_items: [...formData.line_items, { category: '', amount: 0 }],
    });
  };

  const removeLineItem = (index: number) => {
    setFormData({
      ...formData,
      line_items: formData.line_items.filter((_, i) => i !== index),
    });
  };

  const updateLineItem = (index: number, field: string, value: any) => {
    const newItems = [...formData.line_items];
    newItems[index] = { ...newItems[index], [field]: value };
    setFormData({ ...formData, line_items: newItems });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-700',
      active: 'bg-green-100 text-green-700',
      completed: 'bg-blue-100 text-blue-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      monthly: '📅',
      quarterly: '📊',
      annual: '📆',
      project: '📁',
    };
    return icons[type] || '📋';
  };

  const calculateProgress = (budget: Budget) => {
    if (budget.total_amount === 0) return 0;
    return Math.min((budget.spent_amount / budget.total_amount) * 100, 100);
  };

  const filteredBudgets = budgets.filter(b => {
    if (filterStatus !== 'all' && b.status !== filterStatus) return false;
    return true;
  });

  // Calculate totals
  const totalBudgeted = budgets.filter(b => b.status === 'active').reduce((sum, b) => sum + b.total_amount, 0);
  const totalSpent = budgets.filter(b => b.status === 'active').reduce((sum, b) => sum + b.spent_amount, 0);
  const totalRemaining = totalBudgeted - totalSpent;

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
          <Link href="/financial-management" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Budget Management</h1>
            <p className="text-surface-500 mt-1">Plan and track your financial budgets</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Create Budget
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-6 border border-blue-200"
        >
          <div className="text-3xl mb-2">💰</div>
          <div className="text-2xl font-bold text-blue-900">{formatCurrency(totalBudgeted)}</div>
          <div className="text-sm text-blue-600">Total Budgeted</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-xl p-6 border border-amber-200"
        >
          <div className="text-3xl mb-2">📊</div>
          <div className="text-2xl font-bold text-amber-900">{formatCurrency(totalSpent)}</div>
          <div className="text-sm text-amber-600">Total Spent</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-6 border border-green-200"
        >
          <div className="text-3xl mb-2">✅</div>
          <div className="text-2xl font-bold text-green-900">{formatCurrency(totalRemaining)}</div>
          <div className="text-sm text-green-600">Remaining</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-6 border border-purple-200"
        >
          <div className="text-3xl mb-2">📈</div>
          <div className="text-2xl font-bold text-purple-900">
            {totalBudgeted > 0 ? (((totalSpent / totalBudgeted) * 100) || 0).toFixed(1) : 0}%
          </div>
          <div className="text-sm text-purple-600">Budget Used</div>
        </motion.div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl p-4 border border-surface-200">
        <div className="flex gap-2">
          {['all', 'draft', 'active', 'completed'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filterStatus === status
                  ? 'bg-amber-500 text-gray-900'
                  : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Budgets Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredBudgets.map((budget, index) => {
          const progress = calculateProgress(budget);
          const isOverBudget = budget.spent_amount > budget.total_amount;

          return (
            <motion.div
              key={budget.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-white rounded-xl p-6 border border-surface-200 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-3xl">{getTypeIcon(budget.budget_type)}</div>
                  <div>
                    <h3 className="font-bold text-surface-900">{budget.name}</h3>
                    <div className="text-xs text-surface-500">
                      {formatDate(budget.period_start)} - {formatDate(budget.period_end)}
                    </div>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(budget.status)}`}>
                  {budget.status}
                </span>
              </div>

              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-surface-500">Spent</span>
                  <span className={`font-medium ${isOverBudget ? 'text-red-600' : 'text-surface-900'}`}>
                    {formatCurrency(budget.spent_amount)} / {formatCurrency(budget.total_amount)}
                  </span>
                </div>
                <div className="h-3 bg-surface-100 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    className={`h-full rounded-full ${
                      isOverBudget
                        ? 'bg-red-500'
                        : progress > 80
                        ? 'bg-amber-500'
                        : 'bg-green-500'
                    }`}
                  />
                </div>
                <div className="flex justify-between text-xs mt-1">
                  <span className={isOverBudget ? 'text-red-600' : 'text-surface-500'}>
                    {(progress || 0).toFixed(1)}% used
                  </span>
                  <span className="text-surface-500">
                    {formatCurrency(budget.total_amount - budget.spent_amount)} remaining
                  </span>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => loadVariance(budget.id)}
                  className="flex-1 px-3 py-2 bg-surface-100 text-surface-700 rounded-lg text-sm hover:bg-surface-200"
                >
                  View Variance
                </button>
                <button className="px-3 py-2 bg-surface-100 text-surface-700 rounded-lg text-sm hover:bg-surface-200">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
              </div>
            </motion.div>
          );
        })}

        {filteredBudgets.length === 0 && (
          <div className="col-span-3 bg-white rounded-xl p-12 text-center border border-surface-200">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-xl font-bold text-surface-900 mb-2">No Budgets Found</h3>
            <p className="text-surface-500 mb-4">Create your first budget to start tracking expenses</p>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
            >
              Create Budget
            </button>
          </div>
        )}
      </div>

      {/* Create Budget Modal */}
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
                <h2 className="text-xl font-bold text-surface-900">Create New Budget</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Budget Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Q1 2025 Operating Budget"
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Budget Type</label>
                    <select
                      value={formData.budget_type}
                      onChange={(e) => setFormData({ ...formData, budget_type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="annual">Annual</option>
                      <option value="project">Project</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={formData.period_start}
                      onChange={(e) => setFormData({ ...formData, period_start: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">End Date</label>
                    <input
                      type="date"
                      value={formData.period_end}
                      onChange={(e) => setFormData({ ...formData, period_end: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-medium text-surface-700">Budget Line Items</label>
                    <button
                      type="button"
                      onClick={addLineItem}
                      className="text-sm text-amber-600 hover:text-amber-700"
                    >
                      + Add Line Item
                    </button>
                  </div>
                  <div className="space-y-2">
                    {formData.line_items.map((item, index) => (
                      <div key={index} className="flex gap-2">
                        <input
                          type="text"
                          value={item.category || ''}
                          onChange={(e) => updateLineItem(index, 'category', e.target.value)}
                          className="flex-1 px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                          placeholder="Category (e.g., Food Cost)"
                        />
                        <input
                          type="number"
                          value={item.amount || ''}
                          onChange={(e) => updateLineItem(index, 'amount', parseFloat(e.target.value) || 0)}
                          className="w-32 px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                          placeholder="Amount"
                        />
                        {formData.line_items.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeLineItem(index)}
                            className="px-3 py-2 text-red-500 hover:bg-red-50 rounded-lg"
                          >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="mt-2 text-right text-sm text-surface-600">
                    Total: {formatCurrency(formData.line_items.reduce((sum, item) => sum + (item.amount || 0), 0))}
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
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Create Budget
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Variance Modal */}
      <AnimatePresence>
        {showVarianceModal && variance && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">{variance.budget_name} - Variance Report</h2>
                <p className="text-sm text-surface-500">
                  {formatDate(variance.period.start)} - {formatDate(variance.period.end)}
                </p>
              </div>
              <div className="p-6">
                {/* Summary */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <div className="text-sm text-blue-600 mb-1">Budgeted</div>
                    <div className="text-xl font-bold text-blue-900">{formatCurrency(variance.total_budgeted)}</div>
                  </div>
                  <div className="bg-amber-50 rounded-lg p-4">
                    <div className="text-sm text-amber-600 mb-1">Actual</div>
                    <div className="text-xl font-bold text-amber-900">{formatCurrency(variance.total_actual)}</div>
                  </div>
                  <div className={`rounded-lg p-4 ${variance.total_variance >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                    <div className={`text-sm ${variance.total_variance >= 0 ? 'text-green-600' : 'text-red-600'} mb-1`}>
                      Variance
                    </div>
                    <div className={`text-xl font-bold ${variance.total_variance >= 0 ? 'text-green-900' : 'text-red-900'}`}>
                      {formatCurrency(variance.total_variance)}
                    </div>
                  </div>
                  <div className={`rounded-lg p-4 ${variance.variance_percentage >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                    <div className={`text-sm ${variance.variance_percentage >= 0 ? 'text-green-600' : 'text-red-600'} mb-1`}>
                      Variance %
                    </div>
                    <div className={`text-xl font-bold ${variance.variance_percentage >= 0 ? 'text-green-900' : 'text-red-900'}`}>
                      {variance.variance_percentage >= 0 ? '+' : ''}{(variance.variance_percentage || 0).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Line Items */}
                <table className="w-full">
                  <thead className="bg-surface-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Category</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Budgeted</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Actual</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Variance</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-surface-600 uppercase">%</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-100">
                    {variance.line_items.map((item, index) => (
                      <tr key={index} className="hover:bg-surface-50">
                        <td className="px-4 py-3 font-medium text-surface-900">{item.category}</td>
                        <td className="px-4 py-3 text-right text-surface-600">{formatCurrency(item.budgeted)}</td>
                        <td className="px-4 py-3 text-right text-surface-600">{formatCurrency(item.actual)}</td>
                        <td className={`px-4 py-3 text-right font-medium ${item.variance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(item.variance)}
                        </td>
                        <td className={`px-4 py-3 text-right ${item.percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {item.percentage >= 0 ? '+' : ''}{(item.percentage || 0).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-6 border-t border-surface-100">
                <button
                  onClick={() => setShowVarianceModal(false)}
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
