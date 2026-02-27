'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';

interface StaffMember {
  id: number;
  name: string;
  role: string;
  avatar: string;
  hoursWorked: number;
  ordersServed: number;
  revenue: number;
  tips: number;
  avgOrderValue: number;
  customerRating: number;
  shiftsCompleted: number;
}

interface StaffStat {
  label: string;
  value: string;
  subvalue: string;
  color: string;
  icon: string;
}

interface ShiftDistribution {
  shift: string;
  staff: number;
  hours: number;
  avgRating: number;
}

interface PerformanceMetric {
  metric: string;
  value: number;
  color: string;
}

interface StaffReportData {
  stats: StaffStat[];
  staffMembers: StaffMember[];
  shiftDistribution: ShiftDistribution[];
  performanceMetrics: PerformanceMetric[];
}

export default function ReportsStaffPage() {
  const [dateRange, setDateRange] = useState('week');
  const [sortBy, setSortBy] = useState('revenue');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<StaffReportData | null>(null);

  useEffect(() => {
    loadStaffReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const loadStaffReport = async () => {
    setLoading(true);
    try {
      const data = await api.get<StaffReportData>(`/reports/staff?range=${dateRange}`);
      setData(data);
    } catch (error) {
      console.error('Error loading staff report:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const staffMembers = data?.staffMembers || [];

  const sortedStaff = [...staffMembers].sort((a, b) => {
    if (sortBy === 'revenue') return b.revenue - a.revenue;
    if (sortBy === 'hours') return b.hoursWorked - a.hoursWorked;
    if (sortBy === 'tips') return b.tips - a.tips;
    if (sortBy === 'rating') return b.customerRating - a.customerRating;
    return 0;
  });

  const maxRevenue = staffMembers.length > 0 ? Math.max(...staffMembers.map(s => s.revenue)) : 0;

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
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Staff Data</h2>
          <p className="text-surface-600 mb-4">Unable to load staff report. Please try again later.</p>
          <button
            onClick={loadStaffReport}
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
            <h1 className="text-3xl font-display font-bold text-surface-900">Staff Reports</h1>
            <p className="text-surface-500 mt-1">Performance metrics, hours worked, and tips</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <span className="block text-sm font-medium text-surface-700 mb-2">Date Range</span>
            <div className="flex gap-2">
              {['week', 'month', 'quarter'].map((range) => (
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
            <label className="block text-sm font-medium text-surface-700 mb-2">Sort By
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2 border border-surface-200 rounded-lg text-surface-900 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="revenue">Revenue</option>
              <option value="hours">Hours Worked</option>
              <option value="tips">Tips</option>
              <option value="rating">Rating</option>
            </select>
            </label>
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

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Staff Performance */}
        <div className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
            <h2 className="font-semibold text-surface-900">Staff Performance</h2>
          </div>
          <div className="p-4 max-h-[600px] overflow-y-auto">
            <div className="space-y-3">
              {sortedStaff.map((staff, i) => (
                <motion.div
                  key={staff.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="bg-surface-50 rounded-xl p-4 hover:bg-surface-100 transition-colors"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-gray-900 font-bold">
                      {staff.avatar}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-semibold text-surface-900">{staff.name}</h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full font-medium">
                              {staff.role}
                            </span>
                            <div className="flex items-center gap-1">
                              <span className="text-warning-500">⭐</span>
                              <span className="text-xs font-semibold text-surface-700">{staff.customerRating}</span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-success-600">{staff.revenue.toLocaleString()} лв</p>
                          <p className="text-xs text-surface-500">{staff.ordersServed} orders</p>
                        </div>
                      </div>

                      <div className="grid grid-cols-4 gap-3 mt-3">
                        <div>
                          <p className="text-xs text-surface-500">Hours</p>
                          <p className="text-sm font-semibold text-surface-900">{staff.hoursWorked}h</p>
                        </div>
                        <div>
                          <p className="text-xs text-surface-500">Shifts</p>
                          <p className="text-sm font-semibold text-surface-900">{staff.shiftsCompleted}</p>
                        </div>
                        <div>
                          <p className="text-xs text-surface-500">Tips</p>
                          <p className="text-sm font-semibold text-success-600">{staff.tips} лв</p>
                        </div>
                        <div>
                          <p className="text-xs text-surface-500">Avg Order</p>
                          <p className="text-sm font-semibold text-surface-900">{(staff.avgOrderValue || 0).toFixed(1)} лв</p>
                        </div>
                      </div>

                      {staff.revenue > 0 && (
                        <div className="mt-3">
                          <div className="h-1.5 bg-surface-200 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(staff.revenue / maxRevenue) * 100}%` }}
                              transition={{ duration: 0.5, delay: i * 0.03 }}
                              className="h-full bg-gradient-to-r from-success-500 to-success-400 rounded-full"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Shift Distribution */}
          <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
              <h2 className="font-semibold text-surface-900">Shift Distribution</h2>
            </div>
            <div className="p-4">
              <div className="space-y-4">
                {(data.shiftDistribution || []).map((shift, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-surface-900">{shift.shift}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full font-semibold">
                          {shift.staff} staff
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs text-surface-500">
                      <span>{shift.hours}h total</span>
                      <div className="flex items-center gap-1">
                        <span className="text-warning-500">⭐</span>
                        <span className="font-semibold">{shift.avgRating}</span>
                      </div>
                    </div>
                    <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(shift.hours / 892) * 100}%` }}
                        transition={{ duration: 0.5, delay: i * 0.05 }}
                        className="h-full bg-accent-500 rounded-full"
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
              <h2 className="font-semibold text-surface-900">Team Metrics</h2>
            </div>
            <div className="p-4">
              <div className="space-y-4">
                {(data.performanceMetrics || []).map((metric, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-surface-700">{metric.metric}</span>
                      <span className={`text-sm font-bold text-${metric.color}-600`}>{metric.value}%</span>
                    </div>
                    <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${metric.value}%` }}
                        transition={{ duration: 0.6, delay: i * 0.05 }}
                        className={`h-full bg-${metric.color}-500 rounded-full`}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tips Distribution */}
      <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white">
          <h2 className="font-semibold text-surface-900">Tips Distribution (This Week)</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-8 gap-3">
            {sortedStaff.slice(0, 8).map((staff, i) => {
              const maxTips = Math.max(...staffMembers.map(s => s.tips));
              const barHeight = (staff.tips / maxTips) * 100;
              return (
                <motion.div
                  key={staff.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="text-center"
                >
                  <div className="h-32 flex items-end justify-center mb-2">
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: `${barHeight}%` }}
                      transition={{ duration: 0.5, delay: i * 0.05 }}
                      className="w-full bg-gradient-to-t from-success-500 to-success-400 rounded-t-lg flex flex-col items-center justify-start pt-2"
                    >
                      <span className="text-xs font-bold text-gray-900">{staff.tips}</span>
                    </motion.div>
                  </div>
                  <div className="w-10 h-10 mx-auto rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-gray-900 text-xs font-bold mb-1">
                    {staff.avatar}
                  </div>
                  <p className="text-xs text-surface-600 font-medium truncate">{staff.name.split(' ')[0]}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
