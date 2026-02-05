'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface PriceAlert {
  id: number;
  itemName: string;
  itemId: number;
  category: string;
  supplier: string;
  supplierId: number;
  previousPrice: number;
  currentPrice: number;
  changePercent: number;
  changeAmount: number;
  detectedAt: string;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  trend: 'up' | 'down';
  impactOnCost: number;
}

interface PriceHistory {
  id: number;
  itemName: string;
  category: string;
  supplier: string;
  prices: { date: string; price: number }[];
  currentPrice: number;
  avgPrice: number;
  minPrice: number;
  maxPrice: number;
  volatility: number;
}

interface SupplierComparison {
  itemName: string;
  category: string;
  suppliers: {
    name: string;
    price: number;
    lastUpdated: string;
    reliability: number;
    deliveryTime: string;
  }[];
  bestPrice: number;
  currentSupplier: string;
  potentialSavings: number;
}

interface AlertRule {
  id: number;
  name: string;
  category: string;
  threshold: number;
  direction: 'increase' | 'decrease' | 'both';
  notifyEmail: boolean;
  notifySms: boolean;
  notifyPush: boolean;
  isActive: boolean;
  triggeredCount: number;
}

interface CategoryTrend {
  category: string;
  currentAvg: number;
  previousAvg: number;
  changePercent: number;
  itemCount: number;
  topMover: string;
  topMoverChange: number;
}

interface BudgetImpact {
  category: string;
  budgeted: number;
  projected: number;
  variance: number;
  variancePercent: number;
}

export default function PriceTrackerPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [priceHistory, setPriceHistory] = useState<PriceHistory[]>([]);
  const [supplierComparisons, setSupplierComparisons] = useState<SupplierComparison[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [categoryTrends, setCategoryTrends] = useState<CategoryTrend[]>([]);
  const [budgetImpacts, setBudgetImpacts] = useState<BudgetImpact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<PriceHistory | null>(null);
  const [selectedComparison, setSelectedComparison] = useState<SupplierComparison | null>(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [dateRange, setDateRange] = useState('30d');
  const [searchTerm, setSearchTerm] = useState('');

  const getToken = () => localStorage.getItem('access_token');

  const [ruleForm, setRuleForm] = useState({
    name: '',
    category: 'all',
    threshold: 5,
    direction: 'increase' as 'increase' | 'decrease' | 'both',
    notifyEmail: true,
    notifySms: false,
    notifyPush: true
  });

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const token = getToken();

    try {
      // Fetch all data in parallel for better performance
      const [
        alertsRes,
        historyRes,
        comparisonsRes,
        rulesRes,
        trendsRes,
        budgetRes
      ] = await Promise.all([
        fetch(`${API_URL}/price-tracker/alerts?date_range=${dateRange}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/price-tracker/history?date_range=${dateRange}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/price-tracker/supplier-comparisons`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/price-tracker/alert-rules`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/price-tracker/category-trends?date_range=${dateRange}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/price-tracker/budget-impacts?date_range=${dateRange}`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      // Check for errors
      if (!alertsRes.ok || !historyRes.ok || !comparisonsRes.ok ||
          !rulesRes.ok || !trendsRes.ok || !budgetRes.ok) {
        throw new Error('Failed to fetch price tracker data');
      }

      // Parse all responses
      const [
        alertsData,
        historyData,
        comparisonsData,
        rulesData,
        trendsData,
        budgetData
      ] = await Promise.all([
        alertsRes.json(),
        historyRes.json(),
        comparisonsRes.json(),
        rulesRes.json(),
        trendsRes.json(),
        budgetRes.json(),
      ]);

      setAlerts(alertsData);
      setPriceHistory(historyData);
      setSupplierComparisons(comparisonsData);
      setAlertRules(rulesData);
      setCategoryTrends(trendsData);
      setBudgetImpacts(budgetData);
    } catch (err) {
      console.error('Error loading price tracker data:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while loading data');
    } finally {
      setLoading(false);
    }
  };

  const stats = {
    totalAlerts: alerts.length,
    unacknowledged: alerts.filter(a => !a.acknowledged).length,
    criticalAlerts: alerts.filter(a => a.severity === 'critical').length,
    priceIncreases: alerts.filter(a => a.trend === 'up').length,
    priceDecreases: alerts.filter(a => a.trend === 'down').length,
    totalImpact: alerts.reduce((sum, a) => sum + a.impactOnCost, 0),
    avgChange: alerts.length > 0 ? alerts.reduce((sum, a) => sum + Math.abs(a.changePercent), 0) / alerts.length : 0,
    potentialSavings: supplierComparisons.reduce((sum, c) => sum + c.potentialSavings, 0)
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const acknowledgeAlert = async (id: number) => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/price-tracker/alerts/${id}/acknowledge`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const updatedAlert = await res.json();
        setAlerts(alerts.map(a => a.id === id ? updatedAlert : a));
      } else {
        throw new Error('Failed to acknowledge alert');
      }
    } catch (err) {
      console.error('Error acknowledging alert:', err);
      // Optimistic update fallback
      setAlerts(alerts.map(a => a.id === id ? { ...a, acknowledged: true, acknowledgedBy: 'Manager', acknowledgedAt: new Date().toISOString() } : a));
    }
  };

  const acknowledgeAll = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/price-tracker/alerts/acknowledge-all`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        await loadData();
      } else {
        throw new Error('Failed to acknowledge all alerts');
      }
    } catch (err) {
      console.error('Error acknowledging all alerts:', err);
      // Optimistic update fallback
      setAlerts(alerts.map(a => ({ ...a, acknowledged: true, acknowledgedBy: 'Manager', acknowledgedAt: new Date().toISOString() })));
    }
  };

  const handleCreateRule = async () => {
    const token = getToken();
    try {
      const res = await fetch(`${API_URL}/price-tracker/alert-rules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...ruleForm,
          isActive: true,
        }),
      });
      if (res.ok) {
        const newRule = await res.json();
        setAlertRules([...alertRules, newRule]);
        setShowRuleModal(false);
        setRuleForm({
          name: '',
          category: 'all',
          threshold: 5,
          direction: 'increase',
          notifyEmail: true,
          notifySms: false,
          notifyPush: true
        });
      } else {
        throw new Error('Failed to create alert rule');
      }
    } catch (err) {
      console.error('Error creating alert rule:', err);
      // Show error to user but still close modal
      alert('Failed to create alert rule. Please try again.');
    }
  };

  const toggleRuleActive = async (id: number) => {
    const token = getToken();
    const rule = alertRules.find(r => r.id === id);
    if (!rule) return;

    try {
      const res = await fetch(`${API_URL}/price-tracker/alert-rules/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ isActive: !rule.isActive }),
      });
      if (res.ok) {
        const updatedRule = await res.json();
        setAlertRules(alertRules.map(r => r.id === id ? updatedRule : r));
      } else {
        throw new Error('Failed to toggle rule status');
      }
    } catch (err) {
      console.error('Error toggling rule status:', err);
      // Optimistic update fallback
      setAlertRules(alertRules.map(r => r.id === id ? { ...r, isActive: !r.isActive } : r));
    }
  };

  const filteredAlerts = alerts.filter(a => {
    if (filterCategory !== 'all' && a.category !== filterCategory) return false;
    if (filterSeverity !== 'all' && a.severity !== filterSeverity) return false;
    if (searchTerm && !a.itemName.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'alerts', label: 'Price Alerts', icon: '⚠️' },
    { id: 'history', label: 'Price History', icon: '📈' },
    { id: 'suppliers', label: 'Supplier Compare', icon: '🏪' },
    { id: 'budget', label: 'Budget Impact', icon: '💰' },
    { id: 'settings', label: 'Alert Rules', icon: '⚙️' }
  ];

  const categories = ['all', 'Meat', 'Seafood', 'Dairy', 'Beverages', 'Produce', 'Oils'];

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
          <div className="text-gray-900 text-xl">Loading price data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="bg-red-50 border border-red-200 rounded-2xl p-8 max-w-md text-center">
          <div className="text-red-500 text-4xl mb-4">!</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Data</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-6 py-2 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Price Tracker</h1>
            <p className="text-gray-600 mt-1">Monitor supplier prices and cost trends</p>
          </div>
          <div className="flex gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="1y">Last year</option>
            </select>
            <button
              onClick={() => setShowRuleModal(true)}
              className="px-4 py-2 bg-blue-500 text-gray-900 rounded-xl hover:bg-blue-600 flex items-center gap-2"
            >
              + New Alert Rule
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
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

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Critical Alert Banner */}
            {stats.criticalAlerts > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-500/20 border border-red-500/50 rounded-2xl p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <span className="text-3xl">🚨</span>
                  <div>
                    <div className="text-red-300 font-bold">{stats.criticalAlerts} Critical Price Alert{stats.criticalAlerts > 1 ? 's' : ''}</div>
                    <div className="text-red-200/70 text-sm">Immediate attention required</div>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab('alerts')}
                  className="px-4 py-2 bg-red-500 text-gray-900 rounded-xl hover:bg-red-600"
                >
                  View Alerts
                </button>
              </motion.div>
            )}

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Unacknowledged Alerts</div>
                <div className="text-3xl font-bold text-red-400">{stats.unacknowledged}</div>
                <div className="text-white/40 text-sm mt-1">of {stats.totalAlerts} total</div>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Avg Price Change</div>
                <div className={`text-3xl font-bold ${stats.avgChange > 5 ? 'text-red-400' : 'text-yellow-400'}`}>
                  {stats.avgChange.toFixed(1)}%
                </div>
                <div className="text-white/40 text-sm mt-1">across all items</div>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Cost Impact</div>
                <div className={`text-3xl font-bold ${stats.totalImpact > 0 ? 'text-red-400' : 'text-green-400'}`}>
                  {stats.totalImpact > 0 ? '+' : ''}{stats.totalImpact} лв
                </div>
                <div className="text-white/40 text-sm mt-1">monthly projection</div>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-gray-100 rounded-2xl p-4">
                <div className="text-gray-600 text-sm">Potential Savings</div>
                <div className="text-3xl font-bold text-green-400">{stats.potentialSavings} лв</div>
                <div className="text-white/40 text-sm mt-1">by switching suppliers</div>
              </motion.div>
            </div>

            {/* Direction Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-red-500/20 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📈</span>
                    <span className="text-red-300">Price Increases</span>
                  </div>
                  <span className="text-3xl font-bold text-red-400">{stats.priceIncreases}</span>
                </div>
              </div>
              <div className="bg-green-500/20 border border-green-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📉</span>
                    <span className="text-green-300">Price Decreases</span>
                  </div>
                  <span className="text-3xl font-bold text-green-400">{stats.priceDecreases}</span>
                </div>
              </div>
            </div>

            {/* Category Trends */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Category Price Trends</h3>
              <div className="space-y-4">
                {categoryTrends.map((trend, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <div className="w-28 text-gray-900 font-medium">{trend.category}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${trend.changePercent > 0 ? 'bg-red-500' : 'bg-green-500'}`}
                            style={{ width: `${Math.min(Math.abs(trend.changePercent) * 5, 100)}%` }}
                          />
                        </div>
                        <span className={`w-16 text-right font-bold ${trend.changePercent > 0 ? 'text-red-400' : 'text-green-400'}`}>
                          {trend.changePercent > 0 ? '+' : ''}{trend.changePercent.toFixed(1)}%
                        </span>
                      </div>
                      <div className="text-white/40 text-xs">
                        Top mover: {trend.topMover} ({trend.topMoverChange > 0 ? '+' : ''}{trend.topMoverChange}%)
                      </div>
                    </div>
                    <div className="text-gray-600 text-sm">{trend.itemCount} items</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Alerts */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Recent Alerts</h3>
                <button
                  onClick={() => setActiveTab('alerts')}
                  className="text-orange-400 hover:text-orange-300 text-sm"
                >
                  View All →
                </button>
              </div>
              <div className="space-y-3">
                {alerts.slice(0, 5).map(alert => (
                  <div key={alert.id} className={`flex items-center justify-between p-3 rounded-xl ${!alert.acknowledged ? 'bg-red-500/10 border border-red-500/30' : 'bg-white/5'}`}>
                    <div className="flex items-center gap-3">
                      <span className={`w-3 h-3 rounded-full ${getSeverityColor(alert.severity)}`} />
                      <div>
                        <div className="text-gray-900 font-medium">{alert.itemName}</div>
                        <div className="text-gray-500 text-sm">{alert.supplier} • {alert.detectedAt}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`font-bold ${alert.trend === 'up' ? 'text-red-400' : 'text-green-400'}`}>
                        {alert.changePercent > 0 ? '+' : ''}{alert.changePercent.toFixed(1)}%
                      </span>
                      {!alert.acknowledged && (
                        <button
                          onClick={() => acknowledgeAlert(alert.id)}
                          className="px-3 py-1 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm"
                        >
                          Acknowledge
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Alerts Tab */}
        {activeTab === 'alerts' && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-gray-100 rounded-2xl p-4">
              <div className="flex flex-wrap gap-4">
                <input
                  type="text"
                  placeholder="Search items..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 min-w-[200px] px-4 py-2 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                />
                <select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat === 'all' ? 'All Categories' : cat}</option>
                  ))}
                </select>
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                  className="px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                >
                  <option value="all">All Severity</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
                <button
                  onClick={acknowledgeAll}
                  className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                >
                  Acknowledge All
                </button>
              </div>
            </div>

            {/* Alerts Table */}
            <div className="bg-gray-100 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Severity</th>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Item</th>
                    <th className="px-4 py-3 text-left text-gray-700 text-sm">Supplier</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Previous</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Current</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Change</th>
                    <th className="px-4 py-3 text-right text-gray-700 text-sm">Impact</th>
                    <th className="px-4 py-3 text-center text-gray-700 text-sm">Status</th>
                    <th className="px-4 py-3 text-center text-gray-700 text-sm">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAlerts.map(alert => (
                    <tr key={alert.id} className={`border-t border-gray-200 hover:bg-gray-50 ${!alert.acknowledged ? 'bg-red-500/5' : ''}`}>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs text-gray-900 ${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-gray-900 font-medium">{alert.itemName}</div>
                        <div className="text-gray-500 text-sm">{alert.category}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-700">{alert.supplier}</td>
                      <td className="px-4 py-3 text-right text-gray-900">{alert.previousPrice.toFixed(2)} лв</td>
                      <td className="px-4 py-3 text-right text-gray-900 font-medium">{alert.currentPrice.toFixed(2)} лв</td>
                      <td className="px-4 py-3 text-right">
                        <div className={`font-bold ${alert.trend === 'up' ? 'text-red-400' : 'text-green-400'}`}>
                          {alert.changePercent > 0 ? '+' : ''}{alert.changePercent.toFixed(1)}%
                        </div>
                        <div className="text-gray-500 text-xs">
                          {alert.changeAmount > 0 ? '+' : ''}{alert.changeAmount.toFixed(2)} лв
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={alert.impactOnCost > 0 ? 'text-red-400' : 'text-green-400'}>
                          {alert.impactOnCost > 0 ? '+' : ''}{alert.impactOnCost} лв
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {alert.acknowledged ? (
                          <span className="text-green-400 text-sm">✓ {alert.acknowledgedBy}</span>
                        ) : (
                          <span className="text-yellow-400 text-sm">Pending</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {!alert.acknowledged && (
                          <button
                            onClick={() => acknowledgeAlert(alert.id)}
                            className="px-3 py-1 bg-blue-500 text-gray-900 rounded-lg hover:bg-blue-600 text-sm"
                          >
                            Acknowledge
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Price History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {priceHistory.map(item => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-gray-100 rounded-2xl p-6 cursor-pointer hover:bg-white/15"
                  onClick={() => setSelectedItem(item)}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">{item.itemName}</h3>
                      <p className="text-gray-600 text-sm">{item.supplier}</p>
                    </div>
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">{item.category}</span>
                  </div>

                  {/* Mini Chart */}
                  <div className="flex items-end justify-between h-20 gap-1 mb-4">
                    {item.prices.map((p, idx) => {
                      const max = item.maxPrice;
                      const min = item.minPrice;
                      const range = max - min || 1;
                      const height = ((p.price - min) / range) * 100;
                      const isLast = idx === item.prices.length - 1;
                      return (
                        <div key={idx} className="flex-1 flex flex-col items-center">
                          <div
                            className={`w-full rounded-t ${isLast ? 'bg-orange-500' : 'bg-white/30'}`}
                            style={{ height: `${Math.max(height, 10)}%` }}
                          />
                        </div>
                      );
                    })}
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Current</span>
                      <div className="text-gray-900 font-bold">{item.currentPrice.toFixed(2)} лв</div>
                    </div>
                    <div>
                      <span className="text-gray-600">Average</span>
                      <div className="text-gray-900">{item.avgPrice.toFixed(2)} лв</div>
                    </div>
                    <div>
                      <span className="text-gray-600">Min</span>
                      <div className="text-green-400">{item.minPrice.toFixed(2)} лв</div>
                    </div>
                    <div>
                      <span className="text-gray-600">Max</span>
                      <div className="text-red-400">{item.maxPrice.toFixed(2)} лв</div>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Volatility</span>
                      <span className={`font-medium ${item.volatility > 7 ? 'text-red-400' : item.volatility > 4 ? 'text-yellow-400' : 'text-green-400'}`}>
                        {item.volatility.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Supplier Compare Tab */}
        {activeTab === 'suppliers' && (
          <div className="space-y-6">
            {supplierComparisons.map((comparison, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-gray-100 rounded-2xl p-6"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">{comparison.itemName}</h3>
                    <p className="text-gray-600">{comparison.category}</p>
                  </div>
                  {comparison.potentialSavings > 0 && (
                    <div className="bg-green-500/20 border border-green-500/30 rounded-xl px-4 py-2">
                      <div className="text-green-300 text-sm">Potential Savings</div>
                      <div className="text-green-400 font-bold text-lg">{comparison.potentialSavings} лв/month</div>
                    </div>
                  )}
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="px-4 py-2 text-left text-gray-700 text-sm">Supplier</th>
                        <th className="px-4 py-2 text-right text-gray-700 text-sm">Price</th>
                        <th className="px-4 py-2 text-center text-gray-700 text-sm">Reliability</th>
                        <th className="px-4 py-2 text-center text-gray-700 text-sm">Delivery</th>
                        <th className="px-4 py-2 text-center text-gray-700 text-sm">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.suppliers.map((supplier, sIdx) => {
                        const isCurrent = supplier.name === comparison.currentSupplier;
                        const isBest = supplier.price === comparison.bestPrice;
                        return (
                          <tr key={sIdx} className={`border-t border-white/5 ${isCurrent ? 'bg-blue-500/10' : ''}`}>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <span className="text-gray-900 font-medium">{supplier.name}</span>
                                {isCurrent && <span className="px-2 py-0.5 bg-blue-500 text-gray-900 rounded text-xs">Current</span>}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className={`font-bold ${isBest ? 'text-green-400' : 'text-white'}`}>
                                {supplier.price.toFixed(2)} лв
                              </span>
                              {isBest && <span className="ml-2 text-green-400 text-xs">Best</span>}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <div className="flex items-center justify-center gap-2">
                                <div className="w-16 h-2 bg-gray-100 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${supplier.reliability >= 90 ? 'bg-green-500' : supplier.reliability >= 80 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                    style={{ width: `${supplier.reliability}%` }}
                                  />
                                </div>
                                <span className="text-gray-700 text-sm">{supplier.reliability}%</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-center text-gray-700">{supplier.deliveryTime}</td>
                            <td className="px-4 py-3 text-center">
                              {!isCurrent && isBest && (
                                <button className="px-3 py-1 bg-green-500 text-gray-900 rounded-lg hover:bg-green-600 text-sm">
                                  Switch
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Budget Impact Tab */}
        {activeTab === 'budget' && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-100 rounded-2xl p-6">
                <div className="text-gray-600 text-sm">Total Budgeted</div>
                <div className="text-3xl font-bold text-gray-900">
                  {budgetImpacts.reduce((sum, b) => sum + b.budgeted, 0).toLocaleString()} лв
                </div>
              </div>
              <div className="bg-gray-100 rounded-2xl p-6">
                <div className="text-gray-600 text-sm">Projected Spend</div>
                <div className="text-3xl font-bold text-gray-900">
                  {budgetImpacts.reduce((sum, b) => sum + b.projected, 0).toLocaleString()} лв
                </div>
              </div>
              <div className="bg-red-500/20 border border-red-500/30 rounded-2xl p-6">
                <div className="text-red-300 text-sm">Total Variance</div>
                <div className="text-3xl font-bold text-red-400">
                  +{budgetImpacts.reduce((sum, b) => sum + b.variance, 0).toLocaleString()} лв
                </div>
              </div>
            </div>

            {/* Category Breakdown */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Budget Impact by Category</h3>
              <div className="space-y-4">
                {budgetImpacts.map((impact, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <div className="w-28 text-gray-900 font-medium">{impact.category}</div>
                    <div className="flex-1">
                      <div className="flex items-center mb-1">
                        <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                          <div
                            className="absolute left-0 h-full bg-blue-500/50"
                            style={{ width: `${(impact.budgeted / 10000) * 100}%` }}
                          />
                          <div
                            className={`absolute left-0 h-full ${impact.variance > 0 ? 'bg-red-500' : 'bg-green-500'}`}
                            style={{ width: `${(impact.projected / 10000) * 100}%`, opacity: 0.7 }}
                          />
                        </div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>Budget: {impact.budgeted.toLocaleString()} лв</span>
                        <span>Projected: {impact.projected.toLocaleString()} лв</span>
                      </div>
                    </div>
                    <div className={`w-24 text-right font-bold ${impact.variance > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {impact.variance > 0 ? '+' : ''}{impact.variance} лв
                      <div className="text-xs font-normal text-gray-500">
                        {impact.variancePercent > 0 ? '+' : ''}{impact.variancePercent.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendations */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Reduction Recommendations</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-4 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                  <span className="text-2xl">💡</span>
                  <div className="flex-1">
                    <div className="text-gray-900 font-medium">Switch Beef Tenderloin supplier</div>
                    <div className="text-gray-600 text-sm">Local Butcher offers 8.3% lower price with 88% reliability</div>
                  </div>
                  <div className="text-green-400 font-bold">Save 225 лв/month</div>
                </div>
                <div className="flex items-center gap-4 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                  <span className="text-2xl">💡</span>
                  <div className="flex-1">
                    <div className="text-gray-900 font-medium">Bulk purchase Olive Oil</div>
                    <div className="text-gray-600 text-sm">Order 10+ units from Metro Wholesale for 5% discount</div>
                  </div>
                  <div className="text-green-400 font-bold">Save 110 лв/month</div>
                </div>
                <div className="flex items-center gap-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                  <span className="text-2xl">📊</span>
                  <div className="flex-1">
                    <div className="text-gray-900 font-medium">Review Seafood menu pricing</div>
                    <div className="text-gray-600 text-sm">Seafood costs up 8.8% - consider menu price adjustment</div>
                  </div>
                  <div className="text-blue-400 font-bold">Maintain margins</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Alert Rules Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-900">Alert Rules</h3>
              <button
                onClick={() => setShowRuleModal(true)}
                className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
              >
                + New Rule
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {alertRules.map(rule => (
                <motion.div
                  key={rule.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={`bg-gray-100 rounded-2xl p-6 ${!rule.isActive ? 'opacity-50' : ''}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-lg font-bold text-gray-900">{rule.name}</h4>
                      <p className="text-gray-600 text-sm">
                        {rule.category === 'all' ? 'All categories' : rule.category} • {rule.direction === 'both' ? 'Any change' : rule.direction === 'increase' ? 'Price increase' : 'Price decrease'}
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={rule.isActive}
                        onChange={() => toggleRuleActive(rule.id)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-orange-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
                    </label>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-600 text-sm">Threshold</div>
                      <div className="text-xl font-bold text-gray-900">{rule.threshold}%</div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3">
                      <div className="text-gray-600 text-sm">Times Triggered</div>
                      <div className="text-xl font-bold text-orange-400">{rule.triggeredCount}</div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    {rule.notifyEmail && <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">📧 Email</span>}
                    {rule.notifySms && <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">📱 SMS</span>}
                    {rule.notifyPush && <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs">🔔 Push</span>}
                  </div>

                  <div className="flex gap-2 mt-4 pt-4 border-t border-gray-200">
                    <button className="flex-1 py-2 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200 text-sm">
                      Edit
                    </button>
                    <button className="py-2 px-4 bg-red-500/20 text-red-400 rounded-xl hover:bg-red-500/30 text-sm">
                      Delete
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Notification Settings */}
            <div className="bg-gray-100 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Global Notification Settings</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-900">Email Notifications</span>
                    <input type="checkbox" defaultChecked className="w-5 h-5 rounded bg-gray-100 text-orange-500" />
                  </div>
                  <input
                    type="email"
                    placeholder="manager@restaurant.com"
                    className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm"
                  />
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-900">SMS Notifications</span>
                    <input type="checkbox" className="w-5 h-5 rounded bg-gray-100 text-orange-500" />
                  </div>
                  <input
                    type="tel"
                    placeholder="+359888123456"
                    className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm"
                  />
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-900">Daily Digest</span>
                    <input type="checkbox" defaultChecked className="w-5 h-5 rounded bg-gray-100 text-orange-500" />
                  </div>
                  <select className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm">
                    <option value="08:00">8:00 AM</option>
                    <option value="09:00">9:00 AM</option>
                    <option value="10:00">10:00 AM</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Rule Modal */}
      <AnimatePresence>
        {showRuleModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full"
            >
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create Alert Rule</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Rule Name</label>
                  <input
                    type="text"
                    value={ruleForm.name}
                    onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    placeholder="e.g., Critical Meat Price Alert"
                  />
                </div>
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Category</label>
                  <select
                    value={ruleForm.category}
                    onChange={(e) => setRuleForm({ ...ruleForm, category: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                  >
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat === 'all' ? 'All Categories' : cat}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Threshold (%)</label>
                    <input
                      type="number"
                      value={ruleForm.threshold}
                      onChange={(e) => setRuleForm({ ...ruleForm, threshold: Number(e.target.value) })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="text-gray-600 text-sm block mb-2">Direction</label>
                    <select
                      value={ruleForm.direction}
                      onChange={(e) => setRuleForm({ ...ruleForm, direction: e.target.value as any })}
                      className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
                    >
                      <option value="increase">Price Increase</option>
                      <option value="decrease">Price Decrease</option>
                      <option value="both">Any Change</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-gray-600 text-sm block mb-2">Notifications</label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={ruleForm.notifyEmail}
                        onChange={(e) => setRuleForm({ ...ruleForm, notifyEmail: e.target.checked })}
                        className="w-5 h-5 rounded bg-gray-100 text-orange-500"
                      />
                      <span className="text-gray-900">Email</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={ruleForm.notifySms}
                        onChange={(e) => setRuleForm({ ...ruleForm, notifySms: e.target.checked })}
                        className="w-5 h-5 rounded bg-gray-100 text-orange-500"
                      />
                      <span className="text-gray-900">SMS</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={ruleForm.notifyPush}
                        onChange={(e) => setRuleForm({ ...ruleForm, notifyPush: e.target.checked })}
                        className="w-5 h-5 rounded bg-gray-100 text-orange-500"
                      />
                      <span className="text-gray-900">Push</span>
                    </label>
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowRuleModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateRule}
                  className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
                >
                  Create Rule
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Item Price Detail Modal */}
      <AnimatePresence>
        {selectedItem && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-2xl w-full"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">{selectedItem.itemName}</h2>
                  <p className="text-gray-600">{selectedItem.supplier} • {selectedItem.category}</p>
                </div>
                <button onClick={() => setSelectedItem(null)} className="text-gray-600 hover:text-gray-900 text-2xl">
                  &times;
                </button>
              </div>

              {/* Large Chart */}
              <div className="bg-gray-50 rounded-xl p-4 mb-6">
                <div className="flex items-end justify-between h-48 gap-2">
                  {selectedItem.prices.map((p, idx) => {
                    const max = selectedItem.maxPrice;
                    const min = selectedItem.minPrice;
                    const range = max - min || 1;
                    const height = ((p.price - min) / range) * 100;
                    const isLast = idx === selectedItem.prices.length - 1;
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center">
                        <div className="text-gray-500 text-xs mb-1">{p.price.toFixed(2)}</div>
                        <div
                          className={`w-full rounded-t ${isLast ? 'bg-orange-500' : 'bg-white/30'}`}
                          style={{ height: `${Math.max(height, 10)}%` }}
                        />
                        <div className="text-white/40 text-xs mt-2">{p.date.split('-').slice(1).join('/')}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-gray-600 text-sm">Current</div>
                  <div className="text-xl font-bold text-gray-900">{selectedItem.currentPrice.toFixed(2)} лв</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 text-center">
                  <div className="text-gray-600 text-sm">Average</div>
                  <div className="text-xl font-bold text-gray-900">{selectedItem.avgPrice.toFixed(2)} лв</div>
                </div>
                <div className="bg-green-500/20 rounded-xl p-4 text-center">
                  <div className="text-green-300 text-sm">Min</div>
                  <div className="text-xl font-bold text-green-400">{selectedItem.minPrice.toFixed(2)} лв</div>
                </div>
                <div className="bg-red-500/20 rounded-xl p-4 text-center">
                  <div className="text-red-300 text-sm">Max</div>
                  <div className="text-xl font-bold text-red-400">{selectedItem.maxPrice.toFixed(2)} лв</div>
                </div>
              </div>

              <div className="flex gap-3">
                <button className="flex-1 py-3 bg-blue-500 text-gray-900 rounded-xl hover:bg-blue-600">
                  Compare Suppliers
                </button>
                <button className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600">
                  Set Price Alert
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
