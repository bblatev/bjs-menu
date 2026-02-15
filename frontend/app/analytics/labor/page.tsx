'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

interface LaborStats {
  total_labor_cost: number;
  avg_hourly_cost: number;
  labor_percentage: number;
  total_hours_scheduled: number;
  efficiency_score: number;
  overtime_hours: number;
  cost_by_department: { department: string; cost: number; hours: number }[];
  cost_by_day: { day: string; cost: number; revenue: number; percentage: number }[];
  shift_coverage: { shift: string; required: number; scheduled: number; efficiency: number }[];
  top_performers: { name: string; hours: number; sales_per_hour: number; efficiency: number }[];
}

interface ScheduleIssue {
  id: string;
  type: 'understaffed' | 'overstaffed' | 'overtime' | 'skill_gap' | 'conflict';
  severity: 'low' | 'medium' | 'high';
  shift: string;
  date: string;
  description: string;
  recommendation: string;
}

export default function AnalyticsLaborPage() {
  const [stats, setStats] = useState<LaborStats | null>(null);
  const [issues, setIssues] = useState<ScheduleIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedView, setSelectedView] = useState<'cost' | 'efficiency'>('cost');

  useEffect(() => {
    loadLaborData();
  }, []);

  const loadLaborData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/analytics/labor`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setStats(data.stats);
        setIssues(data.issues || []);
      } else {
        console.error('Failed to load labor analytics data');
        setStats(null);
        setIssues([]);
      }
    } catch (error) {
      console.error('Error loading labor analytics:', error);
      setStats(null);
      setIssues([]);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => `€${amount.toFixed(2)}`;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'primary';
      default: return 'surface';
    }
  };

  const getIssueIcon = (type: string) => {
    switch (type) {
      case 'understaffed': return '⚠️';
      case 'overstaffed': return '📊';
      case 'overtime': return '⏰';
      case 'skill_gap': return '🎓';
      case 'conflict': return '❌';
      default: return '📋';
    }
  };

  const getEfficiencyColor = (efficiency: number) => {
    if (efficiency >= 95) return 'success';
    if (efficiency >= 85) return 'primary';
    if (efficiency >= 75) return 'warning';
    return 'error';
  };

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
          <div className="text-6xl mb-4">👥</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Labor Data</h2>
          <p className="text-surface-600 mb-4">Unable to load labor analytics data. Please try again later.</p>
          <button
            onClick={loadLaborData}
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
          <h1 className="text-3xl font-display font-bold text-surface-900">Labor Optimization</h1>
          <p className="text-surface-500 mt-1">Staff scheduling efficiency and cost analysis</p>
        </div>
        <button className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg hover:bg-primary-600 transition-colors text-sm font-medium flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          View Schedule
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-accent-50 to-accent-100 rounded-2xl p-6 border border-accent-200"
        >
          <div className="text-accent-600 text-sm font-semibold mb-1">Labor Cost (7d)</div>
          <div className="text-3xl font-bold text-accent-900">
            {formatCurrency(stats?.total_labor_cost || 0)}
          </div>
          <div className="text-accent-600 text-xs mt-1">Total this week</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl p-6 border border-primary-200"
        >
          <div className="text-primary-600 text-sm font-semibold mb-1">Labor %</div>
          <div className="text-3xl font-bold text-primary-900">
            {stats?.labor_percentage || 0}%
          </div>
          <div className="text-primary-600 text-xs mt-1">Of revenue</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-success-50 to-success-100 rounded-2xl p-6 border border-success-200"
        >
          <div className="text-success-600 text-sm font-semibold mb-1">Efficiency Score</div>
          <div className="text-3xl font-bold text-success-900">
            {stats?.efficiency_score || 0}%
          </div>
          <div className="text-success-600 text-xs mt-1">Schedule optimization</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-warning-50 to-warning-100 rounded-2xl p-6 border border-warning-200"
        >
          <div className="text-warning-600 text-sm font-semibold mb-1">Overtime Hours</div>
          <div className="text-3xl font-bold text-warning-900">
            {stats?.overtime_hours || 0}h
          </div>
          <div className="text-warning-600 text-xs mt-1">This week</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-gradient-to-br from-error-50 to-error-100 rounded-2xl p-6 border border-error-200"
        >
          <div className="text-error-600 text-sm font-semibold mb-1">Avg Hourly Cost</div>
          <div className="text-3xl font-bold text-error-900">
            {formatCurrency(stats?.avg_hourly_cost || 0)}
          </div>
          <div className="text-error-600 text-xs mt-1">Per employee</div>
        </motion.div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Cost by Department */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
        >
          <h3 className="text-xl font-semibold text-surface-900 mb-4">Cost by Department</h3>
          <div className="space-y-4">
            {stats?.cost_by_department.map((dept, i) => {
              const totalCost = stats.cost_by_department.reduce((sum, d) => sum + d.cost, 0);
              const percentage = ((dept.cost / totalCost) * 100).toFixed(0);
              const avgHourlyRate = dept.cost / dept.hours;

              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="space-y-2"
                >
                  <div className="flex justify-between">
                    <div>
                      <span className="text-surface-900 font-medium">{dept.department}</span>
                      <div className="text-xs text-surface-500">{dept.hours}h @ {formatCurrency(avgHourlyRate)}/h</div>
                    </div>
                    <div className="text-right">
                      <div className="text-surface-900 font-bold">{formatCurrency(dept.cost)}</div>
                      <div className="text-xs text-surface-500">{percentage}%</div>
                    </div>
                  </div>
                  <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${percentage}%` }}
                      transition={{ delay: i * 0.1 }}
                      className="h-full bg-gradient-to-r from-primary-400 to-primary-500 rounded-full"
                    />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Weekly Cost & Revenue */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-surface-900">Weekly Labor %</h3>
            <span className="text-xs text-surface-500">Target: &lt;30%</span>
          </div>
          <div className="flex items-end justify-between h-48 gap-2">
            {stats?.cost_by_day.map((day, i) => {
              const percentage = day.percentage;
              const isGood = percentage < 30;
              const isOk = percentage < 35;

              return (
                <div key={i} className="flex flex-col items-center flex-1">
                  <div className="w-full flex flex-col rounded-t-sm overflow-hidden"
                    style={{ height: `${Math.min(percentage * 2, 100)}%`, minHeight: '8px' }}
                  >
                    <div
                      className={`w-full flex-1 ${
                        isGood
                          ? 'bg-gradient-to-t from-success-500 to-success-400'
                          : isOk
                          ? 'bg-gradient-to-t from-warning-500 to-warning-400'
                          : 'bg-gradient-to-t from-error-500 to-error-400'
                      }`}
                      title={`${percentage.toFixed(1)}% labor cost`}
                    />
                  </div>
                  <span className="text-xs font-medium text-surface-900 mt-2">{percentage.toFixed(1)}%</span>
                  <span className="text-xs text-surface-500 mt-0.5">{day.day}</span>
                </div>
              );
            })}
          </div>
        </motion.div>

        {/* Shift Coverage */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
        >
          <h3 className="text-xl font-semibold text-surface-900 mb-4">Shift Coverage</h3>
          <div className="space-y-4">
            {stats?.shift_coverage.map((shift, i) => {
              const efficiencyColor = getEfficiencyColor(shift.efficiency);
              const isUnder = shift.scheduled < shift.required;
              const isOver = shift.scheduled > shift.required;

              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 bg-surface-50 rounded-xl"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-surface-900">{shift.shift}</span>
                    <span className={`text-sm font-bold text-${efficiencyColor}-600`}>
                      {shift.efficiency}%
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-surface-600 mb-2">
                    <span>Required: {shift.required}</span>
                    <span>•</span>
                    <span className={
                      isUnder ? 'text-error-600 font-semibold' :
                      isOver ? 'text-warning-600 font-semibold' :
                      'text-success-600 font-semibold'
                    }>
                      Scheduled: {shift.scheduled}
                    </span>
                  </div>
                  <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${shift.efficiency}%` }}
                      transition={{ delay: i * 0.05 + 0.2 }}
                      className={`h-full rounded-full bg-${efficiencyColor}-500`}
                    />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Schedule Issues */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h3 className="text-xl font-semibold text-surface-900">Schedule Issues</h3>
          </div>
          <div className="divide-y divide-surface-100">
            {issues.map((issue, i) => {
              const severityColor = getSeverityColor(issue.severity);
              return (
                <motion.div
                  key={issue.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 hover:bg-surface-50 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-xl bg-${severityColor}-100 text-2xl`}>
                      {getIssueIcon(issue.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="font-semibold text-surface-900">{issue.description}</h4>
                          <p className="text-sm text-surface-500 mt-0.5">{issue.recommendation}</p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold bg-${severityColor}-100 text-${severityColor}-700 whitespace-nowrap`}>
                          {issue.severity.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-surface-500">
                        <span>📅 {issue.date}</span>
                        <span>⏰ {issue.shift}</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Top Performers */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100"
        >
          <h3 className="text-xl font-semibold text-surface-900 mb-4">Top Performers</h3>
          <div className="space-y-3">
            {stats?.top_performers.map((performer, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center justify-between p-3 bg-surface-50 rounded-xl hover:bg-surface-100 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1">
                  <span className="text-2xl">
                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '⭐'}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium text-surface-900">{performer.name}</div>
                    <div className="text-xs text-surface-500">
                      {performer.hours}h • {formatCurrency(performer.sales_per_hour)}/h
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold ${
                    performer.efficiency >= 90 ? 'text-success-600' :
                    performer.efficiency >= 80 ? 'text-primary-600' :
                    'text-warning-600'
                  }`}>
                    {performer.efficiency}%
                  </div>
                  <div className="text-xs text-surface-500">efficiency</div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Info Panel */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-2xl p-6 border border-primary-200"
      >
        <div className="flex items-start gap-4">
          <span className="text-3xl">💡</span>
          <div className="flex-1">
            <h4 className="font-semibold text-primary-900 mb-2">Smart Labor Optimization</h4>
            <p className="text-sm text-primary-700 leading-relaxed">
              Our AI-powered scheduling system analyzes historical sales data, foot traffic patterns, and employee
              performance to optimize shift coverage. The system identifies overstaffing, understaffing, and skill gaps
              automatically. Target labor cost is 25-30% of revenue. Monitor efficiency scores and address scheduling
              issues proactively to reduce overtime costs and improve service quality.
            </p>
          </div>
          <button className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg hover:bg-primary-600 transition-colors text-sm font-medium">
            Optimize Schedule
          </button>
        </div>
      </motion.div>
    </div>
  );
}
