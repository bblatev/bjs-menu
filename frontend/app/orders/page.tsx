'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
// ============ INTERFACES ============

interface OrderItem {
  id: string;
  name: string;
  quantity: number;
  unit_price: number;
  modifiers?: { name: string; price: number }[];
  notes?: string;
  status: 'pending' | 'preparing' | 'ready' | 'served' | 'cancelled';
  sent_to_kitchen: boolean;
  prepared_by?: string;
  prepared_at?: string;
}

interface Order {
  id: string;
  order_number: number;
  table: string;
  table_id?: string;
  type: 'dine_in' | 'takeaway' | 'delivery' | 'drive_thru';
  status: 'new' | 'preparing' | 'ready' | 'served' | 'paid' | 'cancelled';
  items: OrderItem[];
  subtotal: number;
  tax: number;
  discount: number;
  total: number;
  waiter: string;
  waiter_id: string;
  guests: number;
  created_at: string;
  updated_at: string;
  notes?: string;
  payment_method?: 'cash' | 'card' | 'mixed';
  split_bills?: SplitBill[];
  customer?: {
    name: string;
    phone?: string;
    address?: string;
    loyalty_points?: number;
  };
  delivery_info?: {
    address: string;
    phone: string;
    driver?: string;
    estimated_time?: string;
  };
  time_elapsed: number;
  priority: 'normal' | 'high' | 'rush';
}

interface SplitBill {
  id: string;
  amount: number;
  payment_method: 'cash' | 'card';
  paid: boolean;
}

interface Staff {
  id: string;
  name: string;
  role: 'waiter' | 'bartender' | 'manager';
  active_orders: number;
  total_sales: number;
  avatar?: string;
}

interface Table {
  id: string;
  number: string;
  seats: number;
  status: 'available' | 'occupied' | 'reserved' | 'cleaning';
  current_order_id?: string;
}

interface OrderStats {
  total_orders: number;
  new_orders: number;
  preparing: number;
  ready: number;
  served: number;
  paid: number;
  cancelled: number;
  total_revenue: number;
  avg_order_value: number;
  avg_prep_time: number;
}

// ============ COMPONENT ============

export default function OrdersPage() {
  const [activeTab, setActiveTab] = useState<'active' | 'history' | 'floor' | 'analytics'>('active');
  const [orders, setOrders] = useState<Order[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [stats, setStats] = useState<OrderStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState<'all' | 'new' | 'preparing' | 'ready' | 'served'>('all');
  const [typeFilter, setTypeFilter] = useState<'all' | 'dine_in' | 'takeaway' | 'delivery' | 'drive_thru'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRange, setDateRange] = useState<'today' | 'week' | 'month'>('today');

  // Modal states
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [, setShowNewOrderModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showSplitBillModal, setShowSplitBillModal] = useState(false);
  const [splitWays, setSplitWays] = useState(2);
  const [showVoidModal, setShowVoidModal] = useState(false);
  const [showRefundModal, setShowRefundModal] = useState(false);
  const [voidReason, setVoidReason] = useState('');
  const [refundAmount, setRefundAmount] = useState(0);
  const [refundReason, setRefundReason] = useState('');

  // Void item modal
  const [showVoidItemModal, setShowVoidItemModal] = useState(false);
  const [voidItemReason, setVoidItemReason] = useState('');
  const [voidItemId, setVoidItemId] = useState<string | null>(null);

  // Auto-refresh
  const refreshInterval = useRef<NodeJS.Timeout | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);

  useEffect(() => {
    loadData();
    if (autoRefresh) {
      refreshInterval.current = setInterval(loadData, 30000);
    }
    return () => {
      if (refreshInterval.current) clearInterval(refreshInterval.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh]);

  const loadData = async () => {
    setLoading(true);
    const headers = getAuthHeaders();

    try {
      // Fetch all data in parallel
      const [ordersRes, tablesRes, staffRes, statsRes] = await Promise.allSettled([
        fetch(`${API_URL}/orders`, { credentials: 'include', headers }),
        fetch(`${API_URL}/admin/tables`, { credentials: 'include', headers }),
        fetch(`${API_URL}/staff`, { credentials: 'include', headers }),
        fetch(`${API_URL}/orders/stats`, { credentials: 'include', headers }),
      ]);

      // Process orders
      if (ordersRes.status === 'fulfilled' && ordersRes.value.ok) {
        const data = await ordersRes.value.json();
        const ordersArray = Array.isArray(data) ? data : (data.orders || []);
        // Transform API response to match our Order interface
        const transformedOrders: Order[] = ordersArray.map((order: any) => ({
          id: String(order.id),
          order_number: order.order_number || order.id,
          table: order.table?.number || order.table_number || `T${order.table_id || 0}`,
          table_id: order.table_id ? String(order.table_id) : undefined,
          type: order.order_type || order.type || 'dine_in',
          status: order.status || 'new',
          items: (order.items || []).map((item: any) => ({
            id: String(item.id),
            name: item.menu_item?.name || item.name || 'Unknown Item',
            quantity: item.quantity || 1,
            unit_price: item.unit_price || item.price || 0,
            modifiers: item.modifiers || [],
            notes: item.notes,
            status: item.status || 'pending',
            sent_to_kitchen: item.sent_to_kitchen !== false,
            prepared_by: item.prepared_by,
            prepared_at: item.prepared_at,
          })),
          subtotal: order.subtotal || order.total * 0.8 || 0,
          tax: order.tax || order.total * 0.2 || 0,
          discount: order.discount || 0,
          total: order.total || 0,
          waiter: order.waiter?.name || order.waiter_name || 'N/A',
          waiter_id: order.waiter_id ? String(order.waiter_id) : '0',
          guests: order.guests || order.party_size || 1,
          created_at: order.created_at || new Date().toISOString(),
          updated_at: order.updated_at || new Date().toISOString(),
          notes: order.notes,
          payment_method: order.payment_method,
          customer: order.customer,
          delivery_info: order.delivery_info,
          time_elapsed: order.time_elapsed || Math.floor((Date.now() - new Date(order.created_at || Date.now()).getTime()) / 60000),
          priority: order.priority || 'normal',
        }));
        setOrders(transformedOrders);
      } else {
        setOrders([]);
      }

      // Process tables
      if (tablesRes.status === 'fulfilled' && tablesRes.value.ok) {
        const data = await tablesRes.value.json();
        const tablesArray = Array.isArray(data) ? data : (data.tables || []);
        const transformedTables: Table[] = tablesArray.map((table: any) => ({
          id: String(table.id),
          number: table.number || `T${table.id}`,
          seats: table.capacity || table.seats || 4,
          status: table.status || 'available',
          current_order_id: table.current_order_id ? String(table.current_order_id) : undefined,
        }));
        setTables(transformedTables);
      } else {
        setTables([]);
      }

      // Process staff
      if (staffRes.status === 'fulfilled' && staffRes.value.ok) {
        const data = await staffRes.value.json();
        const staffArray = Array.isArray(data) ? data : (data.staff || []);
        const transformedStaff: Staff[] = staffArray.map((s: any) => ({
          id: String(s.id),
          name: s.name || s.full_name || 'Unknown',
          role: s.role || 'waiter',
          active_orders: s.active_orders || 0,
          total_sales: s.total_sales || 0,
          avatar: s.avatar,
        }));
        setStaff(transformedStaff);
      } else {
        setStaff([]);
      }

      // Process stats
      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        const data = await statsRes.value.json();
        const transformedStats: OrderStats = {
          total_orders: data.total_orders || 0,
          new_orders: data.new_orders || data.new || 0,
          preparing: data.preparing || 0,
          ready: data.ready || 0,
          served: data.served || 0,
          paid: data.paid || data.completed || 0,
          cancelled: data.cancelled || 0,
          total_revenue: data.total_revenue || data.revenue || 0,
          avg_order_value: data.avg_order_value || data.average_order_value || 0,
          avg_prep_time: data.avg_prep_time || data.average_prep_time || 0,
        };
        setStats(transformedStats);
      } else {
        // Calculate stats from orders if stats endpoint fails
        const ordersData = orders.length > 0 ? orders : [];
        setStats({
          total_orders: ordersData.length,
          new_orders: ordersData.filter(o => o.status === 'new').length,
          preparing: ordersData.filter(o => o.status === 'preparing').length,
          ready: ordersData.filter(o => o.status === 'ready').length,
          served: ordersData.filter(o => o.status === 'served').length,
          paid: ordersData.filter(o => o.status === 'paid').length,
          cancelled: ordersData.filter(o => o.status === 'cancelled').length,
          total_revenue: ordersData.reduce((sum, o) => sum + o.total, 0),
          avg_order_value: ordersData.length > 0 ? ordersData.reduce((sum, o) => sum + o.total, 0) / ordersData.length : 0,
          avg_prep_time: 0,
        });
      }
    } catch (error) {
      console.error('Error fetching orders data:', error);
      setOrders([]);
      setTables([]);
      setStaff([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  // ============ HANDLERS ============

  const handleUpdateOrderStatus = async (orderId: string, newStatus: Order['status'], paymentMethod?: string) => {
    const headers = getAuthHeaders();

    try {
      const bodyData: Record<string, string> = { status: newStatus };
      if (paymentMethod) bodyData.payment_method = paymentMethod;
      const response = await fetch(`${API_URL}/orders/${orderId}/status`, {
        credentials: 'include',
        method: 'PUT',
        headers,
        body: JSON.stringify(bodyData),
      });

      if (response.ok) {
        // Update local state
        setOrders(orders.map(o => o.id === orderId ? { ...o, status: newStatus, updated_at: new Date().toISOString() } : o));
        if (selectedOrder?.id === orderId) {
          setSelectedOrder({ ...selectedOrder, status: newStatus });
        }
      } else {
        console.error('Failed to update order status');
        toast.error('Failed to update order status. Please try again.');
      }
    } catch (error) {
      console.error('Error updating order status:', error);
      toast.error('Error updating order status. Please try again.');
    }
  };

  const handleUpdateItemStatus = async (orderId: string, itemId: string, newStatus: OrderItem['status']) => {
    const headers = getAuthHeaders();

    try {
      const response = await fetch(`${API_URL}/orders/${orderId}/items/${itemId}/status`, {
        credentials: 'include',
        method: 'PATCH',
        headers,
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        // Update local state only on success
        setOrders(orders.map(o => {
          if (o.id === orderId) {
            const updatedItems = o.items.map(item =>
              item.id === itemId ? { ...item, status: newStatus, prepared_at: newStatus === 'ready' ? new Date().toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' }) : item.prepared_at } : item
            );
            // Check if all items are ready
            const allReady = updatedItems.filter(i => i.sent_to_kitchen).every(i => i.status === 'ready' || i.status === 'served');
            const allServed = updatedItems.every(i => i.status === 'served');
            return {
              ...o,
              items: updatedItems,
              status: allServed ? 'served' : allReady && o.status === 'preparing' ? 'ready' : o.status
            };
          }
          return o;
        }));
      } else {
        console.error('Failed to update item status');
        toast.error('Failed to update item status. Please try again.');
      }
    } catch (error) {
      console.error('Error updating item status:', error);
      toast.error('Error updating item status. Please try again.');
    }
  };

  const handleVoidOrder = async () => {
    if (!selectedOrder || !voidReason) return;
    const headers = getAuthHeaders();

    try {
      const response = await fetch(`${API_URL}/orders/${selectedOrder.id}/void`, {
        credentials: 'include',
        method: 'POST',
        headers,
        body: JSON.stringify({ reason: voidReason }),
      });
      if (response.ok) {
        setOrders(orders.map(o => o.id === selectedOrder.id ? { ...o, status: 'cancelled' } : o));
        setShowVoidModal(false);
        setSelectedOrder(null);
        setVoidReason('');
      }
    } catch (error) {
      console.error('Error voiding order:', error);
    }
  };

  const handleConfirmVoidItem = async () => {
    if (!selectedOrder || !voidItemId || !voidItemReason) return;
    const headers = getAuthHeaders();
    const itemId = voidItemId;

    try {
      const response = await fetch(`${API_URL}/orders/${selectedOrder.id}/items/${itemId}/void`, {
        credentials: 'include',
        method: 'POST',
        headers,
        body: JSON.stringify({ reason: voidItemReason }),
      });
      if (response.ok) {
        const data = await response.json();
        setOrders(orders.map(o => {
          if (o.id === selectedOrder.id) {
            return {
              ...o,
              items: o.items.map(i => i.id === itemId ? { ...i, status: 'cancelled' as const } : i),
              total: data.new_order_total || o.total
            };
          }
          return o;
        }));
      }
    } catch (error) {
      console.error('Error voiding item:', error);
    } finally {
      setShowVoidItemModal(false);
      setVoidItemId(null);
      setVoidItemReason('');
    }
  };

  const handleRefundOrder = async () => {
    if (!selectedOrder || !refundAmount || !refundReason) return;
    const headers = getAuthHeaders();

    try {
      const response = await fetch(`${API_URL}/orders/${selectedOrder.id}/refund`, {
        credentials: 'include',
        method: 'POST',
        headers,
        body: JSON.stringify({
          amount: refundAmount,
          reason: refundReason,
          refund_method: 'cash'
        }),
      });
      if (response.ok) {
        setShowRefundModal(false);
        setRefundAmount(0);
        setRefundReason('');
        loadData();
      }
    } catch (error) {
      console.error('Error refunding order:', error);
    }
  };

  const handleReprintOrder = async (station: string = 'kitchen') => {
    if (!selectedOrder) return;
    const headers = getAuthHeaders();

    try {
      await fetch(`${API_URL}/orders/${selectedOrder.id}/reprint`, {
        credentials: 'include',
        method: 'POST',
        headers,
        body: JSON.stringify({ station }),
      });
      toast.success('Поръчката е изпратена за повторен печат!');
    } catch (error) {
      console.error('Error reprinting order:', error);
    }
  };

  const handleSetPriority = async (priority: 'rush' | 'high' | 'normal') => {
    if (!selectedOrder) return;
    const headers = getAuthHeaders();

    const endpoint = priority === 'rush'
      ? `${API_URL}/kitchen/rush/${selectedOrder.id}`
      : priority === 'high'
      ? `${API_URL}/kitchen/vip/${selectedOrder.id}`
      : null;

    if (endpoint) {
      try {
        await fetch(endpoint, { credentials: 'include', method: 'POST', headers });
        setOrders(orders.map(o => o.id === selectedOrder.id ? { ...o, priority } : o));
        if (selectedOrder) setSelectedOrder({ ...selectedOrder, priority });
      } catch (error) {
        console.error('Error setting priority:', error);
      }
    }
  };

  const getStatusConfig = (status: string) => {
    const config: Record<string, { label: string; color: string; bg: string }> = {
      new: { label: 'Нова', color: 'text-blue-700', bg: 'bg-blue-100' },
      pending: { label: 'Чакаща', color: 'text-blue-700', bg: 'bg-blue-100' },
      preparing: { label: 'Готви се', color: 'text-orange-700', bg: 'bg-orange-100' },
      ready: { label: 'Готова', color: 'text-green-700', bg: 'bg-green-100' },
      served: { label: 'Сервирана', color: 'text-purple-700', bg: 'bg-purple-100' },
      paid: { label: 'Платена', color: 'text-gray-700', bg: 'bg-gray-100' },
      cancelled: { label: 'Отменена', color: 'text-red-700', bg: 'bg-red-100' },
    };
    return config[status] || { label: status, color: 'text-gray-700', bg: 'bg-gray-100' };
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      dine_in: '🍽️ На място',
      takeaway: '📦 За вкъщи',
      delivery: '🚗 Доставка',
      drive_thru: '🚙 Drive-Thru',
    };
    return labels[type] || type;
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      normal: '',
      high: 'border-l-4 border-l-orange-500',
      rush: 'border-l-4 border-l-red-500 bg-red-50',
    };
    return colors[priority] || '';
  };

  const filteredOrders = orders.filter(o => {
    if (statusFilter !== 'all' && o.status !== statusFilter) return false;
    if (typeFilter !== 'all' && o.type !== typeFilter) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        o.order_number.toString().includes(query) ||
        o.table.toLowerCase().includes(query) ||
        o.waiter.toLowerCase().includes(query) ||
        o.customer?.name?.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const activeOrders = orders.filter(o => !['paid', 'cancelled'].includes(o.status));

  const tabs = [
    { id: 'active', label: 'Активни поръчки', icon: '📋', count: activeOrders.length },
    { id: 'history', label: 'История', icon: '📚' },
    { id: 'floor', label: 'План на залата', icon: '🗺️' },
    { id: 'analytics', label: 'Анализ', icon: '📊' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <div className="text-gray-700 text-lg">Зареждане на поръчки...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              📋 Поръчки
            </h1>
            <p className="text-gray-500 mt-1">Управление на активни поръчки в реално време</p>
          </div>
          <div className="flex gap-3">
            <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl border border-gray-200">
              <span className="text-gray-500 text-sm">Авто-обновяване</span>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`w-10 h-6 rounded-full transition-colors ${autoRefresh ? 'bg-green-500' : 'bg-gray-300'}`}
              >
                <span className={`block w-4 h-4 bg-white rounded-full shadow transform transition-transform ${autoRefresh ? 'translate-x-5' : 'translate-x-1'}`} />
              </button>
            </div>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={`px-4 py-2 rounded-xl border ${soundEnabled ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-gray-100 border-gray-200 text-gray-500'}`}
            >
              {soundEnabled ? '🔔' : '🔕'}
            </button>
            <button onClick={loadData} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200">
              🔄 Обнови
            </button>
            <Link
              href="/orders/quick-reorder"
              className="px-4 py-2 bg-orange-100 text-orange-700 rounded-xl hover:bg-orange-200 flex items-center gap-2"
            >
              ↺ Повтори
            </Link>
            <button
              onClick={() => setShowNewOrderModal(true)}
              className="px-6 py-2 bg-blue-600 text-gray-900 rounded-xl hover:bg-blue-700 shadow-sm flex items-center gap-2"
            >
              <span>+</span> Нова поръчка
            </button>
          </div>
        </div>

        {/* Quick Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-xs">Нови</div>
                  <div className="text-2xl font-bold text-blue-600">{stats.new_orders}</div>
                </div>
                <span className="text-2xl">🆕</span>
              </div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-xs">Готвят се</div>
                  <div className="text-2xl font-bold text-orange-600">{stats.preparing}</div>
                </div>
                <span className="text-2xl">👨‍🍳</span>
              </div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-xs">Готови</div>
                  <div className="text-2xl font-bold text-green-600">{stats.ready}</div>
                </div>
                <span className="text-2xl">✅</span>
              </div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-xs">Сервирани</div>
                  <div className="text-2xl font-bold text-purple-600">{stats.served}</div>
                </div>
                <span className="text-2xl">🍽️</span>
              </div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-xs">Платени</div>
                  <div className="text-2xl font-bold text-gray-600">{stats.paid}</div>
                </div>
                <span className="text-2xl">💰</span>
              </div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-xs">Оборот</div>
                  <div className="text-xl font-bold text-gray-900">{stats.total_revenue.toLocaleString()} лв</div>
                </div>
                <span className="text-2xl">📈</span>
              </div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-xs">Ср. време</div>
                  <div className="text-xl font-bold text-gray-900">{stats.avg_prep_time} мин</div>
                </div>
                <span className="text-2xl">⏱️</span>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-xl font-medium transition-all flex items-center gap-2 ${
                activeTab === tab.id ? 'bg-blue-600 text-gray-900 shadow-sm' : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
              {tab.count !== undefined && (
                <span className={`px-2 py-0.5 rounded-full text-xs ${activeTab === tab.id ? 'bg-gray-200' : 'bg-blue-100 text-blue-700'}`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Active Orders Tab */}
        {activeTab === 'active' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex flex-wrap items-center gap-4">
                <div className="relative flex-1 max-w-md">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Търси по номер, маса, сервитьор..."
                    className="w-full pl-10 pr-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
                  {[
                    { key: 'all', label: 'Всички' },
                    { key: 'new', label: 'Нови' },
                    { key: 'preparing', label: 'Готвене' },
                    { key: 'ready', label: 'Готови' },
                    { key: 'served', label: 'Сервирани' },
                  ].map(tab => (
                    <button
                      key={tab.key}
                      onClick={() => setStatusFilter(tab.key as any)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                        statusFilter === tab.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
                <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
                  {[
                    { key: 'all', label: 'Всички', icon: '' },
                    { key: 'dine_in', label: 'На място', icon: '🍽️' },
                    { key: 'takeaway', label: 'За вкъщи', icon: '📦' },
                    { key: 'delivery', label: 'Доставка', icon: '🚗' },
                    { key: 'drive_thru', label: 'Drive-Thru', icon: '🚙' },
                  ].map(tab => (
                    <button
                      key={tab.key}
                      onClick={() => setTypeFilter(tab.key as any)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                        typeFilter === tab.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      {tab.icon} {tab.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Orders Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {filteredOrders.filter(o => !['paid', 'cancelled'].includes(o.status)).map((order) => {
                  const statusConfig = getStatusConfig(order.status);
                  return (
                    <motion.div
                      key={order.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className={`bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden cursor-pointer hover:shadow-md transition-shadow ${getPriorityColor(order.priority)}`}
                      onClick={() => setSelectedOrder(order)}
                    >
                      {/* Order Header */}
                      <div className="p-4 border-b border-gray-100">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <span className="text-lg font-bold text-gray-900">#{order.order_number}</span>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                              {statusConfig.label}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {order.priority === 'rush' && <span className="text-red-500 animate-pulse">🚨</span>}
                            {order.priority === 'high' && <span className="text-orange-500">⚡</span>}
                            <span className={`text-sm font-medium ${order.time_elapsed > 20 ? 'text-red-600' : order.time_elapsed > 10 ? 'text-orange-600' : 'text-gray-500'}`}>
                              {order.time_elapsed} мин
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-1 bg-gray-100 rounded text-sm font-medium text-gray-700">{order.table}</span>
                            <span className="text-gray-500 text-sm">{getTypeLabel(order.type)}</span>
                          </div>
                          <span className="text-gray-500 text-sm">{order.waiter}</span>
                        </div>
                      </div>

                      {/* Order Items */}
                      <div className="p-4">
                        <div className="space-y-2 max-h-32 overflow-y-auto">
                          {order.items.slice(0, 4).map((item) => {
                            return (
                              <div key={item.id} className="flex items-center justify-between text-sm">
                                <div className="flex items-center gap-2">
                                  <span className={`w-2 h-2 rounded-full ${item.status === 'served' ? 'bg-green-500' : item.status === 'ready' ? 'bg-blue-500' : item.status === 'preparing' ? 'bg-orange-500' : 'bg-gray-300'}`} />
                                  <span className="text-gray-700">{item.quantity}x {item.name}</span>
                                </div>
                                <span className="text-gray-500">{((item.quantity * item.unit_price) || 0).toFixed(2)} лв</span>
                              </div>
                            );
                          })}
                          {order.items.length > 4 && (
                            <div className="text-gray-400 text-xs">+{order.items.length - 4} още артикула</div>
                          )}
                        </div>
                        {order.notes && (
                          <div className="mt-2 p-2 bg-yellow-50 rounded text-xs text-yellow-700">
                            📝 {order.notes}
                          </div>
                        )}
                      </div>

                      {/* Order Footer */}
                      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
                        <span className="text-xl font-bold text-gray-900">{(order.total || 0).toFixed(2)} лв</span>
                        <div className="flex gap-2">
                          {order.status === 'new' && (
                            <button
                              onClick={(e) => { e.stopPropagation(); handleUpdateOrderStatus(order.id, 'preparing'); }}
                              className="px-3 py-1 bg-orange-500 text-gray-900 rounded-lg text-sm hover:bg-orange-600"
                            >
                              👨‍🍳 Готви
                            </button>
                          )}
                          {order.status === 'ready' && (
                            <button
                              onClick={(e) => { e.stopPropagation(); handleUpdateOrderStatus(order.id, 'served'); }}
                              className="px-3 py-1 bg-purple-500 text-gray-900 rounded-lg text-sm hover:bg-purple-600"
                            >
                              🍽️ Сервирай
                            </button>
                          )}
                          {order.status === 'served' && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setSelectedOrder(order); setShowPaymentModal(true); }}
                              className="px-3 py-1 bg-green-500 text-gray-900 rounded-lg text-sm hover:bg-green-600"
                            >
                              💰 Плащане
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>

            {filteredOrders.filter(o => !['paid', 'cancelled'].includes(o.status)).length === 0 && (
              <div className="text-center py-12 bg-white rounded-xl border border-gray-100">
                <span className="text-5xl">📋</span>
                <p className="mt-4 text-gray-500">Няма активни поръчки</p>
              </div>
            )}
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex gap-2">
                {['today', 'week', 'month'].map((range) => (
                  <button
                    key={range}
                    onClick={() => setDateRange(range as any)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium ${dateRange === range ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}
                  >
                    {range === 'today' ? 'Днес' : range === 'week' ? 'Тази седмица' : 'Този месец'}
                  </button>
                ))}
              </div>
              <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">📥 Експорт</button>
            </div>
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Поръчка</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Маса</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Тип</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Сервитьор</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Време</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Сума</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {orders.filter(o => ['paid', 'cancelled'].includes(o.status)).map((order) => {
                  const statusConfig = getStatusConfig(order.status);
                  return (
                    <tr key={order.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedOrder(order)}>
                      <td className="px-4 py-3 font-medium text-gray-900">#{order.order_number}</td>
                      <td className="px-4 py-3 text-gray-600">{order.table}</td>
                      <td className="px-4 py-3 text-gray-600">{getTypeLabel(order.type)}</td>
                      <td className="px-4 py-3 text-gray-600">{order.waiter}</td>
                      <td className="px-4 py-3 text-gray-500 text-sm">{new Date(order.created_at).toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' })}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                          {statusConfig.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-gray-900">{(order.total || 0).toFixed(2)} лв</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Floor Plan Tab */}
        {activeTab === 'floor' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">План на залата</h2>
              <div className="grid grid-cols-4 gap-4">
                {tables.map((table) => {
                  const tableOrder = orders.find(o => o.id === table.current_order_id);
                  return (
                    <motion.div
                      key={table.id}
                      whileHover={{ scale: 1.05 }}
                      className={`aspect-square rounded-xl flex flex-col items-center justify-center cursor-pointer border-2 transition-all ${
                        table.status === 'available' ? 'bg-green-50 border-green-200 hover:border-green-400' :
                        table.status === 'occupied' ? 'bg-orange-50 border-orange-200 hover:border-orange-400' :
                        table.status === 'reserved' ? 'bg-blue-50 border-blue-200 hover:border-blue-400' :
                        'bg-gray-50 border-gray-200'
                      }`}
                      onClick={() => tableOrder && setSelectedOrder(tableOrder)}
                    >
                      <span className="text-2xl font-bold text-gray-900">{table.number}</span>
                      <span className="text-xs text-gray-500 mt-1">{table.seats} места</span>
                      {table.status === 'occupied' && tableOrder && (
                        <span className="text-xs font-medium text-orange-600 mt-1">{(tableOrder.total || 0).toFixed(2)} лв</span>
                      )}
                      {table.status === 'reserved' && <span className="text-xs text-blue-600 mt-1">Резервирана</span>}
                      {table.status === 'cleaning' && <span className="text-xs text-gray-500 mt-1">Почистване</span>}
                    </motion.div>
                  );
                })}
              </div>
              <div className="flex gap-4 mt-6 justify-center">
                <div className="flex items-center gap-2"><span className="w-4 h-4 bg-green-100 border border-green-300 rounded" /><span className="text-sm text-gray-600">Свободна</span></div>
                <div className="flex items-center gap-2"><span className="w-4 h-4 bg-orange-100 border border-orange-300 rounded" /><span className="text-sm text-gray-600">Заета</span></div>
                <div className="flex items-center gap-2"><span className="w-4 h-4 bg-blue-100 border border-blue-300 rounded" /><span className="text-sm text-gray-600">Резервирана</span></div>
                <div className="flex items-center gap-2"><span className="w-4 h-4 bg-gray-100 border border-gray-300 rounded" /><span className="text-sm text-gray-600">Почиства се</span></div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">Сервитьори</h3>
                <div className="space-y-3">
                  {staff.map((s) => (
                    <div key={s.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-gray-900 font-bold">
                          {s.name.charAt(0)}
                        </div>
                        <div>
                          <div className="font-medium text-gray-900">{s.name}</div>
                          <div className="text-xs text-gray-500">{s.active_orders} активни поръчки</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-gray-900">{(s.total_sales || 0).toFixed(2)} лв</div>
                        <div className="text-xs text-gray-500">продажби</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">Бърз преглед</h3>
                <div className="space-y-3">
                  <div className="flex justify-between p-3 bg-green-50 rounded-lg">
                    <span className="text-green-700">Свободни маси</span>
                    <span className="font-bold text-green-700">{tables.filter(t => t.status === 'available').length}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-orange-50 rounded-lg">
                    <span className="text-orange-700">Заети маси</span>
                    <span className="font-bold text-orange-700">{tables.filter(t => t.status === 'occupied').length}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-blue-50 rounded-lg">
                    <span className="text-blue-700">Резервации</span>
                    <span className="font-bold text-blue-700">{tables.filter(t => t.status === 'reserved').length}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && stats && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Статистика за деня</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-gray-500 text-sm">Общо поръчки</div>
                  <div className="text-3xl font-bold text-gray-900">{stats.total_orders}</div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-gray-500 text-sm">Оборот</div>
                  <div className="text-3xl font-bold text-green-600">{stats.total_revenue.toLocaleString()} лв</div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-gray-500 text-sm">Средна поръчка</div>
                  <div className="text-3xl font-bold text-blue-600">{(stats.avg_order_value || 0).toFixed(2)} лв</div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-gray-500 text-sm">Ср. време за готвене</div>
                  <div className="text-3xl font-bold text-orange-600">{stats.avg_prep_time} мин</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Разпределение по статус</h3>
              <div className="space-y-3">
                {[
                  { label: 'Платени', value: stats.paid, color: 'bg-green-500' },
                  { label: 'Нови', value: stats.new_orders, color: 'bg-blue-500' },
                  { label: 'Готвят се', value: stats.preparing, color: 'bg-orange-500' },
                  { label: 'Готови', value: stats.ready, color: 'bg-purple-500' },
                  { label: 'Сервирани', value: stats.served, color: 'bg-indigo-500' },
                  { label: 'Отменени', value: stats.cancelled, color: 'bg-red-500' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-3">
                    <div className="w-24 text-sm text-gray-600">{item.label}</div>
                    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${item.color} transition-all`}
                        style={{ width: `${(item.value / stats.total_orders) * 100}%` }}
                      />
                    </div>
                    <div className="w-12 text-right font-medium text-gray-900">{item.value}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Топ сервитьори</h3>
              <div className="space-y-3">
                {[...staff].sort((a, b) => b.total_sales - a.total_sales).map((s, idx) => (
                  <div key={s.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <span className={`w-8 h-8 rounded-full flex items-center justify-center text-gray-900 font-bold ${idx === 0 ? 'bg-yellow-500' : idx === 1 ? 'bg-gray-400' : idx === 2 ? 'bg-orange-400' : 'bg-gray-300'}`}>
                      {idx + 1}
                    </span>
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{s.name}</div>
                      <div className="text-xs text-gray-500">{s.active_orders} активни</div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-gray-900">{(s.total_sales || 0).toFixed(2)} лв</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">По тип поръчка</h3>
              <div className="grid grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <span className="text-3xl">🍽️</span>
                  <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'dine_in').length}</div>
                  <div className="text-xs text-gray-500">На място</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <span className="text-3xl">📦</span>
                  <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'takeaway').length}</div>
                  <div className="text-xs text-gray-500">За вкъщи</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <span className="text-3xl">🚗</span>
                  <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'delivery').length}</div>
                  <div className="text-xs text-gray-500">Доставка</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <span className="text-3xl">🚙</span>
                  <div className="font-bold text-gray-900 mt-2">{orders.filter(o => o.type === 'drive_thru').length}</div>
                  <div className="text-xs text-gray-500">Drive-Thru</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Order Detail Modal */}
      <AnimatePresence>
        {selectedOrder && !showPaymentModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedOrder(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
              onClick={e => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-2xl font-bold text-gray-900">Поръчка #{selectedOrder.order_number}</h2>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusConfig(selectedOrder.status).bg} ${getStatusConfig(selectedOrder.status).color}`}>
                        {getStatusConfig(selectedOrder.status).label}
                      </span>
                    </div>
                    <p className="text-gray-500 mt-1">
                      {selectedOrder.table} • {getTypeLabel(selectedOrder.type)} • {selectedOrder.waiter} • {selectedOrder.guests} гости
                    </p>
                  </div>
                  <button onClick={() => setSelectedOrder(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
                </div>
              </div>

              {/* Order Items */}
              <div className="p-6 max-h-80 overflow-y-auto">
                <h3 className="font-medium text-gray-900 mb-3">Артикули</h3>
                <div className="space-y-3">
                  {selectedOrder.items.map((item) => {
                    const itemStatus = getStatusConfig(item.status);
                    return (
                      <div key={item.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <span className={`w-3 h-3 rounded-full ${item.status === 'served' ? 'bg-green-500' : item.status === 'ready' ? 'bg-blue-500' : item.status === 'preparing' ? 'bg-orange-500 animate-pulse' : 'bg-gray-300'}`} />
                          <div>
                            <div className="font-medium text-gray-900">{item.quantity}x {item.name}</div>
                            {item.modifiers && item.modifiers.length > 0 && (
                              <div className="text-xs text-gray-500">{item.modifiers.map(m => m.name).join(', ')}</div>
                            )}
                            {item.notes && <div className="text-xs text-orange-600">📝 {item.notes}</div>}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-gray-900 font-medium">{((item.quantity * item.unit_price) || 0).toFixed(2)} лв</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${itemStatus.bg} ${itemStatus.color}`}>{itemStatus.label}</span>
                          {item.sent_to_kitchen && !['served', 'cancelled'].includes(item.status) && (
                            <div className="flex gap-1">
                              {item.status === 'pending' && (
                                <button onClick={() => handleUpdateItemStatus(selectedOrder.id, item.id, 'preparing')} className="p-1 bg-orange-100 text-orange-600 rounded hover:bg-orange-200 text-xs">👨‍🍳</button>
                              )}
                              {item.status === 'preparing' && (
                                <button onClick={() => handleUpdateItemStatus(selectedOrder.id, item.id, 'ready')} className="p-1 bg-green-100 text-green-600 rounded hover:bg-green-200 text-xs">✓</button>
                              )}
                              {item.status === 'ready' && (
                                <button onClick={() => handleUpdateItemStatus(selectedOrder.id, item.id, 'served')} className="p-1 bg-purple-100 text-purple-600 rounded hover:bg-purple-200 text-xs">🍽️</button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {selectedOrder.notes && (
                  <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                    <div className="text-sm font-medium text-yellow-800">Бележки</div>
                    <div className="text-sm text-yellow-700">{selectedOrder.notes}</div>
                  </div>
                )}

                {selectedOrder.delivery_info && (
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                    <div className="text-sm font-medium text-blue-800">Информация за доставка</div>
                    <div className="text-sm text-blue-700">📍 {selectedOrder.delivery_info.address}</div>
                    <div className="text-sm text-blue-700">📞 {selectedOrder.delivery_info.phone}</div>
                    {selectedOrder.delivery_info.estimated_time && (
                      <div className="text-sm text-blue-700">⏱️ {selectedOrder.delivery_info.estimated_time}</div>
                    )}
                  </div>
                )}
              </div>

              {/* Order Summary */}
              <div className="p-6 bg-gray-50 border-t border-gray-100">
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-gray-600"><span>Междинна сума</span><span>{(selectedOrder.subtotal || 0).toFixed(2)} лв</span></div>
                  <div className="flex justify-between text-gray-600"><span>ДДС (20%)</span><span>{(selectedOrder.tax || 0).toFixed(2)} лв</span></div>
                  {selectedOrder.discount > 0 && (
                    <div className="flex justify-between text-green-600"><span>Отстъпка</span><span>-{(selectedOrder.discount || 0).toFixed(2)} лв</span></div>
                  )}
                  <div className="flex justify-between text-xl font-bold text-gray-900 pt-2 border-t border-gray-200">
                    <span>Общо</span><span>{(selectedOrder.total || 0).toFixed(2)} лв</span>
                  </div>
                </div>

                {/* Priority Controls */}
                {!['paid', 'cancelled'].includes(selectedOrder.status) && (
                  <div className="flex gap-2 mb-4">
                    <span className="text-sm text-gray-500 self-center">Приоритет:</span>
                    <button
                      onClick={() => handleSetPriority('normal')}
                      className={`px-3 py-1 rounded-lg text-sm ${selectedOrder.priority === 'normal' ? 'bg-gray-600 text-white' : 'bg-gray-100 text-gray-600'}`}
                    >
                      Нормален
                    </button>
                    <button
                      onClick={() => handleSetPriority('high')}
                      className={`px-3 py-1 rounded-lg text-sm ${selectedOrder.priority === 'high' ? 'bg-orange-500 text-white' : 'bg-orange-50 text-orange-600'}`}
                    >
                      ⚡ VIP
                    </button>
                    <button
                      onClick={() => handleSetPriority('rush')}
                      className={`px-3 py-1 rounded-lg text-sm ${selectedOrder.priority === 'rush' ? 'bg-red-500 text-white' : 'bg-red-50 text-red-600'}`}
                    >
                      🚨 RUSH
                    </button>
                  </div>
                )}

                <div className="flex gap-3">
                  {selectedOrder.status === 'new' && (
                    <button onClick={() => handleUpdateOrderStatus(selectedOrder.id, 'preparing')} className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 font-medium">
                      👨‍🍳 Започни готвене
                    </button>
                  )}
                  {selectedOrder.status === 'preparing' && (
                    <button onClick={() => handleUpdateOrderStatus(selectedOrder.id, 'ready')} className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600 font-medium">
                      ✅ Готова
                    </button>
                  )}
                  {selectedOrder.status === 'ready' && (
                    <button onClick={() => handleUpdateOrderStatus(selectedOrder.id, 'served')} className="flex-1 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600 font-medium">
                      🍽️ Сервирана
                    </button>
                  )}
                  {selectedOrder.status === 'served' && (
                    <>
                      <button onClick={() => setShowSplitBillModal(true)} className="flex-1 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 font-medium">
                        ✂️ Раздели сметка
                      </button>
                      <button onClick={() => setShowPaymentModal(true)} className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600 font-medium">
                        💰 Плащане
                      </button>
                    </>
                  )}
                  {selectedOrder.status === 'paid' && (
                    <button onClick={() => { setRefundAmount(selectedOrder.total); setShowRefundModal(true); }} className="flex-1 py-3 bg-red-100 text-red-700 rounded-xl hover:bg-red-200 font-medium">
                      💸 Възстановяване
                    </button>
                  )}
                </div>

                {/* Secondary Actions */}
                {!['paid', 'cancelled'].includes(selectedOrder.status) && (
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleReprintOrder('kitchen')}
                      className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      🖨️ Печат кухня
                    </button>
                    <button
                      onClick={() => handleReprintOrder('bar')}
                      className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                    >
                      🖨️ Печат бар
                    </button>
                    <button
                      onClick={() => setShowVoidModal(true)}
                      className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 text-sm"
                    >
                      ❌ Анулирай
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Void Order Modal */}
      <AnimatePresence>
        {showVoidModal && selectedOrder && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowVoidModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Анулиране на поръчка #{selectedOrder.order_number}</h2>
              <p className="text-gray-500 mb-4">Въведете причина за анулиране на поръчката. Това действие е необратимо.</p>

              <textarea
                value={voidReason}
                onChange={(e) => setVoidReason(e.target.value)}
                placeholder="Причина за анулиране..."
                className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 focus:border-red-500 focus:outline-none mb-4"
                rows={3}
              />

              <div className="flex gap-3">
                <button
                  onClick={() => { setShowVoidModal(false); setVoidReason(''); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                >
                  Отказ
                </button>
                <button
                  onClick={handleVoidOrder}
                  disabled={!voidReason}
                  className="flex-1 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ❌ Анулирай поръчка
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Refund Order Modal */}
      <AnimatePresence>
        {showRefundModal && selectedOrder && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowRefundModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Възстановяване на сума</h2>
              <p className="text-gray-500 mb-4">Поръчка #{selectedOrder.order_number} - Обща сума: {(selectedOrder.total || 0).toFixed(2)} лв</p>

              <div className="mb-4">
                <label className="block text-sm text-gray-600 mb-1">Сума за възстановяване</label>
                <input
                  type="number"
                  value={refundAmount}
                  onChange={(e) => setRefundAmount(parseFloat(e.target.value) || 0)}
                  max={selectedOrder.total}
                  className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm text-gray-600 mb-1">Причина</label>
                <textarea
                  value={refundReason}
                  onChange={(e) => setRefundReason(e.target.value)}
                  placeholder="Причина за възстановяване..."
                  className="w-full p-3 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none"
                  rows={2}
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => { setShowRefundModal(false); setRefundAmount(0); setRefundReason(''); }}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                >
                  Отказ
                </button>
                <button
                  onClick={handleRefundOrder}
                  disabled={!refundAmount || !refundReason}
                  className="flex-1 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  💸 Възстанови {(refundAmount || 0).toFixed(2)} лв
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Payment Modal */}
      <AnimatePresence>
        {showPaymentModal && selectedOrder && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowPaymentModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Плащане на поръчка #{selectedOrder.order_number}</h2>

              <div className="text-center mb-6">
                <div className="text-4xl font-bold text-gray-900">{(selectedOrder.total || 0).toFixed(2)} лв</div>
                <div className="text-gray-500">Общо за плащане</div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <button
                  onClick={() => { handleUpdateOrderStatus(selectedOrder.id, 'paid', 'cash'); setShowPaymentModal(false); setSelectedOrder(null); }}
                  className="py-6 bg-green-50 border-2 border-green-200 rounded-xl hover:border-green-400 transition-colors"
                >
                  <span className="text-4xl block mb-2">💵</span>
                  <span className="font-medium text-green-700">В брой</span>
                </button>
                <button
                  onClick={() => { handleUpdateOrderStatus(selectedOrder.id, 'paid', 'card'); setShowPaymentModal(false); setSelectedOrder(null); }}
                  className="py-6 bg-blue-50 border-2 border-blue-200 rounded-xl hover:border-blue-400 transition-colors"
                >
                  <span className="text-4xl block mb-2">💳</span>
                  <span className="font-medium text-blue-700">С карта</span>
                </button>
              </div>

              <button
                onClick={() => setShowPaymentModal(false)}
                className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
              >
                Отказ
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Split Bill Modal */}
      <AnimatePresence>
        {showSplitBillModal && selectedOrder && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowSplitBillModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl max-w-md w-full p-6"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Раздели сметка #{selectedOrder.order_number}</h2>

              <div className="text-center mb-6">
                <div className="text-3xl font-bold text-gray-900">{(selectedOrder.total || 0).toFixed(2)} лв</div>
                <div className="text-gray-500">Общо</div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">На колко части?</label>
                <div className="flex gap-2">
                  {[2, 3, 4, 5, 6].map(n => (
                    <button
                      key={n}
                      onClick={() => setSplitWays(n)}
                      className={`flex-1 py-3 rounded-xl font-bold text-lg transition-colors ${
                        splitWays === n
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-blue-50 rounded-xl p-4 mb-6">
                <div className="text-center">
                  <div className="text-sm text-blue-600 mb-1">Всеки плаща</div>
                  <div className="text-3xl font-bold text-blue-700">
                    {((selectedOrder.total / splitWays) || 0).toFixed(2)} лв
                  </div>
                  <div className="text-sm text-blue-500 mt-1">
                    {splitWays} x {((selectedOrder.total / splitWays) || 0).toFixed(2)} лв = {(selectedOrder.total || 0).toFixed(2)} лв
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <button
                  onClick={() => {
                    handleUpdateOrderStatus(selectedOrder.id, 'paid', 'cash');
                    setShowSplitBillModal(false);
                    setSelectedOrder(null);
                  }}
                  className="py-4 bg-green-50 border-2 border-green-200 rounded-xl hover:border-green-400 transition-colors"
                >
                  <span className="text-2xl block mb-1">💵</span>
                  <span className="font-medium text-green-700 text-sm">Всички в брой</span>
                </button>
                <button
                  onClick={() => {
                    handleUpdateOrderStatus(selectedOrder.id, 'paid', 'card');
                    setShowSplitBillModal(false);
                    setSelectedOrder(null);
                  }}
                  className="py-4 bg-blue-50 border-2 border-blue-200 rounded-xl hover:border-blue-400 transition-colors"
                >
                  <span className="text-2xl block mb-1">💳</span>
                  <span className="font-medium text-blue-700 text-sm">Всички с карта</span>
                </button>
              </div>

              <button
                onClick={() => setShowSplitBillModal(false)}
                className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
              >
                Отказ
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Void Item Modal */}
      <AnimatePresence>
        {showVoidItemModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => { setShowVoidItemModal(false); setVoidItemId(null); setVoidItemReason(''); }}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-white rounded-2xl p-6 w-full max-w-md mx-4"
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-lg font-bold text-gray-900 mb-4">Анулиране на артикул</h3>
              <input
                type="text"
                autoFocus
                value={voidItemReason}
                onChange={(e) => setVoidItemReason(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && voidItemReason) handleConfirmVoidItem();
                  if (e.key === 'Escape') { setShowVoidItemModal(false); setVoidItemId(null); setVoidItemReason(''); }
                }}
                placeholder="Причина за анулиране на артикула..."
                className="w-full px-4 py-2 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:outline-none mb-4"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowVoidItemModal(false); setVoidItemId(null); setVoidItemReason(''); }}
                  className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200"
                >
                  Отказ
                </button>
                <button
                  onClick={handleConfirmVoidItem}
                  disabled={!voidItemReason}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Потвърди
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
