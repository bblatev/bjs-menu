'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

import { toast } from '@/lib/toast';
interface BankAccount {
  id: number;
  account_name: string;
  bank_name: string;
  account_number: string;
  current_balance: number;
  currency: string;
}

interface BankTransaction {
  id: number;
  date: string;
  amount: number;
  description: string;
  reference: string;
  type: string;
  is_matched: boolean;
  matched_record?: {
    type: string;
    id: number;
    description: string;
  };
}

interface Reconciliation {
  id: number;
  bank_account_id: number;
  statement_date: string;
  statement_balance: number;
  reconciled_balance: number | null;
  difference: number | null;
  status: 'in_progress' | 'completed';
}

export default function BankReconciliationPage() {
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<BankAccount | null>(null);
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [reconciliation, setReconciliation] = useState<Reconciliation | null>(null);
  const [loading, setLoading] = useState(true);
  const [showNewReconciliation, setShowNewReconciliation] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [formData, setFormData] = useState({
    statement_date: new Date().toISOString().split('T')[0],
    statement_balance: '',
  });

  useEffect(() => {
    loadBankAccounts();
  }, []);

  const loadBankAccounts = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/bank-accounts`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setBankAccounts(data);
        if (data.length > 0) {
          setSelectedAccount(data[0]);
        }
      }
    } catch (error) {
      console.error('Error loading bank accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const startReconciliation = async () => {
    if (!selectedAccount || !formData.statement_balance) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/bank-reconciliation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          bank_account_id: selectedAccount.id,
          statement_date: formData.statement_date,
          statement_balance: parseFloat(formData.statement_balance),
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setReconciliation(data);
        setShowNewReconciliation(false);
      }
    } catch (error) {
      console.error('Error starting reconciliation:', error);
    }
  };

  const matchTransaction = async (bankTransactionId: number, systemRecordType: string, systemRecordId: number) => {
    if (!reconciliation) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/bank-reconciliation/${reconciliation.id}/match`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          bank_transaction_id: bankTransactionId,
          system_record_type: systemRecordType,
          system_record_id: systemRecordId,
        }),
      });
      if (response.ok) {
        loadReconciliation(reconciliation.id);
      }
    } catch (error) {
      console.error('Error matching transaction:', error);
    }
  };

  const completeReconciliation = async () => {
    if (!reconciliation) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/bank-reconciliation/${reconciliation.id}/complete`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        toast.success('Reconciliation completed successfully!');
        setReconciliation(null);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error completing reconciliation');
      }
    } catch (error) {
      console.error('Error completing reconciliation:', error);
    }
  };

  const loadReconciliation = async (id: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/bank-reconciliation/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setReconciliation(data);
      }
    } catch (error) {
      console.error('Error loading reconciliation:', error);
    }
  };

  const formatCurrency = (amount: number, currency: string = 'BGN') => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: currency,
    }).format(amount);
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
          <Link href="/financial-management" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Bank Reconciliation</h1>
            <p className="text-surface-500 mt-1">Match bank statements with system transactions</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewReconciliation(true)}
          className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Start Reconciliation
        </button>
      </div>

      {/* Bank Account Selector */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {bankAccounts.map((account) => (
          <motion.div
            key={account.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
              selectedAccount?.id === account.id
                ? 'border-amber-500 bg-amber-50'
                : 'border-surface-200 bg-white hover:border-amber-300'
            }`}
            onClick={() => setSelectedAccount(account)}
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-surface-900 truncate">{account.account_name}</div>
                <div className="text-xs text-surface-500">{account.bank_name}</div>
              </div>
            </div>
            <div className="mt-3">
              <div className="text-lg font-bold text-surface-900">{formatCurrency(account.current_balance, account.currency)}</div>
              <div className="text-xs text-surface-500">{account.account_number}</div>
            </div>
          </motion.div>
        ))}

        {bankAccounts.length === 0 && (
          <div className="col-span-4 bg-white rounded-xl p-12 text-center border border-surface-200">
            <div className="text-6xl mb-4">🏦</div>
            <h3 className="text-xl font-bold text-surface-900 mb-2">No Bank Accounts</h3>
            <p className="text-surface-500 mb-4">Add a bank account to start reconciliation</p>
            <button className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600">
              Add Bank Account
            </button>
          </div>
        )}
      </div>

      {/* Active Reconciliation */}
      {reconciliation && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl border border-surface-200 overflow-hidden"
        >
          <div className="p-4 bg-gradient-to-r from-blue-50 to-blue-100 border-b border-surface-200">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-surface-900">Reconciliation in Progress</h3>
                <p className="text-sm text-surface-600">Statement Date: {reconciliation.statement_date}</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-sm text-surface-500">Statement Balance</div>
                  <div className="text-lg font-bold text-surface-900">{formatCurrency(reconciliation.statement_balance)}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-surface-500">Difference</div>
                  <div className={`text-lg font-bold ${
                    reconciliation.difference === 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatCurrency(reconciliation.difference || 0)}
                  </div>
                </div>
                <button
                  onClick={completeReconciliation}
                  disabled={reconciliation.difference !== 0}
                  className={`px-4 py-2 rounded-lg ${
                    reconciliation.difference === 0
                      ? 'bg-green-500 text-white hover:bg-green-600'
                      : 'bg-surface-200 text-surface-400 cursor-not-allowed'
                  }`}
                >
                  Complete
                </button>
              </div>
            </div>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-2 gap-6">
              {/* Bank Transactions */}
              <div>
                <h4 className="font-semibold text-surface-900 mb-4 flex items-center gap-2">
                  <span>Bank Transactions</span>
                  <button
                    onClick={() => setShowImportModal(true)}
                    className="text-xs px-2 py-1 bg-blue-100 text-blue-600 rounded hover:bg-blue-200"
                  >
                    Import
                  </button>
                </h4>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {transactions.length === 0 && (
                    <div className="text-center py-8 text-surface-500">
                      <p>No unmatched transactions</p>
                      <p className="text-sm">Import bank statement to begin</p>
                    </div>
                  )}
                  {transactions.filter(t => !t.is_matched).map((transaction) => (
                    <div
                      key={transaction.id}
                      className="p-3 bg-surface-50 rounded-lg hover:bg-surface-100 cursor-pointer"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-surface-900">{transaction.description}</div>
                          <div className="text-xs text-surface-500">{transaction.date} - {transaction.reference}</div>
                        </div>
                        <div className={`font-bold ${transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(transaction.amount)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Matched Transactions */}
              <div>
                <h4 className="font-semibold text-surface-900 mb-4">Matched Transactions</h4>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {transactions.filter(t => t.is_matched).length === 0 && (
                    <div className="text-center py-8 text-surface-500">
                      <p>No matched transactions yet</p>
                    </div>
                  )}
                  {transactions.filter(t => t.is_matched).map((transaction) => (
                    <div
                      key={transaction.id}
                      className="p-3 bg-green-50 rounded-lg border border-green-200"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-surface-900">{transaction.description}</div>
                          <div className="text-xs text-green-600">
                            Matched: {transaction.matched_record?.type} #{transaction.matched_record?.id}
                          </div>
                        </div>
                        <div className="text-green-600">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Quick Stats */}
      {!reconciliation && selectedAccount && (
        <div className="grid grid-cols-4 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl p-6 border border-surface-200"
          >
            <div className="text-3xl mb-2">📊</div>
            <div className="text-2xl font-bold text-surface-900">12</div>
            <div className="text-sm text-surface-500">Pending Transactions</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-xl p-6 border border-surface-200"
          >
            <div className="text-3xl mb-2">✅</div>
            <div className="text-2xl font-bold text-green-600">156</div>
            <div className="text-sm text-surface-500">Matched This Month</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-xl p-6 border border-surface-200"
          >
            <div className="text-3xl mb-2">📅</div>
            <div className="text-2xl font-bold text-surface-900">Dec 28</div>
            <div className="text-sm text-surface-500">Last Reconciled</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-xl p-6 border border-surface-200"
          >
            <div className="text-3xl mb-2">💰</div>
            <div className="text-2xl font-bold text-amber-600">{formatCurrency(0)}</div>
            <div className="text-sm text-surface-500">Variance</div>
          </motion.div>
        </div>
      )}

      {/* Start Reconciliation Modal */}
      <AnimatePresence>
        {showNewReconciliation && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-md w-full"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Start New Reconciliation</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Bank Account</label>
                  <select
                    value={selectedAccount?.id || ''}
                    onChange={(e) => setSelectedAccount(bankAccounts.find(a => a.id === parseInt(e.target.value)) || null)}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg"
                  >
                    {bankAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.account_name} - {account.bank_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Statement Date</label>
                  <input
                    type="date"
                    value={formData.statement_date}
                    onChange={(e) => setFormData({ ...formData, statement_date: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Statement Ending Balance</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.statement_balance}
                    onChange={(e) => setFormData({ ...formData, statement_balance: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-200 rounded-lg"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowNewReconciliation(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={startReconciliation}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Start
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
