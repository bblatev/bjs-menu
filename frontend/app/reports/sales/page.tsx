'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { API_URL } from '@/lib/api';

interface DailySale {
  date: string;
  revenue: number;
  orders: number;
  avgTicket: number;
}

interface TopItem {
  name: string;
  quantity: number;
  revenue: number;
  percentage: number;
}

interface CategoryBreakdown {
  category: string;
  revenue: number;
  orders: number;
  percentage: number;
}

interface RevenueByTime {
  time: string;
  revenue: number;
  orders: number;
  percentage: number;
}

interface SalesStats {
  label: string;
  value: string;
  subvalue: string;
  change: string;
  up: boolean;
  color: string;
}

interface SalesReportData {
  stats: SalesStats[];
  dailySales: DailySale[];
  topItems: TopItem[];
  categoryBreakdown: CategoryBreakdown[];
  revenueByTime: RevenueByTime[];
}

const statColorClass: Record<string, string> = {
  green: 'text-green-600',
  red: 'text-red-600',
  blue: 'text-blue-600',
  yellow: 'text-yellow-600',
  purple: 'text-purple-600',
  orange: 'text-orange-600',
  primary: 'text-primary-600',
  success: 'text-success-600',
  error: 'text-error-600',
  warning: 'text-warning-600',
  accent: 'text-accent-600',
  surface: 'text-surface-600',
};

export default function ReportsSalesPage() {
  const [dateRange, setDateRange] = useState('week');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<SalesReportData | null>(null);

  useEffect(() => {
    loadSalesReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange, startDate, endDate]);

  const loadSalesReport = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      let url = `${API_URL}/reports/sales?period=${dateRange}`;

      if (startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
      }

      const response = await fetch(url, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setData(await response.json());
      } else {
        console.error('Failed to load sales report');
        setData(null);
      }
    } catch (error) {
      console.error('Error loading sales report:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const maxRevenue = data?.dailySales ? Math.max(...data.dailySales.map(d => d.revenue)) : 0;

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
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Sales Data</h2>
          <p className="text-surface-600 mb-4">Unable to load sales report. Please try again later.</p>
          <button
            onClick={loadSalesReport}
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
            <h1 className="text-3xl font-display font-bold text-surface-900">Sales Reports</h1>
            <p className="text-surface-500 mt-1">Revenue analytics and sales performance</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-surface-700 mb-2">Date Range</label>
            <div className="flex gap-2">
              {['today', 'week', 'month', 'quarter'].map((range) => (
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
            <label className="block text-sm font-medium text-surface-700 mb-2">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-surface-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-2">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-surface-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <button className="px-6 py-2 bg-accent-500 text-gray-900 rounded-lg hover:bg-accent-600 transition-colors font-medium">
            Export PDF
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
              {stat.change && (
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  stat.up ? 'bg-success-50 text-success-700' : 'bg-error-50 text-error-700'
                }`}>
                  {stat.change}
                </span>
              )}
            </div>
            <p className={`text-2xl font-display font-bold ${statColorClass[stat.color] || 'text-gray-600'}`}>{stat.value}</p>
            <p className="text-xs text-surface-500 mt-1">{stat.subvalue}</p>
          </motion.div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Daily Revenue Chart */}
        <div className="col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-surface-100">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-surface-900">Daily Revenue Trend</h2>
            <div className="flex gap-2">
              <button className="px-3 py-1.5 text-xs font-medium bg-primary-50 text-primary-700 rounded-lg">
                Revenue
              </button>
              <button className="px-3 py-1.5 text-xs font-medium text-surface-600 hover:bg-surface-50 rounded-lg">
                Orders
              </button>
            </div>
          </div>
          <div className="space-y-3">
            {(data.dailySales || []).map((day, i) => {
              const barWidth = (day.revenue / maxRevenue) * 100;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="space-y-1"
                >
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-surface-600 font-medium">
                      {new Date(day.date).toLocaleDateString('bg-BG', { weekday: 'short', day: 'numeric', month: 'short' })}
                    </span>
                    <span className="text-surface-900 font-semibold">{day.revenue.toLocaleString()} лв</span>
                  </div>
                  <div className="relative h-8 bg-surface-100 rounded-lg overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${barWidth}%` }}
                      transition={{ duration: 0.5, delay: i * 0.05 }}
                      className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-500 to-primary-400 rounded-lg flex items-center justify-end pr-3"
                    >
                      <span className="text-xs font-medium text-gray-900">{day.orders} orders</span>
                    </motion.div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100">
          <h2 className="text-lg font-semibold text-surface-900 mb-6">Revenue by Category</h2>
          <div className="space-y-4">
            {(data.categoryBreakdown || []).map((cat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                className="space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-surface-700">{cat.category}</span>
                  <span className="text-sm font-semibold text-surface-900">{cat.percentage}%</span>
                </div>
                <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${cat.percentage}%` }}
                    transition={{ duration: 0.6, delay: i * 0.05 }}
                    className={`h-full rounded-full ${
                      i === 0 ? 'bg-success-500' :
                      i === 1 ? 'bg-primary-500' :
                      i === 2 ? 'bg-accent-500' :
                      i === 3 ? 'bg-warning-500' : 'bg-error-500'
                    }`}
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-surface-500">
                  <span>{cat.orders} orders</span>
                  <span>{cat.revenue.toLocaleString()} лв</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Tables Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Selling Items */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Top Selling Items</h2>
          </div>
          <div className="p-4">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-100">
                  <th className="text-left py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">#</th>
                  <th className="text-left py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">Item</th>
                  <th className="text-right py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">Qty</th>
                  <th className="text-right py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {(data.topItems || []).map((item, i) => (
                  <motion.tr
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="border-b border-surface-50 hover:bg-surface-50 transition-colors"
                  >
                    <td className="py-3 px-2 text-surface-400 font-medium">{i + 1}</td>
                    <td className="py-3 px-2">
                      <div>
                        <p className="text-sm font-medium text-surface-900">{item.name}</p>
                        <p className="text-xs text-surface-500">{item.percentage}% of sales</p>
                      </div>
                    </td>
                    <td className="text-right py-3 px-2 text-sm font-semibold text-surface-700">{item.quantity}</td>
                    <td className="text-right py-3 px-2 text-sm font-bold text-success-600">
                      {item.revenue.toLocaleString()} лв
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Revenue by Time Period */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Revenue by Time of Day</h2>
          </div>
          <div className="p-4">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-100">
                  <th className="text-left py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">Time</th>
                  <th className="text-right py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">Orders</th>
                  <th className="text-right py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">Revenue</th>
                  <th className="text-right py-3 px-2 text-xs font-semibold uppercase tracking-wider text-surface-500">%</th>
                </tr>
              </thead>
              <tbody>
                {(data.revenueByTime || []).map((period, i) => (
                  <motion.tr
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="border-b border-surface-50 hover:bg-surface-50 transition-colors"
                  >
                    <td className="py-3 px-2">
                      <span className="text-sm font-medium text-surface-900">{period.time}</span>
                    </td>
                    <td className="text-right py-3 px-2 text-sm text-surface-700">{period.orders}</td>
                    <td className="text-right py-3 px-2 text-sm font-bold text-primary-600">
                      {period.revenue.toLocaleString()} лв
                    </td>
                    <td className="text-right py-3 px-2">
                      <span className="text-xs font-medium px-2 py-1 bg-primary-50 text-primary-700 rounded-full">
                        {period.percentage}%
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
