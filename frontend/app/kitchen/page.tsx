'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface Station {
  id: string;
  name: string;
  type: string;
  icon: string;
  current_load: number;
  max_capacity: number;
  active_tickets: number;
  overdue_tickets: number;
  avg_time: number;
}

interface Alert {
  id: number;
  type: 'rush' | 'overdue' | 'item_86' | 'vip';
  message: string;
  order_id?: number;
  created_at: string;
}

interface RecentTicket {
  id: string;
  order_id: number;
  table: string;
  items: number;
  status: 'bumped' | 'in_progress';
  cook_time: number;
  station: string;
}


const getStationIcon = (type: string): string => {
  switch (type) {
    case 'kitchen': return '👨‍🍳';
    case 'bar': return '🍸';
    case 'grill': return '🔥';
    case 'expo': return '📤';
    case 'fryer': return '🍟';
    case 'salad': return '🥗';
    case 'dessert': return '🍰';
    case 'prep': return '🔪';
    default: return '🍽️';
  }
};

export default function KitchenPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recentTickets, setRecentTickets] = useState<RecentTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    activeOrders: 0,
    avgPrepTime: 0,
    pendingItems: 0,
    completedToday: 0,
    rushOrders: 0,
    items86: 0,
  });

  const loadStations = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/kitchen-display/stations`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to load stations');
      const data = await response.json();

      // Transform station data to match the expected format
      const transformedStations: Station[] = data.map((station: {
        station_id: string;
        name: string;
        type: string;
        current_load: number;
        max_capacity: number;
        avg_cook_time?: number;
      }) => ({
        id: station.station_id,
        name: station.name,
        type: station.type,
        icon: getStationIcon(station.type),
        current_load: station.current_load ?? 0,
        max_capacity: station.max_capacity ?? 15,
        active_tickets: station.current_load ?? 0,
        overdue_tickets: 0, // Will be updated from tickets
        avg_time: station.avg_cook_time ?? 10,
      }));

      setStations(transformedStations);
    } catch (err) {
      console.error('Error loading stations:', err);
      // Set default stations if API fails
      setStations([
        { id: 'KITCHEN-1', name: 'Main Kitchen', type: 'kitchen', icon: '👨‍🍳', current_load: 0, max_capacity: 15, active_tickets: 0, overdue_tickets: 0, avg_time: 12 },
        { id: 'BAR-1', name: 'Bar', type: 'bar', icon: '🍸', current_load: 0, max_capacity: 20, active_tickets: 0, overdue_tickets: 0, avg_time: 3 },
        { id: 'GRILL-1', name: 'Grill Station', type: 'grill', icon: '🔥', current_load: 0, max_capacity: 8, active_tickets: 0, overdue_tickets: 0, avg_time: 15 },
        { id: 'EXPO-1', name: 'Expo Window', type: 'expo', icon: '📤', current_load: 0, max_capacity: 25, active_tickets: 0, overdue_tickets: 0, avg_time: 2 },
      ]);
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/kitchen-alerts/?active_only=true`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to load alerts');
      const data = await response.json();

      // Transform alerts to match expected format
      const transformedAlerts: Alert[] = data.map((alert: {
        id: number;
        alert_type: string;
        message: string;
        order_id?: number;
        created_at: string;
      }) => ({
        id: alert.id,
        type: mapAlertType(alert.alert_type),
        message: alert.message,
        order_id: alert.order_id,
        created_at: alert.created_at,
      }));

      setAlerts(transformedAlerts);
    } catch (err) {
      console.error('Error loading alerts:', err);
      setAlerts([]);
    }
  }, []);

  const loadRecentTickets = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/kitchen-display/tickets?status=bumped`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to load tickets');
      const data = await response.json();

      // Transform tickets to match expected format
      const transformedTickets: RecentTicket[] = data.slice(0, 10).map((ticket: {
        ticket_id: string;
        order_id: number;
        table_number?: string;
        item_count: number;
        status: string;
        cook_time_seconds?: number;
        station_id: string;
      }) => ({
        id: ticket.ticket_id,
        order_id: ticket.order_id,
        table: ticket.table_number || 'N/A',
        items: ticket.item_count ?? 0,
        status: ticket.status as 'bumped' | 'in_progress',
        cook_time: ticket.cook_time_seconds ? Math.round(ticket.cook_time_seconds / 60) : 0,
        station: getStationName(ticket.station_id),
      }));

      setRecentTickets(transformedTickets);
    } catch (err) {
      console.error('Error loading tickets:', err);
      setRecentTickets([]);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/kitchen-alerts/stats`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to load stats');
      const data = await response.json();

      // Calculate active orders and pending items from order statuses
      const ordersByStatus = data.orders_by_status || {};
      const activeOrders = (ordersByStatus['pending'] || 0) + (ordersByStatus['preparing'] || 0) + (ordersByStatus['in_progress'] || 0);
      const pendingItems = activeOrders * 2; // Approximate items per order

      setStats({
        activeOrders: activeOrders,
        avgPrepTime: data.avg_prep_time_minutes ?? 0,
        pendingItems: pendingItems,
        completedToday: data.orders_completed_today ?? 0,
        rushOrders: data.rush_orders_today ?? 0,
        items86: data.items_86_count ?? 0,
      });
    } catch (err) {
      console.error('Error loading stats:', err);
      setStats({
        activeOrders: 0,
        avgPrepTime: 0,
        pendingItems: 0,
        completedToday: 0,
        rushOrders: 0,
        items86: 0,
      });
    }
  }, []);

  const mapAlertType = (alertType: string): 'rush' | 'overdue' | 'item_86' | 'vip' => {
    switch (alertType) {
      case 'rush_order': return 'rush';
      case 'order_delayed': return 'overdue';
      case 'item_86': return 'item_86';
      case 'vip_order': return 'vip';
      default: return 'rush';
    }
  };

  const getStationName = (stationId: string): string => {
    const stationNames: Record<string, string> = {
      'KITCHEN-1': 'Main Kitchen',
      'BAR-1': 'Bar',
      'GRILL-1': 'Grill Station',
      'EXPO-1': 'Expo Window',
    };
    return stationNames[stationId] || stationId;
  };

  useEffect(() => {
    const loadAllData = async () => {
      setLoading(true);
      setError(null);
      try {
        await Promise.all([
          loadStations(),
          loadAlerts(),
          loadRecentTickets(),
          loadStats(),
        ]);
      } catch (err) {
        setError('Failed to load kitchen data');
        console.error('Error loading kitchen data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadAllData();

    // Refresh data every 30 seconds
    const interval = setInterval(loadAllData, 30000);
    return () => clearInterval(interval);
  }, [loadStations, loadAlerts, loadRecentTickets, loadStats]);

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'rush': return 'bg-warning-100 text-warning-700 border-warning-200';
      case 'overdue': return 'bg-error-100 text-error-700 border-error-200';
      case 'vip': return 'bg-accent-100 text-accent-700 border-accent-200';
      case 'item_86': return 'bg-surface-100 text-surface-700 border-surface-200';
      default: return 'bg-surface-100 text-surface-700 border-surface-200';
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'rush': return '🚨';
      case 'overdue': return '⏰';
      case 'vip': return '👑';
      case 'item_86': return '❌';
      default: return '📢';
    }
  };

  const getLoadColor = (load: number, max: number) => {
    const percent = (load / max) * 100;
    if (percent >= 90) return 'bg-error-500';
    if (percent >= 70) return 'bg-warning-500';
    if (percent >= 50) return 'bg-primary-500';
    return 'bg-success-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-error-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg font-medium hover:bg-primary-600"
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
        <div>
          <h1 className="text-2xl font-display font-bold text-surface-900">Kitchen Management</h1>
          <p className="text-surface-500 mt-1">Real-time kitchen operations overview</p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/kitchen/display"
            className="px-4 py-2 bg-primary-500 text-gray-900 rounded-lg font-medium hover:bg-primary-600 transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Open KDS
          </Link>
          <button
            onClick={() => {
              localStorage.removeItem('access_token');
              window.location.href = '/login';
            }}
            className="p-2 text-surface-500 hover:text-surface-700 hover:bg-surface-100 rounded-lg transition-colors"
            title="Logout"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-6 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Active Orders</p>
          <p className="text-2xl font-display font-bold text-primary-600 mt-1">{stats.activeOrders}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Avg Prep Time</p>
          <p className="text-2xl font-display font-bold text-success-600 mt-1">{stats.avgPrepTime} min</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Pending Items</p>
          <p className="text-2xl font-display font-bold text-warning-600 mt-1">{stats.pendingItems}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Completed Today</p>
          <p className="text-2xl font-display font-bold text-surface-900 mt-1">{stats.completedToday}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">Rush Orders</p>
          <p className="text-2xl font-display font-bold text-warning-600 mt-1">{stats.rushOrders}</p>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-surface-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">86&apos;d Items</p>
          <p className="text-2xl font-display font-bold text-error-600 mt-1">{stats.items86}</p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Stations Overview */}
        <div className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Station Overview</h2>
            <Link href="/kitchen/stations" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
              Manage Stations
            </Link>
          </div>
          <div className="p-4 grid grid-cols-2 gap-4">
            {stations.map(station => (
              <Link
                key={station.id}
                href={`/kitchen/display?station=${station.id}`}
                className="p-4 rounded-xl border border-surface-100 hover:border-primary-200 hover:shadow-md transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{station.icon}</span>
                    <div>
                      <h3 className="font-semibold text-surface-900 group-hover:text-primary-600">{station.name}</h3>
                      <p className="text-xs text-surface-500">{station.active_tickets} active tickets</p>
                    </div>
                  </div>
                  {station.overdue_tickets > 0 && (
                    <span className="px-2 py-0.5 bg-error-100 text-error-700 rounded text-xs font-medium">
                      {station.overdue_tickets} overdue
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-surface-500">Load</span>
                    <span className="font-medium">{station.current_load}/{station.max_capacity}</span>
                  </div>
                  <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${getLoadColor(station.current_load, station.max_capacity)} transition-all`}
                      style={{ width: `${(station.current_load / station.max_capacity) * 100}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-surface-500">
                    <span>Avg: {station.avg_time} min</span>
                    <span>{Math.round((station.current_load / station.max_capacity) * 100)}% capacity</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Alerts */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Active Alerts</h2>
            <span className="px-2 py-0.5 bg-error-100 text-error-700 rounded-full text-xs font-medium">
              {alerts.length}
            </span>
          </div>
          <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="text-center py-8 text-surface-400">
                <span className="text-3xl block mb-2">✓</span>
                <p className="text-sm">No active alerts</p>
              </div>
            ) : (
              alerts.map(alert => (
                <div
                  key={alert.id}
                  className={`p-3 rounded-lg border ${getAlertColor(alert.type)} flex items-start gap-3`}
                >
                  <span className="text-lg">{getAlertIcon(alert.type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{alert.message}</p>
                    <p className="text-xs opacity-75 mt-0.5">
                      {new Date(alert.created_at).toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                  {alert.order_id && (
                    <Link
                      href={`/orders/${alert.order_id}`}
                      className="px-2 py-1 bg-black/50 rounded text-xs font-medium hover:bg-white/80"
                    >
                      View
                    </Link>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions & Recent Activity */}
      <div className="grid grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100">
            <h2 className="font-semibold text-surface-900">Quick Actions</h2>
          </div>
          <div className="p-4 space-y-2">
            <Link
              href="/kitchen/display"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-surface-50 transition-colors"
            >
              <span className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                <span className="text-xl">📺</span>
              </span>
              <div>
                <p className="font-medium text-surface-900">Kitchen Display</p>
                <p className="text-xs text-surface-500">View all active tickets</p>
              </div>
            </Link>
            <Link
              href="/kitchen/stations"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-surface-50 transition-colors"
            >
              <span className="w-10 h-10 rounded-lg bg-accent-100 flex items-center justify-center">
                <span className="text-xl">🏭</span>
              </span>
              <div>
                <p className="font-medium text-surface-900">Manage Stations</p>
                <p className="text-xs text-surface-500">Configure kitchen stations</p>
              </div>
            </Link>
            <Link
              href="/reports/kitchen"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-surface-50 transition-colors"
            >
              <span className="w-10 h-10 rounded-lg bg-success-100 flex items-center justify-center">
                <span className="text-xl">📊</span>
              </span>
              <div>
                <p className="font-medium text-surface-900">Kitchen Reports</p>
                <p className="text-xs text-surface-500">Performance analytics</p>
              </div>
            </Link>
            <Link
              href="/kitchen/86-items"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-surface-50 transition-colors"
            >
              <span className="w-10 h-10 rounded-lg bg-error-100 flex items-center justify-center">
                <span className="text-xl font-bold text-error-600">86</span>
              </span>
              <div>
                <p className="font-medium text-surface-900">86 Items</p>
                <p className="text-xs text-surface-500">Mark items unavailable</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Recent Completed */}
        <div className="col-span-2 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Recently Completed</h2>
            <span className="text-sm text-surface-500">Last 30 minutes</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Ticket</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Order</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Table</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Station</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Items</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Cook Time</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-surface-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {recentTickets.map(ticket => (
                  <tr key={ticket.id} className="hover:bg-surface-50">
                    <td className="px-4 py-3 text-sm font-medium text-surface-900">{ticket.id}</td>
                    <td className="px-4 py-3 text-sm text-surface-600">#{ticket.order_id}</td>
                    <td className="px-4 py-3 text-sm text-surface-600">{ticket.table}</td>
                    <td className="px-4 py-3 text-sm text-surface-600">{ticket.station}</td>
                    <td className="px-4 py-3 text-sm text-surface-600">{ticket.items}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`font-medium ${ticket.cook_time > 10 ? 'text-warning-600' : 'text-success-600'}`}>
                        {ticket.cook_time} min
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-success-100 text-success-700 rounded text-xs font-medium">
                        Completed
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
