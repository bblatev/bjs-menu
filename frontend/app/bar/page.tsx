'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { clearAuth, api } from '@/lib/api';
import { toast } from '@/lib/toast';
interface BarStats {
  totalSales: number;
  totalCost: number;
  pourCostPercentage: number;
  avgTicket: number;
  topCocktail: string;
  spillageToday: number;
  lowStockItems: number;
  activeRecipes: number;
}
interface TopDrink {
  id: number;
  name: string;
  category: string;
  soldToday: number;
  revenue: number;
  pourCost: number;
  margin: number;
}
interface InventoryAlert {
  id: number;
  item_name: string;
  current_stock: number;
  par_level: number;
  unit: string;
  status: 'critical' | 'low' | 'reorder';
}
interface RecentPour {
  id: number;
  drink_name: string;
  bartender: string;
  time: string;
  type: 'sale' | 'comp' | 'spillage' | 'waste';
  amount: string;
  cost: number;
}
export default function BarManagementPage() {
  const [stats, setStats] = useState<BarStats | null>(null);
  const [topDrinks, setTopDrinks] = useState<TopDrink[]>([]);
  const [alerts, setAlerts] = useState<InventoryAlert[]>([]);
  const [recentPours, setRecentPours] = useState<RecentPour[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<'today' | 'week' | 'month'>('today');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isQuickPourOpen, setIsQuickPourOpen] = useState(false);
  const [quickPour, setQuickPour] = useState({ drink_name: '', type: 'sale' as 'sale' | 'comp' | 'spillage', quantity: 1, notes: '' });
  useEffect(() => {
    const fetchBarData = async () => {
      setLoading(true);
      try {
        const [statsRes, drinksRes, alertsRes, activityRes] = await Promise.allSettled([
  api.get(`/bar/stats?period=${selectedPeriod}`),
  api.get(`/bar/top-drinks?period=${selectedPeriod}`),
  api.get('/bar/inventory-alerts'),
  api.get('/bar/recent-activity')
]);
        // Process stats
        if (statsRes.status === 'fulfilled') {
          const data: any = statsRes.value;
          setStats({
            totalSales: data.total_sales || 0,
            totalCost: data.total_cost || 0,
            pourCostPercentage: data.pour_cost_percentage || 0,
            avgTicket: data.avg_ticket || 0,
            topCocktail: data.top_cocktail || 'N/A',
            spillageToday: data.spillage_today || 0,
            lowStockItems: data.low_stock_items || 0,
            activeRecipes: data.active_recipes || 0
          });
        } else {
          setStats(null);
        }
        // Process top drinks
        if (drinksRes.status === 'fulfilled') {
          const data_topDrinks: any = drinksRes.value;
          const items = Array.isArray(data_topDrinks) ? data_topDrinks : (data_topDrinks.items || []);
          setTopDrinks(items.map((d: any) => ({
            id: d.id,
            name: d.name,
            category: d.category,
            soldToday: d.sold_today,
            revenue: d.revenue,
            pourCost: d.pour_cost,
            margin: d.margin
          })));
        } else {
          setTopDrinks([]);
        }
        // Process alerts
        if (alertsRes.status === 'fulfilled') {
          const data_alerts: any = alertsRes.value;
          const alertsList = Array.isArray(data_alerts) ? data_alerts : (data_alerts.items || []);
          setAlerts(alertsList.map((a: any) => ({
            id: a.id,
            item_name: a.item_name,
            current_stock: a.current_stock,
            par_level: a.par_level,
            unit: a.unit,
            status: a.status
          })));
        } else {
          setAlerts([]);
        }
        // Process recent activity
        if (activityRes.status === 'fulfilled') {
          const data_recentPours: any = activityRes.value;
          const poursList = Array.isArray(data_recentPours) ? data_recentPours : (data_recentPours.items || []);
          setRecentPours(poursList.map((p: any) => ({
            id: p.id,
            drink_name: p.drink_name,
            bartender: p.bartender,
            time: p.time,
            type: p.type,
            amount: p.amount,
            cost: p.cost
          })));
        } else {
          setRecentPours([]);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to fetch bar data:', err);
        setError('Failed to load bar data. Please check your connection.');
      } finally {
        setLoading(false);
      }
    };
    fetchBarData();
  }, [selectedPeriod]);
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical': return 'bg-error-100 text-error-700 border-error-300';
      case 'low': return 'bg-warning-100 text-warning-700 border-warning-300';
      case 'reorder': return 'bg-primary-100 text-primary-700 border-primary-300';
      default: return 'bg-surface-100 text-surface-700';
    }
  };
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'sale': return 'text-success-600';
      case 'comp': return 'text-primary-600';
      case 'spillage': return 'text-warning-600';
      case 'waste': return 'text-error-600';
      default: return 'text-surface-600';
    }
  };
  const getPourCostColor = (cost: number) => {
    if (cost <= 20) return 'text-success-600';
    if (cost <= 25) return 'text-primary-600';
    if (cost <= 30) return 'text-warning-600';
    return 'text-error-600';
  };
  const handleQuickPour = async () => {
    try {
      await api.post('/bar/spillage/records', {
          item_name: quickPour.drink_name,
          quantity: quickPour.quantity,
          reason: quickPour.type === 'spillage' ? 'spillage' : quickPour.type === 'comp' ? 'comp' : 'sale',
          notes: quickPour.notes,
        });
      // Add to recent pours
      const newPour: RecentPour = {
        id: Date.now(),
        drink_name: quickPour.drink_name,
        bartender: 'Current User',
        time: new Date().toLocaleTimeString('bg-BG', { hour: '2-digit', minute: '2-digit' }),
        type: quickPour.type,
        amount: `${quickPour.quantity}`,
        cost: quickPour.quantity * 5.00,
      };
      setRecentPours([newPour, ...recentPours.slice(0, 9)]);
      setIsQuickPourOpen(false);
      setQuickPour({ drink_name: '', type: 'sale', quantity: 1, notes: '' });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to record pour');
    }
  };
  // Loading state
  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading bar data...</p>
        </div>
      </div>
    );
  }
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-4 bg-warning-50 border border-warning-200 rounded-lg text-warning-800">
          {error}
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Bar Management</h1>
          <p className="text-surface-600 mt-1">Pour costs, inventory, recipes & bartender performance</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value as typeof selectedPeriod)}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
          </select>
          <button
            onClick={() => setIsQuickPourOpen(true)}
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Quick Pour
          </button>
          <button
            onClick={() => {
              clearAuth();
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
      {/* Quick Navigation */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
        <Link
          href="/bar/pour-costs"
          className="flex items-center gap-4 p-4 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl border border-purple-200 hover:shadow-md transition-shadow"
        >
          <div className="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center text-gray-900 text-2xl">
            🍸
          </div>
          <div>
            <h3 className="font-semibold text-surface-900">Pour Costs</h3>
            <p className="text-sm text-surface-600">Track drink costs</p>
          </div>
        </Link>
        <Link
          href="/bar/inventory"
          className="flex items-center gap-4 p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl border border-blue-200 hover:shadow-md transition-shadow"
        >
          <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center text-gray-900 text-2xl">
            🍾
          </div>
          <div>
            <h3 className="font-semibold text-surface-900">Liquor Inventory</h3>
            <p className="text-sm text-surface-600">Bottle tracking</p>
          </div>
        </Link>
        <Link
          href="/bar/recipes"
          className="flex items-center gap-4 p-4 bg-gradient-to-br from-green-50 to-green-100 rounded-xl border border-green-200 hover:shadow-md transition-shadow"
        >
          <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center text-gray-900 text-2xl">
            📋
          </div>
          <div>
            <h3 className="font-semibold text-surface-900">Cocktail Recipes</h3>
            <p className="text-sm text-surface-600">Manage recipes</p>
          </div>
        </Link>
        <Link
          href="/bar/happy-hours"
          className="flex items-center gap-4 p-4 bg-gradient-to-br from-pink-50 to-pink-100 rounded-xl border border-pink-200 hover:shadow-md transition-shadow"
        >
          <div className="w-12 h-12 bg-pink-500 rounded-lg flex items-center justify-center text-gray-900 text-2xl">
            🎉
          </div>
          <div>
            <h3 className="font-semibold text-surface-900">Happy Hours</h3>
            <p className="text-sm text-surface-600">Drink specials</p>
          </div>
        </Link>
        <Link
          href="/bar/tabs"
          className="flex items-center gap-4 p-4 bg-gradient-to-br from-cyan-50 to-cyan-100 rounded-xl border border-cyan-200 hover:shadow-md transition-shadow"
        >
          <div className="w-12 h-12 bg-cyan-500 rounded-lg flex items-center justify-center text-gray-900 text-2xl">
            💳
          </div>
          <div>
            <h3 className="font-semibold text-surface-900">Bar Tabs</h3>
            <p className="text-sm text-surface-600">Open tabs</p>
          </div>
        </Link>
        <Link
          href="/bar/spillage"
          className="flex items-center gap-4 p-4 bg-gradient-to-br from-red-50 to-red-100 rounded-xl border border-red-200 hover:shadow-md transition-shadow"
        >
          <div className="w-12 h-12 bg-red-500 rounded-lg flex items-center justify-center text-gray-900 text-2xl">
            💧
          </div>
          <div>
            <h3 className="font-semibold text-surface-900">Spillage</h3>
            <p className="text-sm text-surface-600">Waste tracking</p>
          </div>
        </Link>
        <Link
          href="/reports/bar"
          className="flex items-center gap-4 p-4 bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl border border-orange-200 hover:shadow-md transition-shadow"
        >
          <div className="w-12 h-12 bg-orange-500 rounded-lg flex items-center justify-center text-gray-900 text-2xl">
            📊
          </div>
          <div>
            <h3 className="font-semibold text-surface-900">Bar Reports</h3>
            <p className="text-sm text-surface-600">Analytics</p>
          </div>
        </Link>
      </div>
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Sales</p>
            <p className="text-xl font-bold text-surface-900">${(stats.totalSales || 0).toFixed(2)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Cost</p>
            <p className="text-xl font-bold text-surface-900">${(stats.totalCost || 0).toFixed(2)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Pour Cost %</p>
            <p className={`text-xl font-bold ${getPourCostColor(stats.pourCostPercentage)}`}>
              {(stats.pourCostPercentage || 0).toFixed(1)}%
            </p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Avg Ticket</p>
            <p className="text-xl font-bold text-surface-900">${(stats.avgTicket || 0).toFixed(2)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Top Drink</p>
            <p className="text-xl font-bold text-primary-600">{stats.topCocktail}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Spillage</p>
            <p className="text-xl font-bold text-warning-600">${(stats.spillageToday || 0).toFixed(2)}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Low Stock</p>
            <p className="text-xl font-bold text-error-600">{stats.lowStockItems}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Recipes</p>
            <p className="text-xl font-bold text-surface-900">{stats.activeRecipes}</p>
          </div>
        </div>
      )}
      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Selling Drinks */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-surface-200 shadow-sm">
          <div className="p-4 border-b border-surface-200">
            <h2 className="font-semibold text-surface-900">Top Selling Drinks</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Drink</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Sold</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Revenue</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Pour Cost</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Margin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {topDrinks.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-surface-500">No drink sales data yet</td></tr>
                ) : topDrinks.map((drink) => (
                  <tr key={drink.id} className="hover:bg-surface-50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-surface-900">{drink.name}</p>
                        <p className="text-sm text-surface-500">{drink.category}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="font-medium text-surface-900">{drink.soldToday}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="font-medium text-success-600">${(drink.revenue || 0).toFixed(2)}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-medium ${getPourCostColor(drink.pourCost)}`}>
                        {(drink.pourCost || 0).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-2 bg-surface-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-success-500 rounded-full"
                            style={{ width: `${drink.margin}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-surface-700">{(drink.margin || 0).toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        {/* Low Stock Alerts */}
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm">
          <div className="p-4 border-b border-surface-200 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Inventory Alerts</h2>
            <Link href="/bar/inventory" className="text-sm text-primary-600 hover:text-primary-700">
              View All
            </Link>
          </div>
          <div className="p-4 space-y-3">
            {alerts.length === 0 && (
              <p className="text-center text-surface-500 py-4">No inventory alerts</p>
            )}
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-3 rounded-lg border ${getStatusColor(alert.status)}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium">{alert.item_name}</span>
                  <span className="text-xs uppercase font-semibold">{alert.status}</span>
                </div>
                <div className="text-sm">
                  {alert.current_stock} / {alert.par_level} {alert.unit}
                </div>
                <div className="mt-2 h-2 bg-black/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-current rounded-full opacity-50"
                    style={{ width: `${(alert.current_stock / alert.par_level) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* Recent Activity */}
      <div className="mt-6 bg-white rounded-xl border border-surface-200 shadow-sm">
        <div className="p-4 border-b border-surface-200 flex items-center justify-between">
          <h2 className="font-semibold text-surface-900">Recent Bar Activity</h2>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs text-success-600">
              <span className="w-2 h-2 bg-success-500 rounded-full animate-pulse" />
              Live
            </span>
          </div>
        </div>
        <div className="divide-y divide-surface-100">
          {recentPours.length === 0 && (
            <p className="text-center text-surface-500 py-8">No recent bar activity</p>
          )}
          {recentPours.map((pour) => (
            <div key={pour.id} className="px-4 py-3 flex items-center justify-between hover:bg-surface-50">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-gray-900 ${
                  pour.type === 'sale' ? 'bg-success-500' :
                  pour.type === 'comp' ? 'bg-primary-500' :
                  pour.type === 'spillage' ? 'bg-warning-500' :
                  'bg-error-500'
                }`}>
                  {pour.type === 'sale' ? '💰' :
                   pour.type === 'comp' ? '🎁' :
                   pour.type === 'spillage' ? '💧' :
                   '🗑️'}
                </div>
                <div>
                  <p className="font-medium text-surface-900">{pour.drink_name}</p>
                  <p className="text-sm text-surface-500">{pour.bartender} • {pour.time}</p>
                </div>
              </div>
              <div className="text-right">
                <p className={`font-medium ${getTypeColor(pour.type)}`}>
                  {pour.type === 'sale' ? '+' : '-'}{pour.amount}
                </p>
                <p className="text-sm text-surface-500">${(pour.cost || 0).toFixed(2)} cost</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* Pour Cost Breakdown Chart Placeholder */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Pour Cost by Category</h3>
          <div className="space-y-3">
            {[
              { category: 'Spirits', percentage: 24, target: 22, color: 'bg-purple-500' },
              { category: 'Beer', percentage: 18, target: 20, color: 'bg-amber-500' },
              { category: 'Wine', percentage: 32, target: 30, color: 'bg-red-500' },
              { category: 'Cocktails', percentage: 23, target: 25, color: 'bg-blue-500' },
              { category: 'Non-Alcoholic', percentage: 15, target: 18, color: 'bg-green-500' },
            ].map((item) => (
              <div key={item.category}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-surface-700">{item.category}</span>
                  <span className={`text-sm font-medium ${item.percentage > item.target ? 'text-error-600' : 'text-success-600'}`}>
                    {item.percentage}% {item.percentage > item.target ? '↑' : '↓'} (target: {item.target}%)
                  </span>
                </div>
                <div className="h-3 bg-surface-200 rounded-full overflow-hidden relative">
                  <div
                    className={`h-full ${item.color} rounded-full`}
                    style={{ width: `${(item.percentage / 40) * 100}%` }}
                  />
                  <div
                    className="absolute top-0 h-full w-0.5 bg-white"
                    style={{ left: `${(item.target / 40) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
          <h3 className="font-semibold text-surface-900 mb-4">Bartender Performance</h3>
          <div className="space-y-4">
            {[
              { name: 'Alex', drinks: 45, spillage: 2, avgPourCost: 22.5, tips: 156 },
              { name: 'Maria', drinks: 38, spillage: 1, avgPourCost: 24.0, tips: 132 },
              { name: 'Jordan', drinks: 32, spillage: 0, avgPourCost: 21.8, tips: 98 },
              { name: 'Sam', drinks: 28, spillage: 3, avgPourCost: 26.2, tips: 87 },
            ].map((bartender) => (
              <div key={bartender.name} className="flex items-center justify-between p-3 bg-surface-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center font-semibold text-primary-700">
                    {bartender.name[0]}
                  </div>
                  <div>
                    <p className="font-medium text-surface-900">{bartender.name}</p>
                    <p className="text-sm text-surface-500">{bartender.drinks} drinks made</p>
                  </div>
                </div>
                <div className="text-right grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-surface-500">Spillage</p>
                    <p className={`font-medium ${bartender.spillage > 2 ? 'text-error-600' : 'text-success-600'}`}>
                      {bartender.spillage}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-surface-500">Pour Cost</p>
                    <p className={`font-medium ${getPourCostColor(bartender.avgPourCost)}`}>
                      {bartender.avgPourCost}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-surface-500">Tips</p>
                    <p className="font-medium text-success-600">${bartender.tips}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* Quick Pour Modal */}
      {isQuickPourOpen && (
        <>
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50" onClick={() => setIsQuickPourOpen(false)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white rounded-2xl shadow-2xl">
            <div className="p-6 border-b border-surface-100">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-surface-900">Quick Pour</h2>
                <button onClick={() => setIsQuickPourOpen(false)} className="p-2 rounded-lg hover:bg-surface-100">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Drink Name
                <input
                  type="text"
                  value={quickPour.drink_name}
                  onChange={(e) => setQuickPour({ ...quickPour, drink_name: e.target.value })}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Mojito, Margarita"
                />
                </label>
              </div>
              <div>
                <span className="block text-sm font-medium text-surface-700 mb-1">Type</span>
                <div className="grid grid-cols-3 gap-2">
                  {(['sale', 'comp', 'spillage'] as const).map((type) => (
                    <button
                      key={type}
                      onClick={() => setQuickPour({ ...quickPour, type })}
                      className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                        quickPour.type === type
                          ? type === 'sale' ? 'bg-success-500 text-white'
                          : type === 'comp' ? 'bg-primary-500 text-white'
                          : 'bg-warning-500 text-white'
                          : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                      }`}
                    >
                      {type === 'sale' ? '💰 Sale' : type === 'comp' ? '🎁 Comp' : '💧 Spillage'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <span className="block text-sm font-medium text-surface-700 mb-1">Quantity</span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setQuickPour({ ...quickPour, quantity: Math.max(1, quickPour.quantity - 1) })}
                    className="w-10 h-10 rounded-lg bg-surface-100 hover:bg-surface-200 flex items-center justify-center text-xl"
                  >
                    -
                  </button>
                  <span className="text-2xl font-bold w-12 text-center">{quickPour.quantity}</span>
                  <button
                    onClick={() => setQuickPour({ ...quickPour, quantity: quickPour.quantity + 1 })}
                    className="w-10 h-10 rounded-lg bg-primary-100 hover:bg-primary-200 text-primary-600 flex items-center justify-center text-xl"
                  >
                    +
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Notes (optional)
                <input
                  type="text"
                  value={quickPour.notes}
                  onChange={(e) => setQuickPour({ ...quickPour, notes: e.target.value })}
                  className="w-full px-4 py-3 border border-surface-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Any additional notes..."
                />
                </label>
              </div>
            </div>
            <div className="p-6 border-t border-surface-100 flex gap-3">
              <button
                onClick={() => setIsQuickPourOpen(false)}
                className="flex-1 py-3 bg-surface-100 text-surface-700 font-semibold rounded-xl hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                onClick={handleQuickPour}
                disabled={!quickPour.drink_name}
                className="flex-1 py-3 bg-primary-600 text-gray-900 font-semibold rounded-xl hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Record Pour
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}