'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/api';

interface KitchenMetrics {
  avgPrepTime: number;
  avgPrepTimeTarget: number;
  ticketsCompleted: number;
  itemsCompleted: number;
  overdueTickets: number;
  overdueRate: number;
  peakHour: string;
  busiestStation: string;
  efficiency: number;
}

interface StationPerformance {
  id: string;
  name: string;
  icon: string;
  ticketsCompleted: number;
  avgPrepTime: number;
  targetTime: number;
  overdueRate: number;
  efficiency: number;
}

interface HourlyData {
  hour: string;
  tickets: number;
  avgTime: number;
  overdue: number;
}

interface TopItem {
  name: string;
  quantity: number;
  avgPrepTime: number;
  trend: 'up' | 'down' | 'stable';
}

interface StaffPerformance {
  name: string;
  role: string;
  ticketsHandled: number;
  avgTime: number;
  rating: number;
}

interface KitchenReportData {
  metrics: KitchenMetrics;
  stationPerformance: StationPerformance[];
  hourlyData: HourlyData[];
  topItems: TopItem[];
  staffPerformance: StaffPerformance[];
}

export default function KitchenReportsPage() {
  const [dateRange, setDateRange] = useState<'today' | 'week' | 'month'>('today');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<KitchenReportData | null>(null);

  useEffect(() => {
    loadKitchenReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const loadKitchenReport = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/reports/kitchen?range=${dateRange}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setData(await response.json());
      } else {
        console.error('Failed to load kitchen report');
        setData(null);
      }
    } catch (error) {
      console.error('Error loading kitchen report:', error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const metrics = data?.metrics;
  const stationPerformance = data?.stationPerformance || [];
  const hourlyData = data?.hourlyData || [];
  const topItems = data?.topItems || [];
  const staffPerformance = data?.staffPerformance || [];

  const maxTickets = hourlyData.length > 0 ? Math.max(...hourlyData.map(h => h.tickets)) : 0;

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
          <div className="text-6xl mb-4">👨‍🍳</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">No Kitchen Data</h2>
          <p className="text-surface-600 mb-4">Unable to load kitchen report. Please try again later.</p>
          <button
            onClick={loadKitchenReport}
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/kitchen" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Kitchen Performance</h1>
            <p className="text-surface-500 mt-1">Analytics and insights for kitchen operations</p>
          </div>
        </div>
        <div className="flex gap-2">
          {(['today', 'week', 'month'] as const).map(range => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                dateRange === range
                  ? 'bg-primary-500 text-white'
                  : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
              }`}
            >
              {range.charAt(0).toUpperCase() + range.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Key Metrics */}
      {metrics && (
        <div className="grid grid-cols-5 gap-4">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-surface-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-surface-500">Avg Prep Time</span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                metrics.avgPrepTime <= metrics.avgPrepTimeTarget ? 'bg-success-100 text-success-700' : 'bg-error-100 text-error-700'
              }`}>
                Target: {metrics.avgPrepTimeTarget}m
              </span>
            </div>
            <p className="text-3xl font-display font-bold text-surface-900">{metrics.avgPrepTime}m</p>
            <p className="text-xs text-success-600 mt-1">
              {(((1 - metrics.avgPrepTime / metrics.avgPrepTimeTarget) * 100) ?? 0).toFixed(1)}% under target
            </p>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-surface-100">
            <span className="text-sm font-medium text-surface-500">Tickets Completed</span>
            <p className="text-3xl font-display font-bold text-primary-600 mt-2">{metrics.ticketsCompleted}</p>
            <p className="text-xs text-surface-500 mt-1">{metrics.itemsCompleted} items total</p>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-surface-100">
            <span className="text-sm font-medium text-surface-500">Overdue Tickets</span>
            <p className="text-3xl font-display font-bold text-error-600 mt-2">{metrics.overdueTickets}</p>
            <p className="text-xs text-error-600 mt-1">{metrics.overdueRate}% overdue rate</p>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-surface-100">
            <span className="text-sm font-medium text-surface-500">Kitchen Efficiency</span>
            <p className="text-3xl font-display font-bold text-success-600 mt-2">{metrics.efficiency}%</p>
            <p className="text-xs text-surface-500 mt-1">Based on time targets</p>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-surface-100">
            <span className="text-sm font-medium text-surface-500">Peak Hour</span>
            <p className="text-3xl font-display font-bold text-warning-600 mt-2">{metrics.peakHour.split('-')[0]}</p>
            <p className="text-xs text-surface-500 mt-1">{metrics.busiestStation}</p>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Hourly Volume Chart */}
        <div className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100">
            <h2 className="font-semibold text-surface-900">Hourly Ticket Volume</h2>
          </div>
          <div className="p-6">
            <div className="flex items-end justify-between h-48 gap-2">
              {hourlyData.map((data, i) => (
                <div key={i} className="flex-1 flex flex-col items-center">
                  <div className="w-full flex flex-col items-center gap-1">
                    {data.overdue > 0 && (
                      <span className="text-xs text-error-600 font-medium">{data.overdue}</span>
                    )}
                    <div
                      className="w-full rounded-t relative group"
                      style={{ height: `${(data.tickets / maxTickets) * 160}px` }}
                    >
                      <div className={`absolute inset-0 rounded-t ${data.overdue > 0 ? 'bg-error-400' : 'bg-primary-400'}`}
                        style={{ height: `${(data.overdue / data.tickets) * 100}%`, bottom: 0, top: 'auto' }} />
                      <div className={`absolute inset-0 rounded-t ${data.overdue > 0 ? 'bg-primary-500' : 'bg-primary-500'}`}
                        style={{ height: `${((data.tickets - data.overdue) / data.tickets) * 100}%` }} />
                      <div className="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 bg-white text-gray-900 text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                        {data.tickets} tickets, {data.avgTime}m avg
                      </div>
                    </div>
                  </div>
                  <span className="text-xs text-surface-500 mt-2">{data.hour.slice(0, 2)}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-surface-100">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-primary-500" />
                <span className="text-sm text-surface-600">On Time</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded bg-error-400" />
                <span className="text-sm text-surface-600">Overdue</span>
              </div>
            </div>
          </div>
        </div>

        {/* Top Items */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100">
            <h2 className="font-semibold text-surface-900">Top Items by Volume</h2>
          </div>
          <div className="p-4 space-y-3">
            {topItems.map((item, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-surface-100 flex items-center justify-center text-xs font-bold text-surface-600">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-surface-900 truncate">{item.name}</p>
                  <p className="text-xs text-surface-500">{item.avgPrepTime}m avg prep</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-surface-900">{item.quantity}</p>
                  <span className={`text-xs ${
                    item.trend === 'up' ? 'text-success-600' : item.trend === 'down' ? 'text-error-600' : 'text-surface-500'
                  }`}>
                    {item.trend === 'up' ? '↑' : item.trend === 'down' ? '↓' : '→'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Station Performance & Staff */}
      <div className="grid grid-cols-2 gap-6">
        {/* Station Performance */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Station Performance</h2>
            <Link href="/kitchen/stations" className="text-sm text-primary-600 hover:text-primary-700">
              Manage
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Station</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Tickets</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Avg Time</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Overdue</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-surface-500 uppercase">Efficiency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {stationPerformance.map(station => (
                  <tr key={station.id} className="hover:bg-surface-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{station.icon}</span>
                        <span className="font-medium text-surface-900">{station.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center text-surface-600">{station.ticketsCompleted}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-medium ${station.avgPrepTime <= station.targetTime ? 'text-success-600' : 'text-warning-600'}`}>
                        {station.avgPrepTime}m
                      </span>
                      <span className="text-xs text-surface-400 ml-1">/ {station.targetTime}m</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        station.overdueRate < 5 ? 'bg-success-100 text-success-700' :
                        station.overdueRate < 10 ? 'bg-warning-100 text-warning-700' :
                        'bg-error-100 text-error-700'
                      }`}>
                        {station.overdueRate}%
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-surface-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              station.efficiency >= 95 ? 'bg-success-500' :
                              station.efficiency >= 85 ? 'bg-warning-500' :
                              'bg-error-500'
                            }`}
                            style={{ width: `${station.efficiency}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-surface-700 w-12 text-right">{station.efficiency}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Staff Performance */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Staff Performance</h2>
            <Link href="/staff" className="text-sm text-primary-600 hover:text-primary-700">
              View All
            </Link>
          </div>
          <div className="divide-y divide-surface-100">
            {staffPerformance.map((staff, i) => (
              <div key={i} className="p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-lg font-bold text-primary-600">{staff.name.charAt(0)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-surface-900">{staff.name}</p>
                  <p className="text-xs text-surface-500">{staff.role}</p>
                </div>
                <div className="text-center px-4">
                  <p className="font-bold text-surface-900">{staff.ticketsHandled}</p>
                  <p className="text-xs text-surface-500">tickets</p>
                </div>
                <div className="text-center px-4">
                  <p className="font-bold text-surface-900">{staff.avgTime}m</p>
                  <p className="text-xs text-surface-500">avg time</p>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-warning-500">★</span>
                  <span className="font-bold text-surface-900">{staff.rating}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Insights */}
      <div className="bg-gradient-to-r from-primary-50 to-accent-50 rounded-2xl p-6 border border-primary-100">
        <h2 className="font-semibold text-surface-900 mb-4">Insights & Recommendations</h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white/80 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">📈</span>
              <span className="font-medium text-surface-900">Performance</span>
            </div>
            <p className="text-sm text-surface-600">
              Kitchen efficiency is at {metrics?.efficiency}%, which is above the 90% target.
              Peak hours have slightly higher overdue rates.
            </p>
          </div>
          <div className="bg-white/80 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">⚡</span>
              <span className="font-medium text-surface-900">Optimization</span>
            </div>
            <p className="text-sm text-surface-600">
              Consider adding an extra staff member during 19:00-20:00 peak hours
              to reduce overdue tickets.
            </p>
          </div>
          <div className="bg-white/80 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🎯</span>
              <span className="font-medium text-surface-900">Focus Area</span>
            </div>
            <p className="text-sm text-surface-600">
              Grill Station has the highest overdue rate at 9.5%.
              Review prep procedures for steak items.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
