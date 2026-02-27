'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import { api, isAuthenticated } from '@/lib/api';

// ============ INTERFACES ============

interface Transaction {
  id: string;
  type: 'income' | 'expense' | 'transfer';
  category: string;
  description: string;
  amount: number;
  date: string;
  account: string;
  vendor?: string;
  invoice_id?: string;
  payment_method: 'cash' | 'card' | 'bank_transfer' | 'check';
  status: 'pending' | 'completed' | 'cancelled' | 'reconciled';
  recurring?: {
    frequency: 'daily' | 'weekly' | 'monthly' | 'yearly';
    next_date: string;
  };
  attachments?: string[];
  notes?: string;
  created_by: string;
  approved_by?: string;
}

interface Invoice {
  id: string;
  number: string;
  type: 'receivable' | 'payable';
  customer_vendor: string;
  items: InvoiceItem[];
  subtotal: number;
  tax_amount: number;
  total: number;
  currency: string;
  issue_date: string;
  due_date: string;
  paid_date?: string;
  status: 'draft' | 'sent' | 'viewed' | 'paid' | 'overdue' | 'cancelled';
  payment_terms: string;
  notes?: string;
  reminders_sent: number;
}

interface InvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  total: number;
}

interface Vendor {
  id: string;
  name: string;
  type: 'supplier' | 'contractor' | 'service';
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  tax_id: string;
  payment_terms: number;
  credit_limit: number;
  current_balance: number;
  status: 'active' | 'inactive' | 'blocked';
  rating: number;
  total_orders: number;
  total_spent: number;
  last_order_date?: string;
  notes?: string;
}

interface Account {
  id: string;
  name: string;
  type: 'cash' | 'bank' | 'credit_card' | 'petty_cash';
  balance: number;
  currency: string;
  bank_name?: string;
  account_number?: string;
  is_default: boolean;
  last_reconciled?: string;
}

interface Budget {
  id: string;
  category: string;
  monthly_budget: number;
  spent: number;
  icon: string;
  alerts: { warning: number; critical: number };
}

interface TaxConfig {
  id: string;
  name: string;
  rate: number;
  type: 'vat' | 'sales' | 'service';
  is_default: boolean;
}

interface FinancialAlert {
  id: string;
  type: 'overdue_invoice' | 'budget_warning' | 'low_balance' | 'payment_due' | 'reconciliation';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  date: string;
  action_url?: string;
  dismissed: boolean;
}

// ============ COMPONENT ============

export default function FinancialManagementPage() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'transactions' | 'invoices' | 'vendors' | 'reports' | 'settings'>('dashboard');
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<'today' | 'week' | 'month' | 'quarter' | 'year'>('month');

  // Data states
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [alerts, setAlerts] = useState<FinancialAlert[]>([]);
  const [taxConfigs, setTaxConfigs] = useState<TaxConfig[]>([]);

  // Modal states
  const [showTransactionModal, setShowTransactionModal] = useState(false);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [, setShowVendorModal] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);

  // Filter states
  const [transactionFilter, setTransactionFilter] = useState<'all' | 'income' | 'expense' | 'transfer'>('all');
  const [invoiceFilter, setInvoiceFilter] = useState<'all' | 'receivable' | 'payable' | 'overdue'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [, setAuthError] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Demo data for development/unauthenticated state
  const demoAccounts: Account[] = [
    { id: '1', name: 'Основна каса', type: 'cash', balance: 12450, currency: 'лв', is_default: true, last_reconciled: '2025-12-27' },
    { id: '2', name: 'Банкова сметка', type: 'bank', balance: 85320, currency: 'лв', bank_name: 'УниКредит Булбанк', account_number: 'BG80UNCR...', is_default: false, last_reconciled: '2025-12-25' },
    { id: '3', name: 'POS терминал', type: 'bank', balance: 23100, currency: 'лв', bank_name: 'Борика', is_default: false },
    { id: '4', name: 'Дребни разходи', type: 'petty_cash', balance: 850, currency: 'лв', is_default: false },
  ];

  const demoTransactions: Transaction[] = [
    { id: '1', type: 'income', category: 'Продажби', description: 'Дневен оборот - смяна 1', amount: 4850, date: '2025-12-28', account: 'Основна каса', payment_method: 'cash', status: 'completed', created_by: 'Система' },
    { id: '2', type: 'expense', category: 'Съставки', description: 'Доставка от Metro', amount: 1250, date: '2025-12-28', account: 'Банкова сметка', vendor: 'Metro Cash & Carry', payment_method: 'bank_transfer', status: 'completed', created_by: 'Иван Петров' },
    { id: '3', type: 'income', category: 'Продажби', description: 'Дневен оборот - смяна 2', amount: 6320, date: '2025-12-27', account: 'Основна каса', payment_method: 'cash', status: 'completed', created_by: 'Система' },
    { id: '4', type: 'expense', category: 'Заплати', description: 'Заплати декември', amount: 18500, date: '2025-12-25', account: 'Банкова сметка', payment_method: 'bank_transfer', status: 'pending', created_by: 'Мария Иванова', approved_by: undefined },
    { id: '5', type: 'expense', category: 'Комунални', description: 'Електричество', amount: 890, date: '2025-12-24', account: 'Банкова сметка', payment_method: 'bank_transfer', status: 'completed', created_by: 'Мария Иванова' },
    { id: '6', type: 'transfer', category: 'Вътрешен трансфер', description: 'Депозит в банка', amount: 5000, date: '2025-12-23', account: 'Основна каса', payment_method: 'cash', status: 'completed', created_by: 'Иван Петров' },
  ];

  const demoInvoices: Invoice[] = [
    { id: '1', number: 'INV-2025-0145', type: 'receivable', customer_vendor: 'Хотел Рила', items: [], subtotal: 2500, tax_amount: 500, total: 3000, currency: 'лв', issue_date: '2025-12-20', due_date: '2025-12-30', status: 'sent', payment_terms: 'Нето 10 дни', reminders_sent: 0 },
    { id: '2', number: 'INV-2025-0144', type: 'payable', customer_vendor: 'Metro Cash & Carry', items: [], subtotal: 4200, tax_amount: 840, total: 5040, currency: 'лв', issue_date: '2025-12-15', due_date: '2025-12-25', status: 'overdue', payment_terms: 'Нето 10 дни', reminders_sent: 2 },
    { id: '3', number: 'INV-2025-0143', type: 'receivable', customer_vendor: 'Ski & Fun Events', items: [], subtotal: 8500, tax_amount: 1700, total: 10200, currency: 'лв', issue_date: '2025-12-18', due_date: '2025-01-05', status: 'viewed', payment_terms: 'Нето 14 дни', reminders_sent: 0 },
  ];

  const demoVendors: Vendor[] = [
    { id: '1', name: 'Metro Cash & Carry', type: 'supplier', contact_person: 'Петър Димитров', email: 'orders@metro.bg', phone: '+359 2 960 5000', address: 'София, бул. Цариградско шосе 115', tax_id: 'BG121212121', payment_terms: 14, credit_limit: 20000, current_balance: 5040, status: 'active', rating: 4.5, total_orders: 156, total_spent: 89500, last_order_date: '2025-12-28' },
    { id: '2', name: 'Загорка АД', type: 'supplier', contact_person: 'Мария Колева', email: 'sales@zagorka.bg', phone: '+359 42 600 100', address: 'Стара Загора, ул. Индустриална 1', tax_id: 'BG834567890', payment_terms: 7, credit_limit: 15000, current_balance: 0, status: 'active', rating: 4.8, total_orders: 89, total_spent: 45200, last_order_date: '2025-12-26' },
    { id: '3', name: 'Локал Фреш', type: 'supplier', contact_person: 'Георги Стоянов', email: 'info@localfresh.bg', phone: '+359 888 123 456', address: 'Самоков, ул. Търговска 15', tax_id: 'BG567890123', payment_terms: 0, credit_limit: 5000, current_balance: 0, status: 'active', rating: 4.9, total_orders: 234, total_spent: 28900, last_order_date: '2025-12-28' },
  ];

  const demoBudgets: Budget[] = [
    { id: '1', category: 'Съставки', monthly_budget: 35000, spent: 28500, icon: '🥬', alerts: { warning: 80, critical: 95 } },
    { id: '2', category: 'Заплати', monthly_budget: 45000, spent: 42000, icon: '👥', alerts: { warning: 90, critical: 100 } },
    { id: '3', category: 'Комунални', monthly_budget: 5000, spent: 3200, icon: '💡', alerts: { warning: 80, critical: 95 } },
    { id: '4', category: 'Маркетинг', monthly_budget: 3000, spent: 1800, icon: '📢', alerts: { warning: 80, critical: 95 } },
    { id: '5', category: 'Поддръжка', monthly_budget: 2500, spent: 950, icon: '🔧', alerts: { warning: 80, critical: 95 } },
  ];

  const demoAlerts: FinancialAlert[] = [
    { id: '1', type: 'overdue_invoice', severity: 'critical', message: 'Фактура INV-2025-0144 от Metro е просрочена с 3 дни', date: '2025-12-28', dismissed: false },
    { id: '2', type: 'budget_warning', severity: 'warning', message: 'Бюджетът за Заплати е 93% изчерпан', date: '2025-12-27', dismissed: false },
    { id: '3', type: 'reconciliation', severity: 'info', message: 'Препоръчваме сверка на касата - последна преди 2 дни', date: '2025-12-26', dismissed: false },
  ];

  const demoTaxConfigs: TaxConfig[] = [
    { id: '1', name: 'ДДС стандартен', rate: 20, type: 'vat', is_default: true },
    { id: '2', name: 'ДДС намален', rate: 9, type: 'vat', is_default: false },
    { id: '3', name: 'Без ДДС', rate: 0, type: 'vat', is_default: false },
  ];

  const loadDemoData = useCallback(() => {
    setAccounts(demoAccounts);
    setTransactions(demoTransactions);
    setInvoices(demoInvoices);
    setVendors(demoVendors);
    setBudgets(demoBudgets);
    setAlerts(demoAlerts);
    setTaxConfigs(demoTaxConfigs);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);



  const fetchAccounts = useCallback(async () => {
    const data = await api.get<any>('/financial/accounts/');
    setAccounts(Array.isArray(data) ? data : data.accounts || []);
  }, []);

  const fetchTransactions = useCallback(async () => {
    const data = await api.get<any>('/financial/transactions/');
    setTransactions(Array.isArray(data) ? data : data.transactions || []);
  }, []);

  const fetchInvoices = useCallback(async () => {
    const data = await api.get<any>('/invoices/');
    setInvoices(Array.isArray(data) ? data : data.items || data.invoices || []);
  }, []);

  const fetchVendors = useCallback(async () => {
    const data = await api.get<any>('/suppliers/');
    setVendors(Array.isArray(data) ? data : data.suppliers || []);
  }, []);

  const fetchBudgets = useCallback(async () => {
    try {
      const data = await api.get<any>('/financial/budgets/');
      setBudgets(Array.isArray(data) ? data : data.budgets || []);
    } catch (err) {
      console.error('Error fetching budgets:', err);
    }
  }, []);

  const fetchFinancialAlerts = useCallback(async () => {
    try {
      const data = await api.get<any>('/financial/financial-alerts/');
      setAlerts(Array.isArray(data) ? data : data.alerts || []);
    } catch (err) {
      console.error('Error fetching financial alerts:', err);
    }
  }, []);

  const fetchTaxConfigs = useCallback(async () => {
    try {
      const data = await api.get<any>('/settings/tax/');
      setTaxConfigs(Array.isArray(data) ? data : data.configs || []);
    } catch (err) {
      console.error('Error fetching tax configs:', err);
    }
  }, []);

  const loadFinancialData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setAuthError(false);
    setIsDemoMode(false);

    if (!isAuthenticated()) {
      // Not authenticated - load demo data
      loadDemoData();
      setIsDemoMode(true);
      setLoading(false);
      return;
    }

    try {
      await Promise.all([
        fetchAccounts(),
        fetchTransactions(),
        fetchInvoices(),
        fetchVendors(),
        fetchBudgets(),
        fetchFinancialAlerts(),
        fetchTaxConfigs(),
      ]);
    } catch (err) {
      if (err instanceof Error && err.message === 'AUTH_ERROR') {
        // Auth failed - load demo data as fallback
        loadDemoData();
        setIsDemoMode(true);
        setAuthError(true);
      } else {
        const message = err instanceof Error ? err.message : 'Failed to load financial data';
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [fetchAccounts, fetchTransactions, fetchInvoices, fetchVendors, fetchBudgets, fetchFinancialAlerts, fetchTaxConfigs, loadDemoData]);

  useEffect(() => {
    loadFinancialData();
  }, [loadFinancialData]);

  // ============ CALCULATIONS ============

  const totalBalance = accounts.reduce((sum, acc) => sum + acc.balance, 0);
  const monthlyIncome = transactions.filter(t => t.type === 'income' && t.status === 'completed').reduce((sum, t) => sum + t.amount, 0);
  const monthlyExpenses = transactions.filter(t => t.type === 'expense' && t.status === 'completed').reduce((sum, t) => sum + t.amount, 0);
  const overdueInvoices = invoices.filter(i => i.status === 'overdue');
  const pendingReceivables = invoices.filter(i => i.type === 'receivable' && ['sent', 'viewed'].includes(i.status)).reduce((sum, i) => sum + i.total, 0);
  const pendingPayables = invoices.filter(i => i.type === 'payable' && !['paid', 'cancelled'].includes(i.status)).reduce((sum, i) => sum + i.total, 0);
  const totalBudget = budgets.reduce((sum, b) => sum + b.monthly_budget, 0);
  const totalSpent = budgets.reduce((sum, b) => sum + b.spent, 0);
  const budgetUtilization = (totalSpent / totalBudget) * 100;
  const activeAlerts = alerts.filter(a => !a.dismissed);
  const criticalAlerts = activeAlerts.filter(a => a.severity === 'critical');

  // ============ HANDLERS ============

  const handleApproveTransaction = (id: string) => {
    setTransactions(transactions.map(t => t.id === id ? { ...t, status: 'completed', approved_by: 'Управител' } : t));
  };

  const handleDismissAlert = (id: string) => {
    setAlerts(alerts.map(a => a.id === id ? { ...a, dismissed: true } : a));
  };

  const handleSendInvoice = (id: string) => {
    setInvoices(invoices.map(i => i.id === id ? { ...i, status: 'sent' } : i));
  };

  const handleMarkInvoicePaid = (id: string) => {
    setInvoices(invoices.map(i => i.id === id ? { ...i, status: 'paid', paid_date: new Date().toISOString().split('T')[0] } : i));
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      reconciled: 'bg-blue-100 text-blue-800',
      cancelled: 'bg-red-100 text-red-800',
      draft: 'bg-gray-100 text-gray-800',
      sent: 'bg-blue-100 text-blue-800',
      viewed: 'bg-purple-100 text-purple-800',
      paid: 'bg-green-100 text-green-800',
      overdue: 'bg-red-100 text-red-800',
      active: 'bg-green-100 text-green-800',
      inactive: 'bg-gray-100 text-gray-800',
      blocked: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: 'Чакащ', completed: 'Завършен', reconciled: 'Сверен', cancelled: 'Отменен',
      draft: 'Чернова', sent: 'Изпратена', viewed: 'Прегледана', paid: 'Платена',
      overdue: 'Просрочена', active: 'Активен', inactive: 'Неактивен', blocked: 'Блокиран',
    };
    return labels[status] || status;
  };

  const getCategoryIcon = (category: string) => {
    const icons: Record<string, string> = {
      'Продажби': '💰', 'Съставки': '🥬', 'Заплати': '👥', 'Комунални': '💡',
      'Маркетинг': '📢', 'Оборудване': '🔧', 'Наем': '🏠', 'Застраховки': '📋',
      'Вътрешен трансфер': '🔄', 'Други': '📦',
    };
    return icons[category] || '📄';
  };

  const filteredTransactions = transactions.filter(t => {
    if (transactionFilter !== 'all' && t.type !== transactionFilter) return false;
    if (searchTerm && !t.description.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const filteredInvoices = invoices.filter(i => {
    if (invoiceFilter === 'receivable' && i.type !== 'receivable') return false;
    if (invoiceFilter === 'payable' && i.type !== 'payable') return false;
    if (invoiceFilter === 'overdue' && i.status !== 'overdue') return false;
    if (searchTerm && !i.customer_vendor.toLowerCase().includes(searchTerm.toLowerCase()) && !i.number.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const tabs = [
    { id: 'dashboard', label: 'Табло', icon: '📊' },
    { id: 'transactions', label: 'Транзакции', icon: '💸', count: transactions.filter(t => t.status === 'pending').length },
    { id: 'invoices', label: 'Фактури', icon: '📄', count: overdueInvoices.length },
    { id: 'vendors', label: 'Доставчици', icon: '🏢' },
    { id: 'reports', label: 'Отчети', icon: '📈' },
    { id: 'settings', label: 'Настройки', icon: '⚙️' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <div className="text-gray-700 text-lg">Зареждане на финансови данни...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-red-800">Грешка при зареждане на данни</h3>
            <p className="mt-2 text-sm text-red-700">{error}</p>
            <button
              onClick={loadFinancialData}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Опитай отново
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              💰 Финансово управление
            </h1>
            <p className="text-gray-500 mt-1">Транзакции, фактури, бюджети и отчети</p>
          </div>
          <div className="flex gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as any)}
              className="px-4 py-2 bg-white text-gray-700 rounded-xl border border-gray-200 shadow-sm"
            >
              <option value="today">Днес</option>
              <option value="week">Тази седмица</option>
              <option value="month">Този месец</option>
              <option value="quarter">Това тримесечие</option>
              <option value="year">Тази година</option>
            </select>
            <button
              onClick={() => setShowTransactionModal(true)}
              className="px-4 py-2 bg-green-600 text-gray-900 rounded-xl hover:bg-green-700 flex items-center gap-2 shadow-sm"
            >
              <span>+</span> Транзакция
            </button>
            <button
              onClick={() => setShowInvoiceModal(true)}
              className="px-4 py-2 bg-blue-600 text-gray-900 rounded-xl hover:bg-blue-700 flex items-center gap-2 shadow-sm"
            >
              <span>📄</span> Фактура
            </button>
          </div>
        </div>

        {/* Demo Mode Banner */}
        {isDemoMode && (
          <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🔓</span>
                <div>
                  <div className="text-amber-800 font-medium">Демо режим - показват се примерни данни</div>
                  <div className="text-amber-600 text-sm">Влезте в системата за да видите реални финансови данни</div>
                </div>
              </div>
              <a href="/login" className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700">Вход</a>
            </div>
          </div>
        )}

        {/* Alerts Banner */}
        {criticalAlerts.length > 0 && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🚨</span>
                <div>
                  <div className="text-red-800 font-medium">{criticalAlerts.length} критични известия изискват внимание</div>
                  <div className="text-red-600 text-sm">{criticalAlerts[0].message}</div>
                </div>
              </div>
              <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Преглед</button>
            </div>
          </div>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm">Общо баланс</div>
            <div className="text-2xl font-bold text-gray-900">{totalBalance.toLocaleString()} лв</div>
            <div className="text-green-600 text-xs mt-1">+5.2% от миналия месец</div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm">Приходи (месец)</div>
            <div className="text-2xl font-bold text-green-600">{monthlyIncome.toLocaleString()} лв</div>
            <div className="text-gray-400 text-xs mt-1">+12.8% vs миналия месец</div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm">Разходи (месец)</div>
            <div className="text-2xl font-bold text-red-600">{monthlyExpenses.toLocaleString()} лв</div>
            <div className="text-gray-400 text-xs mt-1">-3.2% vs миналия месец</div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm">Вземания</div>
            <div className="text-2xl font-bold text-blue-600">{pendingReceivables.toLocaleString()} лв</div>
            <div className="text-gray-400 text-xs mt-1">{invoices.filter(i => i.type === 'receivable' && i.status !== 'paid').length} неплатени</div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm">Задължения</div>
            <div className="text-2xl font-bold text-orange-600">{pendingPayables.toLocaleString()} лв</div>
            <div className="text-gray-400 text-xs mt-1">{overdueInvoices.length > 0 ? `${overdueInvoices.length} просрочени!` : 'Всички в срок'}</div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm">Бюджет използван</div>
            <div className="text-2xl font-bold text-purple-600">{(budgetUtilization || 0).toFixed(0)}%</div>
            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
              <div className={`h-1.5 rounded-full ${budgetUtilization > 90 ? 'bg-red-500' : budgetUtilization > 75 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${Math.min(budgetUtilization, 100)}%` }} />
            </div>
          </motion.div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-xl font-medium whitespace-nowrap transition-all flex items-center gap-2 ${
                activeTab === tab.id ? 'bg-blue-600 text-gray-900 shadow-sm' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
              {tab.count && tab.count > 0 && (
                <span className="bg-red-500 text-gray-900 text-xs px-2 py-0.5 rounded-full">{tab.count}</span>
              )}
            </button>
          ))}
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Accounts Overview */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">Сметки и каси</h2>
                <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">🔄 Сверка</button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {accounts.map((account) => (
                  <motion.div
                    key={account.id}
                    whileHover={{ scale: 1.02 }}
                    className={`p-4 rounded-xl cursor-pointer border ${account.balance < 0 ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'}`}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-2xl">
                        {account.type === 'cash' ? '💵' : account.type === 'bank' ? '🏦' : account.type === 'credit_card' ? '💳' : '🪙'}
                      </span>
                      <div>
                        <div className="text-gray-900 font-medium">{account.name}</div>
                        <div className="text-gray-500 text-xs">{account.bank_name || account.type}</div>
                      </div>
                    </div>
                    <div className={`text-2xl font-bold ${account.balance < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                      {account.balance.toLocaleString()} {account.currency}
                    </div>
                    {account.last_reconciled && (
                      <div className="text-gray-400 text-xs mt-2">Последна сверка: {account.last_reconciled}</div>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Alerts */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Известия ({activeAlerts.length})</h2>
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {activeAlerts.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">✅ Няма активни известия</div>
                  ) : (
                    activeAlerts.map((alert) => (
                      <motion.div
                        key={alert.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`p-4 rounded-xl flex items-start justify-between gap-3 ${
                          alert.severity === 'critical' ? 'bg-red-50 border border-red-200' :
                          alert.severity === 'warning' ? 'bg-yellow-50 border border-yellow-200' :
                          'bg-blue-50 border border-blue-200'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-xl">
                            {alert.severity === 'critical' ? '🚨' : alert.severity === 'warning' ? '⚠️' : 'ℹ️'}
                          </span>
                          <div>
                            <div className="text-gray-800 text-sm">{alert.message}</div>
                            <div className="text-gray-500 text-xs mt-1">{alert.date}</div>
                          </div>
                        </div>
                        <button onClick={() => handleDismissAlert(alert.id)} className="text-gray-400 hover:text-gray-600">✕</button>
                      </motion.div>
                    ))
                  )}
                </div>
              </div>

              {/* Budget Overview */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Изпълнение на бюджета</h2>
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {budgets.map((budget) => {
                    const percentage = (budget.spent / budget.monthly_budget) * 100;
                    const isWarning = percentage >= budget.alerts.warning;
                    const isCritical = percentage >= budget.alerts.critical;
                    return (
                      <div key={budget.id} className="p-3 bg-gray-50 rounded-lg">
                        <div className="flex justify-between items-center mb-2">
                          <span className="flex items-center gap-2 text-gray-700">
                            <span>{budget.icon}</span>
                            <span className="text-sm">{budget.category}</span>
                          </span>
                          <span className={`text-sm font-medium ${isCritical ? 'text-red-600' : isWarning ? 'text-yellow-600' : 'text-gray-600'}`}>
                            {budget.spent.toLocaleString()} / {budget.monthly_budget.toLocaleString()} лв
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${isCritical ? 'bg-red-500' : isWarning ? 'bg-yellow-500' : 'bg-green-500'}`}
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Recent Transactions */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold text-gray-900">Последни транзакции</h2>
                  <button onClick={() => setActiveTab('transactions')} className="text-blue-600 hover:text-blue-700 text-sm">Виж всички →</button>
                </div>
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {transactions.slice(0, 6).map((tx) => (
                    <div key={tx.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                      <div className="flex items-center gap-3">
                        <span className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          tx.type === 'income' ? 'bg-green-100 text-green-600' : tx.type === 'expense' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'
                        }`}>
                          {tx.type === 'income' ? '↓' : tx.type === 'expense' ? '↑' : '↔'}
                        </span>
                        <div>
                          <div className="text-gray-900 text-sm">{tx.description}</div>
                          <div className="text-gray-500 text-xs">{tx.date} • {tx.account}</div>
                        </div>
                      </div>
                      <div className={`font-medium ${tx.type === 'income' ? 'text-green-600' : tx.type === 'expense' ? 'text-red-600' : 'text-blue-600'}`}>
                        {tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : ''}{tx.amount.toLocaleString()} лв
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pending Invoices */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold text-gray-900">Чакащи фактури</h2>
                  <button onClick={() => setActiveTab('invoices')} className="text-blue-600 hover:text-blue-700 text-sm">Виж всички →</button>
                </div>
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {invoices.filter(i => !['paid', 'cancelled'].includes(i.status)).slice(0, 5).map((invoice) => (
                    <div key={invoice.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                      <div className="flex items-center gap-3">
                        <span className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          invoice.type === 'receivable' ? 'bg-green-100 text-green-600' : 'bg-orange-100 text-orange-600'
                        }`}>
                          {invoice.type === 'receivable' ? '←' : '→'}
                        </span>
                        <div>
                          <div className="text-gray-900 text-sm">{invoice.customer_vendor}</div>
                          <div className="text-gray-500 text-xs">{invoice.number} • До: {invoice.due_date}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-gray-900 font-medium">{invoice.total.toLocaleString()} лв</div>
                        <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(invoice.status)}`}>{getStatusLabel(invoice.status)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
              <div className="flex gap-2">
                {['all', 'income', 'expense', 'transfer'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setTransactionFilter(filter as any)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      transactionFilter === filter ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {filter === 'all' ? 'Всички' : filter === 'income' ? '↓ Приходи' : filter === 'expense' ? '↑ Разходи' : '↔ Трансфери'}
                  </button>
                ))}
              </div>
              <div className="flex gap-3 w-full md:w-auto">
                <input
                  type="text"
                  placeholder="Търсене..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 md:w-64 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none"
                />
                <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">📥 Експорт</button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-500 text-sm border-b border-gray-200">
                    <th className="pb-3 font-medium">Дата</th>
                    <th className="pb-3 font-medium">Описание</th>
                    <th className="pb-3 font-medium">Категория</th>
                    <th className="pb-3 font-medium">Сметка</th>
                    <th className="pb-3 font-medium text-right">Сума</th>
                    <th className="pb-3 font-medium">Статус</th>
                    <th className="pb-3 font-medium text-center">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredTransactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-gray-50">
                      <td className="py-4 text-gray-900">{tx.date}</td>
                      <td className="py-4">
                        <div className="text-gray-900">{tx.description}</div>
                        {tx.vendor && <div className="text-gray-500 text-xs">{tx.vendor}</div>}
                        {tx.recurring && <span className="inline-flex items-center gap-1 text-xs text-blue-600 mt-1">🔄 Месечно</span>}
                      </td>
                      <td className="py-4">
                        <span className="flex items-center gap-2 text-gray-700">{getCategoryIcon(tx.category)} {tx.category}</span>
                      </td>
                      <td className="py-4 text-gray-600">{tx.account}</td>
                      <td className={`py-4 text-right font-medium ${tx.type === 'income' ? 'text-green-600' : tx.type === 'expense' ? 'text-red-600' : 'text-blue-600'}`}>
                        {tx.type === 'income' ? '+' : tx.type === 'expense' ? '-' : ''}{tx.amount.toLocaleString()} лв
                      </td>
                      <td className="py-4">
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(tx.status)}`}>{getStatusLabel(tx.status)}</span>
                      </td>
                      <td className="py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          {tx.status === 'pending' && (
                            <button onClick={() => handleApproveTransaction(tx.id)} className="p-1.5 bg-green-100 text-green-600 rounded hover:bg-green-200" title="Одобри">✓</button>
                          )}
                          <button onClick={() => setSelectedTransaction(tx)} className="p-1.5 bg-gray-100 text-gray-600 rounded hover:bg-gray-200" title="Детайли">👁</button>
                          <button className="p-1.5 bg-gray-100 text-gray-600 rounded hover:bg-gray-200" title="Редактирай">✏️</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredTransactions.length === 0 && <div className="text-center py-12 text-gray-500">Няма намерени транзакции</div>}
          </div>
        )}

        {/* Invoices Tab */}
        {activeTab === 'invoices' && (
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
              <div className="flex gap-2">
                {['all', 'receivable', 'payable', 'overdue'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setInvoiceFilter(filter as any)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      invoiceFilter === filter ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {filter === 'all' ? 'Всички' : filter === 'receivable' ? '← Вземания' : filter === 'payable' ? '→ Задължения' : '⚠️ Просрочени'}
                  </button>
                ))}
              </div>
              <input
                type="text"
                placeholder="Търсене..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full md:w-64 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="grid gap-4">
              {filteredInvoices.map((invoice) => (
                <motion.div
                  key={invoice.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-4 rounded-xl border ${invoice.status === 'overdue' ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'} hover:shadow-md transition-shadow`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <span className={`w-12 h-12 rounded-full flex items-center justify-center text-xl ${invoice.type === 'receivable' ? 'bg-green-100' : 'bg-orange-100'}`}>
                        {invoice.type === 'receivable' ? '📤' : '📥'}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-900 font-medium">{invoice.number}</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(invoice.status)}`}>{getStatusLabel(invoice.status)}</span>
                        </div>
                        <div className="text-gray-600">{invoice.customer_vendor}</div>
                        <div className="text-gray-500 text-sm">Издадена: {invoice.issue_date} • Падеж: {invoice.due_date}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-gray-500 text-sm">Сума</div>
                        <div className="text-xl font-bold text-gray-900">{invoice.total.toLocaleString()} {invoice.currency}</div>
                        <div className="text-gray-500 text-xs">вкл. ДДС {(invoice.tax_amount || 0).toLocaleString()} лв</div>
                      </div>
                      <div className="flex gap-2">
                        {invoice.status === 'draft' && (
                          <button onClick={() => handleSendInvoice(invoice.id)} className="px-3 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 text-sm">✉️ Изпрати</button>
                        )}
                        {['sent', 'viewed', 'overdue'].includes(invoice.status) && (
                          <button onClick={() => handleMarkInvoicePaid(invoice.id)} className="px-3 py-2 bg-green-600 text-gray-900 rounded-lg hover:bg-green-700 text-sm">
                            {invoice.type === 'payable' ? '💰 Плати' : '✓ Получено'}
                          </button>
                        )}
                        <button onClick={() => setSelectedInvoice(invoice)} className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">👁 Преглед</button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
            {filteredInvoices.length === 0 && <div className="text-center py-12 text-gray-500">Няма намерени фактури</div>}
          </div>
        )}

        {/* Vendors Tab */}
        {activeTab === 'vendors' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <input
                type="text"
                placeholder="Търсене на доставчик..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-64 px-4 py-2 bg-white text-gray-900 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none"
              />
              <button onClick={() => setShowVendorModal(true)} className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700">+ Нов доставчик</button>
            </div>

            <div className="grid gap-4">
              {vendors.filter(v => v.name.toLowerCase().includes(searchTerm.toLowerCase())).map((vendor) => (
                <motion.div key={vendor.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-gray-900 text-xl font-bold">
                        {vendor.name.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-900 font-medium text-lg">{vendor.name}</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(vendor.status)}`}>{getStatusLabel(vendor.status)}</span>
                          <span className="text-yellow-500 text-sm">★ {(vendor.rating || 0).toFixed(1)}</span>
                        </div>
                        <div className="text-gray-600 text-sm">{vendor.contact_person} • {vendor.phone}</div>
                        <div className="text-gray-500 text-xs">{vendor.email}</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                      <div><div className="text-gray-500 text-xs">Поръчки</div><div className="text-gray-900 font-medium">{vendor.total_orders}</div></div>
                      <div><div className="text-gray-500 text-xs">Общо платено</div><div className="text-gray-900 font-medium">{vendor.total_spent.toLocaleString()} лв</div></div>
                      <div><div className="text-gray-500 text-xs">Текущ баланс</div><div className={`font-medium ${vendor.current_balance > 0 ? 'text-orange-600' : 'text-green-600'}`}>{vendor.current_balance.toLocaleString()} лв</div></div>
                      <div><div className="text-gray-500 text-xs">Срок</div><div className="text-gray-900 font-medium">{vendor.payment_terms} дни</div></div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => setSelectedVendor(vendor)} className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">👁 Детайли</button>
                      <button className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">✏️</button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Reports Tab */}
        {activeTab === 'reports' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button className="bg-white rounded-xl p-6 text-left hover:shadow-md transition-shadow border border-gray-100">
                <span className="text-3xl mb-3 block">📊</span>
                <h3 className="text-gray-900 font-medium text-lg">Отчет за приходите и разходите</h3>
                <p className="text-gray-500 text-sm mt-2">Profit & Loss Statement</p>
              </button>
              <button className="bg-white rounded-xl p-6 text-left hover:shadow-md transition-shadow border border-gray-100">
                <span className="text-3xl mb-3 block">📋</span>
                <h3 className="text-gray-900 font-medium text-lg">Баланс</h3>
                <p className="text-gray-500 text-sm mt-2">Balance Sheet</p>
              </button>
              <button className="bg-white rounded-xl p-6 text-left hover:shadow-md transition-shadow border border-gray-100">
                <span className="text-3xl mb-3 block">💹</span>
                <h3 className="text-gray-900 font-medium text-lg">Паричен поток</h3>
                <p className="text-gray-500 text-sm mt-2">Cash Flow Statement</p>
              </button>
            </div>

            {/* P&L Preview */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">Отчет за приходите и разходите - Декември 2025</h2>
                <div className="flex gap-2">
                  <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">📥 PDF</button>
                  <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">📊 Excel</button>
                </div>
              </div>

              <div className="space-y-4">
                <div className="border-b border-gray-200 pb-4">
                  <h3 className="text-gray-900 font-medium mb-3">ПРИХОДИ</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between text-gray-600"><span className="pl-4">Продажби на храни и напитки</span><span>128,450.00 лв</span></div>
                    <div className="flex justify-between text-gray-600"><span className="pl-4">Кетъринг услуги</span><span>12,500.00 лв</span></div>
                    <div className="flex justify-between text-gray-600"><span className="pl-4">Други приходи</span><span>4,050.00 лв</span></div>
                  </div>
                  <div className="flex justify-between text-gray-900 font-bold mt-3 pt-2 border-t border-gray-100"><span>ОБЩО ПРИХОДИ</span><span>145,000.00 лв</span></div>
                </div>

                <div className="border-b border-gray-200 pb-4">
                  <h3 className="text-gray-900 font-medium mb-3">СЕБЕСТОЙНОСТ</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between text-gray-600"><span className="pl-4">Хранителни продукти</span><span>32,500.00 лв</span></div>
                    <div className="flex justify-between text-gray-600"><span className="pl-4">Напитки</span><span>8,900.00 лв</span></div>
                  </div>
                  <div className="flex justify-between text-gray-900 font-bold mt-3 pt-2 border-t border-gray-100"><span>ОБЩО СЕБЕСТОЙНОСТ</span><span>41,400.00 лв</span></div>
                </div>

                <div className="bg-green-50 p-3 rounded-lg flex justify-between text-green-700 font-bold"><span>БРУТНА ПЕЧАЛБА</span><span>103,600.00 лв (71.4%)</span></div>

                <div className="border-b border-gray-200 pb-4">
                  <h3 className="text-gray-900 font-medium mb-3">ОПЕРАТИВНИ РАЗХОДИ</h3>
                  <div className="space-y-2">
                    {budgets.map((budget) => (
                      <div key={budget.id} className="flex justify-between text-gray-600">
                        <span className="pl-4 flex items-center gap-2"><span>{budget.icon}</span>{budget.category}</span>
                        <span>{budget.spent.toLocaleString()}.00 лв</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between text-gray-900 font-bold mt-3 pt-2 border-t border-gray-100"><span>ОБЩО ОПЕРАТИВНИ</span><span>{totalSpent.toLocaleString()}.00 лв</span></div>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="flex justify-between text-blue-800 font-bold text-lg"><span>НЕТНА ПЕЧАЛБА</span><span>{(103600 - totalSpent).toLocaleString()}.00 лв</span></div>
                  <div className="flex justify-between text-blue-600 text-sm mt-2"><span>Марж</span><span>{((((103600 - totalSpent) / 145000) * 100) || 0).toFixed(1)}%</span></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Данъчни настройки</h2>
              <div className="space-y-3">
                {taxConfigs.map((tax) => (
                  <div key={tax.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className={`w-3 h-3 rounded-full ${tax.is_default ? 'bg-green-500' : 'bg-gray-300'}`} />
                      <div><div className="text-gray-900">{tax.name}</div><div className="text-gray-500 text-xs">{tax.type.toUpperCase()}</div></div>
                    </div>
                    <div className="flex items-center gap-3"><span className="text-gray-900 font-medium">{tax.rate}%</span><button className="text-gray-400 hover:text-gray-600">✏️</button></div>
                  </div>
                ))}
                <button className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400">+ Добави данъчна ставка</button>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Настройки за известия</h2>
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2"><span className="text-gray-700">Предупреждение за бюджет</span><span className="text-yellow-600">⚠️ 80%</span></div>
                  <input type="range" min="50" max="100" defaultValue="80" className="w-full" />
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2"><span className="text-gray-700">Критичен лимит</span><span className="text-red-600">🚨 95%</span></div>
                  <input type="range" min="50" max="100" defaultValue="95" className="w-full" />
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-700">Напомняне за сверка</span>
                    <select className="bg-white text-gray-700 rounded px-3 py-1 border border-gray-200"><option>Ежедневно</option><option>Седмично</option><option>Месечно</option></select>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Валутни настройки</h2>
              <div className="space-y-4">
                <div><label className="text-gray-500 text-sm">Основна валута <select className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200"><option>BGN (Български лев)</option><option>EUR (Евро)</option></select></label>
                </div>
                <div><label className="text-gray-500 text-sm">Формат на числата <select className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200"><option>1 234,56 (Европейски)</option><option>1,234.56 (Американски)</option></select></label>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Интеграции</h2>
              <div className="space-y-3">
                <div className="p-4 bg-gray-50 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3"><span className="text-2xl">🏦</span><div><div className="text-gray-900">Банкова интеграция</div><div className="text-gray-500 text-xs">Автоматичен импорт</div></div></div>
                  <button className="px-3 py-1 bg-blue-600 text-gray-900 rounded text-sm">Свържи</button>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3"><span className="text-2xl">🧾</span><div><div className="text-gray-900">НАП интеграция</div><div className="text-gray-500 text-xs">Фискални устройства</div></div></div>
                  <span className="text-green-600 text-sm">✓ Активно</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Transaction Modal */}
      <AnimatePresence>
        {showTransactionModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowTransactionModal(false)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }} className="bg-white rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Нова транзакция</h2>
              <form className="space-y-4">
                <div><span className="text-gray-500 text-sm">Тип</span>
                  <div className="flex gap-2 mt-1">
                    {['income', 'expense', 'transfer'].map(type => (
                      <button key={type} type="button" className={`flex-1 py-2 rounded-lg font-medium border ${type === 'income' ? 'bg-green-50 text-green-700 border-green-200' : type === 'expense' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-blue-50 text-blue-700 border-blue-200'}`}>
                        {type === 'income' ? '↓ Приход' : type === 'expense' ? '↑ Разход' : '↔ Трансфер'}
                      </button>
                    ))}
                  </div>
                </div>
                <div><label className="text-gray-500 text-sm">Описание <input type="text" className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200" placeholder="Напр. Доставка" /></label></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-500 text-sm">Сума <input type="number" className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200" placeholder="0.00" /></label></div>
                  <div><label className="text-gray-500 text-sm">Дата <input type="date" defaultValue={new Date().toISOString().split('T')[0]} className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200" /></label></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-500 text-sm">Категория <select className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200">{budgets.map(b => <option key={b.id}>{b.icon} {b.category}</option>)}</select></label>
                  </div>
                  <div><label className="text-gray-500 text-sm">Сметка <select className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200">{accounts.map(a => <option key={a.id}>{a.name}</option>)}</select></label>
                  </div>
                </div>
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={() => setShowTransactionModal(false)} className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Отказ</button>
                  <button type="submit" className="flex-1 py-3 bg-blue-600 text-gray-900 rounded-xl hover:bg-blue-700">Създай</button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Invoice Modal */}
      <AnimatePresence>
        {showInvoiceModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowInvoiceModal(false)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }} className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Нова фактура</h2>
              <form className="space-y-4">
                <div className="flex gap-4">
                  <div className="flex-1"><span className="text-gray-500 text-sm">Тип</span>
                    <div className="flex gap-2 mt-1">
                      <button type="button" className="flex-1 py-2 bg-green-50 text-green-700 border border-green-200 rounded-lg">← Вземане</button>
                      <button type="button" className="flex-1 py-2 bg-gray-50 text-gray-500 border border-gray-200 rounded-lg">→ Задължение</button>
                    </div>
                  </div>
                  <div className="w-40"><label className="text-gray-500 text-sm">Номер <input type="text" className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200" placeholder="INV-2025-XXX" /></label></div>
                </div>
                <div><label className="text-gray-500 text-sm">Клиент / Доставчик <input type="text" className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200" placeholder="Име на фирма" /></label></div>
                <div className="grid grid-cols-3 gap-4">
                  <div><label className="text-gray-500 text-sm">Дата <input type="date" defaultValue={new Date().toISOString().split('T')[0]} className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200" /></label></div>
                  <div><label className="text-gray-500 text-sm">Падеж <input type="date" className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200" /></label></div>
                  <div><label className="text-gray-500 text-sm">Условия <select className="w-full mt-1 px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-200"><option>Нето 7 дни</option><option>Нето 14 дни</option><option>Нето 30 дни</option></select></label>
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex justify-between text-gray-600 mb-2"><span>Сума без ДДС:</span><span>0.00 лв</span></div>
                  <div className="flex justify-between text-gray-600 mb-2"><span>ДДС:</span><span>0.00 лв</span></div>
                  <div className="flex justify-between text-gray-900 font-bold text-lg pt-2 border-t border-gray-200"><span>Общо:</span><span>0.00 лв</span></div>
                </div>
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={() => setShowInvoiceModal(false)} className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Отказ</button>
                  <button type="button" className="flex-1 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300">Чернова</button>
                  <button type="submit" className="flex-1 py-3 bg-blue-600 text-gray-900 rounded-xl hover:bg-blue-700">Създай и изпрати</button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Transaction Detail Modal */}
      <AnimatePresence>
        {selectedTransaction && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedTransaction(null)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }} className="bg-white rounded-2xl p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Детайли на транзакция</h2>
                <button onClick={() => setSelectedTransaction(null)} className="text-gray-400 hover:text-gray-600">✕</button>
              </div>
              <div className="space-y-4">
                <div className={`text-center p-4 rounded-xl ${selectedTransaction.type === 'income' ? 'bg-green-50' : selectedTransaction.type === 'expense' ? 'bg-red-50' : 'bg-blue-50'}`}>
                  <div className={`text-3xl font-bold ${selectedTransaction.type === 'income' ? 'text-green-600' : selectedTransaction.type === 'expense' ? 'text-red-600' : 'text-blue-600'}`}>
                    {selectedTransaction.type === 'income' ? '+' : selectedTransaction.type === 'expense' ? '-' : ''}{selectedTransaction.amount.toLocaleString()} лв
                  </div>
                  <div className="text-gray-600 mt-1">{selectedTransaction.description}</div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><div className="text-gray-500 text-xs">Дата</div><div className="text-gray-900">{selectedTransaction.date}</div></div>
                  <div><div className="text-gray-500 text-xs">Статус</div><span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(selectedTransaction.status)}`}>{getStatusLabel(selectedTransaction.status)}</span></div>
                  <div><div className="text-gray-500 text-xs">Категория</div><div className="text-gray-900 flex items-center gap-1">{getCategoryIcon(selectedTransaction.category)} {selectedTransaction.category}</div></div>
                  <div><div className="text-gray-500 text-xs">Сметка</div><div className="text-gray-900">{selectedTransaction.account}</div></div>
                </div>
                {selectedTransaction.vendor && <div><div className="text-gray-500 text-xs">Доставчик</div><div className="text-gray-900">{selectedTransaction.vendor}</div></div>}
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setSelectedTransaction(null)} className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">Затвори</button>
                <button className="flex-1 py-3 bg-blue-600 text-gray-900 rounded-xl hover:bg-blue-700">✏️ Редактирай</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Invoice Detail Modal */}
      <AnimatePresence>
        {selectedInvoice && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedInvoice(null)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }} className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedInvoice.number}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(selectedInvoice.status)}`}>{getStatusLabel(selectedInvoice.status)}</span>
                    <span className={`text-sm ${selectedInvoice.type === 'receivable' ? 'text-green-600' : 'text-orange-600'}`}>{selectedInvoice.type === 'receivable' ? '← Вземане' : '→ Задължение'}</span>
                  </div>
                </div>
                <button onClick={() => setSelectedInvoice(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
              </div>
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div><div className="text-gray-500 text-sm">Клиент / Доставчик</div><div className="text-gray-900 text-lg">{selectedInvoice.customer_vendor}</div></div>
                <div className="text-right"><div className="text-gray-500 text-sm">Сума</div><div className="text-gray-900 text-2xl font-bold">{selectedInvoice.total.toLocaleString()} {selectedInvoice.currency}</div></div>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
                <div><div className="text-gray-500 text-xs">Издадена</div><div className="text-gray-900">{selectedInvoice.issue_date}</div></div>
                <div><div className="text-gray-500 text-xs">Падеж</div><div className={selectedInvoice.status === 'overdue' ? 'text-red-600' : 'text-gray-900'}>{selectedInvoice.due_date}</div></div>
                <div><div className="text-gray-500 text-xs">Условия</div><div className="text-gray-900">{selectedInvoice.payment_terms}</div></div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <div className="flex justify-between text-gray-600 mb-2"><span>Сума без ДДС:</span><span>{(selectedInvoice.subtotal || 0).toFixed(2)} лв</span></div>
                <div className="flex justify-between text-gray-600 mb-2"><span>ДДС:</span><span>{(selectedInvoice.tax_amount || 0).toFixed(2)} лв</span></div>
                <div className="flex justify-between text-gray-900 font-bold text-lg pt-2 border-t border-gray-200"><span>Общо:</span><span>{(selectedInvoice.total || 0).toFixed(2)} лв</span></div>
              </div>
              <div className="flex gap-3">
                <button className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">📥 PDF</button>
                <button className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">✉️ Email</button>
                {['sent', 'viewed', 'overdue'].includes(selectedInvoice.status) && (
                  <button onClick={() => { handleMarkInvoicePaid(selectedInvoice.id); setSelectedInvoice(null); }} className="flex-1 py-3 bg-green-600 text-gray-900 rounded-xl hover:bg-green-700">✓ Платена</button>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Vendor Detail Modal */}
      <AnimatePresence>
        {selectedVendor && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedVendor(null)}>
            <motion.div initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }} className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-gray-900 text-2xl font-bold">{selectedVendor.name.charAt(0)}</div>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">{selectedVendor.name}</h2>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(selectedVendor.status)}`}>{getStatusLabel(selectedVendor.status)}</span>
                      <span className="text-yellow-500">★ {(selectedVendor.rating || 0).toFixed(1)}</span>
                    </div>
                  </div>
                </div>
                <button onClick={() => setSelectedVendor(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div><div className="text-gray-500 text-sm">Контакт</div><div className="text-gray-900">{selectedVendor.contact_person}</div></div>
                  <div><div className="text-gray-500 text-sm">Email</div><div className="text-gray-900">{selectedVendor.email}</div></div>
                  <div><div className="text-gray-500 text-sm">Телефон</div><div className="text-gray-900">{selectedVendor.phone}</div></div>
                  <div><div className="text-gray-500 text-sm">Адрес</div><div className="text-gray-900">{selectedVendor.address}</div></div>
                </div>
                <div className="space-y-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-gray-500 text-sm mb-2">Статистика</div>
                    <div className="grid grid-cols-2 gap-4">
                      <div><div className="text-2xl font-bold text-gray-900">{selectedVendor.total_orders}</div><div className="text-gray-500 text-xs">Поръчки</div></div>
                      <div><div className="text-2xl font-bold text-gray-900">{selectedVendor.total_spent.toLocaleString()} лв</div><div className="text-gray-500 text-xs">Платено</div></div>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-gray-500 text-sm mb-2">Условия</div>
                    <div className="space-y-2">
                      <div className="flex justify-between"><span className="text-gray-600">Срок</span><span className="text-gray-900">{selectedVendor.payment_terms} дни</span></div>
                      <div className="flex justify-between"><span className="text-gray-600">Лимит</span><span className="text-gray-900">{selectedVendor.credit_limit.toLocaleString()} лв</span></div>
                      <div className="flex justify-between"><span className="text-gray-600">Баланс</span><span className={selectedVendor.current_balance > 0 ? 'text-orange-600' : 'text-green-600'}>{selectedVendor.current_balance.toLocaleString()} лв</span></div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">📄 Фактури</button>
                <button className="flex-1 py-3 bg-blue-600 text-gray-900 rounded-xl hover:bg-blue-700">🛒 Нова поръчка</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
