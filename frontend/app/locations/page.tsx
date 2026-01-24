'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Location {
  id: number;
  name: string;
  code: string;
  address: string;
  city: string;
  phone: string;
  email: string;
  timezone: string;
  currency: string;
  status: 'active' | 'inactive' | 'coming_soon';
  manager_name: string;
  manager_email: string;
  operating_hours: { day: string; open: string; close: string; closed: boolean }[];
  features: string[];
  created_at: string;
}

interface LocationStats {
  location_id: number;
  today_revenue: number;
  today_orders: number;
  avg_ticket: number;
  labor_cost_percent: number;
  food_cost_percent: number;
  staff_on_duty: number;
  active_tables: number;
  pending_orders: number;
  rating: number;
  reviews_count: number;
}

interface ConsolidatedStats {
  total_revenue: number;
  total_orders: number;
  avg_ticket: number;
  avg_labor_cost: number;
  avg_food_cost: number;
  total_staff: number;
  locations_active: number;
  top_performer: string;
  needs_attention: string[];
}

type TabType = 'overview' | 'locations' | 'compare' | 'menu' | 'staff' | 'inventory' | 'settings';

export default function MultiLocationPage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [locations, setLocations] = useState<Location[]>([]);
  const [locationStats, setLocationStats] = useState<Map<number, LocationStats>>(new Map());
  const [consolidatedStats, setConsolidatedStats] = useState<ConsolidatedStats | null>(null);
  const [selectedLocations, setSelectedLocations] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [dateRange, setDateRange] = useState('today');
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);

  const [newLocation, setNewLocation] = useState({
    name: '',
    code: '',
    address: '',
    city: '',
    phone: '',
    email: '',
    timezone: 'Europe/Sofia',
    currency: 'BGN',
    manager_name: '',
    manager_email: '',
  });

  const [syncOptions, setSyncOptions] = useState({
    menu: true,
    prices: true,
    promotions: true,
    modifiers: true,
    allergens: true,
    recipes: false,
    staff_roles: false,
  });

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('access_token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const params = new URLSearchParams({ date_range: dateRange });

      const [locationsRes, statsRes, consolidatedRes] = await Promise.all([
        fetch(`${API_URL}/v3.1/locations/`, { headers }),
        fetch(`${API_URL}/v3.1/locations/dashboard`, { headers }),
        fetch(`${API_URL}/v3.1/locations/reports/consolidated`, { headers }),
      ]);

      if (!locationsRes.ok) {
        throw new Error('Failed to load locations');
      }

      const locationsData = await locationsRes.json();
      setLocations(locationsData.locations || locationsData || []);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        const statsMap = new Map<number, LocationStats>();
        (statsData.stats || statsData || []).forEach((stat: LocationStats) => {
          statsMap.set(stat.location_id, stat);
        });
        setLocationStats(statsMap);
      }

      if (consolidatedRes.ok) {
        const consolidatedData = await consolidatedRes.json();
        setConsolidatedStats(consolidatedData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      setLocations([]);
      setLocationStats(new Map());
      setConsolidatedStats(null);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: Location['status']) => {
    const styles = {
      active: 'bg-green-100 text-green-800 border-green-300',
      inactive: 'bg-red-100 text-red-800 border-red-300',
      coming_soon: 'bg-blue-100 text-blue-800 border-blue-300',
    };
    const labels = {
      active: 'Active',
      inactive: 'Inactive',
      coming_soon: 'Coming Soon',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  const handleSyncMenu = () => {
    setShowSyncModal(true);
  };

  const executeSyncMenu = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/v3.1/locations/sync-menu`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_locations: selectedLocations,
          options: syncOptions,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to sync menu');
      }

      alert('Menu synced successfully!');
      setShowSyncModal(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to sync menu');
    }
  };

  const handleAddLocation = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/v3.1/locations/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newLocation),
      });

      if (!response.ok) {
        throw new Error('Failed to create location');
      }

      alert('Location created!');
      setShowAddModal(false);
      setNewLocation({
        name: '',
        code: '',
        address: '',
        city: '',
        phone: '',
        email: '',
        timezone: 'Europe/Sofia',
        currency: 'BGN',
        manager_name: '',
        manager_email: '',
      });
      loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create location');
    }
  };

  const toggleLocationSelection = (id: number) => {
    if (selectedLocations.includes(id)) {
      setSelectedLocations(selectedLocations.filter((l) => l !== id));
    } else {
      setSelectedLocations([...selectedLocations, id]);
    }
  };

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'locations', label: 'Locations', icon: '📍' },
    { id: 'compare', label: 'Compare', icon: '📈' },
    { id: 'menu', label: 'Menu Sync', icon: '🍽️' },
    { id: 'staff', label: 'Staff', icon: '👥' },
    { id: 'inventory', label: 'Inventory', icon: '📦' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-6">
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadData}
            className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Multi-Location Management</h1>
            <p className="text-gray-500 mt-1">Centralized control across all your venues</p>
          </div>
          <div className="flex gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg border-0"
            >
              <option value="today">Today</option>
              <option value="yesterday">Yesterday</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="quarter">This Quarter</option>
            </select>
            <button
              onClick={handleSyncMenu}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              🔄 Sync Menu
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              + Add Location
            </button>
          </div>
        </div>

        {/* Consolidated Stats */}
        {consolidatedStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4">
              <div className="text-green-600 text-xs font-medium">Total Revenue</div>
              <div className="text-2xl font-bold text-green-700">{consolidatedStats.total_revenue.toLocaleString()} лв</div>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4">
              <div className="text-blue-600 text-xs font-medium">Total Orders</div>
              <div className="text-2xl font-bold text-blue-700">{consolidatedStats.total_orders}</div>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4">
              <div className="text-purple-600 text-xs font-medium">Avg Ticket</div>
              <div className="text-2xl font-bold text-purple-700">{consolidatedStats.avg_ticket.toFixed(2)} лв</div>
            </div>
            <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-4">
              <div className="text-orange-600 text-xs font-medium">Active Locations</div>
              <div className="text-2xl font-bold text-orange-700">{consolidatedStats.locations_active}</div>
            </div>
            <div className="bg-gradient-to-br from-cyan-50 to-cyan-100 rounded-xl p-4">
              <div className="text-cyan-600 text-xs font-medium">Staff On Duty</div>
              <div className="text-2xl font-bold text-cyan-700">{consolidatedStats.total_staff}</div>
            </div>
            <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-xl p-4">
              <div className="text-yellow-600 text-xs font-medium">Avg Labor %</div>
              <div className="text-2xl font-bold text-yellow-700">{consolidatedStats.avg_labor_cost.toFixed(1)}%</div>
            </div>
            <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-4">
              <div className="text-red-600 text-xs font-medium">Avg Food Cost %</div>
              <div className="text-2xl font-bold text-red-700">{consolidatedStats.avg_food_cost.toFixed(1)}%</div>
            </div>
            <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-4">
              <div className="text-emerald-600 text-xs font-medium">Top Performer</div>
              <div className="text-lg font-bold text-emerald-700 truncate">{consolidatedStats.top_performer}</div>
            </div>
          </div>
        )}

        {/* Alerts */}
        {consolidatedStats && consolidatedStats.needs_attention.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
            <h3 className="text-yellow-800 font-semibold mb-2">⚠️ Attention Required</h3>
            <div className="space-y-1">
              {consolidatedStats.needs_attention.map((alert, idx) => (
                <div key={idx} className="text-yellow-700 text-sm">{alert}</div>
              ))}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl whitespace-nowrap transition ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {/* Location Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {locations.filter((l) => l.status === 'active').map((location) => {
                  const stats = locationStats.get(location.id);
                  return (
                    <div
                      key={location.id}
                      className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => setSelectedLocation(location)}
                    >
                      <div className="p-5">
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h3 className="text-lg font-bold text-gray-900">{location.name}</h3>
                            <p className="text-gray-500 text-sm">{location.city}</p>
                          </div>
                          {getStatusBadge(location.status)}
                        </div>

                        {stats && (
                          <>
                            <div className="grid grid-cols-2 gap-4 mb-4">
                              <div>
                                <div className="text-gray-500 text-xs">Today&apos;s Revenue</div>
                                <div className="text-xl font-bold text-green-600">{stats.today_revenue.toLocaleString()} лв</div>
                              </div>
                              <div>
                                <div className="text-gray-500 text-xs">Orders</div>
                                <div className="text-xl font-bold text-blue-600">{stats.today_orders}</div>
                              </div>
                            </div>

                            <div className="grid grid-cols-3 gap-2 mb-4">
                              <div className="bg-gray-50 rounded-lg p-2 text-center">
                                <div className="text-xs text-gray-500">Staff</div>
                                <div className="font-semibold text-gray-900">{stats.staff_on_duty}</div>
                              </div>
                              <div className="bg-gray-50 rounded-lg p-2 text-center">
                                <div className="text-xs text-gray-500">Tables</div>
                                <div className="font-semibold text-gray-900">{stats.active_tables}</div>
                              </div>
                              <div className="bg-gray-50 rounded-lg p-2 text-center">
                                <div className="text-xs text-gray-500">Pending</div>
                                <div className="font-semibold text-orange-600">{stats.pending_orders}</div>
                              </div>
                            </div>

                            <div className="flex items-center justify-between text-sm">
                              <div className="flex items-center gap-1">
                                <span className="text-yellow-500">⭐</span>
                                <span className="font-medium text-gray-900">{stats.rating}</span>
                                <span className="text-gray-400">({stats.reviews_count})</span>
                              </div>
                              <div className="flex gap-2">
                                <span className={`text-xs ${stats.labor_cost_percent > 30 ? 'text-red-600' : 'text-green-600'}`}>
                                  Labor: {stats.labor_cost_percent}%
                                </span>
                                <span className={`text-xs ${stats.food_cost_percent > 33 ? 'text-red-600' : 'text-green-600'}`}>
                                  Food: {stats.food_cost_percent}%
                                </span>
                              </div>
                            </div>
                          </>
                        )}
                      </div>

                      <div className="border-t border-gray-100 px-5 py-3 flex justify-between items-center bg-gray-50 rounded-b-2xl">
                        <div className="text-xs text-gray-500">
                          👤 {location.manager_name}
                        </div>
                        <div className="flex gap-2">
                          <span className="text-xs text-gray-400">{location.code}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Coming Soon Cards */}
                {locations.filter((l) => l.status === 'coming_soon').map((location) => (
                  <div
                    key={location.id}
                    className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl border border-blue-200 p-5 opacity-80"
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">{location.name}</h3>
                        <p className="text-gray-500 text-sm">{location.city}</p>
                      </div>
                      {getStatusBadge(location.status)}
                    </div>
                    <div className="text-center py-8">
                      <div className="text-4xl mb-2">🚧</div>
                      <div className="text-gray-600">Opening Soon</div>
                      <div className="text-sm text-gray-400">{location.address}</div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'locations' && (
            <motion.div
              key="locations"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-4 text-left text-gray-600 font-medium">Location</th>
                      <th className="px-6 py-4 text-left text-gray-600 font-medium">Address</th>
                      <th className="px-6 py-4 text-left text-gray-600 font-medium">Manager</th>
                      <th className="px-6 py-4 text-left text-gray-600 font-medium">Features</th>
                      <th className="px-6 py-4 text-center text-gray-600 font-medium">Status</th>
                      <th className="px-6 py-4 text-center text-gray-600 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {locations.map((location) => (
                      <tr key={location.id} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="px-6 py-4">
                          <div className="font-semibold text-gray-900">{location.name}</div>
                          <div className="text-sm text-gray-500">{location.code}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-gray-900">{location.address}</div>
                          <div className="text-sm text-gray-500">{location.city}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-gray-900">{location.manager_name || '-'}</div>
                          <div className="text-sm text-gray-500">{location.manager_email || '-'}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap gap-1">
                            {location.features.slice(0, 3).map((f) => (
                              <span key={f} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                                {f}
                              </span>
                            ))}
                            {location.features.length > 3 && (
                              <span className="text-xs text-gray-400">+{location.features.length - 3}</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-center">{getStatusBadge(location.status)}</td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex justify-center gap-2">
                            <button className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm hover:bg-blue-200">
                              Edit
                            </button>
                            <button className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200">
                              View
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {activeTab === 'compare' && (
            <motion.div
              key="compare"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="bg-white rounded-2xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Location Performance Comparison</h3>

                {/* Revenue Comparison */}
                <div className="mb-8">
                  <h4 className="text-sm font-medium text-gray-600 mb-3">Today&apos;s Revenue</h4>
                  <div className="space-y-3">
                    {locations.filter((l) => l.status === 'active').map((location) => {
                      const stats = locationStats.get(location.id);
                      const maxRevenue = Math.max(...Array.from(locationStats.values()).map((s) => s.today_revenue));
                      const percentage = stats ? (stats.today_revenue / maxRevenue) * 100 : 0;
                      return (
                        <div key={location.id} className="flex items-center gap-4">
                          <div className="w-32 text-sm text-gray-700">{location.name}</div>
                          <div className="flex-1 h-8 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full flex items-center justify-end pr-2"
                              style={{ width: `${percentage}%` }}
                            >
                              <span className="text-white text-xs font-medium">
                                {stats?.today_revenue.toLocaleString()} лв
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Orders Comparison */}
                <div className="mb-8">
                  <h4 className="text-sm font-medium text-gray-600 mb-3">Today&apos;s Orders</h4>
                  <div className="space-y-3">
                    {locations.filter((l) => l.status === 'active').map((location) => {
                      const stats = locationStats.get(location.id);
                      const maxOrders = Math.max(...Array.from(locationStats.values()).map((s) => s.today_orders));
                      const percentage = stats ? (stats.today_orders / maxOrders) * 100 : 0;
                      return (
                        <div key={location.id} className="flex items-center gap-4">
                          <div className="w-32 text-sm text-gray-700">{location.name}</div>
                          <div className="flex-1 h-8 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full flex items-center justify-end pr-2"
                              style={{ width: `${percentage}%` }}
                            >
                              <span className="text-white text-xs font-medium">
                                {stats?.today_orders}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Rating Comparison */}
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-3">Customer Rating</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {locations.filter((l) => l.status === 'active').map((location) => {
                      const stats = locationStats.get(location.id);
                      return (
                        <div key={location.id} className="bg-gray-50 rounded-xl p-4 text-center">
                          <div className="text-3xl font-bold text-yellow-500">{stats?.rating}</div>
                          <div className="text-yellow-400">{'★'.repeat(Math.round(stats?.rating || 0))}</div>
                          <div className="text-sm text-gray-600 mt-1">{location.name}</div>
                          <div className="text-xs text-gray-400">{stats?.reviews_count} reviews</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'menu' && (
            <motion.div
              key="menu"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="bg-white rounded-2xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Menu Synchronization</h3>
                <p className="text-gray-600 mb-6">
                  Select locations to sync menu items, prices, and promotions from the master location.
                </p>

                {/* Select Source */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Source Location (Master)</label>
                  <select className="w-full md:w-64 px-4 py-2 border border-gray-300 rounded-lg">
                    {locations.filter((l) => l.status === 'active').map((loc) => (
                      <option key={loc.id} value={loc.id}>{loc.name}</option>
                    ))}
                  </select>
                </div>

                {/* Target Locations */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Target Locations</label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {locations.filter((l) => l.status === 'active').map((loc) => (
                      <label
                        key={loc.id}
                        className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition ${
                          selectedLocations.includes(loc.id)
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedLocations.includes(loc.id)}
                          onChange={() => toggleLocationSelection(loc.id)}
                          className="rounded border-gray-300 text-blue-600"
                        />
                        <span className="text-sm text-gray-700">{loc.name}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Sync Options */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">What to Sync</label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(syncOptions).map(([key, value]) => (
                      <label
                        key={key}
                        className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition ${
                          value ? 'border-green-500 bg-green-50' : 'border-gray-200'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={value}
                          onChange={() => setSyncOptions({ ...syncOptions, [key]: !value })}
                          className="rounded border-gray-300 text-green-600"
                        />
                        <span className="text-sm text-gray-700 capitalize">{key.replace('_', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <button
                  onClick={executeSyncMenu}
                  disabled={selectedLocations.length === 0}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  🔄 Sync to {selectedLocations.length} Location(s)
                </button>
              </div>
            </motion.div>
          )}

          {activeTab === 'staff' && (
            <motion.div
              key="staff"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="bg-white rounded-2xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Staff Across Locations</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {locations.filter((l) => l.status === 'active').map((location) => {
                    const stats = locationStats.get(location.id);
                    return (
                      <div key={location.id} className="bg-gray-50 rounded-xl p-4">
                        <div className="flex justify-between items-start mb-3">
                          <h4 className="font-medium text-gray-900">{location.name}</h4>
                          <span className="text-2xl font-bold text-blue-600">{stats?.staff_on_duty || 0}</span>
                        </div>
                        <div className="text-sm text-gray-500 mb-3">Staff on duty now</div>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-500">Manager</span>
                            <span className="text-gray-700">{location.manager_name}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Labor Cost</span>
                            <span className={stats && stats.labor_cost_percent > 30 ? 'text-red-600' : 'text-green-600'}>
                              {stats?.labor_cost_percent}%
                            </span>
                          </div>
                        </div>
                        <button className="w-full mt-4 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200">
                          View Staff Schedule
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'inventory' && (
            <motion.div
              key="inventory"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="bg-white rounded-2xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Inventory Across Locations</h3>

                {/* Low Stock Alerts */}
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
                  <h4 className="text-red-800 font-medium mb-2">⚠️ Low Stock Alerts</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-red-700">Coca-Cola 330ml</span>
                      <span className="text-red-600">Downtown Central - 12 units</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-red-700">Mozzarella Cheese</span>
                      <span className="text-red-600">Plovdiv Central - 2.5 kg</span>
                    </div>
                  </div>
                </div>

                {/* Transfer Buttons */}
                <div className="flex gap-4 mb-6">
                  <button className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
                    📦 Create Inter-Location Transfer
                  </button>
                  <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
                    📊 View Consolidated Inventory
                  </button>
                </div>

                {/* Inventory by Location */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {locations.filter((l) => l.status === 'active').map((location) => (
                    <div key={location.id} className="bg-gray-50 rounded-xl p-4">
                      <h4 className="font-medium text-gray-900 mb-3">{location.name}</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Stock Items</span>
                          <span className="text-gray-700">{150 + location.id * 10}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Total Value</span>
                          <span className="text-gray-700">{(12000 + location.id * 1500).toLocaleString()} лв</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Low Stock Items</span>
                          <span className="text-red-600">{location.id}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Expiring (7d)</span>
                          <span className="text-yellow-600">{location.id + 2}</span>
                        </div>
                      </div>
                      <button className="w-full mt-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
                        View Inventory
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'settings' && (
            <motion.div
              key="settings"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Global Settings */}
                <div className="bg-white rounded-2xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Global Settings</h3>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Centralized Menu</div>
                        <div className="text-sm text-gray-500">Sync menu from master location</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Unified Pricing</div>
                        <div className="text-sm text-gray-500">Same prices across all locations</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Shared Loyalty Program</div>
                        <div className="text-sm text-gray-500">Points work across all locations</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Consolidated Reports</div>
                        <div className="text-sm text-gray-500">Aggregate data from all locations</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Permissions */}
                <div className="bg-white rounded-2xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Location Permissions</h3>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Local Menu Changes</div>
                        <div className="text-sm text-gray-500">Allow managers to edit menu</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Price Adjustments</div>
                        <div className="text-sm text-gray-500">Allow local price changes</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Staff Management</div>
                        <div className="text-sm text-gray-500">Managers can hire/schedule</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-gray-900">Promotions</div>
                        <div className="text-sm text-gray-500">Create local promotions</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-200 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Add Location Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-bold text-gray-900">Add New Location</h2>
                <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600 text-2xl">
                  ×
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Location Name *</label>
                  <input
                    type="text"
                    value={newLocation.name}
                    onChange={(e) => setNewLocation({ ...newLocation, name: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="Downtown Central"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Location Code *</label>
                  <input
                    type="text"
                    value={newLocation.code}
                    onChange={(e) => setNewLocation({ ...newLocation, code: e.target.value.toUpperCase() })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="DTC-001"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Address *</label>
                  <input
                    type="text"
                    value={newLocation.address}
                    onChange={(e) => setNewLocation({ ...newLocation, address: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="бул. Витоша 89"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">City *</label>
                  <input
                    type="text"
                    value={newLocation.city}
                    onChange={(e) => setNewLocation({ ...newLocation, city: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="София"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={newLocation.phone}
                    onChange={(e) => setNewLocation({ ...newLocation, phone: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="+359 2 123 4567"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={newLocation.email}
                    onChange={(e) => setNewLocation({ ...newLocation, email: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="location@restaurant.bg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
                  <select
                    value={newLocation.currency}
                    onChange={(e) => setNewLocation({ ...newLocation, currency: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="BGN">BGN (лв)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="USD">USD ($)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Manager Name</label>
                  <input
                    type="text"
                    value={newLocation.manager_name}
                    onChange={(e) => setNewLocation({ ...newLocation, manager_name: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="Мария Иванова"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Manager Email</label>
                  <input
                    type="email"
                    value={newLocation.manager_email}
                    onChange={(e) => setNewLocation({ ...newLocation, manager_email: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    placeholder="manager@restaurant.bg"
                  />
                </div>
              </div>

              <div className="flex gap-4 mt-6">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddLocation}
                  className="flex-1 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Create Location
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Location Details Modal */}
        {selectedLocation && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{selectedLocation.name}</h2>
                  <p className="text-gray-500">{selectedLocation.code}</p>
                </div>
                <button onClick={() => setSelectedLocation(null)} className="text-gray-400 hover:text-gray-600 text-2xl">
                  ×
                </button>
              </div>

              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Contact Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Address</span>
                      <span className="text-gray-900">{selectedLocation.address}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">City</span>
                      <span className="text-gray-900">{selectedLocation.city}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Phone</span>
                      <span className="text-gray-900">{selectedLocation.phone}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Email</span>
                      <span className="text-gray-900">{selectedLocation.email}</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Management</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Manager</span>
                      <span className="text-gray-900">{selectedLocation.manager_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Manager Email</span>
                      <span className="text-gray-900">{selectedLocation.manager_email}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Status</span>
                      {getStatusBadge(selectedLocation.status)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Operating Hours */}
              <div className="mb-6">
                <h4 className="font-medium text-gray-700 mb-2">Operating Hours</h4>
                <div className="grid grid-cols-7 gap-2">
                  {selectedLocation.operating_hours.map((hours) => (
                    <div key={hours.day} className="bg-gray-50 rounded-lg p-2 text-center text-sm">
                      <div className="font-medium text-gray-700">{hours.day.slice(0, 3)}</div>
                      {hours.closed ? (
                        <div className="text-red-500">Closed</div>
                      ) : (
                        <div className="text-gray-600">
                          {hours.open}<br/>{hours.close}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Features */}
              <div className="mb-6">
                <h4 className="font-medium text-gray-700 mb-2">Features</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedLocation.features.map((f) => (
                    <span key={f} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                      {f}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setSelectedLocation(null)}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  Close
                </button>
                <button className="flex-1 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Edit Location
                </button>
                <button className="py-3 px-6 bg-orange-500 text-white rounded-lg hover:bg-orange-600">
                  Open Dashboard
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
