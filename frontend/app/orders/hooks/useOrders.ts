'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Order, OrderItem, Table, Staff, OrderStats } from '../types';
import { api } from '@/lib/api';
interface UseOrdersReturn {
  orders: Order[];
  tables: Table[];
  staff: Staff[];
  stats: OrderStats | null;
  loading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
  updateOrderStatus: (orderId: string, status: Order['status']) => Promise<void>;
  updateItemStatus: (orderId: string, itemId: string, status: OrderItem['status']) => Promise<void>;
  voidOrder: (orderId: string, reason: string) => Promise<boolean>;
  refundOrder: (orderId: string, amount: number, reason: string) => Promise<boolean>;
  setPriority: (orderId: string, priority: Order['priority']) => Promise<void>;
  reprintOrder: (orderId: string, station: string) => Promise<void>;
}
export function useOrders(autoRefresh: boolean = true, refreshIntervalMs: number = 30000): UseOrdersReturn {
  const [orders, setOrders] = useState<Order[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [stats, setStats] = useState<OrderStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refreshInterval = useRef<NodeJS.Timeout | null>(null);
  const transformOrders = (data: any[]): Order[] => {
    return data.map((order: any) => ({
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
  };
  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ordersRes, tablesRes, staffRes, statsRes] = await Promise.allSettled([
  api.get('/orders'),
  api.get('/admin/tables'),
  api.get('/staff'),
  api.get('/orders/stats')
]);
      // Process orders
      if (ordersRes.status === 'fulfilled') {
        const data: any = ordersRes.value;
        const ordersArray = Array.isArray(data) ? data : (data.items || data.orders || []);
        setOrders(transformOrders(ordersArray));
      } else {
        setOrders([]);
      }
      // Process tables
      if (tablesRes.status === 'fulfilled') {
        const data_tables: any = tablesRes.value;
        const tablesArray = Array.isArray(data_tables) ? data_tables : (data_tables.items || data_tables.tables || []);
        setTables(tablesArray.map((table: any) => ({
          id: String(table.id),
          number: table.number || `T${table.id}`,
          seats: table.capacity || table.seats || 4,
          status: table.status || 'available',
          current_order_id: table.current_order_id ? String(table.current_order_id) : undefined,
        })));
      }
      // Process staff
      if (staffRes.status === 'fulfilled') {
        const data_staff: any = staffRes.value;
        const staffArray = Array.isArray(data_staff) ? data_staff : (data_staff.items || data_staff.staff || []);
        setStaff(staffArray.map((s: any) => ({
          id: String(s.id),
          name: s.name || s.full_name || 'Unknown',
          role: s.role || 'waiter',
          active_orders: s.active_orders || 0,
          total_sales: s.total_sales || 0,
          avatar: s.avatar,
        })));
      }
      // Process stats
      if (statsRes.status === 'fulfilled') {
        const data_stats: any = statsRes.value;
        setStats({
          total_orders: data_stats.total_orders || 0,
          new_orders: data_stats.new_orders || data_stats.new || 0,
          preparing: data_stats.preparing || 0,
          ready: data_stats.ready || 0,
          served: data_stats.served || 0,
          paid: data_stats.paid || data_stats.completed || 0,
          cancelled: data_stats.cancelled || 0,
          total_revenue: data_stats.total_revenue || data_stats.revenue || 0,
          avg_order_value: data_stats.avg_order_value || data_stats.average_order_value || 0,
          avg_prep_time: data_stats.avg_prep_time || data_stats.average_prep_time || 0,
        });
      }
    } catch (err) {
      console.error('Error fetching orders data:', err);
      setError('Failed to load orders data');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    refreshData();
    if (autoRefresh) {
      refreshInterval.current = setInterval(refreshData, refreshIntervalMs);
    }
    return () => {
      if (refreshInterval.current) {
        clearInterval(refreshInterval.current);
      }
    };
  }, [autoRefresh, refreshIntervalMs, refreshData]);
  const updateOrderStatus = useCallback(async (orderId: string, newStatus: Order['status']) => {
    try {
      await api.put(`/orders/${orderId}/status`, { status: newStatus });
    } catch (err) {
      console.error('Error updating order status:', err);
    }
    // Update local state optimistically
    setOrders(prev => prev.map(o =>
      o.id === orderId
        ? { ...o, status: newStatus, updated_at: new Date().toISOString() }
        : o
    ));
  }, []);
  const updateItemStatus = useCallback(async (orderId: string, itemId: string, newStatus: OrderItem['status']) => {
    try {
      await api.patch(`/orders/${orderId}/items/${itemId}/status`, { status: newStatus });
    } catch (err) {
      console.error('Error updating item status:', err);
    }
    // Update local state optimistically
    setOrders(prev => prev.map(o => {
      if (o.id !== orderId) return o;
      const updatedItems = o.items.map(item =>
        item.id === itemId
          ? { ...item, status: newStatus, prepared_at: newStatus === 'ready' ? new Date().toISOString() : item.prepared_at }
          : item
      );
      const allReady = updatedItems.filter(i => i.sent_to_kitchen).every(i => i.status === 'ready' || i.status === 'served');
      const allServed = updatedItems.every(i => i.status === 'served');
      return {
        ...o,
        items: updatedItems,
        status: allServed ? 'served' : allReady && o.status === 'preparing' ? 'ready' : o.status
      };
    }));
  }, []);
  const voidOrder = useCallback(async (orderId: string, reason: string): Promise<boolean> => {
    try {
      await api.post(`/orders/${orderId}/void`, { reason });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'cancelled' } : o));
      return true;
    } catch (err) {
      console.error('Error voiding order:', err);
    }
    return false;
  }, []);
  const refundOrder = useCallback(async (orderId: string, amount: number, reason: string): Promise<boolean> => {
    try {
      await api.post(`/orders/${orderId}/refund`, { amount, reason, refund_method: 'cash' });
      await refreshData();
      return true;
    } catch (err) {
      console.error('Error refunding order:', err);
    }
    return false;
  }, [refreshData]);
  const setPriority = useCallback(async (orderId: string, priority: Order['priority']) => {
    const path = priority === 'rush'
      ? `/kitchen/rush/${orderId}`
      : priority === 'high'
      ? `/kitchen/vip/${orderId}`
      : null;
    if (path) {
      try {
        await api.post(path);
      } catch (err) {
        console.error('Error setting priority:', err);
      }
    }
    setOrders(prev => prev.map(o => o.id === orderId ? { ...o, priority } : o));
  }, []);
  const reprintOrder = useCallback(async (orderId: string, station: string) => {
    try {
      await api.post(`/orders/${orderId}/reprint`, { station });
    } catch (err) {
      console.error('Error reprinting order:', err);
    }
  }, []);
  return {
    orders,
    tables,
    staff,
    stats,
    loading,
    error,
    refreshData,
    updateOrderStatus,
    updateItemStatus,
    voidOrder,
    refundOrder,
    setPriority,
    reprintOrder,
  };
}