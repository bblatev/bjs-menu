'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface WaitTimeData { current_wait_minutes: number; avg_wait_today: number; tables_available: number; tables_total: number; queue_length: number; estimated_next_available: string; hourly_trend: { hour: string; avg_wait: number }[]; }

export default function WaitTimesPage() {
  const [data, setData] = useState<WaitTimeData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      const result = await api.get<WaitTimeData>('/reservations/wait-times');
      setData(result);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  return (
    <AdminLayout>
      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Wait Time Transparency</h1>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : !data ? (
          <div className="text-center py-12 text-gray-500">Wait time data unavailable</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className={`text-3xl font-bold ${data.current_wait_minutes > 30 ? 'text-red-600' : data.current_wait_minutes > 15 ? 'text-yellow-600' : 'text-green-600'}`}>{data.current_wait_minutes} min</div>
                <div className="text-sm text-gray-500">Current Wait</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className="text-3xl font-bold text-gray-900 dark:text-white">{data.avg_wait_today} min</div>
                <div className="text-sm text-gray-500">Avg Today</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className="text-3xl font-bold text-gray-900 dark:text-white">{data.tables_available}/{data.tables_total}</div>
                <div className="text-sm text-gray-500">Tables Available</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
                <div className="text-3xl font-bold text-gray-900 dark:text-white">{data.queue_length}</div>
                <div className="text-sm text-gray-500">In Queue</div>
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Hourly Wait Times</h2>
              <div className="flex items-end gap-2 h-48">
                {data.hourly_trend.map((h, i) => {
                  const maxWait = Math.max(...data.hourly_trend.map(t => t.avg_wait), 1);
                  const pct = (h.avg_wait / maxWait) * 100;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center">
                      <div className="w-full rounded-t" style={{ height: `${pct}%`, backgroundColor: h.avg_wait > 30 ? '#ef4444' : h.avg_wait > 15 ? '#eab308' : '#22c55e' }} />
                      <div className="text-xs text-gray-500 mt-1">{h.hour}</div>
                      <div className="text-xs font-medium text-gray-700 dark:text-gray-300">{h.avg_wait}m</div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-700 dark:text-blue-300">
              Next table estimated: {data.estimated_next_available ? new Date(data.estimated_next_available).toLocaleTimeString() : 'Unknown'}. Auto-refreshing every 30 seconds.
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
