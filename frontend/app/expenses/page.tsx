'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

interface Expense {
  id: number;
  expense_number: string;
  category_id: number;
  category_name: string;
  vendor_name: string;
  amount: number;
  expense_date: string;
  description: string;
  status: 'pending' | 'approved' | 'rejected' | 'paid';
  receipt_url?: string;
  payment_method?: string;
  created_by: string;
}

interface ExpenseCategory {
  id: number;
  name: string;
  budget_amount: number;
  spent_amount: number;
}

export default function ExpensesPage() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });
  const [formData, setFormData] = useState({
    category_id: '',
    vendor_name: '',
    amount: '',
    expense_date: new Date().toISOString().split('T')[0],
    description: '',
    payment_method: 'cash',
  });

  useEffect(() => {
    loadExpenses();
    loadCategories();
  }, []);

  const loadExpenses = async () => {
    try {
      const token = localStorage.getItem('access_token');
      // Mock data for now - would connect to real API
      setExpenses([
        {
          id: 1,
          expense_number: 'EXP-001',
          category_id: 1,
          category_name: 'Food Supplies',
          vendor_name: 'Metro Cash & Carry',
          amount: 1250.50,
          expense_date: '2024-12-28',
          description: 'Weekly food inventory',
          status: 'approved',
          payment_method: 'Bank Transfer',
          created_by: 'John Smith',
        },
        {
          id: 2,
          expense_number: 'EXP-002',
          category_id: 2,
          category_name: 'Utilities',
          vendor_name: 'EVN Bulgaria',
          amount: 450.00,
          expense_date: '2024-12-27',
          description: 'Electricity bill December',
          status: 'paid',
          payment_method: 'Bank Transfer',
          created_by: 'Maria Petrova',
        },
        {
          id: 3,
          expense_number: 'EXP-003',
          category_id: 3,
          category_name: 'Equipment',
          vendor_name: 'Restaurant Supply Co',
          amount: 890.00,
          expense_date: '2024-12-26',
          description: 'New blender replacement',
          status: 'pending',
          created_by: 'Peter Ivanov',
        },
      ]);
    } catch (error) {
      console.error('Error loading expenses:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    // Mock categories
    setCategories([
      { id: 1, name: 'Food Supplies', budget_amount: 5000, spent_amount: 3200 },
      { id: 2, name: 'Utilities', budget_amount: 1500, spent_amount: 850 },
      { id: 3, name: 'Equipment', budget_amount: 2000, spent_amount: 890 },
      { id: 4, name: 'Marketing', budget_amount: 1000, spent_amount: 450 },
      { id: 5, name: 'Maintenance', budget_amount: 800, spent_amount: 200 },
    ]);
  };

  const handleCreate = async () => {
    // Would submit to API
    setShowModal(false);
    loadExpenses();
  };

  const handleApprove = async (id: number) => {
    // Would call API to approve
    setExpenses(expenses.map(e => e.id === id ? { ...e, status: 'approved' as const } : e));
  };

  const handleReject = async (id: number) => {
    // Would call API to reject
    setExpenses(expenses.map(e => e.id === id ? { ...e, status: 'rejected' as const } : e));
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
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-blue-100 text-blue-700',
      rejected: 'bg-red-100 text-red-700',
      paid: 'bg-green-100 text-green-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  const filteredExpenses = expenses.filter(e => {
    if (filterStatus !== 'all' && e.status !== filterStatus) return false;
    if (filterCategory !== 'all' && e.category_id !== parseInt(filterCategory)) return false;
    return true;
  });

  // Calculate totals
  const totalExpenses = expenses.reduce((sum, e) => sum + e.amount, 0);
  const pendingExpenses = expenses.filter(e => e.status === 'pending').reduce((sum, e) => sum + e.amount, 0);
  const approvedExpenses = expenses.filter(e => e.status === 'approved' || e.status === 'paid').reduce((sum, e) => sum + e.amount, 0);

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
            <h1 className="text-2xl font-display font-bold text-surface-900">Expense Tracking</h1>
            <p className="text-surface-500 mt-1">Track and manage all business expenses</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Expense
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <span className="text-xl">💸</span>
            </div>
            <span className="text-sm text-surface-500">Total Expenses</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{formatCurrency(totalExpenses)}</div>
          <div className="text-xs text-surface-500 mt-1">This month</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-100 flex items-center justify-center">
              <span className="text-xl">⏳</span>
            </div>
            <span className="text-sm text-surface-500">Pending Approval</span>
          </div>
          <div className="text-2xl font-bold text-yellow-600">{formatCurrency(pendingExpenses)}</div>
          <div className="text-xs text-surface-500 mt-1">{expenses.filter(e => e.status === 'pending').length} expenses</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <span className="text-xl">✅</span>
            </div>
            <span className="text-sm text-surface-500">Approved</span>
          </div>
          <div className="text-2xl font-bold text-green-600">{formatCurrency(approvedExpenses)}</div>
          <div className="text-xs text-surface-500 mt-1">{expenses.filter(e => e.status === 'approved' || e.status === 'paid').length} expenses</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl p-6 border border-surface-200"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
              <span className="text-xl">📊</span>
            </div>
            <span className="text-sm text-surface-500">Categories</span>
          </div>
          <div className="text-2xl font-bold text-surface-900">{categories.length}</div>
          <div className="text-xs text-surface-500 mt-1">Active categories</div>
        </motion.div>
      </div>

      {/* Category Budgets */}
      <div className="bg-white rounded-xl p-6 border border-surface-200">
        <h3 className="font-semibold text-surface-900 mb-4">Category Spending</h3>
        <div className="grid grid-cols-5 gap-4">
          {categories.map((cat) => {
            const percentage = (cat.spent_amount / cat.budget_amount) * 100;
            const isOverBudget = percentage > 100;
            return (
              <div key={cat.id} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-surface-900">{cat.name}</span>
                  <span className={`${isOverBudget ? 'text-red-600' : 'text-surface-500'}`}>
                    {percentage.toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      isOverBudget ? 'bg-red-500' : percentage > 80 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(percentage, 100)}%` }}
                  />
                </div>
                <div className="text-xs text-surface-500">
                  {formatCurrency(cat.spent_amount)} / {formatCurrency(cat.budget_amount)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl p-4 border border-surface-200">
        <div className="flex gap-4 flex-wrap">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="paid">Paid</option>
          </select>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
            className="px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
          />
          <span className="self-center text-surface-400">to</span>
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
            className="px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
          />
        </div>
      </div>

      {/* Expenses Table */}
      <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Expense #</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Vendor</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase">Date</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Amount</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {filteredExpenses.map((expense, index) => (
              <motion.tr
                key={expense.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className="hover:bg-surface-50"
              >
                <td className="px-6 py-4">
                  <span className="font-mono text-sm text-surface-600">{expense.expense_number}</span>
                </td>
                <td className="px-6 py-4">
                  <span className="font-medium text-surface-900">{expense.category_name}</span>
                </td>
                <td className="px-6 py-4">
                  <div>
                    <div className="font-medium text-surface-900">{expense.vendor_name}</div>
                    <div className="text-xs text-surface-500">{expense.description}</div>
                  </div>
                </td>
                <td className="px-6 py-4 text-surface-600">{formatDate(expense.expense_date)}</td>
                <td className="px-6 py-4 text-right font-bold text-surface-900">{formatCurrency(expense.amount)}</td>
                <td className="px-6 py-4 text-center">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(expense.status)}`}>
                    {expense.status.charAt(0).toUpperCase() + expense.status.slice(1)}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex justify-end gap-2">
                    {expense.status === 'pending' && (
                      <>
                        <button
                          onClick={() => handleApprove(expense.id)}
                          className="p-1 text-green-600 hover:bg-green-50 rounded"
                          title="Approve"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleReject(expense.id)}
                          className="p-1 text-red-600 hover:bg-red-50 rounded"
                          title="Reject"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </>
                    )}
                    <button className="p-1 text-surface-400 hover:text-surface-600 rounded">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>

        {filteredExpenses.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🧾</div>
            <h3 className="text-xl font-bold text-surface-900 mb-2">No Expenses Found</h3>
            <p className="text-surface-500">Try adjusting your filters or add a new expense</p>
          </div>
        )}
      </div>

      {/* Add Expense Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-lg w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Add New Expense</h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Category</label>
                    <select
                      value={formData.category_id}
                      onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="">Select category</option>
                      {categories.map((cat) => (
                        <option key={cat.id} value={cat.id}>{cat.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Date</label>
                    <input
                      type="date"
                      value={formData.expense_date}
                      onChange={(e) => setFormData({ ...formData, expense_date: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Vendor Name</label>
                  <input
                    type="text"
                    value={formData.vendor_name}
                    onChange={(e) => setFormData({ ...formData, vendor_name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Metro Cash & Carry"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Amount</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.amount}
                      onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Payment Method</label>
                    <select
                      value={formData.payment_method}
                      onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="cash">Cash</option>
                      <option value="card">Card</option>
                      <option value="bank_transfer">Bank Transfer</option>
                      <option value="check">Check</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    rows={2}
                    placeholder="Brief description of the expense..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Receipt (optional)</label>
                  <div className="border-2 border-dashed border-surface-200 rounded-lg p-4 text-center">
                    <input type="file" className="hidden" id="receipt" accept="image/*,.pdf" />
                    <label htmlFor="receipt" className="cursor-pointer">
                      <div className="text-3xl mb-2">📎</div>
                      <div className="text-sm text-surface-500">Click to upload receipt</div>
                    </label>
                  </div>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Add Expense
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
