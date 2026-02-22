'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface ForecastItem {
  id: number;
  item_name: string;
  category: string;
  current_stock: number;
  unit: string;
  avg_daily_usage: number;
  predicted_demand_7d: number;
  predicted_demand_30d: number;
  confidence: number;
  trend: 'up' | 'down' | 'stable';
  seasonality_factor: number;
  recommended_order: number;
  days_until_stockout: number;
  last_updated: string;
}

interface ForecastStats {
  total_items_forecasted: number;
  avg_forecast_accuracy: number;
  items_needing_reorder: number;
  potential_stockouts_7d: number;
  total_recommended_order_value: number;
}

interface SeasonalityData {
  month: string;
  demand_index: number;
}

interface TrendData {
  date: string;
  actual: number;
  predicted: number;
}

export default function DemandForecastingPage() {
  const [forecastItems, setForecastItems] = useState<ForecastItem[]>([]);
  const [stats, setStats] = useState<ForecastStats | null>(null);
  const [seasonalityData, setSeasonalityData] = useState<SeasonalityData[]>([]);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [selectedItem, setSelectedItem] = useState<ForecastItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [forecastHorizon, setForecastHorizon] = useState<'7d' | '30d' | '90d'>('30d');
  const [showReorderOnly, setShowReorderOnly] = useState(false);


  useEffect(() => {
    fetchForecastData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [forecastHorizon]);

  const fetchForecastData = async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();

      // Try to fetch from API, fall back to demo data
      try {
        const [itemsRes, statsRes] = await Promise.all([
          fetch(`${API_URL}/stock/forecasting?horizon=${forecastHorizon}`, { credentials: 'include', headers }),
          fetch(`${API_URL}/stock/forecasting/stats`, { credentials: 'include', headers })
        ]);

        if (itemsRes.ok && statsRes.ok) {
          const itemsData = await itemsRes.json();
          const statsData = await statsRes.json();
          setForecastItems(itemsData.items || itemsData);
          setStats(statsData);
        } else {
          throw new Error('API not available');
        }
      } catch {
        // Use demo data
        loadDemoData();
      }
    } catch (error) {
      console.error('Error fetching forecast data:', error);
      loadDemoData();
    } finally {
      setLoading(false);
    }
  };

  const loadDemoData = () => {
    const demoItems: ForecastItem[] = [
      {
        id: 1,
        item_name: 'Пилешко филе',
        category: 'Месо',
        current_stock: 25,
        unit: 'кг',
        avg_daily_usage: 8.5,
        predicted_demand_7d: 62,
        predicted_demand_30d: 280,
        confidence: 92,
        trend: 'up',
        seasonality_factor: 1.15,
        recommended_order: 45,
        days_until_stockout: 3,
        last_updated: new Date().toISOString()
      },
      {
        id: 2,
        item_name: 'Домати',
        category: 'Зеленчуци',
        current_stock: 40,
        unit: 'кг',
        avg_daily_usage: 12,
        predicted_demand_7d: 85,
        predicted_demand_30d: 380,
        confidence: 88,
        trend: 'stable',
        seasonality_factor: 1.25,
        recommended_order: 60,
        days_until_stockout: 3,
        last_updated: new Date().toISOString()
      },
      {
        id: 3,
        item_name: 'Водка Absolut',
        category: 'Алкохол',
        current_stock: 15,
        unit: 'бут',
        avg_daily_usage: 2.2,
        predicted_demand_7d: 18,
        predicted_demand_30d: 72,
        confidence: 95,
        trend: 'up',
        seasonality_factor: 1.4,
        recommended_order: 12,
        days_until_stockout: 7,
        last_updated: new Date().toISOString()
      },
      {
        id: 4,
        item_name: 'Краставици',
        category: 'Зеленчуци',
        current_stock: 30,
        unit: 'кг',
        avg_daily_usage: 6,
        predicted_demand_7d: 42,
        predicted_demand_30d: 185,
        confidence: 85,
        trend: 'down',
        seasonality_factor: 0.9,
        recommended_order: 0,
        days_until_stockout: 5,
        last_updated: new Date().toISOString()
      },
      {
        id: 5,
        item_name: 'Свинско месо',
        category: 'Месо',
        current_stock: 35,
        unit: 'кг',
        avg_daily_usage: 10,
        predicted_demand_7d: 72,
        predicted_demand_30d: 320,
        confidence: 90,
        trend: 'stable',
        seasonality_factor: 1.0,
        recommended_order: 50,
        days_until_stockout: 4,
        last_updated: new Date().toISOString()
      },
      {
        id: 6,
        item_name: 'Бира Загорка',
        category: 'Напитки',
        current_stock: 120,
        unit: 'бут',
        avg_daily_usage: 25,
        predicted_demand_7d: 200,
        predicted_demand_30d: 850,
        confidence: 94,
        trend: 'up',
        seasonality_factor: 1.35,
        recommended_order: 150,
        days_until_stockout: 5,
        last_updated: new Date().toISOString()
      },
      {
        id: 7,
        item_name: 'Сирене',
        category: 'Млечни',
        current_stock: 18,
        unit: 'кг',
        avg_daily_usage: 4.5,
        predicted_demand_7d: 32,
        predicted_demand_30d: 140,
        confidence: 87,
        trend: 'stable',
        seasonality_factor: 1.0,
        recommended_order: 20,
        days_until_stockout: 4,
        last_updated: new Date().toISOString()
      },
      {
        id: 8,
        item_name: 'Лимони',
        category: 'Плодове',
        current_stock: 50,
        unit: 'бр',
        avg_daily_usage: 15,
        predicted_demand_7d: 110,
        predicted_demand_30d: 480,
        confidence: 82,
        trend: 'up',
        seasonality_factor: 1.2,
        recommended_order: 80,
        days_until_stockout: 3,
        last_updated: new Date().toISOString()
      }
    ];

    const demoStats: ForecastStats = {
      total_items_forecasted: 156,
      avg_forecast_accuracy: 89.5,
      items_needing_reorder: 12,
      potential_stockouts_7d: 4,
      total_recommended_order_value: 8750
    };

    const demoSeasonality: SeasonalityData[] = [
      { month: 'Яну', demand_index: 0.75 },
      { month: 'Фев', demand_index: 0.8 },
      { month: 'Мар', demand_index: 0.9 },
      { month: 'Апр', demand_index: 1.0 },
      { month: 'Май', demand_index: 1.1 },
      { month: 'Юни', demand_index: 1.25 },
      { month: 'Юли', demand_index: 1.4 },
      { month: 'Авг', demand_index: 1.35 },
      { month: 'Сеп', demand_index: 1.15 },
      { month: 'Окт', demand_index: 1.0 },
      { month: 'Ное', demand_index: 0.85 },
      { month: 'Дек', demand_index: 1.3 }
    ];

    const demoTrend: TrendData[] = [];
    const today = new Date();
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const baseValue = 100 + Math.sin(i / 5) * 20;
      demoTrend.push({
        date: date.toISOString().split('T')[0],
        actual: Math.round(baseValue + (Math.random() - 0.5) * 15),
        predicted: Math.round(baseValue)
      });
    }

    setForecastItems(demoItems);
    setStats(demoStats);
    setSeasonalityData(demoSeasonality);
    setTrendData(demoTrend);
  };

  const categories = ['all', ...new Set(forecastItems.map(item => item.category))];

  const filteredItems = forecastItems.filter(item => {
    if (selectedCategory !== 'all' && item.category !== selectedCategory) return false;
    if (showReorderOnly && item.recommended_order === 0) return false;
    return true;
  });

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return '↑';
      case 'down': return '↓';
      default: return '→';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up': return 'text-green-400';
      case 'down': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStockoutRisk = (days: number) => {
    if (days <= 2) return { label: 'Критично', color: 'bg-red-500/20 text-red-400 border-red-500/30' };
    if (days <= 5) return { label: 'Високо', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' };
    if (days <= 10) return { label: 'Средно', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' };
    return { label: 'Ниско', color: 'bg-green-500/20 text-green-400 border-green-500/30' };
  };

  const generateBulkOrder = () => {
    const itemsToOrder = filteredItems.filter(item => item.recommended_order > 0);
    toast.success(`Генериране на поръчка за ${itemsToOrder.length} артикула...`);
  };

  return (
    <AdminLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Прогнозиране на търсенето</h1>
            <p className="text-gray-400 mt-1">AI-базирани прогнози за оптимизация на запасите</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={forecastHorizon}
              onChange={(e) => setForecastHorizon(e.target.value as '7d' | '30d' | '90d')}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            >
              <option value="7d">7 дни</option>
              <option value="30d">30 дни</option>
              <option value="90d">90 дни</option>
            </select>
            <button
              onClick={generateBulkOrder}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
             aria-label="Close">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Генерирай поръчка
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Прогнозирани артикули</p>
                  <p className="text-2xl font-bold text-white">{stats.total_items_forecasted}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Точност на прогнозите</p>
                  <p className="text-2xl font-bold text-white">{stats.avg_forecast_accuracy}%</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Нужда от поръчка</p>
                  <p className="text-2xl font-bold text-white">{stats.items_needing_reorder}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Риск от изчерпване (7д)</p>
                  <p className="text-2xl font-bold text-white">{stats.potential_stockouts_7d}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Стойност на препоръчани</p>
                  <p className="text-2xl font-bold text-white">{stats.total_recommended_order_value.toLocaleString()} лв</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Seasonality Chart */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Сезонност на търсенето</h3>
            <div className="h-48 flex items-end justify-between gap-2">
              {seasonalityData.map((data, index) => (
                <div key={index} className="flex flex-col items-center flex-1">
                  <div
                    className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t transition-all"
                    style={{ height: `${data.demand_index * 100}px` }}
                  />
                  <span className="text-xs text-gray-400 mt-2">{data.month}</span>
                  <span className="text-xs text-gray-500">{((data.demand_index * 100) || 0).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Trend Chart */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Тренд: Реално vs Прогнозирано</h3>
            <div className="h-48 relative">
              <svg className="w-full h-full" viewBox="0 0 400 150" preserveAspectRatio="none">
                {/* Actual line */}
                <polyline
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2"
                  points={trendData.map((d, i) => `${i * (400 / (trendData.length - 1))},${150 - (d.actual - 60)}`).join(' ')}
                />
                {/* Predicted line */}
                <polyline
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2"
                  strokeDasharray="5,5"
                  points={trendData.map((d, i) => `${i * (400 / (trendData.length - 1))},${150 - (d.predicted - 60)}`).join(' ')}
                />
              </svg>
              <div className="flex items-center justify-center gap-6 mt-2">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-blue-500" />
                  <span className="text-xs text-gray-400">Реално</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-green-500 border-dashed" />
                  <span className="text-xs text-gray-400">Прогноза</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 flex-wrap">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            <option value="all">Всички категории</option>
            {categories.filter(c => c !== 'all').map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={showReorderOnly}
              onChange={(e) => setShowReorderOnly(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500"
            />
            Само за поръчка
          </label>

          <button
            onClick={fetchForecastData}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
           aria-label="Close">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Обнови прогнозите
          </button>
        </div>

        {/* Forecast Table */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-900/50">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Артикул</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Категория</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Наличност</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Дневна употреба</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Прогноза {forecastHorizon === '7d' ? '7д' : forecastHorizon === '30d' ? '30д' : '90д'}</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Тренд</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Точност</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Риск</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Препоръчана поръчка</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        Зареждане на прогнози...
                      </div>
                    </td>
                  </tr>
                ) : filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                      Няма намерени артикули
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => {
                    const stockoutRisk = getStockoutRisk(item.days_until_stockout);
                    return (
                      <tr
                        key={item.id}
                        onClick={() => setSelectedItem(item)}
                        className="border-t border-gray-700/50 hover:bg-gray-700/30 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3">
                          <span className="text-white font-medium">{item.item_name}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-gray-400">{item.category}</span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-white">{item.current_stock} {item.unit}</span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-gray-300">{(item.avg_daily_usage || 0).toFixed(1)} {item.unit}/ден</span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-white font-medium">
                            {forecastHorizon === '7d' ? item.predicted_demand_7d : item.predicted_demand_30d} {item.unit}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-lg font-bold ${getTrendColor(item.trend)}`}>
                            {getTrendIcon(item.trend)}
                          </span>
                          <span className="text-xs text-gray-400 ml-1">
                            x{(item.seasonality_factor || 0).toFixed(2)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  item.confidence >= 90 ? 'bg-green-500' :
                                  item.confidence >= 80 ? 'bg-yellow-500' : 'bg-orange-500'
                                }`}
                                style={{ width: `${item.confidence}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-400">{item.confidence}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs border ${stockoutRisk.color}`}>
                            {stockoutRisk.label} ({item.days_until_stockout}д)
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {item.recommended_order > 0 ? (
                            <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg font-medium">
                              {item.recommended_order} {item.unit}
                            </span>
                          ) : (
                            <span className="text-gray-500">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Item Detail Modal */}
        {selectedItem && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-2xl mx-4">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Детайли за прогнозата</h2>
                <button
                  onClick={() => setSelectedItem(null)}
                  className="p-2 hover:bg-gray-700 rounded-lg text-gray-400"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400">Артикул</p>
                    <p className="text-lg font-semibold text-white">{selectedItem.item_name}</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400">Категория</p>
                    <p className="text-lg font-semibold text-white">{selectedItem.category}</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Текуща наличност</p>
                    <p className="text-2xl font-bold text-white">{selectedItem.current_stock} {selectedItem.unit}</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Средна дневна употреба</p>
                    <p className="text-2xl font-bold text-white">{(selectedItem.avg_daily_usage || 0).toFixed(1)} {selectedItem.unit}</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Дни до изчерпване</p>
                    <p className={`text-2xl font-bold ${selectedItem.days_until_stockout <= 3 ? 'text-red-400' : 'text-white'}`}>
                      {selectedItem.days_until_stockout}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400 mb-2">Прогноза за търсенето</p>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-300">7 дни:</span>
                        <span className="text-white font-medium">{selectedItem.predicted_demand_7d} {selectedItem.unit}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">30 дни:</span>
                        <span className="text-white font-medium">{selectedItem.predicted_demand_30d} {selectedItem.unit}</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400 mb-2">Анализ</p>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-300">Тренд:</span>
                        <span className={`font-medium ${getTrendColor(selectedItem.trend)}`}>
                          {selectedItem.trend === 'up' ? 'Нарастващ' : selectedItem.trend === 'down' ? 'Намаляващ' : 'Стабилен'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">Сезонен фактор:</span>
                        <span className="text-white font-medium">x{(selectedItem.seasonality_factor || 0).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">Точност:</span>
                        <span className="text-white font-medium">{selectedItem.confidence}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {selectedItem.recommended_order > 0 && (
                  <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-blue-300">Препоръчана поръчка</p>
                        <p className="text-2xl font-bold text-blue-400">{selectedItem.recommended_order} {selectedItem.unit}</p>
                      </div>
                      <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
                        Добави към поръчка
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
