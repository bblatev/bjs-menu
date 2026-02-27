'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { api } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Account {
  id: number;
  account_code: string;
  account_name: string;
  account_type: 'asset' | 'liability' | 'equity' | 'revenue' | 'expense';
  parent_id: number | null;
  description: string | null;
  current_balance: number;
  is_active: boolean;
  children?: Account[];
}

interface AccountForm {
  account_code: string;
  account_name: string;
  account_type: 'asset' | 'liability' | 'equity' | 'revenue' | 'expense';
  parent_id: number | null;
  description: string;
}

export default function ChartOfAccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState<AccountForm>({
    account_code: '',
    account_name: '',
    account_type: 'asset',
    parent_id: null,
    description: '',
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await api.get<Account[]>('/financial/chart-of-accounts');
      setAccounts(data);
    } catch (error) {
      console.error('Error loading accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/financial/chart-of-accounts', formData);
      loadAccounts();
      closeModal();
    } catch (error: any) {
      if (error?.data?.detail) {
        toast.error(error.data.detail);
      } else {
        console.error('Error creating account:', error);
      }
    }
  };

  const openCreateModal = () => {
    setEditingAccount(null);
    setFormData({
      account_code: '',
      account_name: '',
      account_type: 'asset',
      parent_id: null,
      description: '',
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingAccount(null);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(amount);
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      asset: 'bg-blue-100 text-blue-800',
      liability: 'bg-red-100 text-red-800',
      equity: 'bg-purple-100 text-purple-800',
      revenue: 'bg-green-100 text-green-800',
      expense: 'bg-orange-100 text-orange-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      asset: '💰',
      liability: '📋',
      equity: '🏛️',
      revenue: '📈',
      expense: '📉',
    };
    return icons[type] || '📊';
  };

  // Filter accounts
  const filteredAccounts = accounts.filter(account => {
    if (filterType !== 'all' && account.account_type !== filterType) return false;
    if (searchTerm && !account.account_name.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !account.account_code.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  // Calculate totals by type
  const totals = accounts.reduce((acc, account) => {
    if (!acc[account.account_type]) {
      acc[account.account_type] = 0;
    }
    acc[account.account_type] += account.current_balance;
    return acc;
  }, {} as Record<string, number>);

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
            <h1 className="text-2xl font-display font-bold text-surface-900">Chart of Accounts</h1>
            <p className="text-surface-500 mt-1">Manage your general ledger accounts</p>
          </div>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Account
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        {['asset', 'liability', 'equity', 'revenue', 'expense'].map((type) => (
          <motion.div
            key={type}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-4 rounded-xl border ${
              filterType === type ? 'ring-2 ring-amber-500' : ''
            } bg-white cursor-pointer hover:shadow-md transition-all`}
            onClick={() => setFilterType(filterType === type ? 'all' : type)}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{getTypeIcon(type)}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${getTypeColor(type)}`}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </span>
            </div>
            <div className="text-xl font-bold text-surface-900">
              {formatCurrency(totals[type] || 0)}
            </div>
            <div className="text-xs text-surface-500">
              {accounts.filter(a => a.account_type === type).length} accounts
            </div>
          </motion.div>
        ))}
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-xl p-4 border border-surface-200">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <svg className="w-5 h-5 text-surface-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search accounts..."
              className="w-full pl-10 pr-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
          >
            <option value="all">All Types</option>
            <option value="asset">Assets</option>
            <option value="liability">Liabilities</option>
            <option value="equity">Equity</option>
            <option value="revenue">Revenue</option>
            <option value="expense">Expenses</option>
          </select>
        </div>
      </div>

      {/* Accounts Table */}
      <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase tracking-wider">Code</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase tracking-wider">Account Name</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-surface-600 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase tracking-wider">Balance</th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-surface-600 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-surface-600 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {filteredAccounts.map((account, index) => (
              <motion.tr
                key={account.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className="hover:bg-surface-50"
              >
                <td className="px-6 py-4">
                  <span className="font-mono text-sm text-surface-600">{account.account_code}</span>
                </td>
                <td className="px-6 py-4">
                  <div className="font-medium text-surface-900">{account.account_name}</div>
                  {account.description && (
                    <div className="text-xs text-surface-500">{account.description}</div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(account.account_type)}`}>
                    {account.account_type.charAt(0).toUpperCase() + account.account_type.slice(1)}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`font-bold ${
                    account.current_balance >= 0 ? 'text-surface-900' : 'text-red-600'
                  }`}>
                    {formatCurrency(account.current_balance)}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    account.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {account.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="text-surface-400 hover:text-surface-600 p-1">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>

        {filteredAccounts.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📒</div>
            <h3 className="text-xl font-bold text-surface-900 mb-2">No Accounts Found</h3>
            <p className="text-surface-500">Try adjusting your search or filters</p>
          </div>
        )}
      </div>

      {/* Create Account Modal */}
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
                <h2 className="text-xl font-bold text-surface-900">
                  {editingAccount ? 'Edit Account' : 'Add New Account'}
                </h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Account Code
                    <input
                      type="text"
                      value={formData.account_code}
                      onChange={(e) => setFormData({ ...formData, account_code: e.target.value })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                      placeholder="e.g., 1000"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-surface-700 mb-1">Account Type
                    <select
                      value={formData.account_type}
                      onChange={(e) => setFormData({ ...formData, account_type: e.target.value as any })}
                      className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    >
                      <option value="asset">Asset</option>
                      <option value="liability">Liability</option>
                      <option value="equity">Equity</option>
                      <option value="revenue">Revenue</option>
                      <option value="expense">Expense</option>
                    </select>
                    </label>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Account Name
                  <input
                    type="text"
                    value={formData.account_name}
                    onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="e.g., Cash on Hand"
                  />
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Parent Account (optional)
                  <select
                    value={formData.parent_id || ''}
                    onChange={(e) => setFormData({ ...formData, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                  >
                    <option value="">No parent (top-level)</option>
                    {accounts.filter(a => a.account_type === formData.account_type && !a.parent_id).map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.account_code} - {account.account_name}
                      </option>
                    ))}
                  </select>
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Description
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
                    rows={2}
                    placeholder="Optional description..."
                  />
                  </label>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={closeModal}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  {editingAccount ? 'Update' : 'Create'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
