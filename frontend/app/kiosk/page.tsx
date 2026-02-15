'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface Kiosk {
  id: number;
  name: string;
  location: string;
  status: 'online' | 'offline' | 'maintenance' | 'error';
  ip_address: string;
  last_heartbeat: string;
  version: string;
  screen_state: 'idle' | 'in_use' | 'payment' | 'receipt' | 'error';
  current_session?: KioskSession;
  hardware: HardwareStatus;
  daily_stats: DailyStats;
}

interface KioskSession {
  session_id: string;
  started_at: string;
  language: string;
  order_type: 'dine_in' | 'takeaway';
  items_count: number;
  cart_total: number;
  stage: 'browsing' | 'customizing' | 'cart' | 'payment' | 'completed';
}

interface HardwareStatus {
  printer: 'ok' | 'error' | 'paper_low' | 'offline';
  card_reader: 'ok' | 'error' | 'offline';
  cash_module: 'ok' | 'error' | 'full' | 'low' | 'offline';
  touchscreen: 'ok' | 'error' | 'calibration_needed';
  barcode_scanner: 'ok' | 'error' | 'offline';
  temperature: number;
  uptime_hours: number;
}

interface DailyStats {
  sessions: number;
  completed_orders: number;
  total_revenue: number;
  avg_order_value: number;
  avg_session_time: number;
  abandoned_rate: number;
}

interface UpsellRule {
  id: number;
  name: string;
  trigger_item: string;
  suggest_item: string;
  discount_percent: number;
  is_active: boolean;
  success_rate: number;
}

interface MenuLayout {
  id: number;
  name: string;
  categories: string[];
  featured_items: number[];
  is_active: boolean;
}

export default function KioskManagementPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'kiosks' | 'sessions' | 'upselling' | 'layout' | 'settings' | 'analytics'>('overview');
  const [kiosks, setKiosks] = useState<Kiosk[]>([]);
  const [selectedKiosk, setSelectedKiosk] = useState<Kiosk | null>(null);
  const [upsellRules, setUpsellRules] = useState<UpsellRule[]>([]);
  const [layouts, setLayouts] = useState<MenuLayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('today');
  const [showKioskModal, setShowKioskModal] = useState(false);
  const [showUpsellModal, setShowUpsellModal] = useState(false);

  // Settings state
  const [settings, setSettings] = useState({
    enable_upselling: true,
    age_verification: true,
    accept_cash: true,
    accept_card: true,
    accept_nfc: true,
    high_contrast: true,
    screen_reader: false,
    session_timeout: 5,
    idle_timeout: 30,
    default_language: 'bg',
    receipt_print_auto: true,
    loyalty_integration: true,
    calories_display: true,
    allergen_display: true,
  });

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // In real app, fetch from API
      setKiosks(getMockKiosks());
      setUpsellRules(getMockUpsellRules());
      setLayouts(getMockLayouts());
    } finally {
      setLoading(false);
    }
  };

  const getMockKiosks = (): Kiosk[] => [
    {
      id: 1,
      name: 'Kiosk 1',
      location: 'Main Entrance',
      status: 'online',
      ip_address: '192.168.1.101',
      last_heartbeat: new Date(Date.now() - 5000).toISOString(),
      version: '3.2.1',
      screen_state: 'in_use',
      current_session: {
        session_id: 'sess-001',
        started_at: new Date(Date.now() - 120000).toISOString(),
        language: 'bg',
        order_type: 'dine_in',
        items_count: 3,
        cart_total: 24.50,
        stage: 'cart',
      },
      hardware: {
        printer: 'ok',
        card_reader: 'ok',
        cash_module: 'ok',
        touchscreen: 'ok',
        barcode_scanner: 'ok',
        temperature: 42,
        uptime_hours: 168,
      },
      daily_stats: {
        sessions: 45,
        completed_orders: 38,
        total_revenue: 1245.50,
        avg_order_value: 32.78,
        avg_session_time: 145,
        abandoned_rate: 15.5,
      },
    },
    {
      id: 2,
      name: 'Kiosk 2',
      location: 'Food Court',
      status: 'online',
      ip_address: '192.168.1.102',
      last_heartbeat: new Date(Date.now() - 3000).toISOString(),
      version: '3.2.1',
      screen_state: 'idle',
      hardware: {
        printer: 'paper_low',
        card_reader: 'ok',
        cash_module: 'ok',
        touchscreen: 'ok',
        barcode_scanner: 'ok',
        temperature: 38,
        uptime_hours: 72,
      },
      daily_stats: {
        sessions: 52,
        completed_orders: 48,
        total_revenue: 1567.00,
        avg_order_value: 32.65,
        avg_session_time: 128,
        abandoned_rate: 7.7,
      },
    },
    {
      id: 3,
      name: 'Kiosk 3',
      location: 'Drive-Thru Lane',
      status: 'error',
      ip_address: '192.168.1.103',
      last_heartbeat: new Date(Date.now() - 300000).toISOString(),
      version: '3.2.0',
      screen_state: 'error',
      hardware: {
        printer: 'ok',
        card_reader: 'error',
        cash_module: 'ok',
        touchscreen: 'ok',
        barcode_scanner: 'offline',
        temperature: 55,
        uptime_hours: 24,
      },
      daily_stats: {
        sessions: 12,
        completed_orders: 8,
        total_revenue: 285.00,
        avg_order_value: 35.62,
        avg_session_time: 165,
        abandoned_rate: 33.3,
      },
    },
    {
      id: 4,
      name: 'Kiosk 4',
      location: 'Second Floor',
      status: 'maintenance',
      ip_address: '192.168.1.104',
      last_heartbeat: new Date(Date.now() - 3600000).toISOString(),
      version: '3.2.1',
      screen_state: 'idle',
      hardware: {
        printer: 'offline',
        card_reader: 'offline',
        cash_module: 'offline',
        touchscreen: 'calibration_needed',
        barcode_scanner: 'offline',
        temperature: 25,
        uptime_hours: 0,
      },
      daily_stats: {
        sessions: 0,
        completed_orders: 0,
        total_revenue: 0,
        avg_order_value: 0,
        avg_session_time: 0,
        abandoned_rate: 0,
      },
    },
  ];

  const getMockUpsellRules = (): UpsellRule[] => [
    { id: 1, name: 'Burger Combo', trigger_item: 'Any Burger', suggest_item: 'Fries + Drink Combo', discount_percent: 15, is_active: true, success_rate: 42.5 },
    { id: 2, name: 'Pizza Size Up', trigger_item: 'Medium Pizza', suggest_item: 'Large Pizza', discount_percent: 10, is_active: true, success_rate: 28.3 },
    { id: 3, name: 'Dessert Add', trigger_item: 'Any Main', suggest_item: 'Dessert of the Day', discount_percent: 20, is_active: true, success_rate: 18.7 },
    { id: 4, name: 'Drink Upgrade', trigger_item: 'Regular Drink', suggest_item: 'Large Drink', discount_percent: 0, is_active: true, success_rate: 55.2 },
    { id: 5, name: 'Extra Cheese', trigger_item: 'Any Pizza', suggest_item: 'Extra Cheese Topping', discount_percent: 0, is_active: false, success_rate: 35.8 },
  ];

  const getMockLayouts = (): MenuLayout[] => [
    { id: 1, name: 'Default Layout', categories: ['Popular', 'Burgers', 'Pizza', 'Drinks', 'Desserts'], featured_items: [1, 5, 12], is_active: true },
    { id: 2, name: 'Lunch Special', categories: ['Lunch Deals', 'Quick Bites', 'Drinks'], featured_items: [8, 9, 10], is_active: false },
    { id: 3, name: 'Weekend Menu', categories: ['Brunch', 'Family Meals', 'Kids Menu', 'Desserts'], featured_items: [15, 16, 17], is_active: false },
  ];

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      online: 'bg-green-500',
      offline: 'bg-gray-500',
      maintenance: 'bg-yellow-500',
      error: 'bg-red-500',
    };
    return colors[status] || 'bg-gray-500';
  };

  const getHardwareColor = (status: string) => {
    const colors: Record<string, string> = {
      ok: 'text-green-400',
      error: 'text-red-400',
      paper_low: 'text-yellow-400',
      full: 'text-yellow-400',
      low: 'text-yellow-400',
      offline: 'text-gray-400',
      calibration_needed: 'text-orange-400',
    };
    return colors[status] || 'text-gray-400';
  };

  const getHardwareIcon = (status: string) => {
    const icons: Record<string, string> = {
      ok: '✓',
      error: '✗',
      paper_low: '⚠',
      full: '⚠',
      low: '⚠',
      offline: '○',
      calibration_needed: '⚠',
    };
    return icons[status] || '?';
  };

  const overallStats = {
    totalKiosks: kiosks.length,
    onlineKiosks: kiosks.filter(k => k.status === 'online').length,
    totalSessions: kiosks.reduce((sum, k) => sum + k.daily_stats.sessions, 0),
    totalRevenue: kiosks.reduce((sum, k) => sum + k.daily_stats.total_revenue, 0),
    avgOrderValue: kiosks.filter(k => k.daily_stats.completed_orders > 0).reduce((sum, k) => sum + k.daily_stats.avg_order_value, 0) / kiosks.filter(k => k.daily_stats.completed_orders > 0).length || 0,
    conversionRate: kiosks.reduce((sum, k) => sum + k.daily_stats.completed_orders, 0) / kiosks.reduce((sum, k) => sum + k.daily_stats.sessions, 0) * 100 || 0,
  };

  const handleRestartKiosk = (kioskId: number) => {
    setKiosks(kiosks.map(k => k.id === kioskId ? { ...k, status: 'maintenance' as const, screen_state: 'idle' as const } : k));
    setTimeout(() => {
      setKiosks(prev => prev.map(k => k.id === kioskId ? { ...k, status: 'online' as const } : k));
    }, 3000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading kiosk data...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Self-Service Kiosks</h1>
            <p className="text-gray-600 mt-1">Manage kiosk hardware, sessions, and configuration</p>
          </div>
          <div className="flex gap-3">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
            >
              <option value="today">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
            </select>
            <button
              onClick={() => setShowKioskModal(true)}
              className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
            >
              + Add Kiosk
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Total Kiosks</div>
            <div className="text-2xl font-bold text-gray-900">{overallStats.totalKiosks}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Online</div>
            <div className="text-2xl font-bold text-green-400">{overallStats.onlineKiosks}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Sessions Today</div>
            <div className="text-2xl font-bold text-blue-400">{overallStats.totalSessions}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Revenue</div>
            <div className="text-2xl font-bold text-green-400">{(overallStats.totalRevenue || 0).toFixed(0)} лв</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Avg Order</div>
            <div className="text-2xl font-bold text-purple-400">{(overallStats.avgOrderValue || 0).toFixed(2)} лв</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Conversion</div>
            <div className="text-2xl font-bold text-cyan-400">{(overallStats.conversionRate || 0).toFixed(1)}%</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'overview', label: 'Overview', icon: '📊' },
            { id: 'kiosks', label: 'Kiosk Fleet', icon: '🖥️' },
            { id: 'sessions', label: 'Live Sessions', icon: '👤' },
            { id: 'upselling', label: 'Upselling', icon: '📈' },
            { id: 'layout', label: 'Menu Layout', icon: '📋' },
            { id: 'settings', label: 'Settings', icon: '⚙️' },
            { id: 'analytics', label: 'Analytics', icon: '📉' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-xl whitespace-nowrap transition-all ${
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
              {/* Kiosk Status Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                {kiosks.map(kiosk => (
                  <div
                    key={kiosk.id}
                    className="bg-gray-100 rounded-2xl p-5 cursor-pointer hover:bg-white/15 transition-all"
                    onClick={() => setSelectedKiosk(kiosk)}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">{kiosk.name}</h3>
                        <p className="text-gray-500 text-sm">{kiosk.location}</p>
                      </div>
                      <span className={`w-3 h-3 rounded-full ${getStatusColor(kiosk.status)} animate-pulse`}></span>
                    </div>

                    {/* Screen Preview */}
                    <div className={`h-24 rounded-lg mb-3 flex items-center justify-center ${
                      kiosk.screen_state === 'idle' ? 'bg-slate-700' :
                      kiosk.screen_state === 'in_use' ? 'bg-blue-900/50' :
                      kiosk.screen_state === 'payment' ? 'bg-green-900/50' :
                      kiosk.screen_state === 'error' ? 'bg-red-900/50' :
                      'bg-slate-700'
                    }`}>
                      {kiosk.screen_state === 'idle' && <span className="text-white/40">IDLE</span>}
                      {kiosk.screen_state === 'in_use' && (
                        <div className="text-center">
                          <span className="text-blue-400 text-sm">In Use</span>
                          <div className="text-gray-900 font-bold">{(kiosk.current_session?.cart_total || 0).toFixed(2)} лв</div>
                        </div>
                      )}
                      {kiosk.screen_state === 'payment' && <span className="text-green-400">Processing Payment...</span>}
                      {kiosk.screen_state === 'error' && <span className="text-red-400">ERROR</span>}
                    </div>

                    {/* Hardware Indicators */}
                    <div className="flex gap-2 mb-3">
                      <span className={`text-xs ${getHardwareColor(kiosk.hardware.printer)}`} title="Printer">
                        🖨️{getHardwareIcon(kiosk.hardware.printer)}
                      </span>
                      <span className={`text-xs ${getHardwareColor(kiosk.hardware.card_reader)}`} title="Card Reader">
                        💳{getHardwareIcon(kiosk.hardware.card_reader)}
                      </span>
                      <span className={`text-xs ${getHardwareColor(kiosk.hardware.cash_module)}`} title="Cash">
                        💵{getHardwareIcon(kiosk.hardware.cash_module)}
                      </span>
                      <span className={`text-xs ${getHardwareColor(kiosk.hardware.touchscreen)}`} title="Screen">
                        📱{getHardwareIcon(kiosk.hardware.touchscreen)}
                      </span>
                    </div>

                    {/* Daily Stats */}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="text-gray-500">Orders: <span className="text-gray-900">{kiosk.daily_stats.completed_orders}</span></div>
                      <div className="text-gray-500">Revenue: <span className="text-green-400">{(kiosk.daily_stats.total_revenue || 0).toFixed(0)} лв</span></div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Alerts */}
              {kiosks.some(k => k.status === 'error' || k.hardware.printer === 'paper_low' || k.hardware.card_reader === 'error') && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-2xl p-4 mb-6">
                  <h3 className="text-red-400 font-bold mb-2">Alerts Requiring Attention</h3>
                  <div className="space-y-2">
                    {kiosks.filter(k => k.status === 'error').map(k => (
                      <div key={`err-${k.id}`} className="flex items-center gap-2 text-gray-800">
                        <span className="text-red-400">●</span>
                        <span>{k.name} is offline - Last seen {Math.round((Date.now() - new Date(k.last_heartbeat).getTime()) / 60000)} min ago</span>
                        <button
                          onClick={() => handleRestartKiosk(k.id)}
                          className="ml-auto px-3 py-1 bg-orange-500/30 text-orange-400 rounded text-sm"
                        >
                          Restart
                        </button>
                      </div>
                    ))}
                    {kiosks.filter(k => k.hardware.printer === 'paper_low').map(k => (
                      <div key={`paper-${k.id}`} className="flex items-center gap-2 text-gray-800">
                        <span className="text-yellow-400">●</span>
                        <span>{k.name} - Printer paper low</span>
                      </div>
                    ))}
                    {kiosks.filter(k => k.hardware.card_reader === 'error').map(k => (
                      <div key={`card-${k.id}`} className="flex items-center gap-2 text-gray-800">
                        <span className="text-red-400">●</span>
                        <span>{k.name} - Card reader malfunction</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Popular Items */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Top Kiosk Items</h3>
                  <div className="space-y-3">
                    {[
                      { name: 'Combo Meal #1', count: 89, revenue: 890 },
                      { name: 'Large Pizza', count: 67, revenue: 1005 },
                      { name: 'Burger Deluxe', count: 54, revenue: 648 },
                      { name: 'Chicken Wings', count: 48, revenue: 432 },
                      { name: 'Ice Cream Sundae', count: 42, revenue: 252 },
                    ].map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-orange-500 text-gray-900 text-xs flex items-center justify-center">{idx + 1}</span>
                          <span className="text-gray-900">{item.name}</span>
                        </div>
                        <div className="text-right">
                          <div className="text-gray-700 text-sm">{item.count} orders</div>
                          <div className="text-green-400 text-xs">{item.revenue} лв</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Peak Hours */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Peak Hours</h3>
                  <div className="flex items-end justify-between h-32">
                    {['10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'].map((hour, idx) => {
                      const heights = [15, 25, 60, 95, 70, 45, 35, 55, 85, 100, 75, 40];
                      return (
                        <div key={hour} className="flex flex-col items-center">
                          <div
                            className="w-4 bg-gradient-to-t from-orange-500 to-yellow-400 rounded-t"
                            style={{ height: `${heights[idx]}%` }}
                          ></div>
                          <span className="text-gray-500 text-xs mt-1">{hour}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Upsell Performance */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Upsell Success</h3>
                  <div className="text-center mb-4">
                    <div className="text-4xl font-bold text-green-400">34.2%</div>
                    <div className="text-gray-500">Acceptance Rate</div>
                  </div>
                  <div className="space-y-2">
                    {upsellRules.filter(r => r.is_active).slice(0, 3).map(rule => (
                      <div key={rule.id} className="flex justify-between items-center text-sm">
                        <span className="text-gray-700">{rule.name}</span>
                        <span className="text-green-400">{rule.success_rate}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'kiosks' && (
            <motion.div
              key="kiosks"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="bg-gray-100 rounded-2xl overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-4 text-left text-gray-900">Kiosk</th>
                      <th className="px-6 py-4 text-left text-gray-900">Location</th>
                      <th className="px-6 py-4 text-center text-gray-900">Status</th>
                      <th className="px-6 py-4 text-left text-gray-900">Hardware</th>
                      <th className="px-6 py-4 text-right text-gray-900">Today&apos;s Stats</th>
                      <th className="px-6 py-4 text-center text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {kiosks.map(kiosk => (
                      <tr key={kiosk.id} className="border-t border-gray-200">
                        <td className="px-6 py-4">
                          <div className="text-gray-900 font-semibold">{kiosk.name}</div>
                          <div className="text-gray-500 text-sm">v{kiosk.version} • {kiosk.ip_address}</div>
                        </td>
                        <td className="px-6 py-4 text-gray-700">{kiosk.location}</td>
                        <td className="px-6 py-4 text-center">
                          <span className={`px-3 py-1 rounded-full text-xs text-gray-900 ${getStatusColor(kiosk.status)}`}>
                            {kiosk.status}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex gap-3">
                            <span className={`text-sm ${getHardwareColor(kiosk.hardware.printer)}`}>🖨️ {kiosk.hardware.printer}</span>
                            <span className={`text-sm ${getHardwareColor(kiosk.hardware.card_reader)}`}>💳 {kiosk.hardware.card_reader}</span>
                            <span className={`text-sm ${getHardwareColor(kiosk.hardware.cash_module)}`}>💵 {kiosk.hardware.cash_module}</span>
                          </div>
                          <div className="text-white/40 text-xs mt-1">
                            Temp: {kiosk.hardware.temperature}°C • Uptime: {kiosk.hardware.uptime_hours}h
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="text-gray-900">{kiosk.daily_stats.completed_orders} orders</div>
                          <div className="text-green-400">{(kiosk.daily_stats.total_revenue || 0).toFixed(0)} лв</div>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex justify-center gap-2">
                            <button
                              onClick={() => setSelectedKiosk(kiosk)}
                              className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded text-sm"
                            >
                              View
                            </button>
                            <button
                              onClick={() => handleRestartKiosk(kiosk.id)}
                              className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded text-sm"
                            >
                              Restart
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

          {activeTab === 'sessions' && (
            <motion.div
              key="sessions"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {kiosks.filter(k => k.current_session).map(kiosk => (
                  <div key={kiosk.id} className="bg-gray-100 rounded-2xl p-5">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">{kiosk.name}</h3>
                        <p className="text-gray-500 text-sm">{kiosk.location}</p>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs ${
                        kiosk.current_session?.stage === 'browsing' ? 'bg-blue-500' :
                        kiosk.current_session?.stage === 'cart' ? 'bg-yellow-500' :
                        kiosk.current_session?.stage === 'payment' ? 'bg-green-500' :
                        'bg-gray-500'
                      } text-white`}>
                        {kiosk.current_session?.stage}
                      </span>
                    </div>

                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Language</span>
                        <span className="text-gray-900">{kiosk.current_session?.language === 'bg' ? '🇧🇬 Bulgarian' : '🇬🇧 English'}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Order Type</span>
                        <span className="text-gray-900">{kiosk.current_session?.order_type === 'dine_in' ? 'Dine In' : 'Takeaway'}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Items</span>
                        <span className="text-gray-900">{kiosk.current_session?.items_count}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Duration</span>
                        <span className="text-gray-900">
                          {Math.round((Date.now() - new Date(kiosk.current_session?.started_at || '').getTime()) / 60000)} min
                        </span>
                      </div>
                    </div>

                    <div className="border-t border-gray-200 pt-3 flex justify-between items-center">
                      <span className="text-gray-600">Cart Total</span>
                      <span className="text-2xl font-bold text-green-400">{(kiosk.current_session?.cart_total || 0).toFixed(2)} лв</span>
                    </div>

                    <div className="flex gap-2 mt-4">
                      <button className="flex-1 py-2 bg-blue-500/20 text-blue-400 rounded-lg text-sm">
                        View Cart
                      </button>
                      <button className="flex-1 py-2 bg-red-500/20 text-red-400 rounded-lg text-sm">
                        End Session
                      </button>
                    </div>
                  </div>
                ))}
                {kiosks.filter(k => k.current_session).length === 0 && (
                  <div className="col-span-full bg-gray-100 rounded-2xl p-12 text-center">
                    <div className="text-white/40 text-lg">No active sessions</div>
                    <p className="text-white/30 mt-2">Sessions will appear here when customers use the kiosks</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'upselling' && (
            <motion.div
              key="upselling"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">Upselling Rules</h2>
                <button
                  onClick={() => setShowUpsellModal(true)}
                  className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                >
                  + Add Rule
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {upsellRules.map(rule => (
                  <div key={rule.id} className={`bg-gray-100 rounded-2xl p-5 ${!rule.is_active ? 'opacity-50' : ''}`}>
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">{rule.name}</h3>
                        <p className="text-gray-500 text-sm">When: {rule.trigger_item}</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={rule.is_active}
                          onChange={() => {
                            setUpsellRules(rules => rules.map(r =>
                              r.id === rule.id ? { ...r, is_active: !r.is_active } : r
                            ));
                          }}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-600 peer-checked:bg-green-500 rounded-full"></div>
                      </label>
                    </div>

                    <div className="bg-gray-50 rounded-xl p-3 mb-3">
                      <div className="text-gray-600 text-xs mb-1">Suggest:</div>
                      <div className="text-gray-900 font-semibold">{rule.suggest_item}</div>
                      {rule.discount_percent > 0 && (
                        <span className="inline-block mt-1 px-2 py-0.5 bg-green-500/30 text-green-400 rounded text-xs">
                          {rule.discount_percent}% OFF
                        </span>
                      )}
                    </div>

                    <div className="flex justify-between items-center">
                      <div className="text-gray-600 text-sm">Success Rate</div>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-green-500 to-emerald-400"
                            style={{ width: `${rule.success_rate}%` }}
                          ></div>
                        </div>
                        <span className="text-green-400 text-sm">{rule.success_rate}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'layout' && (
            <motion.div
              key="layout"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Layout List */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Menu Layouts</h2>
                  <div className="space-y-3">
                    {layouts.map(layout => (
                      <div
                        key={layout.id}
                        className={`rounded-xl p-4 cursor-pointer transition-all ${
                          layout.is_active
                            ? 'bg-green-500/20 border border-green-500'
                            : 'bg-gray-50 hover:bg-white/10'
                        }`}
                        onClick={() => {
                          setLayouts(l => l.map(lay => ({ ...lay, is_active: lay.id === layout.id })));
                        }}
                      >
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="text-gray-900 font-semibold">{layout.name}</h3>
                          {layout.is_active && <span className="text-green-400 text-sm">Active</span>}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {layout.categories.map((cat, i) => (
                            <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                              {cat}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <button className="w-full mt-4 py-3 bg-green-500/20 text-green-400 rounded-xl hover:bg-green-500/30">
                    + Create New Layout
                  </button>
                </div>

                {/* Layout Preview */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Layout Preview</h2>
                  <div className="bg-gray-50 rounded-xl p-4 aspect-video flex flex-col">
                    {/* Kiosk Header */}
                    <div className="bg-orange-500 rounded-t-lg p-2 text-gray-900 text-center text-sm font-bold">
                      Welcome! Touch to Order
                    </div>

                    {/* Category Tabs */}
                    <div className="flex gap-1 p-2 bg-slate-700 overflow-x-auto">
                      {layouts.find(l => l.is_active)?.categories.map((cat, i) => (
                        <button
                          key={i}
                          className={`px-3 py-1 rounded text-xs whitespace-nowrap ${
                            i === 0 ? 'bg-orange-500 text-white' : 'bg-slate-600 text-gray-700'
                          }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>

                    {/* Product Grid */}
                    <div className="flex-1 p-2 grid grid-cols-3 gap-2">
                      {[1, 2, 3, 4, 5, 6].map(i => (
                        <div key={i} className="bg-slate-600 rounded-lg p-2 flex flex-col items-center">
                          <div className="w-8 h-8 bg-slate-500 rounded mb-1"></div>
                          <div className="w-full h-2 bg-slate-500 rounded mb-1"></div>
                          <div className="w-8 h-2 bg-orange-500/50 rounded"></div>
                        </div>
                      ))}
                    </div>

                    {/* Cart Footer */}
                    <div className="bg-slate-700 rounded-b-lg p-2 flex justify-between items-center">
                      <span className="text-gray-700 text-xs">Cart: 0 items</span>
                      <span className="bg-green-500 text-gray-900 px-3 py-1 rounded text-xs">Checkout</span>
                    </div>
                  </div>
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
                {/* Payment Settings */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Payment Options</h2>
                  <div className="space-y-4">
                    {[
                      { key: 'accept_card', label: 'Accept Card Payments', icon: '💳' },
                      { key: 'accept_cash', label: 'Accept Cash Payments', icon: '💵' },
                      { key: 'accept_nfc', label: 'Accept NFC/Apple Pay', icon: '📱' },
                    ].map(item => (
                      <div key={item.key} className="flex justify-between items-center">
                        <span className="text-gray-900">{item.icon} {item.label}</span>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={settings[item.key as keyof typeof settings] as boolean}
                            onChange={() => setSettings({ ...settings, [item.key]: !settings[item.key as keyof typeof settings] })}
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-gray-600 peer-checked:bg-green-500 rounded-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Accessibility */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Accessibility</h2>
                  <div className="space-y-4">
                    {[
                      { key: 'high_contrast', label: 'High Contrast Mode', icon: '🔆' },
                      { key: 'screen_reader', label: 'Screen Reader Support', icon: '🔊' },
                    ].map(item => (
                      <div key={item.key} className="flex justify-between items-center">
                        <span className="text-gray-900">{item.icon} {item.label}</span>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={settings[item.key as keyof typeof settings] as boolean}
                            onChange={() => setSettings({ ...settings, [item.key]: !settings[item.key as keyof typeof settings] })}
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-gray-600 peer-checked:bg-green-500 rounded-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Display Options */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Display Options</h2>
                  <div className="space-y-4">
                    {[
                      { key: 'calories_display', label: 'Show Calories', icon: '🔥' },
                      { key: 'allergen_display', label: 'Show Allergens', icon: '⚠️' },
                      { key: 'loyalty_integration', label: 'Loyalty Points', icon: '⭐' },
                    ].map(item => (
                      <div key={item.key} className="flex justify-between items-center">
                        <span className="text-gray-900">{item.icon} {item.label}</span>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={settings[item.key as keyof typeof settings] as boolean}
                            onChange={() => setSettings({ ...settings, [item.key]: !settings[item.key as keyof typeof settings] })}
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-gray-600 peer-checked:bg-green-500 rounded-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Timeouts & Language */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Session Settings</h2>
                  <div className="space-y-4">
                    <div>
                      <label className="text-gray-600 text-sm">Session Timeout (minutes)</label>
                      <input
                        type="number"
                        value={settings.session_timeout}
                        onChange={(e) => setSettings({ ...settings, session_timeout: parseInt(e.target.value) })}
                        className="w-full mt-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      />
                    </div>
                    <div>
                      <label className="text-gray-600 text-sm">Idle Screen Timeout (seconds)</label>
                      <input
                        type="number"
                        value={settings.idle_timeout}
                        onChange={(e) => setSettings({ ...settings, idle_timeout: parseInt(e.target.value) })}
                        className="w-full mt-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      />
                    </div>
                    <div>
                      <label className="text-gray-600 text-sm">Default Language</label>
                      <select
                        value={settings.default_language}
                        onChange={(e) => setSettings({ ...settings, default_language: e.target.value })}
                        className="w-full mt-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      >
                        <option value="bg">🇧🇬 Bulgarian</option>
                        <option value="en">🇬🇧 English</option>
                        <option value="de">🇩🇪 German</option>
                        <option value="ru">🇷🇺 Russian</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Compliance */}
                <div className="bg-gray-100 rounded-2xl p-6 md:col-span-2">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Compliance & Safety</h2>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-900">🔞 Age Verification for Alcohol</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.age_verification}
                          onChange={() => setSettings({ ...settings, age_verification: !settings.age_verification })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-600 peer-checked:bg-green-500 rounded-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-900">📈 Enable Upselling</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.enable_upselling}
                          onChange={() => setSettings({ ...settings, enable_upselling: !settings.enable_upselling })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-600 peer-checked:bg-green-500 rounded-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                      </label>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-900">🧾 Auto-Print Receipt</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.receipt_print_auto}
                          onChange={() => setSettings({ ...settings, receipt_print_auto: !settings.receipt_print_auto })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-600 peer-checked:bg-green-500 rounded-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <button className="mt-6 w-full py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600">
                Save Settings
              </button>
            </motion.div>
          )}

          {activeTab === 'analytics' && (
            <motion.div
              key="analytics"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Conversion Funnel */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Conversion Funnel</h3>
                  <div className="space-y-3">
                    {[
                      { stage: 'Sessions Started', count: 109, percent: 100 },
                      { stage: 'Items Added', count: 87, percent: 80 },
                      { stage: 'Cart Viewed', count: 72, percent: 66 },
                      { stage: 'Payment Started', count: 68, percent: 62 },
                      { stage: 'Completed', count: 94, percent: 86 },
                    ].map((item, idx) => (
                      <div key={idx}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-900">{item.stage}</span>
                          <span className="text-gray-700">{item.count}</span>
                        </div>
                        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-orange-500 to-yellow-400"
                            style={{ width: `${item.percent}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Average Session Time */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Session Duration</h3>
                  <div className="text-center mb-4">
                    <div className="text-4xl font-bold text-blue-400">2:24</div>
                    <div className="text-gray-500">Average Session</div>
                  </div>
                  <div className="space-y-2">
                    {[
                      { range: '< 1 min', percent: 15, desc: 'Quick orders' },
                      { range: '1-3 min', percent: 55, desc: 'Standard' },
                      { range: '3-5 min', percent: 22, desc: 'Browsing' },
                      { range: '> 5 min', percent: 8, desc: 'Needs help' },
                    ].map((item, idx) => (
                      <div key={idx}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-700">{item.range}</span>
                          <span className="text-gray-900">{item.percent}%</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                            style={{ width: `${item.percent}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Abandonment Reasons */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Abandonment Reasons</h3>
                  <div className="space-y-3">
                    {[
                      { reason: 'Timeout', count: 12, color: 'bg-yellow-500' },
                      { reason: 'Payment Failed', count: 8, color: 'bg-red-500' },
                      { reason: 'User Cancelled', count: 6, color: 'bg-gray-500' },
                      { reason: 'Item Unavailable', count: 3, color: 'bg-orange-500' },
                      { reason: 'Technical Error', count: 2, color: 'bg-purple-500' },
                    ].map((item, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${item.color}`}></div>
                        <span className="text-gray-700 flex-1">{item.reason}</span>
                        <span className="text-gray-900">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Payment Methods */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Payment Methods</h3>
                  <div className="flex items-center justify-center h-40">
                    <div className="relative w-32 h-32">
                      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="15" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#22c55e" strokeWidth="15"
                          strokeDasharray={`${65 * 2.51} ${100 * 2.51}`} />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#3b82f6" strokeWidth="15"
                          strokeDasharray={`${25 * 2.51} ${100 * 2.51}`} strokeDashoffset={`${-65 * 2.51}`} />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#f59e0b" strokeWidth="15"
                          strokeDasharray={`${10 * 2.51} ${100 * 2.51}`} strokeDashoffset={`${-90 * 2.51}`} />
                      </svg>
                    </div>
                  </div>
                  <div className="flex justify-center gap-4 text-sm">
                    <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-500 rounded-full"></span> Card 65%</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded-full"></span> NFC 25%</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 bg-yellow-500 rounded-full"></span> Cash 10%</span>
                  </div>
                </div>

                {/* Daily Comparison */}
                <div className="bg-gray-100 rounded-2xl p-6 md:col-span-2">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Weekly Performance</h3>
                  <div className="grid grid-cols-7 gap-2">
                    {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, idx) => {
                      const orders = [85, 92, 78, 88, 105, 142, 128][idx];
                      const revenue = [2550, 2760, 2340, 2640, 3150, 4260, 3840][idx];
                      return (
                        <div key={day} className="bg-gray-50 rounded-xl p-3 text-center">
                          <div className="text-gray-500 text-sm mb-2">{day}</div>
                          <div className="text-gray-900 font-bold">{orders}</div>
                          <div className="text-white/40 text-xs">orders</div>
                          <div className="text-green-400 text-sm mt-1">{revenue} лв</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Kiosk Detail Modal */}
        {selectedKiosk && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedKiosk.name}</h2>
                  <p className="text-gray-600">{selectedKiosk.location}</p>
                </div>
                <button onClick={() => setSelectedKiosk(null)} className="text-gray-600 hover:text-gray-900 text-2xl">×</button>
              </div>

              {/* Hardware Status */}
              <div className="bg-gray-100 rounded-xl p-4 mb-4">
                <h3 className="text-gray-900 font-semibold mb-3">Hardware Status</h3>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(selectedKiosk.hardware).filter(([k]) => !['temperature', 'uptime_hours'].includes(k)).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center">
                      <span className="text-gray-700 capitalize">{key.replace('_', ' ')}</span>
                      <span className={getHardwareColor(value as string)}>{value}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200 flex justify-between">
                  <span className="text-gray-500">Temperature: {selectedKiosk.hardware.temperature}°C</span>
                  <span className="text-gray-500">Uptime: {selectedKiosk.hardware.uptime_hours}h</span>
                </div>
              </div>

              {/* Daily Stats */}
              <div className="bg-gray-100 rounded-xl p-4 mb-4">
                <h3 className="text-gray-900 font-semibold mb-3">Today&apos;s Performance</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-900">{selectedKiosk.daily_stats.sessions}</div>
                    <div className="text-gray-500 text-sm">Sessions</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">{selectedKiosk.daily_stats.completed_orders}</div>
                    <div className="text-gray-500 text-sm">Completed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-400">{(selectedKiosk.daily_stats.total_revenue || 0).toFixed(0)} лв</div>
                    <div className="text-gray-500 text-sm">Revenue</div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleRestartKiosk(selectedKiosk.id)}
                  className="py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                >
                  Restart Kiosk
                </button>
                <button className="py-3 bg-blue-500 text-gray-900 rounded-xl hover:bg-blue-600">
                  Remote Access
                </button>
                <button className="py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600">
                  View Logs
                </button>
                <button className="py-3 bg-red-500 text-gray-900 rounded-xl hover:bg-red-600">
                  Disable Kiosk
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
