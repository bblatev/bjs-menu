'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface OfflineStatus {
  is_online: boolean;
  last_sync: string;
  pending_orders: number;
  pending_payments: number;
  conflicts: number;
}

interface OfflineOrder {
  id: string;
  order_number: string;
  total: number;
  status: string;
  created_at: string;
}

export default function OfflinePOSPage() {
  const [status, setStatus] = useState<OfflineStatus | null>(null);
  const [pendingOrders, setPendingOrders] = useState<OfflineOrder[]>([]);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetchStatus();
    fetchPendingOrders();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const data: any = await api.get('/enterprise/offline/connectivity');
      setStatus(data);
    } catch (error) {
      console.error('Failed to fetch offline status:', error);
    }
  };

  const fetchPendingOrders = async () => {
    try {
      const data: any = await api.get('/enterprise/offline/sync-queue');
      setPendingOrders(data.orders || []);
    } catch (error) {
      console.error('Failed to fetch pending orders:', error);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.post('/enterprise/offline/sync');
      await fetchStatus();
      await fetchPendingOrders();
    } catch (error) {
      console.error('Sync failed:', error);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">True Offline POS</h1>
      
      {/* Connection Status */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold mb-2">Connection Status</h2>
            <div className={`flex items-center gap-2 ${status?.is_online ? 'text-green-600' : 'text-red-600'}`}>
              <div className={`w-3 h-3 rounded-full ${status?.is_online ? 'bg-green-500' : 'bg-red-500'}`} />
              {status?.is_online ? 'Online' : 'Offline'}
            </div>
            {status?.last_sync && (
              <p className="text-gray-500 text-sm mt-1">
                Last sync: {new Date(status.last_sync).toLocaleString()}
              </p>
            )}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="bg-blue-600 text-gray-900 px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Pending Orders</h3>
          <p className="text-3xl font-bold">{status?.pending_orders || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Pending Payments</h3>
          <p className="text-3xl font-bold">{status?.pending_payments || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-gray-500 text-sm">Conflicts</h3>
          <p className="text-3xl font-bold text-red-600">{status?.conflicts || 0}</p>
        </div>
      </div>

      {/* Pending Orders List */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="text-xl font-semibold">Sync Queue</h2>
        </div>
        <div className="p-4">
          {pendingOrders.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No pending orders to sync</p>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2">Order #</th>
                  <th className="pb-2">Total</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {pendingOrders.map((order) => (
                  <tr key={order.id} className="border-b">
                    <td className="py-3">{order.order_number}</td>
                    <td className="py-3">{(order.total || 0).toFixed(2)} лв</td>
                    <td className="py-3">
                      <span className="px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800">
                        {order.status}
                      </span>
                    </td>
                    <td className="py-3">{new Date(order.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
