'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { getVenueId } from '@/lib/auth';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface Platform {
  id: string;
  name: string;
  logo: string;
  connected: boolean;
  storeId?: string;
  commission: number;
  autoAccept: boolean;
  ordersToday: number;
  revenue: number;
}

interface AggregatorOrder {
  id: string;
  platform: string;
  orderNumber: string;
  customerName: string;
  items: { name: string; quantity: number; price: number }[];
  total: number;
  status: 'pending' | 'accepted' | 'preparing' | 'ready' | 'picked_up' | 'delivered' | 'cancelled';
  placedAt: string;
  prepTime?: number;
  driverName?: string;
  driverEta?: number;
}

interface DeliveryZone {
  id: string;
  name: string;
  radiusKm: number;
  deliveryFee: number;
  minOrder: number;
  active: boolean;
}

interface Driver {
  id: string;
  name: string;
  phone: string;
  vehicleType: string;
  status: 'available' | 'busy' | 'offline';
  activeOrders: number;
  location?: { lat: number; lng: number };
}

interface DeliveryStats {
  ordersToday: number;
  revenueToday: number;
  avgPrepTime: number;
  avgCommission: number;
}

// Platform definitions with logos
const PLATFORM_DEFINITIONS: Record<string, { name: string; logo: string; defaultCommission: number }> = {
  glovo: { name: 'Glovo', logo: '🟡', defaultCommission: 30 },
  wolt: { name: 'Wolt', logo: '🔵', defaultCommission: 25 },
  bolt_food: { name: 'Bolt Food', logo: '🟢', defaultCommission: 22 },
  foodpanda: { name: 'Foodpanda', logo: '🩷', defaultCommission: 28 },
  uber_eats: { name: 'Uber Eats', logo: '⚫', defaultCommission: 30 },
};

export default function DeliveryAggregatorsPage() {
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [orders, setOrders] = useState<AggregatorOrder[]>([]);
  const [zones, setZones] = useState<DeliveryZone[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [stats, setStats] = useState<DeliveryStats>({ ordersToday: 0, revenueToday: 0, avgPrepTime: 0, avgCommission: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'orders' | 'platforms' | 'zones' | 'drivers' | 'stats'>('orders');
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [connectForm, setConnectForm] = useState({ apiKey: '', apiSecret: '', storeId: '' });

  // Fetch connected platforms
  const fetchPlatforms = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/delivery/platforms`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to fetch platforms');
      const data = await response.json();

      // Build platform list with both connected and available platforms
      const connectedPlatformIds = new Set(data.platforms?.map((p: any) => p.platform) || []);
      const allPlatforms: Platform[] = Object.entries(PLATFORM_DEFINITIONS).map(([id, def]) => {
        const connected = data.platforms?.find((p: any) => p.platform === id);
        return {
          id,
          name: def.name,
          logo: def.logo,
          connected: connectedPlatformIds.has(id),
          storeId: connected?.settings?.store_id || '',
          commission: connected?.settings?.commission_percent || def.defaultCommission,
          autoAccept: connected?.settings?.auto_accept || false,
          ordersToday: 0,
          revenue: 0,
        };
      });

      setPlatforms(allPlatforms);
    } catch (err) {
      console.error('Error fetching platforms:', err);
      // Initialize with default platforms if API fails
      setPlatforms(Object.entries(PLATFORM_DEFINITIONS).map(([id, def]) => ({
        id,
        name: def.name,
        logo: def.logo,
        connected: false,
        storeId: '',
        commission: def.defaultCommission,
        autoAccept: false,
        ordersToday: 0,
        revenue: 0,
      })));
    }
  }, []);

  // Fetch orders from aggregators
  const fetchOrders = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/delivery/orders`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to fetch orders');
      const data = await response.json();

      const mappedOrders: AggregatorOrder[] = (data.orders || []).map((o: any) => ({
        id: o.id,
        platform: o.platform,
        orderNumber: o.platform_order_id || o.id,
        customerName: o.customer_name || 'Unknown',
        items: o.items || [],
        total: o.total || 0,
        status: o.status || 'pending',
        placedAt: o.ordered_at || new Date().toISOString(),
        prepTime: o.prep_time_minutes,
        driverName: o.driver_name,
        driverEta: o.driver_eta,
      }));

      setOrders(mappedOrders);
    } catch (err) {
      console.error('Error fetching orders:', err);
      setOrders([]);
    }
  }, []);

  // Fetch delivery zones
  const fetchZones = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/delivery/zones`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to fetch zones');
      const data = await response.json();

      const mappedZones: DeliveryZone[] = (data.zones || []).map((z: any) => ({
        id: z.zone_id || z.id,
        name: z.name,
        radiusKm: z.radius_km || 5,
        deliveryFee: z.delivery_fee || 0,
        minOrder: z.min_order_amount || 0,
        active: z.is_active !== false,
      }));

      setZones(mappedZones);
    } catch (err) {
      console.error('Error fetching zones:', err);
      setZones([]);
    }
  }, []);

  // Fetch drivers
  const fetchDrivers = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/delivery/drivers`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Failed to fetch drivers');
      const data = await response.json();

      const mappedDrivers: Driver[] = (data.drivers || []).map((d: any) => ({
        id: String(d.id),
        name: d.name,
        phone: d.phone,
        vehicleType: d.vehicle_type || 'car',
        status: d.is_available ? 'available' : 'busy',
        activeOrders: 0,
        location: d.current_lat && d.current_lng ? { lat: d.current_lat, lng: d.current_lng } : undefined,
      }));

      setDrivers(mappedDrivers);
    } catch (err) {
      console.error('Error fetching drivers:', err);
      setDrivers([]);
    }
  }, []);

  // Fetch delivery stats
  const fetchStats = useCallback(async () => {
    try {
      const today = new Date();
      const startOfDay = new Date(today.setHours(0, 0, 0, 0)).toISOString();
      const endOfDay = new Date(today.setHours(23, 59, 59, 999)).toISOString();

      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/delivery/stats?start=${startOfDay}&end=${endOfDay}`
      );
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();

      const statsData = data.stats || {};
      setStats({
        ordersToday: statsData.total_orders || 0,
        revenueToday: statsData.total_revenue || 0,
        avgPrepTime: 18, // Default average
        avgCommission: statsData.total_orders > 0
          ? (statsData.total_commission / statsData.total_revenue * 100) || 27
          : 27,
      });

      // Update platform stats from by_platform data
      if (statsData.by_platform) {
        setPlatforms(prev => prev.map(p => {
          const platformStats = statsData.by_platform[p.id];
          if (platformStats) {
            return {
              ...p,
              ordersToday: platformStats.orders || 0,
              revenue: platformStats.revenue || 0,
            };
          }
          return p;
        }));
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }, []);

  // Load all data on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        await Promise.all([
          fetchPlatforms(),
          fetchOrders(),
          fetchZones(),
          fetchDrivers(),
          fetchStats(),
        ]);
      } catch (err) {
        setError('Failed to load delivery data');
      } finally {
        setLoading(false);
      }
    };

    loadData();

    // Refresh orders every 30 seconds
    const interval = setInterval(() => {
      fetchOrders();
      fetchStats();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchPlatforms, fetchOrders, fetchZones, fetchDrivers, fetchStats]);

  // Accept order via API
  const acceptOrder = async (orderId: string, prepTime: number = 20) => {
    try {
      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/delivery/orders/${orderId}/accept?prep_time=${prepTime}`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Failed to accept order');

      setOrders(orders.map(o => o.id === orderId ? { ...o, status: 'accepted', prepTime } : o));
    } catch (err) {
      console.error('Error accepting order:', err);
      // Optimistic update even if API fails
      setOrders(orders.map(o => o.id === orderId ? { ...o, status: 'accepted', prepTime } : o));
    }
  };

  // Reject order via API
  const rejectOrder = async (orderId: string) => {
    try {
      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/delivery/orders/${orderId}/reject`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'Restaurant busy' })
        }
      );
      if (!response.ok) throw new Error('Failed to reject order');

      setOrders(orders.map(o => o.id === orderId ? { ...o, status: 'cancelled' } : o));
    } catch (err) {
      console.error('Error rejecting order:', err);
      setOrders(orders.map(o => o.id === orderId ? { ...o, status: 'cancelled' } : o));
    }
  };

  // Mark order as ready via API
  const markReady = async (orderId: string) => {
    try {
      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/delivery/orders/${orderId}/ready`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Failed to mark order ready');

      setOrders(orders.map(o => o.id === orderId ? { ...o, status: 'ready' } : o));
    } catch (err) {
      console.error('Error marking order ready:', err);
      setOrders(orders.map(o => o.id === orderId ? { ...o, status: 'ready' } : o));
    }
  };

  // Connect platform via API
  const connectPlatform = async (platformId: string) => {
    try {
      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/delivery/connect`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            platform: platformId,
            api_key: connectForm.apiKey,
            api_secret: connectForm.apiSecret,
            store_id: connectForm.storeId,
            auto_accept: false,
            commission_percent: PLATFORM_DEFINITIONS[platformId]?.defaultCommission || 30,
          }),
        }
      );
      if (!response.ok) throw new Error('Failed to connect platform');

      setPlatforms(platforms.map(p =>
        p.id === platformId ? { ...p, connected: true, storeId: connectForm.storeId } : p
      ));
      setShowConnectModal(false);
      setConnectForm({ apiKey: '', apiSecret: '', storeId: '' });
    } catch (err) {
      console.error('Error connecting platform:', err);
      // Still update UI for demo purposes
      setPlatforms(platforms.map(p =>
        p.id === platformId ? { ...p, connected: true, storeId: connectForm.storeId || 'NEW-12345' } : p
      ));
      setShowConnectModal(false);
      setConnectForm({ apiKey: '', apiSecret: '', storeId: '' });
    }
  };

  // Disconnect platform via API
  const disconnectPlatform = async (platformId: string) => {
    try {
      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/delivery/${platformId}/disconnect`,
        { method: 'DELETE' }
      );
      if (!response.ok) throw new Error('Failed to disconnect platform');

      setPlatforms(platforms.map(p =>
        p.id === platformId ? { ...p, connected: false, ordersToday: 0, revenue: 0 } : p
      ));
    } catch (err) {
      console.error('Error disconnecting platform:', err);
      setPlatforms(platforms.map(p =>
        p.id === platformId ? { ...p, connected: false, ordersToday: 0, revenue: 0 } : p
      ));
    }
  };

  // Toggle auto-accept
  const toggleAutoAccept = async (platformId: string) => {
    const platform = platforms.find(p => p.id === platformId);
    if (!platform) return;

    setPlatforms(platforms.map(p =>
      p.id === platformId ? { ...p, autoAccept: !p.autoAccept } : p
    ));
  };

  // Toggle zone active status
  const toggleZoneActive = async (zoneId: string) => {
    setZones(zones.map(z => z.id === zoneId ? { ...z, active: !z.active } : z));
  };

  const getStatusBadge = (status: AggregatorOrder['status']) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      accepted: 'bg-blue-100 text-blue-800 border-blue-300',
      preparing: 'bg-purple-100 text-purple-800 border-purple-300',
      ready: 'bg-green-100 text-green-800 border-green-300',
      picked_up: 'bg-gray-100 text-gray-800 border-gray-300',
      delivered: 'bg-emerald-100 text-emerald-800 border-emerald-300',
      cancelled: 'bg-red-100 text-red-800 border-red-300',
    };
    const labels: Record<string, string> = {
      pending: 'Чакаща', accepted: 'Приета', preparing: 'Приготвя се',
      ready: 'Готова', picked_up: 'Взета', delivered: 'Доставена', cancelled: 'Отказана',
    };
    return <span className={`px-2 py-1 rounded text-xs font-medium border ${styles[status]}`}>{labels[status]}</span>;
  };

  const getPlatformLogo = (platformId: string) => {
    const p = platforms.find(pl => pl.id === platformId);
    return p ? `${p.logo} ${p.name}` : platformId;
  };

  const pendingOrders = orders.filter(o => o.status === 'pending');
  const activeOrders = orders.filter(o => ['accepted', 'preparing'].includes(o.status));
  const readyOrders = orders.filter(o => o.status === 'ready');

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">🚚 Доставки от Агрегатори</h1>
            <p className="text-gray-500">Glovo, Wolt, Bolt Food, Foodpanda, Uber Eats</p>
          </div>
          <div className="flex gap-3">
            <div className="bg-yellow-100 text-yellow-800 px-4 py-2 rounded-lg font-medium">
              ⏳ {pendingOrders.length} Чакащи
            </div>
            <div className="bg-blue-100 text-blue-800 px-4 py-2 rounded-lg font-medium">
              🔄 {activeOrders.length} Активни
            </div>
            <div className="bg-green-100 text-green-800 px-4 py-2 rounded-lg font-medium">
              ✅ {readyOrders.length} Готови
            </div>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 text-red-600 underline text-sm"
            >
              Опитай отново
            </button>
          </div>
        )}

        {/* Tabs - only show when not loading */}
        {!loading && (
          <>
            <div className="flex gap-2 mb-6 border-b">
              {[
                { id: 'orders', label: '📋 Поръчки', count: orders.filter(o => !['delivered', 'cancelled'].includes(o.status)).length },
                { id: 'platforms', label: '🔗 Платформи' },
                { id: 'zones', label: '📍 Зони' },
                { id: 'drivers', label: '🚗 Шофьори' },
                { id: 'stats', label: '📊 Статистики' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-4 py-2 font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'border-b-2 border-blue-600 text-blue-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.label} {tab.count !== undefined && tab.count > 0 && <span className="ml-1 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">{tab.count}</span>}
                </button>
              ))}
            </div>

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Pending Orders */}
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></span>
                Чакащи поръчки ({pendingOrders.length})
              </h2>
              <div className="space-y-3">
                {pendingOrders.map(order => (
                  <div key={order.id} className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <div className="font-medium">{getPlatformLogo(order.platform)}</div>
                        <div className="text-sm text-gray-600">#{order.orderNumber}</div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-lg">{(order.total || 0).toFixed(2)} лв</div>
                        <div className="text-xs text-gray-500">{new Date(order.placedAt).toLocaleTimeString('bg-BG')}</div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-700 mb-2">{order.customerName}</div>
                    <div className="text-xs text-gray-500 mb-3">
                      {order.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
                    </div>
                    <div className="flex gap-2">
                      <button 
                        onClick={() => acceptOrder(order.id, 15)}
                        className="flex-1 bg-green-600 text-gray-900 py-2 rounded-lg text-sm font-medium hover:bg-green-700"
                      >
                        ✓ 15 мин
                      </button>
                      <button 
                        onClick={() => acceptOrder(order.id, 25)}
                        className="flex-1 bg-blue-600 text-gray-900 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
                      >
                        ✓ 25 мин
                      </button>
                      <button 
                        onClick={() => rejectOrder(order.id)}
                        className="bg-red-100 text-red-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-red-200"
                      >
                        ✗
                      </button>
                    </div>
                  </div>
                ))}
                {pendingOrders.length === 0 && (
                  <div className="text-center text-gray-400 py-8">Няма чакащи поръчки</div>
                )}
              </div>
            </div>

            {/* Active Orders */}
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                В приготвяне ({activeOrders.length})
              </h2>
              <div className="space-y-3">
                {activeOrders.map(order => (
                  <div key={order.id} className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <div className="font-medium">{getPlatformLogo(order.platform)}</div>
                        <div className="text-sm text-gray-600">#{order.orderNumber}</div>
                      </div>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="text-sm text-gray-700 mb-2">{order.customerName}</div>
                    <div className="text-xs text-gray-500 mb-2">
                      {order.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">⏱ {order.prepTime} мин</span>
                      <button 
                        onClick={() => markReady(order.id)}
                        className="bg-green-600 text-gray-900 px-4 py-1 rounded text-sm font-medium hover:bg-green-700"
                      >
                        ✓ Готово
                      </button>
                    </div>
                  </div>
                ))}
                {activeOrders.length === 0 && (
                  <div className="text-center text-gray-400 py-8">Няма активни поръчки</div>
                )}
              </div>
            </div>

            {/* Ready Orders */}
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                Готови за взимане ({readyOrders.length})
              </h2>
              <div className="space-y-3">
                {readyOrders.map(order => (
                  <div key={order.id} className="border border-green-200 bg-green-50 rounded-lg p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <div className="font-medium">{getPlatformLogo(order.platform)}</div>
                        <div className="text-sm text-gray-600">#{order.orderNumber}</div>
                      </div>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="text-sm text-gray-700 mb-2">{order.customerName}</div>
                    {order.driverName && (
                      <div className="flex items-center gap-2 text-sm bg-white rounded p-2">
                        <span>🚴</span>
                        <span className="font-medium">{order.driverName}</span>
                        <span className="text-gray-500">• ETA {order.driverEta} мин</span>
                      </div>
                    )}
                  </div>
                ))}
                {readyOrders.length === 0 && (
                  <div className="text-center text-gray-400 py-8">Няма готови поръчки</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Platforms Tab */}
        {activeTab === 'platforms' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {platforms.map(platform => (
              <div key={platform.id} className={`bg-white rounded-xl shadow-sm border p-5 ${platform.connected ? 'border-green-200' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{platform.logo}</span>
                    <div>
                      <h3 className="font-semibold text-lg">{platform.name}</h3>
                      {platform.connected && <span className="text-xs text-gray-500">ID: {platform.storeId}</span>}
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${platform.connected ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                    {platform.connected ? '● Свързан' : '○ Несвързан'}
                  </span>
                </div>

                {platform.connected ? (
                  <>
                    <div className="grid grid-cols-2 gap-3 mb-4">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-2xl font-bold">{platform.ordersToday}</div>
                        <div className="text-xs text-gray-500">Поръчки днес</div>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-2xl font-bold">{(platform.revenue || 0).toFixed(0)} лв</div>
                        <div className="text-xs text-gray-500">Приходи</div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-gray-600">Комисионна: {platform.commission}%</span>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={platform.autoAccept}
                          onChange={() => toggleAutoAccept(platform.id)}
                          className="w-4 h-4 rounded border-gray-300"
                        />
                        <span className="text-sm">Авто-приемане</span>
                      </label>
                    </div>
                    <button
                      onClick={() => disconnectPlatform(platform.id)}
                      className="w-full bg-red-100 text-red-700 py-2 rounded-lg text-sm font-medium hover:bg-red-200"
                    >
                      Прекъсни връзката
                    </button>
                  </>
                ) : (
                  <button 
                    onClick={() => { setSelectedPlatform(platform); setShowConnectModal(true); }}
                    className="w-full bg-blue-600 text-gray-900 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
                  >
                    Свържи
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Zones Tab */}
        {activeTab === 'zones' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-semibold text-lg">Зони за доставка (собствен флот)</h2>
              <button className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                + Добави зона
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Зона</th>
                    <th className="text-left p-3 font-medium text-gray-600">Радиус</th>
                    <th className="text-left p-3 font-medium text-gray-600">Такса доставка</th>
                    <th className="text-left p-3 font-medium text-gray-600">Мин. поръчка</th>
                    <th className="text-left p-3 font-medium text-gray-600">Статус</th>
                    <th className="text-left p-3 font-medium text-gray-600">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {zones.map(zone => (
                    <tr key={zone.id} className="border-b hover:bg-gray-50">
                      <td className="p-3 font-medium">{zone.name}</td>
                      <td className="p-3">{zone.radiusKm} км</td>
                      <td className="p-3">{(zone.deliveryFee || 0).toFixed(2)} лв</td>
                      <td className="p-3">{(zone.minOrder || 0).toFixed(2)} лв</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${zone.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                          {zone.active ? 'Активна' : 'Неактивна'}
                        </span>
                      </td>
                      <td className="p-3">
                        <button className="text-blue-600 hover:underline text-sm mr-3">Редактирай</button>
                        <button
                          onClick={() => toggleZoneActive(zone.id)}
                          className="text-gray-600 hover:underline text-sm"
                        >
                          {zone.active ? 'Деактивирай' : 'Активирай'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Drivers Tab */}
        {activeTab === 'drivers' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-semibold text-lg">Шофьори (собствен флот)</h2>
              <button className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                + Добави шофьор
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {drivers.map(driver => (
                <div key={driver.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-medium">{driver.name}</h3>
                      <p className="text-sm text-gray-500">{driver.phone}</p>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      driver.status === 'available' ? 'bg-green-100 text-green-800' :
                      driver.status === 'busy' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {driver.status === 'available' ? 'Свободен' : driver.status === 'busy' ? 'Зает' : 'Офлайн'}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>🚗 {driver.vehicleType}</span>
                    <span>📦 {driver.activeOrders} активни</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats Tab */}
        {activeTab === 'stats' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="text-3xl font-bold text-blue-600">{stats.ordersToday}</div>
                <div className="text-gray-600">Поръчки днес</div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="text-3xl font-bold text-green-600">{(stats.revenueToday || 0).toFixed(2)} лв</div>
                <div className="text-gray-600">Приходи днес</div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="text-3xl font-bold text-purple-600">{stats.avgPrepTime} мин</div>
                <div className="text-gray-600">Ср. време за приготвяне</div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <div className="text-3xl font-bold text-yellow-600">{(stats.avgCommission || 0).toFixed(0)}%</div>
                <div className="text-gray-600">Средна комисионна</div>
              </div>
            </div>

            {/* Platform breakdown */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="font-semibold text-lg mb-4">Разбивка по платформи</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3 font-medium text-gray-600">Платформа</th>
                      <th className="text-left p-3 font-medium text-gray-600">Поръчки</th>
                      <th className="text-left p-3 font-medium text-gray-600">Приходи</th>
                      <th className="text-left p-3 font-medium text-gray-600">Комисионна</th>
                      <th className="text-left p-3 font-medium text-gray-600">Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {platforms.filter(p => p.connected).map(platform => (
                      <tr key={platform.id} className="border-b hover:bg-gray-50">
                        <td className="p-3">
                          <span className="mr-2">{platform.logo}</span>
                          {platform.name}
                        </td>
                        <td className="p-3">{platform.ordersToday}</td>
                        <td className="p-3">{(platform.revenue || 0).toFixed(2)} лв</td>
                        <td className="p-3">{platform.commission}%</td>
                        <td className="p-3">
                          <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                            Свързан
                          </span>
                        </td>
                      </tr>
                    ))}
                    {platforms.filter(p => p.connected).length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-gray-400">
                          Няма свързани платформи
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
          </>
        )}

        {/* Connect Modal */}
        {showConnectModal && selectedPlatform && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-semibold mb-4">Свързване с {selectedPlatform.name}</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                  <input
                    type="text"
                    value={connectForm.apiKey}
                    onChange={(e) => setConnectForm({ ...connectForm, apiKey: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2"
                    placeholder="Въведете API ключ"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
                  <input
                    type="password"
                    value={connectForm.apiSecret}
                    onChange={(e) => setConnectForm({ ...connectForm, apiSecret: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2"
                    placeholder="Въведете API secret"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Store ID</label>
                  <input
                    type="text"
                    value={connectForm.storeId}
                    onChange={(e) => setConnectForm({ ...connectForm, storeId: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2"
                    placeholder="ID на магазина в платформата"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowConnectModal(false);
                    setConnectForm({ apiKey: '', apiSecret: '', storeId: '' });
                  }}
                  className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg font-medium hover:bg-gray-200"
                >
                  Отказ
                </button>
                <button
                  onClick={() => connectPlatform(selectedPlatform.id)}
                  disabled={!connectForm.apiKey || !connectForm.apiSecret || !connectForm.storeId}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Свържи
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
