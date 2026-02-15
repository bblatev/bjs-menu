'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { API_URL } from '@/lib/api';

interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string;
  totalSpent: number;
  totalOrders: number;
  avgOrderValue: number;
  lastVisit: string;
  loyaltyPoints: number;
  segment: 'VIP' | 'Regular' | 'New' | 'At Risk';
}

interface CustomerStat {
  label: string;
  value: string;
  subvalue: string;
  color: string;
  icon: string;
}

interface CustomerSegment {
  segment: string;
  count: number;
  percentage: number;
  avgSpent: number;
  color: string;
}

interface VisitFrequency {
  frequency: string;
  customers: number;
  percentage: number;
}

interface SpendingDistribution {
  range: string;
  customers: number;
  percentage: number;
}

interface CustomerLifetime {
  month: string;
  newCustomers: number;
  churnedCustomers: number;
}

interface CustomerReportData {
  stats: CustomerStat[];
  customers: Customer[];
  customerSegments: CustomerSegment[];
  visitFrequency: VisitFrequency[];
  spendingDistribution: SpendingDistribution[];
  customerLifetime: CustomerLifetime[];
}

export default function ReportsCustomersPage() {
  const [dateRange, setDateRange] = useState('month');
  const [segmentFilter, setSegmentFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<CustomerReportData | null>(null);

  useEffect(() => {
    loadCustomerReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const loadCustomerReport = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/reports/customers?range=${dateRange}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setData(await response.json());
      } else {
        console.error('Failed to load customer report');
        setData(null);
      }
    } catch (error) {
      console.error('Error loading customer report:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const filteredCustomers = data?.customers
    ? (segmentFilter === 'all' ? data.customers : data.customers.filter(c => c.segment === segmentFilter))
    : [];

  const getSegmentColor = (segment: string) => {
    switch (segment) {
      case 'VIP': return 'warning';
      case 'Regular': return 'primary';
      case 'New': return 'success';
      case 'At Risk': return 'error';
      default: return 'surface';
    }
  };

  const maxSpending = data?.customers ? Math.max(...data.customers.map(c => c.totalSpent)) : 0;

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
          <div className="text-6xl mb-4">👥</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Customer Data</h2>
          <p className="text-surface-600 mb-4">Unable to load customer report. Please try again later.</p>
          <button
            onClick={loadCustomerReport}
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
            <h1 className="text-3xl font-display font-bold text-surface-900">Customer Reports</h1>
            <p className="text-surface-500 mt-1">Analytics, retention, and spending patterns</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-surface-700 mb-2">Date Range</label>
            <div className="flex gap-2">
              {['week', 'month', 'quarter', 'year'].map((range) => (
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
            <label className="block text-sm font-medium text-surface-700 mb-2">Segment</label>
            <select
              value={segmentFilter}
              onChange={(e) => setSegmentFilter(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-surface-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">All Segments</option>
              <option value="VIP">VIP</option>
              <option value="Regular">Regular</option>
              <option value="New">New</option>
              <option value="At Risk">At Risk</option>
            </select>
          </div>
          <button className="px-6 py-2 bg-accent-500 text-gray-900 rounded-lg hover:bg-accent-600 transition-colors font-medium">
            Export Report
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
              <span className="text-2xl">{stat.icon}</span>
            </div>
            <p className={`text-2xl font-display font-bold text-${stat.color}-600`}>{stat.value}</p>
            <p className="text-xs text-surface-500 mt-1">{stat.subvalue}</p>
          </motion.div>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Customer List */}
        <div className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-surface-900">Top Customers</h2>
              <span className="text-sm text-surface-500">{filteredCustomers.length} customers</span>
            </div>
          </div>
          <div className="p-4 max-h-[600px] overflow-y-auto">
            <div className="space-y-3">
              {filteredCustomers.map((customer, i) => (
                <motion.div
                  key={customer.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="bg-surface-50 rounded-xl p-4 hover:bg-surface-100 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-gray-900 font-bold">
                        {customer.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <h3 className="font-semibold text-surface-900">{customer.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-surface-500">{customer.email}</span>
                          <span className="text-xs text-surface-400">•</span>
                          <span className="text-xs text-surface-500">{customer.phone}</span>
                        </div>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold bg-${getSegmentColor(customer.segment)}-50 text-${getSegmentColor(customer.segment)}-700`}>
                      {customer.segment}
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-3 mb-3">
                    <div>
                      <p className="text-xs text-surface-500">Total Spent</p>
                      <p className="text-sm font-bold text-success-600">{customer.totalSpent.toLocaleString()} лв</p>
                    </div>
                    <div>
                      <p className="text-xs text-surface-500">Orders</p>
                      <p className="text-sm font-semibold text-surface-900">{customer.totalOrders}</p>
                    </div>
                    <div>
                      <p className="text-xs text-surface-500">Avg Order</p>
                      <p className="text-sm font-semibold text-surface-900">{customer.avgOrderValue.toFixed(2)} лв</p>
                    </div>
                    <div>
                      <p className="text-xs text-surface-500">Loyalty Points</p>
                      <p className="text-sm font-semibold text-warning-600">{customer.loyaltyPoints}</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-surface-500">
                    <span>Last visit: {new Date(customer.lastVisit).toLocaleDateString('bg-BG', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                  </div>

                  <div className="mt-2">
                    <div className="h-1.5 bg-surface-200 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(customer.totalSpent / maxSpending) * 100}%` }}
                        transition={{ duration: 0.5, delay: i * 0.03 }}
                        className="h-full bg-gradient-to-r from-success-500 to-success-400 rounded-full"
                      />
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Customer Segments */}
          <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
              <h2 className="font-semibold text-surface-900">Customer Segments</h2>
            </div>
            <div className="p-4">
              <div className="space-y-4">
                {(data.customerSegments || []).map((segment, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-surface-900">{segment.segment}</span>
                      <span className="text-xs font-semibold text-surface-700">{segment.count}</span>
                    </div>
                    <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${segment.percentage}%` }}
                        transition={{ duration: 0.6, delay: i * 0.05 }}
                        className={`h-full bg-${segment.color}-500 rounded-full`}
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs text-surface-500">
                      <span>{segment.percentage}% of total</span>
                      <span className="font-semibold text-success-600">Avg: {segment.avgSpent} лв</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>

          {/* Visit Frequency */}
          <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
              <h2 className="font-semibold text-surface-900">Visit Frequency</h2>
            </div>
            <div className="p-4">
              <div className="space-y-3">
                {(data.visitFrequency || []).map((freq, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center justify-between py-2"
                  >
                    <span className="text-sm text-surface-700">{freq.frequency}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-surface-900">{freq.customers}</span>
                      <span className="text-xs text-surface-500">({freq.percentage}%)</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Analytics Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Spending Distribution */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Spending Distribution</h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {(data.spendingDistribution || []).map((dist, i) => {
                const maxCustomers = Math.max(...(data.spendingDistribution || []).map(d => d.customers));
                const barWidth = (dist.customers / maxCustomers) * 100;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="space-y-1"
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-surface-700 font-medium">{dist.range}</span>
                      <span className="text-surface-900 font-semibold">{dist.customers} customers</span>
                    </div>
                    <div className="relative h-6 bg-surface-100 rounded-lg overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${barWidth}%` }}
                        transition={{ duration: 0.5, delay: i * 0.05 }}
                        className="absolute inset-y-0 left-0 bg-gradient-to-r from-accent-500 to-accent-400 rounded-lg flex items-center justify-end pr-2"
                      >
                        <span className="text-xs font-medium text-gray-900">{dist.percentage}%</span>
                      </motion.div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Customer Lifetime */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Customer Acquisition & Churn</h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {(data.customerLifetime || []).map((lifeData, i) => {
                const maxValue = Math.max(...(data.customerLifetime || []).map(d => Math.max(d.newCustomers, d.churnedCustomers)));
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="space-y-1"
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-surface-700 font-medium w-12">{lifeData.month}</span>
                      <div className="flex-1 flex items-center gap-2">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${(lifeData.newCustomers / maxValue) * 45}%` }}
                          transition={{ duration: 0.5, delay: i * 0.05 }}
                          className="h-6 bg-success-500 rounded flex items-center justify-center"
                        >
                          <span className="text-xs font-medium text-gray-900">+{lifeData.newCustomers}</span>
                        </motion.div>
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${(lifeData.churnedCustomers / maxValue) * 45}%` }}
                          transition={{ duration: 0.5, delay: i * 0.05 }}
                          className="h-6 bg-error-500 rounded flex items-center justify-center"
                        >
                          <span className="text-xs font-medium text-gray-900">-{lifeData.churnedCustomers}</span>
                        </motion.div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
            <div className="flex items-center gap-4 mt-6 pt-4 border-t border-surface-100">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-success-500 rounded"></div>
                <span className="text-xs text-surface-600">New Customers</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-error-500 rounded"></div>
                <span className="text-xs text-surface-600">Churned</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
