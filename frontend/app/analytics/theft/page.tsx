'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

interface TheftAlert {
  id: string;
  timestamp: string;
  type: 'void' | 'discount' | 'refund' | 'cash_variance' | 'inventory' | 'suspicious_pattern';
  severity: 'low' | 'medium' | 'high' | 'critical';
  employee: string;
  description: string;
  amount?: number;
  details: string;
  status: 'new' | 'reviewed' | 'resolved' | 'dismissed';
}

interface TheftStats {
  total_alerts: number;
  critical_alerts: number;
  total_risk_amount: number;
  patterns_detected: number;
  alerts_by_type: { type: string; count: number }[];
  alerts_by_employee: { employee: string; count: number; risk_score: number }[];
  daily_alerts: { date: string; count: number }[];
}

export default function AnalyticsTheftPage() {
  const [alerts, setAlerts] = useState<TheftAlert[]>([]);
  const [stats, setStats] = useState<TheftStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    loadTheftData();
  }, []);

  const loadTheftData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/theft`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setAlerts(data.alerts || []);
        setStats(data.stats);
      } else {
        console.error('Failed to load theft detection data');
        setAlerts([]);
        setStats(null);
      }
    } catch (error) {
      console.error('Error loading theft detection data:', error);
      setAlerts([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => `€${amount.toFixed(2)}`;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'accent';
      case 'low': return 'primary';
      default: return 'surface';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'void': return '🗑️';
      case 'discount': return '💸';
      case 'refund': return '↩️';
      case 'cash_variance': return '💰';
      case 'inventory': return '📦';
      case 'suspicious_pattern': return '🔍';
      default: return '⚠️';
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    if (filterSeverity !== 'all' && alert.severity !== filterSeverity) return false;
    if (filterType !== 'all' && alert.type !== filterType) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🛡️</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Theft Detection Data</h2>
          <p className="text-surface-600 mb-4">Unable to load theft detection data. Please try again later.</p>
          <button
            onClick={loadTheftData}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/analytics" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-display font-bold text-surface-900">Theft Detection</h1>
          <p className="text-surface-500 mt-1">AI-powered anomaly detection and fraud prevention</p>
        </div>
        <button className="px-4 py-2 bg-error-500 text-gray-900 rounded-lg hover:bg-error-600 transition-colors text-sm font-medium flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Generate Report
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-error-50 to-error-100 rounded-2xl p-6 border border-error-200"
        >
          <div className="text-error-600 text-sm font-semibold mb-1">Critical Alerts</div>
          <div className="text-3xl font-bold text-error-900">
            {stats?.critical_alerts || 0}
          </div>
          <div className="text-error-600 text-xs mt-1">Require immediate action</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-warning-50 to-warning-100 rounded-2xl p-6 border border-warning-200"
        >
          <div className="text-warning-600 text-sm font-semibold mb-1">Total Alerts (7d)</div>
          <div className="text-3xl font-bold text-warning-900">
            {stats?.total_alerts || 0}
          </div>
          <div className="text-warning-600 text-xs mt-1">Past 7 days</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-accent-50 to-accent-100 rounded-2xl p-6 border border-accent-200"
        >
          <div className="text-accent-600 text-sm font-semibold mb-1">Risk Amount</div>
          <div className="text-3xl font-bold text-accent-900">
            {formatCurrency(stats?.total_risk_amount || 0)}
          </div>
          <div className="text-accent-600 text-xs mt-1">Potential loss</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-6 border border-primary-200"
        >
          <div className="text-primary-600 text-sm font-semibold mb-1">Patterns Detected</div>
          <div className="text-3xl font-bold text-primary-900">
            {stats?.patterns_detected || 0}
          </div>
          <div className="text-primary-600 text-xs mt-1">Suspicious patterns</div>
        </motion.div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-surface-100">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-surface-700">Filter:</span>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-4 py-2 border border-surface-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-surface-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Types</option>
            <option value="void">Voids</option>
            <option value="discount">Discounts</option>
            <option value="refund">Refunds</option>
            <option value="cash_variance">Cash Variance</option>
            <option value="inventory">Inventory</option>
            <option value="suspicious_pattern">Suspicious Patterns</option>
          </select>
          <div className="flex-1" />
          <span className="text-sm text-surface-500">
            {filteredAlerts.length} alert{filteredAlerts.length !== 1 ? 's' : ''} shown
          </span>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Alerts List */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h3 className="text-xl font-semibold text-surface-900">Recent Alerts</h3>
          </div>
          <div className="divide-y divide-surface-100 max-h-[600px] overflow-y-auto">
            {filteredAlerts.map((alert, i) => {
              const color = getSeverityColor(alert.severity);
              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 hover:bg-surface-50 transition-colors cursor-pointer"
                >
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-xl bg-${color}-100 text-2xl`}>
                      {getTypeIcon(alert.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="font-semibold text-surface-900">{alert.description}</h4>
                          <p className="text-sm text-surface-500 mt-0.5">{alert.details}</p>
                        </div>
                        {alert.amount && (
                          <div className={`text-lg font-bold text-${color}-600 whitespace-nowrap`}>
                            {formatCurrency(alert.amount)}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-3">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold bg-${color}-100 text-${color}-700`}>
                          {alert.severity.toUpperCase()}
                        </span>
                        <span className="text-xs text-surface-500">👤 {alert.employee}</span>
                        <span className="text-xs text-surface-500">🕐 {alert.timestamp}</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          alert.status === 'new'
                            ? 'bg-primary-100 text-primary-700'
                            : alert.status === 'reviewed'
                            ? 'bg-warning-100 text-warning-700'
                            : alert.status === 'resolved'
                            ? 'bg-success-100 text-success-700'
                            : 'bg-surface-200 text-surface-700'
                        }`}>
                          {alert.status}
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Side Panels */}
        <div className="space-y-6">
          {/* Alerts by Type */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
          >
            <h3 className="text-xl font-semibold text-surface-900 mb-4">Alerts by Type</h3>
            <div className="space-y-3">
              {stats?.alerts_by_type.map((item, i) => {
                const total = stats.alerts_by_type.reduce((sum, t) => sum + t.count, 0);
                const percentage = ((item.count / total) * 100).toFixed(0);
                return (
                  <div key={i} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-surface-700 font-medium">{item.type}</span>
                      <span className="text-surface-900 font-semibold">{item.count}</span>
                    </div>
                    <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        transition={{ delay: i * 0.1 }}
                        className="h-full bg-gradient-to-r from-error-400 to-error-500 rounded-full"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>

          {/* Risk Score by Employee */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
          >
            <h3 className="text-xl font-semibold text-surface-900 mb-4">Risk Score by Employee</h3>
            <div className="space-y-3">
              {stats?.alerts_by_employee.map((emp, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 bg-surface-50 rounded-xl"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-surface-900">{emp.employee}</span>
                    <span className={`text-sm font-bold ${
                      emp.risk_score >= 80 ? 'text-error-600' :
                      emp.risk_score >= 60 ? 'text-warning-600' :
                      emp.risk_score >= 40 ? 'text-accent-600' :
                      'text-success-600'
                    }`}>
                      {emp.risk_score}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-surface-200 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${emp.risk_score}%` }}
                        transition={{ delay: i * 0.05 + 0.2 }}
                        className={`h-full rounded-full ${
                          emp.risk_score >= 80 ? 'bg-error-500' :
                          emp.risk_score >= 60 ? 'bg-warning-500' :
                          emp.risk_score >= 40 ? 'bg-accent-500' :
                          'bg-success-500'
                        }`}
                      />
                    </div>
                    <span className="text-xs text-surface-500 w-16 text-right">{emp.count} alerts</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Weekly Trend */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
          >
            <h3 className="text-xl font-semibold text-surface-900 mb-4">Weekly Trend</h3>
            <div className="flex items-end justify-between h-32 gap-2">
              {stats?.daily_alerts.map((day, i) => {
                const maxCount = Math.max(...(stats.daily_alerts.map(d => d.count) || [1]));
                const percentage = (day.count / maxCount) * 100;
                return (
                  <div key={i} className="flex flex-col items-center flex-1">
                    <div
                      className="w-full bg-gradient-to-t from-warning-500 to-warning-400 rounded-t-sm"
                      style={{
                        height: `${percentage}%`,
                        minHeight: day.count > 0 ? '8px' : '0px',
                      }}
                      title={`${day.count} alerts`}
                    />
                    <span className="text-xs text-surface-500 mt-2">{day.date}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Info Panel */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-2xl p-6 border border-primary-200"
      >
        <div className="flex items-start gap-4">
          <span className="text-3xl">🛡️</span>
          <div className="flex-1">
            <h4 className="font-semibold text-primary-900 mb-2">AI-Powered Theft Detection</h4>
            <p className="text-sm text-primary-700 leading-relaxed">
              Our advanced machine learning algorithms analyze transaction patterns, employee behavior,
              inventory movements, and cash handling in real-time. The system flags anomalies and suspicious
              activities automatically, helping you prevent losses before they escalate. Review alerts regularly
              and investigate high-risk patterns to maintain security and accountability.
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
