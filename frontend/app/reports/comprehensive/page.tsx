'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

// Types
interface ReportTab {
  key: string;
  label: string;
  icon: string;
  endpoint: string;
}

interface KPIMetric {
  name: string;
  value: number;
  target?: number;
  unit: string;
  change_percentage?: number;
  change_direction?: string;
  status: string;
}

interface DashboardKPIs {
  timestamp: string;
  period: string;
  total_revenue: KPIMetric;
  revenue_growth: KPIMetric;
  average_order_value: KPIMetric;
  total_orders: KPIMetric;
  orders_growth: KPIMetric;
  items_per_order: KPIMetric;
  food_cost_percentage: KPIMetric;
  labor_cost_percentage: KPIMetric;
  total_profit_margin: KPIMetric;
  customer_satisfaction: KPIMetric;
  average_service_rating: KPIMetric;
  returning_customers: KPIMetric;
  table_turnover: KPIMetric;
  average_prep_time: KPIMetric;
  void_percentage: KPIMetric;
  active_orders: number;
  pending_calls: number;
  low_stock_items: number;
}

export default function ComprehensiveReportsPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('kpis');
  const [period, setPeriod] = useState('week');
  const [loading, setLoading] = useState(false);
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [reportData, setReportData] = useState<any>(null);

  const tabs: ReportTab[] = [
    { key: 'kpis', label: 'Dashboard KPIs', icon: '📊', endpoint: '/api/v1/analytics/dashboard/kpis' },
    { key: 'sales', label: 'Sales Report', icon: '💰', endpoint: '/api/v1/reports/sales/detailed' },
    { key: 'labor', label: 'Labor Costs', icon: '👥', endpoint: '/api/v1/reports/labor-costs' },
    { key: 'food-cost', label: 'Food Costs', icon: '🍽️', endpoint: '/api/v1/reports/food-costs' },
    { key: 'product-mix', label: 'Product Mix', icon: '📈', endpoint: '/api/v1/reports/product-mix' },
    { key: 'server-perf', label: 'Server Performance', icon: '⭐', endpoint: '/api/v1/reports/server-performance' },
    { key: 'voids-comps', label: 'Voids & Comps', icon: '🚫', endpoint: '/api/v1/reports/voids-comps' },
    { key: 'trends', label: 'Trend Analysis', icon: '📉', endpoint: '/api/v1/reports/trends' },
  ];

  const periods = [
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: 'week', label: 'Week' },
    { value: 'month', label: 'Month' },
    { value: 'quarter', label: 'Quarter' },
    { value: 'year', label: 'Year' },
  ];

  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (!storedToken) {
      router.push('/login');
      return;
    }
    setToken(storedToken);
  }, [router]);

  useEffect(() => {
    if (token) {
      fetchReportData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, period, token]);

  const fetchReportData = async () => {
    if (!token) return;
    setLoading(true);

    try {
      const currentTab = tabs.find(t => t.key === activeTab);
      if (!currentTab) return;

      const url = activeTab === 'kpis'
        ? `${API_URL}${currentTab.endpoint}`
        : `${API_URL}${currentTab.endpoint}?period=${period}`;

      const res = await fetch(url, {
        credentials: 'include',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        if (activeTab === 'kpis') {
          setKpis(data);
        } else {
          setReportData(data);
        }
      } else {
        console.error('Failed to fetch report data');
      }
    } catch (err) {
      console.error('Error fetching report data:', err);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (format: 'pdf' | 'excel' | 'csv') => {
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/reports/export/${activeTab}`, {
        credentials: 'include',
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          report_type: activeTab,
          format: format,
          period: period
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${activeTab}_report_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (err) {
      console.error('Error exporting report:', err);
    }
  };

  const formatValue = (metric: KPIMetric) => {
    if (metric.unit === '%') {
      return `${(metric.value || 0).toFixed(1)}${metric.unit}`;
    } else if (metric.unit === 'лв') {
      return `${(metric.value || 0).toFixed(2)} ${metric.unit}`;
    } else {
      return `${(metric.value || 0).toFixed(0)}${metric.unit}`;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'bg-green-500/20 border-green-500/30';
      case 'warning': return 'bg-yellow-500/20 border-yellow-500/30';
      case 'critical': return 'bg-red-500/20 border-red-500/30';
      default: return 'bg-blue-500/20 border-blue-500/30';
    }
  };

  const getStatusTextColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-400';
      case 'warning': return 'text-yellow-400';
      case 'critical': return 'text-red-400';
      default: return 'text-blue-400';
    }
  };

  const renderKPIDashboard = () => {
    if (!kpis) return null;

    const mainKPIs = [
      kpis.total_revenue,
      kpis.revenue_growth,
      kpis.total_orders,
      kpis.average_order_value,
      kpis.orders_growth,
      kpis.items_per_order,
    ];

    const costKPIs = [
      kpis.food_cost_percentage,
      kpis.labor_cost_percentage,
      kpis.total_profit_margin,
    ];

    const qualityKPIs = [
      kpis.customer_satisfaction,
      kpis.average_service_rating,
      kpis.returning_customers,
    ];

    const operationalKPIs = [
      kpis.table_turnover,
      kpis.average_prep_time,
      kpis.void_percentage,
    ];

    return (
      <div className="space-y-6">
        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-orange-500/20 to-orange-600/10 p-4 rounded-xl border border-orange-500/30">
            <div className="text-orange-400 text-sm font-medium mb-1">Active Orders</div>
            <div className="text-3xl font-bold text-gray-900">{kpis.active_orders}</div>
          </div>
          <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 p-4 rounded-xl border border-blue-500/30">
            <div className="text-blue-400 text-sm font-medium mb-1">Pending Calls</div>
            <div className="text-3xl font-bold text-gray-900">{kpis.pending_calls}</div>
          </div>
          <div className="bg-gradient-to-br from-red-500/20 to-red-600/10 p-4 rounded-xl border border-red-500/30">
            <div className="text-red-400 text-sm font-medium mb-1">Low Stock Items</div>
            <div className="text-3xl font-bold text-gray-900">{kpis.low_stock_items}</div>
          </div>
        </div>

        {/* Main KPIs */}
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-4">Revenue & Volume Metrics</h3>
          <div className="grid grid-cols-3 gap-4">
            {mainKPIs.map((metric, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-4 rounded-xl border ${getStatusColor(metric.status)}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="text-gray-600 text-sm font-medium">{metric.name}</div>
                  {metric.change_percentage !== undefined && (
                    <span className={`text-xs font-bold px-2 py-1 rounded-full ${
                      metric.change_direction === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {metric.change_direction === 'up' ? '↑' : '↓'} {(Math.abs(metric.change_percentage) || 0).toFixed(1)}%
                    </span>
                  )}
                </div>
                <div className={`text-2xl font-bold ${getStatusTextColor(metric.status)}`}>
                  {formatValue(metric)}
                </div>
                {metric.target !== undefined && (
                  <div className="text-xs text-gray-500 mt-1">
                    Target: {formatValue({ ...metric, value: metric.target })}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Cost Metrics */}
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-4">Cost & Profitability</h3>
          <div className="grid grid-cols-3 gap-4">
            {costKPIs.map((metric, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-4 rounded-xl border ${getStatusColor(metric.status)}`}
              >
                <div className="text-gray-600 text-sm font-medium mb-2">{metric.name}</div>
                <div className={`text-2xl font-bold ${getStatusTextColor(metric.status)}`}>
                  {formatValue(metric)}
                </div>
                {metric.target !== undefined && (
                  <div className="text-xs text-gray-500 mt-1">
                    Target: {formatValue({ ...metric, value: metric.target })}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Quality Metrics */}
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-4">Customer Experience</h3>
          <div className="grid grid-cols-3 gap-4">
            {qualityKPIs.map((metric, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-4 rounded-xl border ${getStatusColor(metric.status)}`}
              >
                <div className="text-gray-600 text-sm font-medium mb-2">{metric.name}</div>
                <div className={`text-2xl font-bold ${getStatusTextColor(metric.status)}`}>
                  {formatValue(metric)}
                </div>
                {metric.target !== undefined && (
                  <div className="text-xs text-gray-500 mt-1">
                    Target: {formatValue({ ...metric, value: metric.target })}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Operational Metrics */}
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-4">Operational Efficiency</h3>
          <div className="grid grid-cols-3 gap-4">
            {operationalKPIs.map((metric, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className={`p-4 rounded-xl border ${getStatusColor(metric.status)}`}
              >
                <div className="text-gray-600 text-sm font-medium mb-2">{metric.name}</div>
                <div className={`text-2xl font-bold ${getStatusTextColor(metric.status)}`}>
                  {formatValue(metric)}
                </div>
                {metric.target !== undefined && (
                  <div className="text-xs text-gray-500 mt-1">
                    Target: {formatValue({ ...metric, value: metric.target })}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Comprehensive Reports & Analytics</h1>
              <p className="text-gray-600 mt-1">Industry-standard reporting matching Toast POS, iiko & TouchBistro</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => exportReport('pdf')}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors text-sm font-medium"
              >
                Export PDF
              </button>
              <button
                onClick={() => exportReport('excel')}
                className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors text-sm font-medium"
              >
                Export Excel
              </button>
              <Link
                href="/reports"
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm font-medium"
              >
                Back to Reports
              </Link>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map(tab => (
            <motion.button
              key={tab.key}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 whitespace-nowrap text-sm ${
                activeTab === tab.key
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </motion.button>
          ))}
        </div>

        {/* Period selector (not for KPIs) */}
        {activeTab !== 'kpis' && (
          <div className="mb-6 flex flex-wrap gap-2">
            {periods.map(p => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  period === p.value
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading report...</p>
            </div>
          </div>
        )}

        {/* Content */}
        {!loading && (
          <div>
            {activeTab === 'kpis' && renderKPIDashboard()}
            {activeTab !== 'kpis' && reportData && (
              <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
                <pre className="text-xs text-gray-700 overflow-auto">
                  {JSON.stringify(reportData, null, 2)}
                </pre>
                <p className="text-sm text-gray-600 mt-4">
                  This report is now fetching real data from the backend.
                  The frontend UI components for this specific report type are ready for styling.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
