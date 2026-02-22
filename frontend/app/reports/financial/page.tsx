'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { API_URL } from '@/lib/api';

interface ExpenseCategory {
  category: string;
  amount: number;
  percentage: number;
  change: number;
}

interface FinancialStat {
  label: string;
  value: string;
  subvalue: string;
  change: string;
  up: boolean;
  color: string;
}

interface RevenueStream {
  source: string;
  amount: number;
  percentage: number;
  change: number;
}

interface MonthlyPL {
  month: string;
  revenue: number;
  expenses: number;
  profit: number;
}

interface CashFlowItem {
  item: string;
  amount: number;
  type: 'positive' | 'negative';
}

interface FinancialReportData {
  stats: FinancialStat[];
  revenueStreams: RevenueStream[];
  expenseCategories: ExpenseCategory[];
  monthlyPL: MonthlyPL[];
  cashFlow: CashFlowItem[];
  netProfit: number;
}

export default function ReportsFinancialPage() {
  const [dateRange, setDateRange] = useState('month');
  const [viewType, setViewType] = useState('summary');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<FinancialReportData | null>(null);

  useEffect(() => {
    loadFinancialReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const loadFinancialReport = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/financial/reports/financial?range=${dateRange}`, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setData(await response.json());
      } else {
        console.error('Failed to load financial report');
        setData(null);
      }
    } catch (error) {
      console.error('Error loading financial report:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const maxRevenue = data?.monthlyPL ? Math.max(...data.monthlyPL.map(m => m.revenue)) : 0;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">💰</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Financial Data</h2>
          <p className="text-surface-600 mb-4">Unable to load financial report. Please try again later.</p>
          <button
            onClick={loadFinancialReport}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/reports" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-3xl font-display font-bold text-surface-900">Financial Reports</h1>
            <p className="text-surface-500 mt-1">P&L statements, cash flow, and expenses</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-surface-700 mb-2">Period</label>
            <div className="flex gap-2">
              {['month', 'quarter', 'year'].map((range) => (
                <button
                  key={range}
                  onClick={() => setDateRange(range)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    dateRange === range
                      ? 'bg-primary-500 text-gray-900 shadow-sm'
                      : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                  }`}
                >
                  {range.charAt(0).toUpperCase() + range.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-2">View</label>
            <div className="flex gap-2">
              {['summary', 'detailed'].map((view) => (
                <button
                  key={view}
                  onClick={() => setViewType(view)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    viewType === view
                      ? 'bg-accent-500 text-gray-900 shadow-sm'
                      : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                  }`}
                >
                  {view.charAt(0).toUpperCase() + view.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <button className="px-6 py-2 bg-success-500 text-gray-900 rounded-lg hover:bg-success-600 transition-colors font-medium">
            Export P&L
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        {(data.stats || []).map((stat, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">{stat.label}</p>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                stat.up ? 'bg-success-50 text-success-700' : 'bg-error-50 text-error-700'
              }`}>
                {stat.change}
              </span>
            </div>
            <p className={`text-2xl font-display font-bold text-${stat.color}-600`}>{stat.value}</p>
            <p className="text-xs text-surface-500 mt-1">{stat.subvalue}</p>
          </motion.div>
        ))}
      </div>

      {/* P&L Statement */}
      <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
          <h2 className="font-semibold text-surface-900">Profit & Loss Statement</h2>
        </div>
        <div className="p-6">
          <div className="space-y-6">
            {/* Revenue Section */}
            <div>
              <h3 className="text-sm font-semibold text-surface-700 mb-3">Revenue</h3>
              <div className="space-y-2">
                {(data.revenueStreams || []).map((stream, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center justify-between py-2 px-3 bg-surface-50 rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-surface-900">{stream.source}</span>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            stream.change >= 0 ? 'bg-success-50 text-success-700' : 'bg-error-50 text-error-700'
                          }`}>
                            {stream.change >= 0 ? '+' : ''}{stream.change}%
                          </span>
                          <span className="text-sm font-bold text-success-600 min-w-[100px] text-right">
                            {stream.amount.toLocaleString()} лв
                          </span>
                        </div>
                      </div>
                      <div className="h-1.5 bg-surface-200 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${stream.percentage}%` }}
                          transition={{ duration: 0.5, delay: i * 0.05 }}
                          className="h-full bg-success-500 rounded-full"
                        />
                      </div>
                    </div>
                  </motion.div>
                ))}
                <div className="flex items-center justify-between py-2 px-3 bg-success-50 rounded-lg mt-3">
                  <span className="text-sm font-bold text-success-900">Total Revenue</span>
                  <span className="text-lg font-bold text-success-700">
                    {(data.revenueStreams || []).reduce((sum, s) => sum + s.amount, 0).toLocaleString()} лв
                  </span>
                </div>
              </div>
            </div>

            {/* Expenses Section */}
            <div>
              <h3 className="text-sm font-semibold text-surface-700 mb-3">Expenses</h3>
              <div className="space-y-2">
                {(data.expenseCategories || []).map((expense, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center justify-between py-2 px-3 bg-surface-50 rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-surface-900">{expense.category}</span>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            expense.change >= 0 ? 'bg-error-50 text-error-700' : 'bg-success-50 text-success-700'
                          }`}>
                            {expense.change >= 0 ? '+' : ''}{expense.change}%
                          </span>
                          <span className="text-sm font-bold text-error-600 min-w-[100px] text-right">
                            {expense.amount.toLocaleString()} лв
                          </span>
                        </div>
                      </div>
                      <div className="h-1.5 bg-surface-200 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${expense.percentage}%` }}
                          transition={{ duration: 0.5, delay: i * 0.05 }}
                          className="h-full bg-error-500 rounded-full"
                        />
                      </div>
                    </div>
                  </motion.div>
                ))}
                <div className="flex items-center justify-between py-2 px-3 bg-error-50 rounded-lg mt-3">
                  <span className="text-sm font-bold text-error-900">Total Expenses</span>
                  <span className="text-lg font-bold text-error-700">
                    {(data.expenseCategories || []).reduce((sum, e) => sum + e.amount, 0).toLocaleString()} лв
                  </span>
                </div>
              </div>
            </div>

            {/* Net Profit */}
            <div className="border-t-2 border-surface-200 pt-4">
              <div className="flex items-center justify-between py-3 px-4 bg-gradient-to-r from-primary-50 to-primary-100 rounded-xl">
                <span className="text-lg font-bold text-primary-900">Net Profit</span>
                <span className="text-2xl font-bold text-primary-700">{data.netProfit?.toLocaleString() || ((data.revenueStreams || []).reduce((sum, s) => sum + s.amount, 0) - (data.expenseCategories || []).reduce((sum, e) => sum + e.amount, 0)).toLocaleString()} лв</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Monthly Trend */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Monthly Trend</h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {(data.monthlyPL || []).map((month, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-surface-900">{month.month}</span>
                    <span className="text-sm font-bold text-primary-600">{month.profit.toLocaleString()} лв profit</span>
                  </div>
                  <div className="relative">
                    <div className="flex items-center gap-1">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(month.revenue / maxRevenue) * 60}%` }}
                        transition={{ duration: 0.5, delay: i * 0.05 }}
                        className="h-8 bg-success-500 rounded-l-lg flex items-center justify-end pr-2"
                      >
                        <span className="text-xs font-medium text-gray-900">{month.revenue.toLocaleString()}</span>
                      </motion.div>
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(month.expenses / maxRevenue) * 60}%` }}
                        transition={{ duration: 0.5, delay: i * 0.05 }}
                        className="h-8 bg-error-500 rounded-r-lg flex items-center justify-end pr-2"
                      >
                        <span className="text-xs font-medium text-gray-900">{month.expenses.toLocaleString()}</span>
                      </motion.div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-6 pt-4 border-t border-surface-100">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-success-500 rounded"></div>
                <span className="text-xs text-surface-600">Revenue</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-error-500 rounded"></div>
                <span className="text-xs text-surface-600">Expenses</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cash Flow */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Cash Flow Statement</h2>
          </div>
          <div className="p-6">
            <div className="space-y-2">
              {(data.cashFlow || []).map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className={`flex items-center justify-between py-2.5 px-3 rounded-lg ${
                    item.item.includes('Balance')
                      ? 'bg-primary-50 border border-primary-200'
                      : 'bg-surface-50'
                  }`}
                >
                  <span className={`text-sm ${
                    item.item.includes('Balance')
                      ? 'font-bold text-primary-900'
                      : 'font-medium text-surface-900'
                  }`}>
                    {item.item}
                  </span>
                  <span className={`text-sm font-bold ${
                    item.type === 'positive'
                      ? 'text-success-600'
                      : 'text-error-600'
                  }`}>
                    {item.amount >= 0 ? '' : ''}{item.amount.toLocaleString()} лв
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-gradient-to-br from-success-50 to-success-100 rounded-2xl p-6 border border-success-200"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-success-900">Revenue Growth</h3>
            <span className="text-2xl">📈</span>
          </div>
          <p className="text-3xl font-bold text-success-700">+15.2%</p>
          <p className="text-sm text-success-600 mt-2">vs. previous period</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-6 border border-primary-200"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-primary-900">Operating Ratio</h3>
            <span className="text-2xl">⚖️</span>
          </div>
          <p className="text-3xl font-bold text-primary-700">65.6%</p>
          <p className="text-sm text-primary-600 mt-2">Expenses/Revenue</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-accent-50 to-accent-100 rounded-2xl p-6 border border-accent-200"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-accent-900">Break-even Point</h3>
            <span className="text-2xl">🎯</span>
          </div>
          <p className="text-3xl font-bold text-accent-700">82,340 лв</p>
          <p className="text-sm text-accent-600 mt-2">Monthly target achieved</p>
        </motion.div>
      </div>
    </div>
  );
}
