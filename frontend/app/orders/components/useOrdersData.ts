"use client";
import { useState, useEffect, useRef } from 'react';
import { apiFetch, api } from '@/lib/api';
import { toast } from '@/lib/toast';
import type { Order, OrderItem, Table, Staff, OrderStats, OrderTab } from './types';
export function useOrdersData() {
  const [activeTab, setActiveTab] = useState<OrderTab>('active');
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
  const [showNewOrderModal, setShowNewOrderModal] = useState(false);
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
    try {
      const [ordersRes, tablesRes, staffRes, statsRes] = await Promise.allSettled([
        apiFetch('/orders'),
        apiFetch('/admin/tables'),
        apiFetch('/staff'),
        apiFetch('/orders/stats'),
      ]);
      // Process orders
      if (ordersRes.status === 'fulfilled') {
        const data: any = ordersRes.value;
        const ordersArray = Array.isArray(data) ? data : (data.items || data.orders || []);
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
      if (tablesRes.status === 'fulfilled') {
        const data_2: any = tablesRes.value;
        const tablesArray = Array.isArray(data_2) ? data_2 : (data_2.items || data_2.tables || []);
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
      if (staffRes.status === 'fulfilled') {
        const data_3: any = staffRes.value;
        const staffArray = Array.isArray(data_3) ? data_3 : (data_3.items || data_3.staff || []);
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
      if (statsRes.status === 'fulfilled') {
        const data_4: any = statsRes.value;
        const transformedStats: OrderStats = {
          total_orders: data_4.total_orders || 0,
          new_orders: data_4.new_orders || data_4.new || 0,
          preparing: data_4.preparing || 0,
          ready: data_4.ready || 0,
          served: data_4.served || 0,
          paid: data_4.paid || data_4.completed || 0,
          cancelled: data_4.cancelled || 0,
          total_revenue: data_4.total_revenue || data_4.revenue || 0,
          avg_order_value: data_4.avg_order_value || data_4.average_order_value || 0,
          avg_prep_time: data_4.avg_prep_time || data_4.average_prep_time || 0,
        };
        setStats(transformedStats);
      } else {
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
  const handleUpdateOrderStatus = async (orderId: string, newStatus: Order['status'], paymentMethod?: string) => {
    try {
      const bodyData: Record<string, string> = { status: newStatus };
      if (paymentMethod) bodyData.payment_method = paymentMethod;
      await api.put(`/orders/${orderId}/status`, bodyData);
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: newStatus, updated_at: new Date().toISOString() } : o));
      if (selectedOrder?.id === orderId) {
        setSelectedOrder(prev => prev ? { ...prev, status: newStatus } : null);
      }
    } catch (error) {
      console.error('Error updating order status:', error);
      toast.error('Error updating order status. Please try again.');
    }
  };
  const handleUpdateItemStatus = async (orderId: string, itemId: string, newStatus: OrderItem['status']) => {
    try {
      await api.patch(`/orders/${orderId}/items/${itemId}/status`, { status: newStatus });
      setOrders(prev => prev.map(o => {
        if (o.id === orderId) {
          const updatedItems = o.items.map(item =>
            item.id === itemId ? { ...item, status: newStatus, prepared_at: newStatus === 'ready' ? new Date().toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' }) : item.prepared_at } : item
          );
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
    } catch (error) {
      console.error('Error updating item status:', error);
      toast.error('Error updating item status. Please try again.');
    }
  };
  const handleVoidOrder = async () => {
    if (!selectedOrder || !voidReason) return;
    try {
      await api.post(`/orders/${selectedOrder.id}/void`, { reason: voidReason });
      setOrders(prev => prev.map(o => o.id === selectedOrder.id ? { ...o, status: 'cancelled' } : o));
      setShowVoidModal(false);
      setSelectedOrder(null);
      setVoidReason('');
    } catch (error) {
      console.error('Error voiding order:', error);
    }
  };
  const handleConfirmVoidItem = async () => {
    if (!selectedOrder || !voidItemId || !voidItemReason) return;
    const itemId = voidItemId;
    try {
      const data: any = await api.post(`/orders/${selectedOrder.id}/items/${itemId}/void`, { reason: voidItemReason });
      setOrders(prev => prev.map(o => {
        if (o.id === selectedOrder.id) {
          return {
            ...o,
            items: o.items.map(i => i.id === itemId ? { ...i, status: 'cancelled' as const } : i),
            total: data.new_order_total || o.total
          };
        }
        return o;
      }));
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
    try {
      await api.post(`/orders/${selectedOrder.id}/refund`, {
        amount: refundAmount,
        reason: refundReason,
        refund_method: 'cash'
      });
      setShowRefundModal(false);
      setRefundAmount(0);
      setRefundReason('');
      loadData();
    } catch (error) {
      console.error('Error refunding order:', error);
    }
  };
  const handleReprintOrder = async (station: string = 'kitchen') => {
    if (!selectedOrder) return;
    try {
      await api.post(`/orders/${selectedOrder.id}/reprint`, { station });
      toast.success('Reprint sent!');
    } catch (error) {
      console.error('Error reprinting order:', error);
    }
  };
  const handleSetPriority = async (priority: 'rush' | 'high' | 'normal') => {
    if (!selectedOrder) return;
    const path = priority === 'rush'
      ? `/kitchen/rush/${selectedOrder.id}`
      : priority === 'high'
      ? `/kitchen/vip/${selectedOrder.id}`
      : null;
    if (path) {
      try {
        await api.post(path);
        setOrders(prev => prev.map(o => o.id === selectedOrder.id ? { ...o, priority } : o));
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
    { id: 'active' as const, label: 'Активни поръчки', icon: '📋', count: activeOrders.length },
    { id: 'history' as const, label: 'История', icon: '📚' },
    { id: 'floor' as const, label: 'План на залата', icon: '🗺️' },
    { id: 'analytics' as const, label: 'Анализ', icon: '📊' },
  ];
  return {
    // State
    activeTab, setActiveTab,
    orders, tables, staff, stats, loading,
    statusFilter, setStatusFilter,
    typeFilter, setTypeFilter,
    searchQuery, setSearchQuery,
    dateRange, setDateRange,
    selectedOrder, setSelectedOrder,
    showNewOrderModal, setShowNewOrderModal,
    showPaymentModal, setShowPaymentModal,
    showSplitBillModal, setShowSplitBillModal,
    splitWays, setSplitWays,
    showVoidModal, setShowVoidModal,
    showRefundModal, setShowRefundModal,
    voidReason, setVoidReason,
    refundAmount, setRefundAmount,
    refundReason, setRefundReason,
    showVoidItemModal, setShowVoidItemModal,
    voidItemReason, setVoidItemReason,
    voidItemId, setVoidItemId,
    autoRefresh, setAutoRefresh,
    soundEnabled, setSoundEnabled,
    // Derived
    filteredOrders, activeOrders, tabs,
    // Handlers
    loadData,
    handleUpdateOrderStatus,
    handleUpdateItemStatus,
    handleVoidOrder,
    handleConfirmVoidItem,
    handleRefundOrder,
    handleReprintOrder,
    handleSetPriority,
    // Helpers
    getStatusConfig, getTypeLabel, getPriorityColor,
  };
}