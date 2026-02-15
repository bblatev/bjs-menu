'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { getVenueId } from '@/lib/auth';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface VirtualBrand {
  id: string;
  name: string;
  logo: string;
  cuisineType: string;
  description: string;
  platforms: string[];
  status: 'active' | 'paused' | 'draft';
  menuItems: number;
  ordersToday: number;
  revenueToday: number;
  rating: number;
  color: string;
}

interface KitchenStation {
  id: string;
  name: string;
  type: 'grill' | 'fry' | 'cold' | 'prep' | 'dessert' | 'drinks';
  maxConcurrent: number;
  currentOrders: number;
  assignedBrands: string[];
  status: 'active' | 'busy' | 'offline';
}

interface BrandOrder {
  id: string;
  brandId: string;
  orderNumber: string;
  platform: string;
  items: { name: string; quantity: number }[];
  total: number;
  status: 'new' | 'preparing' | 'ready' | 'completed';
  station: string;
  createdAt: string;
}

interface CloudKitchenStats {
  avgPrepTime: number;
  avgRating: number;
}

// Color mapping for cuisine types
const CUISINE_COLORS: Record<string, string> = {
  'Бургери': 'bg-orange-500',
  'Суши': 'bg-red-500',
  'Пица': 'bg-green-500',
  'Здравословно': 'bg-emerald-500',
  'Десерти': 'bg-pink-500',
  'default': 'bg-blue-500',
};

export default function CloudKitchenPage() {
  const [activeTab, setActiveTab] = useState<'brands' | 'stations' | 'orders' | 'performance' | 'menu'>('brands');
  const [loading, setLoading] = useState(true);

  const [brands, setBrands] = useState<VirtualBrand[]>([]);
  const [stations, setStations] = useState<KitchenStation[]>([]);
  const [orders, setOrders] = useState<BrandOrder[]>([]);
  const [stats, setStats] = useState<CloudKitchenStats>({ avgPrepTime: 0, avgRating: 0 });

  const [showBrandModal, setShowBrandModal] = useState(false);
  const [editingBrand, setEditingBrand] = useState<VirtualBrand | null>(null);

  // Fetch virtual brands
  const fetchBrands = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/cloud-kitchen/brands`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        const brandsData = (data.brands || []).map((b: any) => ({
          id: b.id || b.brand_id,
          name: b.name,
          logo: b.logo || '🍽️',
          cuisineType: b.cuisine_type || 'Друго',
          description: b.description || '',
          platforms: b.platforms || [],
          status: b.status || 'draft',
          menuItems: b.menu_items_count || 0,
          ordersToday: b.orders_today || 0,
          revenueToday: b.revenue_today || 0,
          rating: b.rating || 0,
          color: CUISINE_COLORS[b.cuisine_type] || CUISINE_COLORS.default,
        }));
        setBrands(brandsData);
      }
    } catch (err) {
      console.error('Error fetching brands:', err);
      setBrands([]);
    }
  }, []);

  // Fetch kitchen stations
  const fetchStations = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/v6/${getVenueId()}/cloud-kitchen/stations`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        const stationsData = (data.stations || []).map((s: any) => ({
          id: s.id || s.station_id,
          name: s.name,
          type: s.station_type || 'prep',
          maxConcurrent: s.max_concurrent_orders || 5,
          currentOrders: s.current_orders || 0,
          assignedBrands: s.assigned_brands || [],
          status: s.current_orders > s.max_concurrent_orders * 0.8 ? 'busy' : 'active',
        }));
        setStations(stationsData);
      }
    } catch (err) {
      console.error('Error fetching stations:', err);
      setStations([]);
    }
  }, []);

  // Fetch cloud kitchen performance/stats
  const fetchStats = useCallback(async () => {
    try {
      const now = new Date();
      const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const response = await fetch(
        `${API_URL}/v6/${getVenueId()}/cloud-kitchen/performance?start=${startOfDay.toISOString()}&end=${now.toISOString()}`
      );
      if (response.ok) {
        const data = await response.json();
        // Calculate average rating and prep time from brands data
        const activeBrands = brands.filter(b => b.status === 'active' && b.rating > 0);
        const avgRating = activeBrands.length > 0
          ? activeBrands.reduce((sum, b) => sum + b.rating, 0) / activeBrands.length
          : 0;
        setStats({
          avgPrepTime: data.avg_prep_time || 14,
          avgRating: avgRating,
        });
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }, [brands]);

  // Load all data on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchBrands(),
        fetchStations(),
      ]);
      setLoading(false);
    };
    loadData();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchBrands();
      fetchStations();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchBrands, fetchStations]);

  useEffect(() => {
    if (!loading) {
      fetchStats();
    }
  }, [loading, fetchStats]);

  const getBrandById = (id: string) => brands.find(b => b.id === id);
  const getStationIcon = (type: string) => {
    const icons: Record<string, string> = { grill: '🔥', fry: '🍟', cold: '❄️', prep: '🔪', dessert: '🍰', drinks: '🥤' };
    return icons[type] || '🍳';
  };

  const totalOrdersToday = brands.reduce((sum, b) => sum + b.ordersToday, 0);
  const totalRevenueToday = brands.reduce((sum, b) => sum + b.revenueToday, 0);
  const activeOrders = orders.filter(o => o.status !== 'completed').length;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">☁️ Cloud Kitchen</h1>
            <p className="text-gray-500">Виртуални брандове и Ghost Kitchen управление</p>
          </div>
          <div className="flex gap-3">
            <div className="bg-blue-100 text-blue-800 px-4 py-2 rounded-lg font-medium">
              🏷️ {brands.filter(b => b.status === 'active').length} Активни бранда
            </div>
            <div className="bg-green-100 text-green-800 px-4 py-2 rounded-lg font-medium">
              📦 {activeOrders} Активни поръчки
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <div className="text-3xl font-bold text-blue-600">{totalOrdersToday}</div>
            <div className="text-gray-600">Поръчки днес</div>
            <div className="text-sm text-gray-500 mt-1">От всички брандове</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <div className="text-3xl font-bold text-green-600">{(totalRevenueToday || 0).toFixed(0)} лв</div>
            <div className="text-gray-600">Приходи днес</div>
            <div className="text-sm text-gray-500 mt-1">Общо приходи</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <div className="text-3xl font-bold text-purple-600">{stats.avgPrepTime > 0 ? stats.avgPrepTime : '-'} мин</div>
            <div className="text-gray-600">Ср. време приготвяне</div>
            <div className="text-sm text-gray-500 mt-1">Средно за деня</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <div className="text-3xl font-bold text-yellow-600">{stats.avgRating > 0 ? (stats.avgRating || 0).toFixed(1) : '-'}</div>
            <div className="text-gray-600">Ср. рейтинг</div>
            <div className="flex mt-1">{'⭐'.repeat(Math.round(stats.avgRating || 0))}</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b">
          {[
            { id: 'brands', label: '🏷️ Брандове' },
            { id: 'stations', label: '🍳 Станции' },
            { id: 'orders', label: '📋 Поръчки', count: activeOrders },
            { id: 'performance', label: '📊 Производителност' },
            { id: 'menu', label: '📜 Менюта' },
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
              {tab.label} {tab.count && <span className="ml-1 bg-red-500 text-gray-900 text-xs px-2 py-0.5 rounded-full">{tab.count}</span>}
            </button>
          ))}
        </div>

        {/* Brands Tab */}
        {activeTab === 'brands' && (
          <>
            <div className="flex justify-end mb-4">
              <button 
                onClick={() => { setEditingBrand(null); setShowBrandModal(true); }}
                className="bg-blue-600 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
              >
                + Нов виртуален бранд
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {brands.map(brand => (
                <div key={brand.id} className="bg-white rounded-xl shadow-sm border overflow-hidden">
                  <div className={`${brand.color} h-2`}></div>
                  <div className="p-5">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-4xl">{brand.logo}</span>
                        <div>
                          <h3 className="font-semibold text-lg">{brand.name}</h3>
                          <p className="text-sm text-gray-500">{brand.cuisineType}</p>
                        </div>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        brand.status === 'active' ? 'bg-green-100 text-green-800' :
                        brand.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {brand.status === 'active' ? 'Активен' : brand.status === 'paused' ? 'Паузиран' : 'Чернова'}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-4">{brand.description}</p>
                    
                    {brand.status === 'active' && (
                      <>
                        <div className="grid grid-cols-3 gap-2 mb-4">
                          <div className="bg-gray-50 rounded p-2 text-center">
                            <div className="font-bold text-lg">{brand.ordersToday}</div>
                            <div className="text-xs text-gray-500">Поръчки</div>
                          </div>
                          <div className="bg-gray-50 rounded p-2 text-center">
                            <div className="font-bold text-lg">{(brand.revenueToday || 0).toFixed(0)}</div>
                            <div className="text-xs text-gray-500">Приходи</div>
                          </div>
                          <div className="bg-gray-50 rounded p-2 text-center">
                            <div className="font-bold text-lg">⭐ {brand.rating}</div>
                            <div className="text-xs text-gray-500">Рейтинг</div>
                          </div>
                        </div>
                        
                        <div className="flex flex-wrap gap-2 mb-4">
                          {brand.platforms.map(p => (
                            <span key={p} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded capitalize">
                              {p.replace('_', ' ')}
                            </span>
                          ))}
                        </div>
                      </>
                    )}
                    
                    <div className="flex gap-2">
                      <button 
                        onClick={() => { setEditingBrand(brand); setShowBrandModal(true); }}
                        className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
                      >
                        ✏️ Редактирай
                      </button>
                      {brand.status === 'active' ? (
                        <button 
                          onClick={() => setBrands(brands.map(b => b.id === brand.id ? {...b, status: 'paused'} : b))}
                          className="flex-1 bg-yellow-100 text-yellow-800 py-2 rounded-lg text-sm font-medium hover:bg-yellow-200"
                        >
                          ⏸️ Паузирай
                        </button>
                      ) : (
                        <button 
                          onClick={() => setBrands(brands.map(b => b.id === brand.id ? {...b, status: 'active'} : b))}
                          className="flex-1 bg-green-100 text-green-800 py-2 rounded-lg text-sm font-medium hover:bg-green-200"
                        >
                          ▶️ Активирай
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Stations Tab */}
        {activeTab === 'stations' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stations.map(station => (
              <div key={station.id} className={`bg-white rounded-xl shadow-sm border p-5 ${
                station.status === 'busy' ? 'border-yellow-300' : station.status === 'offline' ? 'border-gray-300' : 'border-green-200'
              }`}>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{getStationIcon(station.type)}</span>
                    <div>
                      <h3 className="font-semibold">{station.name}</h3>
                      <p className="text-sm text-gray-500 capitalize">{station.type}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    station.status === 'busy' ? 'bg-yellow-100 text-yellow-800' :
                    station.status === 'active' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {station.status === 'busy' ? 'Зает' : station.status === 'active' ? 'Свободен' : 'Офлайн'}
                  </span>
                </div>
                
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Капацитет</span>
                    <span>{station.currentOrders}/{station.maxConcurrent}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div 
                      className={`h-3 rounded-full ${
                        station.currentOrders / station.maxConcurrent > 0.8 ? 'bg-red-500' :
                        station.currentOrders / station.maxConcurrent > 0.5 ? 'bg-yellow-500' :
                        'bg-green-500'
                      }`}
                      style={{ width: `${(station.currentOrders / station.maxConcurrent) * 100}%` }}
                    ></div>
                  </div>
                </div>
                
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Обслужва брандове:</h4>
                  <div className="flex flex-wrap gap-1">
                    {station.assignedBrands.map(bId => {
                      const b = getBrandById(bId);
                      return b ? (
                        <span key={bId} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded flex items-center gap-1">
                          {b.logo} {b.name}
                        </span>
                      ) : null;
                    })}
                  </div>
                </div>
                
                <button className="w-full bg-gray-100 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">
                  ⚙️ Настройки
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* New Orders */}
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></span>
                Нови ({orders.filter(o => o.status === 'new').length})
              </h2>
              <div className="space-y-3">
                {orders.filter(o => o.status === 'new').map(order => {
                  const brand = getBrandById(order.brandId);
                  return (
                    <div key={order.id} className="border border-yellow-200 bg-yellow-50 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{brand?.logo}</span>
                          <div>
                            <div className="font-medium">{brand?.name}</div>
                            <div className="text-xs text-gray-500">#{order.orderNumber}</div>
                          </div>
                        </div>
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded capitalize">{order.platform}</span>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">
                        {order.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="font-bold">{(order.total || 0).toFixed(2)} лв</span>
                        <button 
                          onClick={() => setOrders(orders.map(o => o.id === order.id ? {...o, status: 'preparing'} : o))}
                          className="bg-blue-600 text-gray-900 px-4 py-1 rounded text-sm font-medium hover:bg-blue-700"
                        >
                          Започни
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Preparing */}
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                В приготвяне ({orders.filter(o => o.status === 'preparing').length})
              </h2>
              <div className="space-y-3">
                {orders.filter(o => o.status === 'preparing').map(order => {
                  const brand = getBrandById(order.brandId);
                  return (
                    <div key={order.id} className="border border-blue-200 bg-blue-50 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{brand?.logo}</span>
                          <div>
                            <div className="font-medium">{brand?.name}</div>
                            <div className="text-xs text-gray-500">#{order.orderNumber}</div>
                          </div>
                        </div>
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded">{order.station}</span>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">
                        {order.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
                      </div>
                      <button 
                        onClick={() => setOrders(orders.map(o => o.id === order.id ? {...o, status: 'ready'} : o))}
                        className="w-full bg-green-600 text-gray-900 py-1 rounded text-sm font-medium hover:bg-green-700"
                      >
                        ✓ Готово
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Ready */}
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                Готови ({orders.filter(o => o.status === 'ready').length})
              </h2>
              <div className="space-y-3">
                {orders.filter(o => o.status === 'ready').map(order => {
                  const brand = getBrandById(order.brandId);
                  return (
                    <div key={order.id} className="border border-green-200 bg-green-50 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{brand?.logo}</span>
                          <div>
                            <div className="font-medium">{brand?.name}</div>
                            <div className="text-xs text-gray-500">#{order.orderNumber}</div>
                          </div>
                        </div>
                        <span className="text-xs bg-green-200 px-2 py-1 rounded capitalize">{order.platform}</span>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">
                        {order.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
                      </div>
                      <button 
                        onClick={() => setOrders(orders.map(o => o.id === order.id ? {...o, status: 'completed'} : o))}
                        className="w-full bg-gray-600 text-gray-900 py-1 rounded text-sm font-medium hover:bg-gray-100"
                      >
                        🚚 Предадено
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Performance Tab */}
        {activeTab === 'performance' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="font-semibold text-lg mb-6">Производителност по брандове</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-medium text-gray-600">Бранд</th>
                    <th className="text-left p-3 font-medium text-gray-600">Поръчки днес</th>
                    <th className="text-left p-3 font-medium text-gray-600">Приходи</th>
                    <th className="text-left p-3 font-medium text-gray-600">Ср. чек</th>
                    <th className="text-left p-3 font-medium text-gray-600">Ср. време</th>
                    <th className="text-left p-3 font-medium text-gray-600">Рейтинг</th>
                    <th className="text-left p-3 font-medium text-gray-600">Платформи</th>
                  </tr>
                </thead>
                <tbody>
                  {brands.filter(b => b.status === 'active').map(brand => (
                    <tr key={brand.id} className="border-b hover:bg-gray-50">
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{brand.logo}</span>
                          <div>
                            <div className="font-medium">{brand.name}</div>
                            <div className="text-xs text-gray-500">{brand.cuisineType}</div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3 font-bold">{brand.ordersToday}</td>
                      <td className="p-3 font-bold text-green-600">{(brand.revenueToday || 0).toFixed(2)} лв</td>
                      <td className="p-3">{((brand.revenueToday / (brand.ordersToday || 1)) || 0).toFixed(2)} лв</td>
                      <td className="p-3">12-18 мин</td>
                      <td className="p-3">
                        <span className="flex items-center gap-1">
                          ⭐ {brand.rating}
                        </span>
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1">
                          {brand.platforms.map(p => (
                            <span key={p} className="bg-gray-100 text-xs px-2 py-1 rounded capitalize">{p}</span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Menu Tab */}
        {activeTab === 'menu' && (
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="font-semibold text-lg mb-6">Управление на менюта</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {brands.map(brand => (
                <div key={brand.id} className="border rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-3xl">{brand.logo}</span>
                    <div>
                      <h3 className="font-medium">{brand.name}</h3>
                      <p className="text-sm text-gray-500">{brand.menuItems} артикула</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <button className="w-full bg-blue-600 text-gray-900 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                      📜 Редактирай меню
                    </button>
                    <button className="w-full bg-gray-100 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">
                      🔄 Синхронизирай
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Brand Modal */}
        {showBrandModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-lg">
              <h2 className="text-xl font-semibold mb-4">
                {editingBrand ? 'Редактирай бранд' : 'Нов виртуален бранд'}
              </h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Име на бранда</label>
                    <input type="text" className="w-full border rounded-lg px-3 py-2" defaultValue={editingBrand?.name} placeholder="напр. Вкусна Пица" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Емоджи/Лого</label>
                    <input type="text" className="w-full border rounded-lg px-3 py-2" defaultValue={editingBrand?.logo} placeholder="🍕" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Тип кухня</label>
                  <select className="w-full border rounded-lg px-3 py-2" defaultValue={editingBrand?.cuisineType}>
                    <option>Бургери</option>
                    <option>Пица</option>
                    <option>Суши</option>
                    <option>Здравословно</option>
                    <option>Десерти</option>
                    <option>Друго</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                  <textarea className="w-full border rounded-lg px-3 py-2" rows={2} defaultValue={editingBrand?.description} placeholder="Кратко описание на бранда"></textarea>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Платформи</label>
                  <div className="flex flex-wrap gap-2">
                    {['glovo', 'wolt', 'bolt_food', 'foodpanda', 'uber_eats'].map(p => (
                      <label key={p} className="flex items-center gap-2 bg-gray-100 px-3 py-1 rounded cursor-pointer">
                        <input type="checkbox" defaultChecked={editingBrand?.platforms.includes(p)} />
                        <span className="capitalize">{p.replace('_', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => setShowBrandModal(false)}
                  className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg font-medium hover:bg-gray-200"
                >
                  Отказ
                </button>
                <button 
                  onClick={() => setShowBrandModal(false)}
                  className="flex-1 bg-blue-600 text-gray-900 py-2 rounded-lg font-medium hover:bg-blue-700"
                >
                  {editingBrand ? 'Запази' : 'Създай'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
