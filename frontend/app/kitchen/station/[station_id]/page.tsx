'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';

import { API_URL, WS_URL, getAuthHeaders } from '@/lib/api';

export default function KitchenStationPage() {
  const params = useParams();
  const router = useRouter();
  const stationId = params?.station_id as string;

  const [orders, setOrders] = useState<any[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [token, setToken] = useState('');
  const [filter, setFilter] = useState<'all' | 'dine-in' | 'takeaway'>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [printing, setPrinting] = useState<number | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (!storedToken) {
      router.push('/login');
      return;
    }
    setToken(storedToken);
    loadOrders(storedToken);
    connectWebSocket(storedToken);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stationId]);

  const loadOrders = async (authToken: string) => {
    try {
      setLoading(true);
      setError('');
      const response = await axios.get(
        `${API_URL}/orders/station/${stationId}?status=new&status=accepted&status=preparing&status=ready`,
        { headers: { Authorization: `Bearer ${authToken}` } }
      );
      setOrders(response.data);
    } catch (err: any) {
      console.error('Failed to load orders', err);
      setError(err.response?.data?.detail || 'Failed to load orders');
      if (err.response?.status === 401) {
        localStorage.removeItem('access_token');
        router.push('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = (authToken: string) => {
    const socket = new WebSocket(`${WS_URL}/ws/station/${stationId}`);

    socket.onopen = () => { /* WebSocket connected */ };
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'order_update') {
        loadOrders(authToken);
      }
    };
    socket.onerror = () => { /* WebSocket error */ };
    socket.onclose = () => { /* WebSocket disconnected */ };

    setWs(socket);

    return () => socket.close();
  };

  const updateOrderStatus = async (orderId: number, status: string) => {
    try {
      await axios.put(
        `${API_URL}/orders/${orderId}/status`,
        { status },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadOrders(token);
    } catch (err) {
      alert('Failed to update order status');
    }
  };

  const printFiscalReceipt = async (orderId: number, paymentType: string = 'cash') => {
    try {
      setPrinting(orderId);
      const response = await axios.post(
        `${API_URL}/fiscal/receipt`,
        { order_id: orderId, payment_type: paymentType },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.data.success) {
        alert(`Receipt printed! Number: ${response.data.receipt_number || 'N/A'}`);
      } else {
        alert(`Print failed: ${response.data.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      alert(`Print error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setPrinting(null);
    }
  };

  const printKitchenTicket = async (orderId: number) => {
    try {
      setPrinting(orderId);
      const response = await axios.post(
        `${API_URL}/fiscal/kitchen-ticket/${orderId}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.data.success) {
        alert('Kitchen ticket printed!');
      } else {
        alert(`Print failed: ${response.data.error || 'Unknown error'}`);
      }
    } catch (err: any) {
      alert(`Print error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setPrinting(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return 'bg-blue-500';
      case 'accepted': return 'bg-yellow-500';
      case 'preparing': return 'bg-orange-500';
      case 'ready': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getNextStatus = (currentStatus: string) => {
    switch (currentStatus) {
      case 'new': return 'accepted';
      case 'accepted': return 'preparing';
      case 'preparing': return 'ready';
      case 'ready': return 'served';
      default: return null;
    }
  };

  const filteredOrders = orders.filter(order => {
    if (filter === 'all') return true;
    return order.order_type === filter;
  });

  const takeawayCount = orders.filter(o => o.order_type === 'takeaway').length;
  const dineInCount = orders.filter(o => o.order_type === 'dine-in' || !o.order_type).length;

  if (loading && orders.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-primary text-xl">Loading orders...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-display text-primary">
            {stationId === '5' ? 'Kitchen' : 'Bar'} Station
          </h1>
          <a href="/dashboard" className="text-gray-300 hover:text-primary">← Back to Dashboard</a>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => setFilter('all')}
            className={`px-6 py-3 rounded-lg font-semibold transition ${
              filter === 'all' 
                ? 'bg-primary text-white' 
                : 'bg-secondary text-gray-300 hover:bg-secondary/80'
            }`}
          >
            All ({orders.length})
          </button>
          <button
            onClick={() => setFilter('dine-in')}
            className={`px-6 py-3 rounded-lg font-semibold transition flex items-center gap-2 ${
              filter === 'dine-in' 
                ? 'bg-blue-500 text-white' 
                : 'bg-secondary text-gray-300 hover:bg-secondary/80'
            }`}
          >
            🍽️ Dine-in ({dineInCount})
          </button>
          <button
            onClick={() => setFilter('takeaway')}
            className={`px-6 py-3 rounded-lg font-semibold transition flex items-center gap-2 ${
              filter === 'takeaway' 
                ? 'bg-amber-500 text-white' 
                : 'bg-secondary text-gray-300 hover:bg-secondary/80'
            }`}
          >
            🥡 Takeaway ({takeawayCount})
          </button>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {filteredOrders.length === 0 ? (
            <div className="col-span-3 text-center py-12 text-gray-400">
              No active orders
            </div>
          ) : (
            filteredOrders.map((order) => (
              <div 
                key={order.id} 
                className={`rounded-lg p-6 shadow-lg ${
                  order.order_type === 'takeaway' 
                    ? 'bg-amber-900/30 border-2 border-amber-500' 
                    : 'bg-secondary'
                }`}
              >
                {/* Takeaway Badge */}
                {order.order_type === 'takeaway' && (
                  <div className="bg-amber-500 text-gray-900 px-3 py-1 rounded-full text-sm font-bold inline-flex items-center gap-2 mb-3">
                    🥡 TAKEAWAY
                  </div>
                )}

                <div className="flex justify-between items-start mb-4">
                  <div>
                    {order.order_type === 'takeaway' ? (
                      <>
                        <div className="text-2xl font-bold text-gray-900">
                          {order.customer_name || 'Customer'}
                        </div>
                        {order.customer_phone && (
                          <div className="text-sm text-gray-400">📞 {order.customer_phone}</div>
                        )}
                        <div className="text-sm text-amber-400">{order.order_number}</div>
                      </>
                    ) : (
                      <>
                        <div className="text-2xl font-bold text-gray-900">Table {order.table_number}</div>
                        <div className="text-sm text-gray-400">{order.order_number}</div>
                      </>
                    )}
                  </div>
                  <div className={`px-3 py-1 rounded-full text-gray-900 text-sm font-semibold ${getStatusColor(order.status)}`}>
                    {order.status}
                  </div>
                </div>

                <div className="space-y-3 mb-4">
                  {order.items.map((item: any) => (
                    <div key={item.id} className={`border-l-4 pl-3 ${
                      order.order_type === 'takeaway' ? 'border-amber-500' : 'border-primary'
                    }`}>
                      <div className="text-gray-900 font-semibold">{item.quantity}x {item.item_name?.bg || item.item_name?.en || item.name}</div>
                      {item.modifiers && item.modifiers.length > 0 && (
                        <div className="text-sm text-gray-400">
                          + {item.modifiers.map((m: any) => m.option_name?.bg || m.option_name?.en || m.name).join(', ')}
                        </div>
                      )}
                      {item.notes && (
                        <div className="text-sm text-yellow-400 mt-1">Note: {item.notes}</div>
                      )}
                    </div>
                  ))}
                </div>

                {order.notes && (
                  <div className="bg-yellow-500/20 border border-yellow-500/50 rounded-lg p-2 mb-4">
                    <div className="text-yellow-400 text-sm">📝 {order.notes}</div>
                  </div>
                )}

                <div className={`text-xl font-bold mb-4 ${
                  order.order_type === 'takeaway' ? 'text-amber-400' : 'text-primary'
                }`}>
                  {order.total?.toFixed(2)} €.
                </div>

                <div className="flex gap-2 flex-wrap">
                  {getNextStatus(order.status) && (
                    <button
                      onClick={() => updateOrderStatus(order.id, getNextStatus(order.status)!)}
                      className={`flex-1 text-gray-900 py-2 rounded-lg font-semibold transition ${
                        order.order_type === 'takeaway'
                          ? 'bg-amber-500 hover:bg-amber-600'
                          : 'bg-primary hover:bg-primary/80'
                      }`}
                    >
                      {getNextStatus(order.status) === 'accepted' && 'Accept'}
                      {getNextStatus(order.status) === 'preparing' && 'Start'}
                      {getNextStatus(order.status) === 'ready' && (order.order_type === 'takeaway' ? '✓ Ready for Pickup' : 'Ready')}
                      {getNextStatus(order.status) === 'served' && (order.order_type === 'takeaway' ? 'Picked Up' : 'Served')}
                    </button>
                  )}
                  <button
                    onClick={() => updateOrderStatus(order.id, 'cancelled')}
                    className="px-4 bg-red-500 hover:bg-red-600 text-gray-900 py-2 rounded-lg transition"
                  >
                    Cancel
                  </button>
                </div>

                {/* Print Buttons */}
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => printKitchenTicket(order.id)}
                    disabled={printing === order.id}
                    className="flex-1 bg-gray-600 hover:bg-gray-500 text-gray-900 py-2 rounded-lg font-medium transition disabled:opacity-50"
                  >
                    {printing === order.id ? 'Printing...' : '🎫 Kitchen Ticket'}
                  </button>
                  <button
                    onClick={() => printFiscalReceipt(order.id, 'cash')}
                    disabled={printing === order.id}
                    className="flex-1 bg-green-600 hover:bg-green-500 text-gray-900 py-2 rounded-lg font-medium transition disabled:opacity-50"
                  >
                    {printing === order.id ? 'Printing...' : '🧾 Fiscal Receipt'}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
