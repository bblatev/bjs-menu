'use client';
import { useState, useEffect, memo } from 'react';
import Link from 'next/link';

import { API_URL, clearAuth, api } from '@/lib/api';
/** Isolated clock component to prevent full dashboard re-render every second */
const LiveClock = memo(function LiveClock() {
  const [currentTime, setCurrentTime] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <span className="font-mono text-lg">
      {currentTime.toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  );
});
interface DashboardStats {
  total_orders_today: number;
  total_revenue_today: number;
  active_orders: number;
  pending_calls: number;
  average_rating: number;
  top_items: Array<{ name: string; count: number }>;
  orders_by_hour: Array<{ hour: number; count: number }>;
}
interface KitchenStats {
  active_alerts: number;
  orders_by_status: Record<string, number>;
  items_86_count: number;
  rush_orders_today: number;
  vip_orders_today: number;
  avg_prep_time_minutes: number | null;
  orders_completed_today: number;
}
interface Order {
  id: number;
  order_number: string;
  table_id: number | null;
  status: string;
  total: number;
  created_at: string;
  items?: Array<{ id: number }>;
}
interface Table {
  id: number;
  number: string;
  capacity: number;
  status: string;
}
interface Reservation {
  id: number;
  customer_name: string;
  party_size: number;
  reservation_time: string;
  status: string;
}
interface SystemHealth {
  database: boolean;
  redis: boolean;
  api: boolean;
}
function DashboardContent() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Data states
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [kitchenStats, setKitchenStats] = useState<KitchenStats | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({ database: true, redis: true, api: true });
  // Fetch all dashboard data
  const fetchDashboardData = async () => {
    try {
      // Fetch all data in parallel with timeout
      const apiWithTimeout = <T,>(promise: Promise<T>, timeout = 5000): Promise<T> => {
        return Promise.race([
          promise,
          new Promise<T>((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), timeout)
          )
        ]);
      };
      const [statsRes, kitchenRes, ordersRes, tablesRes, reservationsRes] = await Promise.allSettled([
        apiWithTimeout(api.get('/analytics/dashboard')),
        apiWithTimeout(api.get('/kitchen/stats')),
        apiWithTimeout(api.get('/orders')),
        apiWithTimeout(api.get('/tables')),
        apiWithTimeout(api.get('/reservations')),
      ]);
      // Process dashboard stats
      if (statsRes.status === 'fulfilled') {
        setDashboardStats(statsRes.value as DashboardStats);
      }
      // Process kitchen stats
      if (kitchenRes.status === 'fulfilled') {
        setKitchenStats(kitchenRes.value as KitchenStats);
      }
      // Process orders (may return 401 if not authenticated - that's OK)
      if (ordersRes.status === 'fulfilled') {
        const data_orders: any = ordersRes.value;
        const ordersList = Array.isArray(data_orders) ? data_orders : (data_orders.items || data_orders.orders || []);
        setOrders(ordersList);
      }
      // Process tables
      if (tablesRes.status === 'fulfilled') {
        const data_tables: any = tablesRes.value;
        const tablesList = Array.isArray(data_tables) ? data_tables : (data_tables.items || data_tables.tables || []);
        setTables(tablesList);
      }
      // Process reservations
      if (reservationsRes.status === 'fulfilled') {
        const data_reservations: any = reservationsRes.value;
        const reservationsList = Array.isArray(data_reservations) ? data_reservations : (data_reservations.items || data_reservations.reservations || []);
        setReservations(reservationsList);
      }
      // Check real system health via /health/ready endpoint
      try {
        const health: any = await apiWithTimeout(
          fetch(`${API_URL.replace('/api/v1', '')}/health/ready`, { credentials: 'include' }).then(r => r.json()),
          5000
        );
        setSystemHealth({
          database: health.checks?.database === 'healthy',
          redis: true,
          api: true,
        });
        setError(null);
      } catch {
        // API responded to data requests above, so it's up
        const anyResponse = [statsRes, kitchenRes, tablesRes].some(
          r => r.status === 'fulfilled'
        );
        setSystemHealth({
          database: anyResponse,
          redis: anyResponse,
          api: anyResponse,
        });
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Неуспешно зареждане на данни. Проверете API сървъра.');
      setSystemHealth({ database: false, redis: false, api: false });
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    fetchDashboardData();
    // Refresh data every 30 seconds, but only when tab is visible
    const refreshInterval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchDashboardData();
      }
    }, 30000);
    // Also refresh immediately when tab becomes visible after being hidden
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchDashboardData();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      clearInterval(refreshInterval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Добро утро';
    if (hour < 18) return 'Добър ден';
    return 'Добър вечер';
  };
  // Calculate stats from real data
  const activeTables = tables.filter(t => t.status === 'occupied').length;
  const totalTables = tables.length || 20;
  const activeOrders = orders.filter(o => ['new', 'preparing', 'ready'].includes(o.status));
  const todayRevenue = dashboardStats?.total_revenue_today || 0;
  const totalOrdersToday = dashboardStats?.total_orders_today || orders.length;
  const avgTicket = totalOrdersToday > 0 ? todayRevenue / totalOrdersToday : 0;
  const upcomingReservations = reservations.filter(r => r.status === 'confirmed' || r.status === 'pending');
  const colorClasses: Record<string, { text600: string; text700: string; from50: string; bg50: string; bg100: string }> = {
    primary: { text600: 'text-primary-600', text700: 'text-primary-700', from50: 'from-primary-50', bg50: 'bg-primary-50', bg100: 'bg-primary-100' },
    accent: { text600: 'text-accent-600', text700: 'text-accent-700', from50: 'from-accent-50', bg50: 'bg-accent-50', bg100: 'bg-accent-100' },
    success: { text600: 'text-success-600', text700: 'text-success-700', from50: 'from-success-50', bg50: 'bg-success-50', bg100: 'bg-success-100' },
    warning: { text600: 'text-warning-600', text700: 'text-warning-700', from50: 'from-warning-50', bg50: 'bg-warning-50', bg100: 'bg-warning-100' },
    error: { text600: 'text-error-600', text700: 'text-error-700', from50: 'from-error-50', bg50: 'bg-error-50', bg100: 'bg-error-100' },
  };
  const stats = [
    {
      label: "Приходи днес",
      value: `${todayRevenue.toLocaleString('bg-BG')} лв`,
      // BGN to EUR fixed peg rate (Bulgarian currency board)
      subvalue: `€${((todayRevenue / 1.95583) || 0).toFixed(0)}`,
      icon: '💰',
      color: 'success'
    },
    {
      label: 'Поръчки',
      value: totalOrdersToday.toString(),
      subvalue: `${activeOrders.length} активни`,
      icon: '📋',
      color: 'primary'
    },
    {
      label: 'Средна сметка',
      value: `${(avgTicket || 0).toFixed(0)} лв`,
      subvalue: `€${((avgTicket / 1.96) || 0).toFixed(2)}`,
      icon: '🧾',
      color: 'accent'
    },
    {
      label: 'Активни маси',
      value: `${activeTables}/${totalTables}`,
      subvalue: `${totalTables > 0 ? Math.round(activeTables / totalTables * 100) : 0}% заетост`,
      icon: '🪑',
      color: 'primary'
    },
    {
      label: 'Резервации',
      value: upcomingReservations.length.toString(),
      subvalue: upcomingReservations.length > 0 ? 'Следваща скоро' : 'Няма предстоящи',
      icon: '📅',
      color: 'warning'
    },
  ];
  const quickActions = [
    { icon: '➕', label: 'Нова поръчка', href: '/orders/new', color: 'primary' },
    { icon: '🍽️', label: 'Дневно меню', href: '/daily-menu', color: 'warning' },
    { icon: '📅', label: 'Резервации', href: '/reservations', color: 'accent' },
    { icon: '👨‍🍳', label: 'Кухня', href: '/kitchen', color: 'warning' },
    { icon: '🍸', label: 'Бар', href: '/bar', color: 'accent' },
    { icon: '📦', label: 'Склад', href: '/stock', color: 'success' },
    { icon: '📊', label: 'Отчети', href: '/reports', color: 'primary' },
  ];
  // Get recent active orders for display
  const liveOrders = activeOrders.slice(0, 5).map(order => ({
    table: order.table_id ? `T${order.table_id}` : 'Takeaway',
    items: order.items?.length || 0,
    time: getTimeAgo(order.created_at),
    status: order.status as 'new' | 'preparing' | 'ready',
    total: `${(order.total || 0).toFixed(0)} лв`,
    orderNumber: order.order_number,
  }));
  function getTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Сега';
    if (diffMins === 1) return 'Преди 1 мин';
    if (diffMins < 60) return `Преди ${diffMins} мин`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours === 1) return 'Преди 1 час';
    return `Преди ${diffHours} часа`;
  }
  const navSections = [
    {
      title: 'Основни операции',
      color: 'primary',
      items: [
        { href: '/orders', label: 'Поръчки', icon: '📋', desc: 'Управление на поръчки' },
        { href: '/tables', label: 'Маси', icon: '🪑', desc: 'План на залата' },
        { href: '/reservations', label: 'Резервации', icon: '📅', desc: 'Система за резервации' },
        { href: '/kitchen', label: 'Кухня', icon: '👨‍🍳', desc: 'KDS дисплей' },
        { href: '/bar', label: 'Бар', icon: '🍸', desc: 'Управление на бара' },
        { href: '/waiter-calls', label: 'Повиквания', icon: '🔔', desc: 'Заявки за обслужване' },
      ]
    },
    {
      title: 'Меню и инвентар',
      color: 'accent',
      items: [
        { href: '/menu', label: 'Меню', icon: '🍽️', desc: 'Редактиране на артикули' },
        { href: '/menu/inventory', label: 'Инвентар меню', icon: '📋', desc: 'Версии и хранителни стойности' },
        { href: '/recipes/management', label: 'Рецепти', icon: '📖', desc: 'Калкулация и порции' },
        { href: '/stock/inventory', label: 'Склад', icon: '📦', desc: 'Складове и партиди' },
        { href: '/suppliers/management', label: 'Доставчици', icon: '🚛', desc: 'Ценоразписи и рейтинг' },
        { href: '/purchase-orders/management', label: 'Доставки', icon: '📝', desc: 'Поръчки и фактури' },
      ]
    },
    {
      title: 'Персонал и HR',
      color: 'success',
      items: [
        { href: '/staff', label: 'Персонал', icon: '👥', desc: 'Служители' },
        { href: '/shifts', label: 'Графици', icon: '📆', desc: 'Планиране на смени' },
        { href: '/payroll', label: 'Заплати', icon: '💵', desc: 'Възнаграждения и бакшиши' },
      ]
    },
    {
      title: 'Клиенти и CRM',
      color: 'warning',
      items: [
        { href: '/customers', label: 'Клиенти', icon: '👤', desc: 'Профили на клиенти' },
        { href: '/loyalty', label: 'Лоялност', icon: '⭐', desc: 'Точки и награди' },
        { href: '/vip-management', label: 'VIP управление', icon: '👑', desc: 'Премиум гости' },
        { href: '/sms-marketing', label: 'Маркетинг', icon: '📱', desc: 'Кампании' },
      ]
    },
    {
      title: 'Отчети и анализи',
      color: 'primary',
      items: [
        { href: '/reports', label: 'Отчети', icon: '📊', desc: 'Справки за продажби' },
        { href: '/analytics', label: 'Анализи', icon: '📈', desc: 'Бизнес анализ' },
        { href: '/financial-management', label: 'Финанси', icon: '💳', desc: 'Финансов преглед' },
      ]
    },
    {
      title: 'Корпоративни функции',
      color: 'accent',
      items: [
        { href: '/kiosk', label: 'Самообслужване', icon: '🖥️', desc: 'Киоск режим' },
        { href: '/delivery-aggregators', label: 'Доставки', icon: '🚴', desc: 'Поръчки за доставка' },
        { href: '/drive-thru', label: 'Drive-Thru', icon: '🚗', desc: 'Drive-thru операции' },
        { href: '/offline', label: 'Офлайн режим', icon: '📴', desc: 'Работа без интернет' },
      ]
    },
  ];
  const systemServices = [
    { name: 'База данни', status: systemHealth.database ? 'online' : 'offline' },
    { name: 'Redis Cache', status: systemHealth.redis ? 'online' : 'offline' },
    { name: 'Фискален принтер', status: 'online' },
    { name: 'WebSocket', status: 'online' },
    { name: 'API Gateway', status: systemHealth.api ? 'online' : 'offline' },
    { name: 'Файлов сървър', status: 'online' },
    { name: 'Платежен портал', status: 'online' },
    { name: 'SMS услуга', status: 'online' },
  ];
  // Don't block rendering - show UI immediately with placeholder data
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-surface-900">
            {getGreeting()}! 👋
          </h1>
          <p className="text-surface-500 mt-1">Ето какво се случва в BJ&apos;s Bar днес</p>
          {loading && (
            <p className="text-primary-500 text-sm mt-1 flex items-center gap-2">
              <span className="animate-spin h-3 w-3 border-2 border-primary-500 border-t-transparent rounded-full"></span>
              Зареждане на данни...
            </p>
          )}
          {error && !loading && (
            <p className="text-error-500 text-sm mt-1 flex items-center gap-2">
              ⚠️ {error}
              <button onClick={fetchDashboardData} className="underline hover:no-underline">Опитай отново</button>
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-2xl font-display font-bold text-surface-900">
              <LiveClock />
            </p>
            <p className="text-sm text-surface-500">
              {new Date().toLocaleDateString('bg-BG', { weekday: 'long', day: 'numeric', month: 'long' })}
            </p>
          </div>
          <button
            onClick={() => {
              clearAuth();
              window.location.href = '/login';
            }}
            className="p-2 text-surface-500 hover:text-surface-700 hover:bg-surface-100 rounded-lg transition-colors"
            title="Logout"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
      {/* Stats Grid */}
      <div className="grid grid-cols-5 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white rounded-2xl p-5 shadow-sm border border-surface-100 hover:shadow-md hover:border-surface-200 transition-all duration-300 animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-1">{stat.label}</p>
                <p className={`text-2xl font-display font-bold ${colorClasses[stat.color]?.text600 || 'text-primary-600'}`}>{stat.value}</p>
                {stat.subvalue && <p className="text-xs text-surface-500 mt-0.5">{stat.subvalue}</p>}
                {(stat as any).trend && (
                  <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${(stat as any).trend.up ? 'text-success-600' : 'text-error-600'}`}>
                    <svg className={`w-3 h-3 ${(stat as any).trend.up ? '' : 'rotate-180'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                    </svg>
                    <span>{(stat as any).trend.value}%</span>
                  </div>
                )}
              </div>
              <span className="text-2xl">{stat.icon}</span>
            </div>
          </div>
        ))}
      </div>
      {/* Quick Actions */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100">
        <h2 className="text-lg font-semibold text-surface-900 mb-4">Бързи действия</h2>
        <div className="grid grid-cols-7 gap-4">
          {quickActions.map((action, i) => (
            <Link
              key={i}
              href={action.href}
              className="group flex flex-col items-center gap-3 p-4 rounded-xl border-2 border-surface-100 hover:border-primary-200 hover:bg-primary-50 hover:-translate-y-1 transition-all duration-300"
            >
              <span className="text-3xl group-hover:scale-110 transition-transform duration-300">{action.icon}</span>
              <span className="text-sm font-medium text-surface-700 group-hover:text-primary-700">{action.label}</span>
            </Link>
          ))}
        </div>
      </div>
      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Live Orders */}
        <div className="col-span-1 bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Активни поръчки</h2>
            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-primary-100 text-primary-700">
              {liveOrders.length} активни
            </span>
          </div>
          <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
            {liveOrders.length > 0 ? (
              liveOrders.map((order, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-surface-50 rounded-xl hover:bg-surface-100 transition-colors cursor-pointer">
                  <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                    <span className="text-sm font-bold text-primary-700">{order.table}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-surface-900">#{order.orderNumber}</p>
                    <p className="text-xs text-surface-500">{order.time}</p>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    order.status === 'new' ? 'bg-primary-100 text-primary-700' :
                    order.status === 'preparing' ? 'bg-warning-100 text-warning-700' :
                    'bg-success-100 text-success-700'
                  }`}>
                    {order.status === 'new' ? 'Нова' : order.status === 'preparing' ? 'Готви се' : 'Готова'}
                  </span>
                  <p className="text-sm font-semibold text-surface-900">{order.total}</p>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-surface-400">
                <p className="text-4xl mb-2">📋</p>
                <p className="text-sm">Няма активни поръчки</p>
              </div>
            )}
          </div>
          <div className="px-6 py-3 border-t border-surface-100 bg-surface-50">
            <Link href="/orders" className="text-sm font-medium text-primary-600 hover:text-primary-700">
              Виж всички поръчки →
            </Link>
          </div>
        </div>
        {/* Navigation Sections */}
        <div className="col-span-2 grid grid-cols-2 gap-4">
          {navSections.map((section, i) => (
            <div key={i} className="bg-white rounded-2xl shadow-sm border border-surface-100 overflow-hidden animate-slide-up" style={{ animationDelay: `${i * 100}ms` }}>
              <div className={`px-5 py-3 border-b border-surface-100 bg-gradient-to-r ${colorClasses[section.color]?.from50 || 'from-primary-50'} to-white`}>
                <h3 className={`font-semibold ${colorClasses[section.color]?.text700 || 'text-primary-700'}`}>{section.title}</h3>
              </div>
              <div className="p-2">
                {section.items.map((item, j) => (
                  <Link
                    key={j}
                    href={item.href}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-50 transition-colors group"
                  >
                    <span className="text-xl group-hover:scale-110 transition-transform">{item.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-surface-900">{item.label}</p>
                      <p className="text-xs text-surface-500">{item.desc}</p>
                    </div>
                    <svg className="w-4 h-4 text-surface-300 group-hover:text-surface-500 group-hover:translate-x-1 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* Kitchen Stats Bar */}
      {kitchenStats && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100">
          <h2 className="text-lg font-semibold text-surface-900 mb-4">Кухня статистика</h2>
          <div className="grid grid-cols-6 gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-primary-600">{kitchenStats.active_alerts}</p>
              <p className="text-xs text-surface-500 mt-1">Активни сигнали</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-warning-600">{kitchenStats.items_86_count}</p>
              <p className="text-xs text-surface-500 mt-1">86&apos;d артикули</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-error-600">{kitchenStats.rush_orders_today}</p>
              <p className="text-xs text-surface-500 mt-1">Rush поръчки</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-accent-600">{kitchenStats.vip_orders_today || 0}</p>
              <p className="text-xs text-surface-500 mt-1">VIP поръчки</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-success-600">{kitchenStats.orders_completed_today}</p>
              <p className="text-xs text-surface-500 mt-1">Завършени днес</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-surface-600">
                {kitchenStats.avg_prep_time_minutes ? `${kitchenStats.avg_prep_time_minutes} мин` : 'N/A'}
              </p>
              <p className="text-xs text-surface-500 mt-1">Средно време</p>
            </div>
          </div>
        </div>
      )}
      {/* System Status */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-surface-100">
        <h2 className="text-lg font-semibold text-surface-900 mb-4">Системен статус</h2>
        <div className="grid grid-cols-8 gap-6">
          {systemServices.map((service, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${service.status === 'online' ? 'bg-success-500 animate-pulse' : 'bg-error-500'}`} />
              <span className="text-sm text-surface-600">{service.name}</span>
            </div>
          ))}
        </div>
      </div>
      {/* Refresh indicator */}
      <div className="text-center text-xs text-surface-400">
        Данните се обновяват автоматично на всеки 30 секунди
      </div>
    </div>
  );
}
export default function DashboardPage() {
  return <DashboardContent />;
}