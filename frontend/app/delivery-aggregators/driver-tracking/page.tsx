'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface ActiveDelivery { order_id: number; platform: string; driver_name: string; status: string; eta_minutes: number; customer_address: string; placed_at: string; items_count: number; total: number; }

export default function DriverTrackingPage() {
  const [deliveries, setDeliveries] = useState<ActiveDelivery[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      const data = await api.get<ActiveDelivery[]>('/delivery/active-deliveries');
      setDeliveries(Array.isArray(data) ? data : []);
    } catch { setDeliveries([]); }
    finally { setLoading(false); }
  }

  const statusColor = (s: string) => {
    switch (s) {
      case 'picked_up': return 'bg-blue-100 text-blue-700';
      case 'en_route': return 'bg-yellow-100 text-yellow-700';
      case 'delivered': return 'bg-green-100 text-green-700';
      case 'preparing': return 'bg-purple-100 text-purple-700';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const platformIcon = (p: string) => {
    const l = p.toLowerCase();
    if (l.includes('doordash')) return '🔴';
    if (l.includes('uber')) return '🟢';
    if (l.includes('grubhub')) return '🟠';
    return '📦';
  };

  return (
    <AdminLayout>
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Driver Tracking</h1>
          <span className="text-sm text-gray-500">Auto-refreshing every 15s</span>
        </div>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : deliveries.length === 0 ? (
          <div className="text-center py-12 text-gray-500">No active deliveries</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {deliveries.map(d => (
              <div key={d.order_id} className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono font-bold text-gray-900 dark:text-white">#{d.order_id}</span>
                  <span className={`px-2 py-1 text-xs rounded-full ${statusColor(d.status)}`}>{d.status.replace('_', ' ')}</span>
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <span>{platformIcon(d.platform)}</span>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{d.platform}</span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Driver</span><span className="text-gray-900 dark:text-white">{d.driver_name}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">ETA</span><span className={`font-medium ${d.eta_minutes > 30 ? 'text-red-600' : 'text-gray-900 dark:text-white'}`}>{d.eta_minutes} min</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Items</span><span className="text-gray-900 dark:text-white">{d.items_count}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Total</span><span className="font-medium text-gray-900 dark:text-white">${d.total.toFixed(2)}</span></div>
                </div>
                <div className="mt-2 pt-2 border-t dark:border-gray-700 text-xs text-gray-500 truncate">{d.customer_address}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
