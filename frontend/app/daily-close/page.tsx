'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '@/lib/api';
import Link from 'next/link';

import { toast } from '@/lib/toast';
interface DailyReconciliation {
  id: number;
  business_date: string;
  status: 'open' | 'in_progress' | 'completed';
  expected_cash: number;
  actual_cash: number;
  cash_variance: number;
  total_sales: number;
  total_card_payments: number;
  total_cash_payments: number;
  total_other_payments: number;
  closed_at?: string;
  closed_by?: string;
}

interface CashDrawer {
  id: number;
  name: string;
  opening_balance: number;
  current_balance: number;
  status: 'open' | 'closed';
}

interface DenominationCount {
  denomination: string;
  count: number;
  value: number;
}

export default function DailyClosePage() {
  const [reconciliation, setReconciliation] = useState<DailyReconciliation | null>(null);
  const [drawers, setDrawers] = useState<CashDrawer[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [showCashCountModal, setShowCashCountModal] = useState(false);
  const [denominations, setDenominations] = useState<DenominationCount[]>([
    { denomination: '100', count: 0, value: 100 },
    { denomination: '50', count: 0, value: 50 },
    { denomination: '20', count: 0, value: 20 },
    { denomination: '10', count: 0, value: 10 },
    { denomination: '5', count: 0, value: 5 },
    { denomination: '2', count: 0, value: 2 },
    { denomination: '1', count: 0, value: 1 },
    { denomination: '0.50', count: 0, value: 0.5 },
    { denomination: '0.20', count: 0, value: 0.2 },
    { denomination: '0.10', count: 0, value: 0.1 },
    { denomination: '0.05', count: 0, value: 0.05 },
    { denomination: '0.02', count: 0, value: 0.02 },
    { denomination: '0.01', count: 0, value: 0.01 },
  ]);

  useEffect(() => {
    loadDailyData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate]);

  const loadDailyData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/daily-reconciliation/${selectedDate}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setReconciliation(data);
      } else {
        // No reconciliation for this date yet
        setReconciliation(null);
      }
    } catch (error) {
      console.error('Error loading daily data:', error);
      setReconciliation(null);
    } finally {
      setLoading(false);
    }
  };

  const startDailyClose = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/daily-close?business_date=${selectedDate}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        loadDailyData();
      }
    } catch (error) {
      console.error('Error starting daily close:', error);
    }
  };

  const recordCashCount = async () => {
    if (!reconciliation) return;
    try {
      const token = localStorage.getItem('access_token');
      const denominationCounts: Record<string, number> = {};
      denominations.forEach(d => {
        if (d.count > 0) {
          denominationCounts[d.denomination] = d.count;
        }
      });

      const response = await fetch(`${API_URL}/financial/daily-reconciliation/${reconciliation.id}/cash-count`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ denomination_counts: denominationCounts }),
      });
      if (response.ok) {
        setShowCashCountModal(false);
        loadDailyData();
      }
    } catch (error) {
      console.error('Error recording cash count:', error);
    }
  };

  const completeDailyClose = async () => {
    if (!reconciliation) return;
    if (!confirm('Are you sure you want to complete the daily close? This action cannot be undone.')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/daily-reconciliation/${reconciliation.id}/complete`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        toast.success('Daily close completed successfully!');
        loadDailyData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Error completing daily close');
      }
    } catch (error) {
      console.error('Error completing daily close:', error);
    }
  };

  const updateDenomination = (index: number, count: number) => {
    const newDenominations = [...denominations];
    newDenominations[index].count = count;
    setDenominations(newDenominations);
  };

  const totalCashCount = denominations.reduce((sum, d) => sum + (d.count * d.value), 0);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
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
            <h1 className="text-2xl font-display font-bold text-surface-900">Daily Close</h1>
            <p className="text-surface-500 mt-1">End of day reconciliation and cash count</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-4 py-2 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500"
          />
        </div>
      </div>

      {/* Date Header */}
      <div className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-xl p-6 border border-amber-200">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-3xl font-bold text-amber-900">{formatDate(selectedDate)}</div>
            {reconciliation && (
              <div className={`mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${
                reconciliation.status === 'completed'
                  ? 'bg-green-100 text-green-700'
                  : reconciliation.status === 'in_progress'
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-blue-100 text-blue-700'
              }`}>
                <span className={`w-2 h-2 rounded-full ${
                  reconciliation.status === 'completed' ? 'bg-green-500' :
                  reconciliation.status === 'in_progress' ? 'bg-yellow-500' : 'bg-blue-500'
                }`}></span>
                {reconciliation.status === 'completed' ? 'Day Closed' :
                 reconciliation.status === 'in_progress' ? 'In Progress' : 'Open'}
              </div>
            )}
          </div>
          {!reconciliation && (
            <button
              onClick={startDailyClose}
              className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600 font-medium"
            >
              Start Daily Close
            </button>
          )}
        </div>
      </div>

      {reconciliation ? (
        <>
          {/* Sales Summary */}
          <div className="grid grid-cols-4 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl p-6 border border-surface-200"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                  <span className="text-xl">💰</span>
                </div>
                <span className="text-sm text-surface-500">Total Sales</span>
              </div>
              <div className="text-2xl font-bold text-surface-900">{formatCurrency(reconciliation.total_sales)}</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-xl p-6 border border-surface-200"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <span className="text-xl">💳</span>
                </div>
                <span className="text-sm text-surface-500">Card Payments</span>
              </div>
              <div className="text-2xl font-bold text-blue-600">{formatCurrency(reconciliation.total_card_payments)}</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-xl p-6 border border-surface-200"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                  <span className="text-xl">💵</span>
                </div>
                <span className="text-sm text-surface-500">Cash Payments</span>
              </div>
              <div className="text-2xl font-bold text-green-600">{formatCurrency(reconciliation.total_cash_payments)}</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-white rounded-xl p-6 border border-surface-200"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                  <span className="text-xl">📱</span>
                </div>
                <span className="text-sm text-surface-500">Other Payments</span>
              </div>
              <div className="text-2xl font-bold text-purple-600">{formatCurrency(reconciliation.total_other_payments)}</div>
            </motion.div>
          </div>

          {/* Cash Reconciliation */}
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-surface-900 text-lg">Cash Drawer Reconciliation</h3>
                {reconciliation.status !== 'completed' && (
                  <button
                    onClick={() => setShowCashCountModal(true)}
                    className="px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                  >
                    Count Cash
                  </button>
                )}
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-3 gap-6">
                <div className="bg-surface-50 rounded-lg p-4">
                  <div className="text-sm text-surface-500 mb-1">Expected Cash</div>
                  <div className="text-2xl font-bold text-surface-900">{formatCurrency(reconciliation.expected_cash)}</div>
                  <div className="text-xs text-surface-500 mt-1">Based on cash transactions</div>
                </div>
                <div className="bg-surface-50 rounded-lg p-4">
                  <div className="text-sm text-surface-500 mb-1">Actual Cash Count</div>
                  <div className="text-2xl font-bold text-surface-900">{formatCurrency(reconciliation.actual_cash)}</div>
                  <div className="text-xs text-surface-500 mt-1">From drawer count</div>
                </div>
                <div className={`rounded-lg p-4 ${
                  reconciliation.cash_variance === 0 ? 'bg-green-50' :
                  Math.abs(reconciliation.cash_variance) < 5 ? 'bg-yellow-50' : 'bg-red-50'
                }`}>
                  <div className="text-sm text-surface-500 mb-1">Variance</div>
                  <div className={`text-2xl font-bold ${
                    reconciliation.cash_variance === 0 ? 'text-green-600' :
                    reconciliation.cash_variance > 0 ? 'text-blue-600' : 'text-red-600'
                  }`}>
                    {reconciliation.cash_variance >= 0 ? '+' : ''}{formatCurrency(reconciliation.cash_variance)}
                  </div>
                  <div className="text-xs text-surface-500 mt-1">
                    {reconciliation.cash_variance === 0 ? 'Balanced!' :
                     reconciliation.cash_variance > 0 ? 'Over' : 'Short'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          {reconciliation.status !== 'completed' && (
            <div className="bg-white rounded-xl p-6 border border-surface-200">
              <h3 className="font-semibold text-surface-900 mb-4">Close Day Checklist</h3>
              <div className="space-y-3 mb-6">
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-5 h-5 rounded text-amber-500" />
                  <span className="text-surface-700">All orders have been completed or voided</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-5 h-5 rounded text-amber-500" />
                  <span className="text-surface-700">Cash drawer has been counted</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-5 h-5 rounded text-amber-500" />
                  <span className="text-surface-700">Card payments have been batched</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-5 h-5 rounded text-amber-500" />
                  <span className="text-surface-700">Tips have been distributed</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-5 h-5 rounded text-amber-500" />
                  <span className="text-surface-700">Kitchen inventory has been counted</span>
                </label>
              </div>
              <button
                onClick={completeDailyClose}
                className="w-full px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 font-medium"
              >
                Complete Daily Close
              </button>
            </div>
          )}

          {/* Completed Info */}
          {reconciliation.status === 'completed' && reconciliation.closed_at && (
            <div className="bg-green-50 rounded-xl p-6 border border-green-200">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <div className="font-semibold text-green-900">Day Closed Successfully</div>
                  <div className="text-sm text-green-700">
                    Closed on {new Date(reconciliation.closed_at).toLocaleString()} by {reconciliation.closed_by}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="bg-white rounded-xl p-12 text-center border border-surface-200">
          <div className="text-6xl mb-4">📅</div>
          <h3 className="text-xl font-bold text-surface-900 mb-2">No Daily Close Started</h3>
          <p className="text-surface-500 mb-6">Start the daily close process to reconcile cash and finalize the day</p>
          <button
            onClick={startDailyClose}
            className="px-6 py-3 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
          >
            Start Daily Close
          </button>
        </div>
      )}

      {/* Cash Count Modal */}
      <AnimatePresence>
        {showCashCountModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-surface-100">
                <h2 className="text-xl font-bold text-surface-900">Cash Drawer Count</h2>
                <p className="text-sm text-surface-500 mt-1">Enter the count for each denomination</p>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium text-surface-900 mb-3">Bills</h4>
                    {denominations.filter(d => parseFloat(d.denomination) >= 5).map((denom, index) => {
                      const actualIndex = denominations.findIndex(d2 => d2.denomination === denom.denomination);
                      return (
                        <div key={denom.denomination} className="flex items-center gap-3 mb-2">
                          <span className="w-16 text-surface-600">{denom.denomination} лв</span>
                          <input
                            type="number"
                            min="0"
                            value={denom.count || ''}
                            onChange={(e) => updateDenomination(actualIndex, parseInt(e.target.value) || 0)}
                            className="w-20 px-3 py-1 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500 text-center"
                          />
                          <span className="text-surface-500">= {formatCurrency(denom.count * denom.value)}</span>
                        </div>
                      );
                    })}
                  </div>
                  <div>
                    <h4 className="font-medium text-surface-900 mb-3">Coins</h4>
                    {denominations.filter(d => parseFloat(d.denomination) < 5).map((denom, index) => {
                      const actualIndex = denominations.findIndex(d2 => d2.denomination === denom.denomination);
                      return (
                        <div key={denom.denomination} className="flex items-center gap-3 mb-2">
                          <span className="w-16 text-surface-600">{denom.denomination} лв</span>
                          <input
                            type="number"
                            min="0"
                            value={denom.count || ''}
                            onChange={(e) => updateDenomination(actualIndex, parseInt(e.target.value) || 0)}
                            className="w-20 px-3 py-1 border border-surface-200 rounded-lg focus:ring-2 focus:ring-amber-500 text-center"
                          />
                          <span className="text-surface-500">= {formatCurrency(denom.count * denom.value)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="mt-6 p-4 bg-amber-50 rounded-lg border border-amber-200">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-amber-900">Total Cash Count</span>
                    <span className="text-2xl font-bold text-amber-900">{formatCurrency(totalCashCount)}</span>
                  </div>
                </div>
              </div>
              <div className="p-6 border-t border-surface-100 flex gap-3">
                <button
                  onClick={() => setShowCashCountModal(false)}
                  className="flex-1 px-4 py-2 border border-surface-200 text-surface-700 rounded-lg hover:bg-surface-50"
                >
                  Cancel
                </button>
                <button
                  onClick={recordCashCount}
                  className="flex-1 px-4 py-2 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-600"
                >
                  Save Count
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
