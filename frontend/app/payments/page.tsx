'use client';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import { api } from '@/lib/api';
interface PaymentTransaction {
  id: string;
  orderId: string;
  amount: number;
  currency: string;
  status: 'pending' | 'processing' | 'succeeded' | 'failed' | 'refunded';
  method: string;
  cardBrand?: string;
  cardLast4?: string;
  customerEmail?: string;
  createdAt: string;
  receiptUrl?: string;
}
interface WalletConfig {
  applePay: { enabled: boolean; merchantId?: string };
  googlePay: { enabled: boolean; merchantName: string };
  link: { enabled: boolean };
  supportedNetworks: string[];
}
interface PaymentStats {
  totalPayments: number;
  succeeded: number;
  failed: number;
  successRate: number;
  totalAmount: number;
  byWalletType: {
    apple_pay: number;
    google_pay: number;
    link: number;
  };
}
export default function PaymentsPage() {
  const [activeTab, setActiveTab] = useState<'transactions' | 'terminal' | 'wallets' | 'settings'>('transactions');
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [walletConfig, setWalletConfig] = useState<WalletConfig | null>(null);
  const [stats, setStats] = useState<PaymentStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTransaction, setSelectedTransaction] = useState<PaymentTransaction | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [terminalStatus, setTerminalStatus] = useState<'disconnected' | 'connected' | 'processing'>('disconnected');
  useEffect(() => {
    loadData();
  }, []);
  const loadData = async () => {
    setIsLoading(true);
    try {
      const [txRes, _statusRes, walletRes, walletStatsRes] = await Promise.allSettled([
  api.get('/payments/transactions'),
  api.get('/payments/status'),
  api.get('/mobile-wallet/config'),
  api.get('/mobile-wallet/stats')
]);
      // Load transactions from API or use defaults
      if (txRes.status === 'fulfilled') {
        const data: any = txRes.value;
        if (Array.isArray(data) && data.length > 0) {
          setTransactions(data.map((t: any) => ({
            id: t.payment_intent_id || t.id,
            orderId: t.order_id || t.orderId || '-',
            amount: t.amount,
            currency: t.currency || 'usd',
            status: t.status,
            method: t.payment_method || t.method || 'card',
            cardBrand: t.card_brand || t.cardBrand,
            cardLast4: t.card_last4 || t.cardLast4,
            customerEmail: t.customer_email || t.customerEmail,
            createdAt: t.created_at || t.createdAt || new Date().toISOString(),
            receiptUrl: t.receipt_url || t.receiptUrl,
          })));
        } else {
          setTransactions([]);
        }
      } else {
        setTransactions([]);
      }
      // Wallet config
      if (walletRes.status === 'fulfilled') {
        const data_walletConfig: any = walletRes.value;
        setWalletConfig({
          applePay: { enabled: data_walletConfig.apple_pay_enabled ?? true, merchantId: data_walletConfig.apple_pay_merchant_id || 'merchant.com.bjs.pos' },
          googlePay: { enabled: data_walletConfig.google_pay_enabled ?? true, merchantName: data_walletConfig.merchant_name || "BJ's Bar" },
          link: { enabled: data_walletConfig.link_enabled ?? false },
          supportedNetworks: data_walletConfig.supported_networks || ['visa', 'mastercard'],
        });
      } else {
        setWalletConfig({
          applePay: { enabled: true, merchantId: 'merchant.com.bjs.pos' },
          googlePay: { enabled: true, merchantName: "BJ's Bar" },
          link: { enabled: false },
          supportedNetworks: ['visa', 'mastercard', 'amex', 'discover'],
        });
      }
      // Stats from wallet
      if (walletStatsRes.status === 'fulfilled') {
        const data_stats: any = walletStatsRes.value;
        setStats({
          totalPayments: data_stats.total_payments || 0,
          succeeded: data_stats.completed || 0,
          failed: data_stats.failed || 0,
          successRate: data_stats.success_rate || 0,
          totalAmount: (data_stats.total_volume || 0) / 100,
          byWalletType: {
            apple_pay: data_stats.apple_pay_count || 0,
            google_pay: data_stats.google_pay_count || 0,
            link: data_stats.link_count || 0,
          },
        });
      } else {
        setStats({
          totalPayments: 0, succeeded: 0, failed: 0, successRate: 0, totalAmount: 0,
          byWalletType: { apple_pay: 0, google_pay: 0, link: 0 },
        });
      }
    } catch (err) {
      console.error('Error loading payment data:', err);
      setTransactions([]);
      setStats({
        totalPayments: 0, succeeded: 0, failed: 0, successRate: 0, totalAmount: 0,
        byWalletType: { apple_pay: 0, google_pay: 0, link: 0 },
      });
    } finally {
      setIsLoading(false);
    }
  };
  const formatAmount = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  };
  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      succeeded: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      refunded: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };
  const getMethodIcon = (method: string) => {
    switch (method) {
      case 'apple_pay':
        return (
          <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
          </svg>
        );
      case 'google_pay':
        return (
          <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"/>
          </svg>
        );
      default:
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
          </svg>
        );
    }
  };
  const processRefund = async (transactionId: string) => {
    setIsProcessing(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      setTransactions(prev =>
        prev.map(t =>
          t.id === transactionId ? { ...t, status: 'refunded' as const } : t
        )
      );
    } finally {
      setIsProcessing(false);
      setSelectedTransaction(null);
    }
  };
  const connectTerminal = async () => {
    setTerminalStatus('processing');
    try {
      await new Promise(resolve => setTimeout(resolve, 2000));
      setTerminalStatus('connected');
    } catch {
      setTerminalStatus('disconnected');
    }
  };
  const toggleWalletSetting = (wallet: 'applePay' | 'googlePay' | 'link') => {
    if (!walletConfig) return;
    setWalletConfig(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        [wallet]: { ...prev[wallet], enabled: !prev[wallet].enabled },
      };
    });
  };
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500"></div>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Payment Processing</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage transactions, terminals, and payment methods</p>
        </div>
      </div>
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-surface-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-surface-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">Total Revenue</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">${(stats.totalAmount || 0).toFixed(2)}</p>
          </div>
          <div className="bg-white dark:bg-surface-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-surface-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">Success Rate</p>
            <p className="text-2xl font-bold text-green-600">{stats.successRate}%</p>
          </div>
          <div className="bg-white dark:bg-surface-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-surface-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">Total Transactions</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.totalPayments}</p>
          </div>
          <div className="bg-white dark:bg-surface-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-surface-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">Mobile Wallets</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.byWalletType.apple_pay + stats.byWalletType.google_pay}
            </p>
          </div>
        </div>
      )}
      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-surface-700">
        <nav className="flex space-x-8">
          {(['transactions', 'terminal', 'wallets', 'settings'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>
      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'transactions' && (
          <motion.div
            key="transactions"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-white dark:bg-surface-800 rounded-xl shadow-sm border border-gray-200 dark:border-surface-700 overflow-hidden"
          >
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-surface-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Transaction</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Method</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-surface-700">
                  {transactions.map(transaction => (
                    <tr key={transaction.id} className="hover:bg-gray-50 dark:hover:bg-surface-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{transaction.orderId}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{transaction.id}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {formatAmount(transaction.amount, transaction.currency)}
                        </p>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="text-gray-600 dark:text-gray-400">
                            {getMethodIcon(transaction.method)}
                          </span>
                          <div>
                            <p className="text-sm text-gray-900 dark:text-white capitalize">{transaction.method.replace('_', ' ')}</p>
                            {transaction.cardLast4 && (
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                {transaction.cardBrand?.toUpperCase()} ****{transaction.cardLast4}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(transaction.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(transaction.createdAt).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-2">
                          {transaction.receiptUrl && (
                            <a
                              href={transaction.receiptUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                            </a>
                          )}
                          {transaction.status === 'succeeded' && (
                            <button
                              onClick={() => setSelectedTransaction(transaction)}
                              className="text-red-400 hover:text-red-600"
                            >
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
        {activeTab === 'terminal' && (
          <motion.div
            key="terminal"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Card Terminal</h3>
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-surface-700 rounded-lg">
                <div className="flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${
                    terminalStatus === 'connected' ? 'bg-green-500' :
                    terminalStatus === 'processing' ? 'bg-yellow-500 animate-pulse' :
                    'bg-red-500'
                  }`} />
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Stripe Terminal BBPOS</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Status: {terminalStatus.charAt(0).toUpperCase() + terminalStatus.slice(1)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={connectTerminal}
                  disabled={terminalStatus === 'processing'}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    terminalStatus === 'connected'
                      ? 'bg-red-500 hover:bg-red-600 text-white'
                      : 'bg-amber-500 hover:bg-amber-600 text-gray-900'
                  } disabled:opacity-50`}
                >
                  {terminalStatus === 'connected' ? 'Disconnect' : terminalStatus === 'processing' ? 'Connecting...' : 'Connect'}
                </button>
              </div>
              {terminalStatus === 'connected' && (
                <div className="mt-6 grid grid-cols-3 gap-4">
                  <button className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg text-center hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors">
                    <svg className="w-8 h-8 mx-auto text-green-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                    </svg>
                    <p className="text-sm font-medium text-green-700 dark:text-green-400">Chip Insert</p>
                  </button>
                  <button className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-center hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors">
                    <svg className="w-8 h-8 mx-auto text-blue-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                    </svg>
                    <p className="text-sm font-medium text-blue-700 dark:text-blue-400">Tap to Pay</p>
                  </button>
                  <button className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-center hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors">
                    <svg className="w-8 h-8 mx-auto text-purple-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <p className="text-sm font-medium text-purple-700 dark:text-purple-400">Swipe Card</p>
                  </button>
                </div>
              )}
            </div>
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Manual Entry</h3>
              <form className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Card Number
                  <input
                    type="text"
                    placeholder="4242 4242 4242 4242"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white"
                  />
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Expiry
                    <input
                      type="text"
                      placeholder="MM/YY"
                      className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">CVC
                    <input
                      type="text"
                      placeholder="123"
                      className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white"
                    />
                    </label>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Amount
                  <input
                    type="text"
                    placeholder="$0.00"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white"
                  />
                  </label>
                </div>
                <button
                  type="button"
                  className="w-full px-4 py-3 bg-amber-500 hover:bg-amber-600 text-gray-900 font-medium rounded-lg transition-colors"
                >
                  Process Payment
                </button>
              </form>
            </div>
          </motion.div>
        )}
        {activeTab === 'wallets' && walletConfig && (
          <motion.div
            key="wallets"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {/* Apple Pay */}
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-black rounded-lg flex items-center justify-center text-white">
                    {getMethodIcon('apple_pay')}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Apple Pay</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">iOS & Safari</p>
                  </div>
                </div>
                <button
                  onClick={() => toggleWalletSetting('applePay')}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    walletConfig.applePay.enabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-surface-600'
                  }`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow transform transition-transform ${
                    walletConfig.applePay.enabled ? 'translate-x-6' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>
              {stats && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {stats.byWalletType.apple_pay} transactions this month
                </p>
              )}
            </div>
            {/* Google Pay */}
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-white dark:bg-surface-700 border border-gray-200 dark:border-surface-600 rounded-lg flex items-center justify-center">
                    {getMethodIcon('google_pay')}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Google Pay</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Android & Chrome</p>
                  </div>
                </div>
                <button
                  onClick={() => toggleWalletSetting('googlePay')}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    walletConfig.googlePay.enabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-surface-600'
                  }`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow transform transition-transform ${
                    walletConfig.googlePay.enabled ? 'translate-x-6' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>
              {stats && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {stats.byWalletType.google_pay} transactions this month
                </p>
              )}
            </div>
            {/* Link */}
            <div className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center text-white">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">Stripe Link</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">One-click checkout</p>
                  </div>
                </div>
                <button
                  onClick={() => toggleWalletSetting('link')}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    walletConfig.link.enabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-surface-600'
                  }`}
                >
                  <div className={`w-5 h-5 bg-white rounded-full shadow transform transition-transform ${
                    walletConfig.link.enabled ? 'translate-x-6' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>
              {stats && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {stats.byWalletType.link} transactions this month
                </p>
              )}
            </div>
          </motion.div>
        )}
        {activeTab === 'settings' && (
          <motion.div
            key="settings"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-white dark:bg-surface-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-surface-700"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Payment Settings</h3>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Stripe Publishable Key
                <input
                  type="text"
                  placeholder="pk_live_..."
                  className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white"
                />
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Currency
                <select className="w-full px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700 text-gray-900 dark:text-white">
                  <option value="usd">USD - US Dollar</option>
                  <option value="eur">EUR - Euro</option>
                  <option value="gbp">GBP - British Pound</option>
                  <option value="bgn">BGN - Bulgarian Lev</option>
                </select>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Accepted Card Networks
                <div className="flex flex-wrap gap-2 mt-2">
                  {['Visa', 'Mastercard', 'American Express', 'Discover'].map(network => (
                    <label key={network} className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-surface-700 rounded-lg cursor-pointer">
                      <input type="checkbox" defaultChecked className="rounded text-amber-500" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{network}</span>
                    </label>
                  ))}
                </div>
                </label>
              </div>
              <div className="pt-4">
                <button className="px-6 py-2 bg-amber-500 hover:bg-amber-600 text-gray-900 font-medium rounded-lg transition-colors">
                  Save Settings
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      {/* Refund Modal */}
      {selectedTransaction && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-surface-800 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Confirm Refund</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Are you sure you want to refund{' '}
              <strong>{formatAmount(selectedTransaction.amount, selectedTransaction.currency)}</strong> for order{' '}
              <strong>{selectedTransaction.orderId}</strong>?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setSelectedTransaction(null)}
                disabled={isProcessing}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-surface-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-surface-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => processRefund(selectedTransaction.id)}
                disabled={isProcessing}
                className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {isProcessing ? 'Processing...' : 'Refund'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}