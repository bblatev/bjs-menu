'use client';

import { useState, useEffect } from 'react';

import { api } from '@/lib/api';

interface MenuItem {
  id: number;
  name: string;
  category: string;
  price: number;
  food_cost: number;
  food_cost_percentage: number;
  profit_margin: number;
  popularity_score: number;
  sold_count: number;
  revenue: number;
  profit: number;
  quadrant: 'star' | 'puzzle' | 'plow_horse' | 'dog';
  trend: 'up' | 'down' | 'stable';
  recommendations: string[];
}

interface MagicQuadrant {
  stars: MenuItem[];
  puzzles: MenuItem[];
  plow_horses: MenuItem[];
  dogs: MenuItem[];
  avg_profit_margin: number;
  avg_popularity: number;
}

interface CategoryAnalysis {
  category: string;
  items_count: number;
  total_revenue: number;
  total_profit: number;
  avg_food_cost: number;
  stars: number;
  puzzles: number;
  plow_horses: number;
  dogs: number;
  optimization_score: number;
}

interface PricingRecommendation {
  item_id: number;
  item_name: string;
  current_price: number;
  recommended_price: number;
  change_percentage: number;
  reason: string;
  expected_impact: string;
}

const QUADRANT_CONFIG = {
  star: { label: 'Stars', icon: '⭐', color: 'bg-success-100 border-success-500 text-success-800', description: 'High Profit, High Popularity - Promote & Protect' },
  puzzle: { label: 'Puzzles', icon: '🧩', color: 'bg-primary-100 border-primary-500 text-primary-800', description: 'High Profit, Low Popularity - Promote More' },
  plow_horse: { label: 'Plow Horses', icon: '🐴', color: 'bg-warning-100 border-warning-500 text-warning-800', description: 'Low Profit, High Popularity - Reprice or Reengineer' },
  dog: { label: 'Dogs', icon: '🐕', color: 'bg-error-100 border-error-500 text-error-800', description: 'Low Profit, Low Popularity - Consider Removing' },
};

export default function MenuEngineeringPage() {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [quadrant, setQuadrant] = useState<MagicQuadrant | null>(null);
  const [categories, setCategories] = useState<CategoryAnalysis[]>([]);
  const [pricingRecs, setPricingRecs] = useState<PricingRecommendation[]>([]);
  const [selectedView, setSelectedView] = useState<'quadrant' | 'abc' | 'pricing' | 'categories'>('quadrant');
  const [selectedDays, setSelectedDays] = useState(30);
  const [showItemModal, setShowItemModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDays]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({ days: selectedDays.toString() });

      const itemsData = await api.get<{ items?: MenuItem[] } | MenuItem[]>(`/menu-engineering/items?${params}`);
      const rawItems = Array.isArray(itemsData) ? itemsData : ((itemsData as { items?: MenuItem[] }).items || itemsData);
      const menuItems: MenuItem[] = Array.isArray(rawItems) ? rawItems : [];
      setItems(menuItems);

      // Calculate quadrant data
      const stars = menuItems.filter((i: MenuItem) => i.quadrant === 'star');
      const puzzles = menuItems.filter((i: MenuItem) => i.quadrant === 'puzzle');
      const plow_horses = menuItems.filter((i: MenuItem) => i.quadrant === 'plow_horse');
      const dogs = menuItems.filter((i: MenuItem) => i.quadrant === 'dog');

      setQuadrant({
        stars,
        puzzles,
        plow_horses,
        dogs,
        avg_profit_margin: menuItems.length > 0 ? menuItems.reduce((s: number, i: MenuItem) => s + i.profit_margin, 0) / menuItems.length : 0,
        avg_popularity: menuItems.length > 0 ? menuItems.reduce((s: number, i: MenuItem) => s + i.popularity_score, 0) / menuItems.length : 0,
      });

      try {
        const categoriesData = await api.get<{ categories?: CategoryAnalysis[] } | CategoryAnalysis[]>(`/menu-engineering/categories?${params}`);
        setCategories(Array.isArray(categoriesData) ? categoriesData : ((categoriesData as { categories?: CategoryAnalysis[] }).categories || []));
      } catch {
        // Categories data is optional
      }

      try {
        const pricingData = await api.get<{ recommendations?: PricingRecommendation[] } | PricingRecommendation[]>(`/menu-engineering/pricing-recommendations?${params}`);
        setPricingRecs(Array.isArray(pricingData) ? pricingData : ((pricingData as { recommendations?: PricingRecommendation[] }).recommendations || []));
      } catch {
        // Pricing data is optional
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      setItems([]);
      setQuadrant(null);
      setCategories([]);
      setPricingRecs([]);
    } finally {
      setLoading(false);
    }
  };

  const totalRevenue = items.reduce((s, i) => s + i.revenue, 0);
  const totalProfit = items.reduce((s, i) => s + i.profit, 0);
  const avgFoodCost = items.length > 0 ? items.reduce((s, i) => s + i.food_cost_percentage, 0) / items.length : 0;
  const optimizationPotential = pricingRecs.reduce((s, r) => {
    const match = r.expected_impact.match(/\+\$(\d+)/);
    return s + (match ? parseInt(match[1]) : 0);
  }, 0);

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
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
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Menu Engineering</h1>
          <p className="text-surface-600 mt-1">Analyze profitability, popularity & optimize pricing</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedDays}
            onChange={(e) => setSelectedDays(parseInt(e.target.value))}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50 flex items-center gap-2" aria-label="Close">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export Report
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Total Revenue</p>
          <p className="text-xl font-bold text-surface-900">${totalRevenue.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Total Profit</p>
          <p className="text-xl font-bold text-success-600">${totalProfit.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Avg Food Cost</p>
          <p className={`text-xl font-bold ${avgFoodCost <= 30 ? 'text-success-600' : avgFoodCost <= 35 ? 'text-warning-600' : 'text-error-600'}`}>
            {(avgFoodCost || 0).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-xs text-surface-500 uppercase">Menu Items</p>
          <p className="text-xl font-bold text-surface-900">{items.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-success-200 shadow-sm bg-success-50">
          <p className="text-xs text-success-600 uppercase">Stars</p>
          <p className="text-xl font-bold text-success-700">{quadrant?.stars.length || 0}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-primary-200 shadow-sm bg-primary-50">
          <p className="text-xs text-primary-600 uppercase">Optimization $</p>
          <p className="text-xl font-bold text-primary-700">+${optimizationPotential}/mo</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6 border-b border-surface-200 pb-2">
        {[
          { key: 'quadrant', label: 'Magic Quadrant', icon: '📊' },
          { key: 'abc', label: 'ABC Analysis', icon: '📈' },
          { key: 'pricing', label: 'Pricing Optimizer', icon: '💰' },
          { key: 'categories', label: 'Category Analysis', icon: '📁' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setSelectedView(tab.key as typeof selectedView)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              selectedView === tab.key
                ? 'bg-primary-600 text-white'
                : 'text-surface-600 hover:bg-surface-100'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Magic Quadrant View */}
      {selectedView === 'quadrant' && quadrant && (
        <div className="space-y-6">
          {/* Visual Quadrant Chart */}
          <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-6">
            <h3 className="font-semibold text-surface-900 mb-4">Menu Item Distribution</h3>
            <div className="grid grid-cols-2 gap-1 h-96">
              {/* Top Left - Puzzles (High Profit, Low Popularity) */}
              <div className="bg-primary-50 border border-primary-200 rounded-tl-xl p-4 relative">
                <div className="absolute top-2 left-2">
                  <span className="text-xl">{QUADRANT_CONFIG.puzzle.icon}</span>
                  <span className="ml-2 font-semibold text-primary-700">Puzzles</span>
                </div>
                <div className="pt-8 space-y-2 max-h-72 overflow-y-auto">
                  {quadrant.puzzles.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => { setSelectedItem(item); setShowItemModal(true); }}
                      className="bg-white rounded-lg p-2 shadow-sm hover:shadow-md cursor-pointer transition-shadow"
                    >
                      <p className="font-medium text-sm text-surface-900">{item.name}</p>
                      <p className="text-xs text-surface-500">{item.profit_margin}% margin • {item.sold_count} sold</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Right - Stars (High Profit, High Popularity) */}
              <div className="bg-success-50 border border-success-200 rounded-tr-xl p-4 relative">
                <div className="absolute top-2 left-2">
                  <span className="text-xl">{QUADRANT_CONFIG.star.icon}</span>
                  <span className="ml-2 font-semibold text-success-700">Stars</span>
                </div>
                <div className="pt-8 space-y-2 max-h-72 overflow-y-auto">
                  {quadrant.stars.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => { setSelectedItem(item); setShowItemModal(true); }}
                      className="bg-white rounded-lg p-2 shadow-sm hover:shadow-md cursor-pointer transition-shadow"
                    >
                      <p className="font-medium text-sm text-surface-900">{item.name}</p>
                      <p className="text-xs text-surface-500">{item.profit_margin}% margin • {item.sold_count} sold</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bottom Left - Dogs (Low Profit, Low Popularity) */}
              <div className="bg-error-50 border border-error-200 rounded-bl-xl p-4 relative">
                <div className="absolute top-2 left-2">
                  <span className="text-xl">{QUADRANT_CONFIG.dog.icon}</span>
                  <span className="ml-2 font-semibold text-error-700">Dogs</span>
                </div>
                <div className="pt-8 space-y-2 max-h-72 overflow-y-auto">
                  {quadrant.dogs.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => { setSelectedItem(item); setShowItemModal(true); }}
                      className="bg-white rounded-lg p-2 shadow-sm hover:shadow-md cursor-pointer transition-shadow"
                    >
                      <p className="font-medium text-sm text-surface-900">{item.name}</p>
                      <p className="text-xs text-surface-500">{item.profit_margin}% margin • {item.sold_count} sold</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Bottom Right - Plow Horses (Low Profit, High Popularity) */}
              <div className="bg-warning-50 border border-warning-200 rounded-br-xl p-4 relative">
                <div className="absolute top-2 left-2">
                  <span className="text-xl">{QUADRANT_CONFIG.plow_horse.icon}</span>
                  <span className="ml-2 font-semibold text-warning-700">Plow Horses</span>
                </div>
                <div className="pt-8 space-y-2 max-h-72 overflow-y-auto">
                  {quadrant.plow_horses.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => { setSelectedItem(item); setShowItemModal(true); }}
                      className="bg-white rounded-lg p-2 shadow-sm hover:shadow-md cursor-pointer transition-shadow"
                    >
                      <p className="font-medium text-sm text-surface-900">{item.name}</p>
                      <p className="text-xs text-surface-500">{item.profit_margin}% margin • {item.sold_count} sold</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Axis Labels */}
            <div className="flex items-center justify-center mt-4 text-sm text-surface-500">
              <div className="flex items-center gap-8">
                <span>← Low Popularity</span>
                <span className="font-semibold text-surface-700">Popularity Score</span>
                <span>High Popularity →</span>
              </div>
            </div>
            <div className="absolute left-4 top-1/2 transform -rotate-90 text-sm text-surface-500 font-semibold">
              Profit Margin
            </div>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(QUADRANT_CONFIG).map(([key, config]) => {
              const quadrantKey = `${key}s` as keyof MagicQuadrant;
              const quadrantValue = quadrant[quadrantKey];
              const count = Array.isArray(quadrantValue) ? quadrantValue.length : 0;
              return (
                <div key={key} className={`rounded-xl border-l-4 p-4 ${config.color}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">{config.icon}</span>
                    <h3 className="font-semibold">{config.label}</h3>
                  </div>
                  <p className="text-3xl font-bold mb-1">{count}</p>
                  <p className="text-xs opacity-80">{config.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ABC Analysis View */}
      {selectedView === 'abc' && (
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-surface-200">
            <h2 className="font-semibold text-surface-900">ABC Revenue Analysis</h2>
            <p className="text-sm text-surface-500">A = Top 80% revenue, B = Next 15%, C = Remaining 5%</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Item</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Sold</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Revenue</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Profit</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Cumulative %</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {items
                  .sort((a, b) => b.revenue - a.revenue)
                  .map((item, index) => {
                    const cumulativeRevenue = items
                      .sort((a, b) => b.revenue - a.revenue)
                      .slice(0, index + 1)
                      .reduce((s, i) => s + i.revenue, 0);
                    const cumulativePercentage = (cumulativeRevenue / totalRevenue) * 100;
                    const abcCategory = cumulativePercentage <= 80 ? 'A' : cumulativePercentage <= 95 ? 'B' : 'C';

                    return (
                      <tr key={item.id} className="hover:bg-surface-50">
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                            abcCategory === 'A' ? 'bg-success-100 text-success-700' :
                            abcCategory === 'B' ? 'bg-warning-100 text-warning-700' :
                            'bg-error-100 text-error-700'
                          }`}>
                            {abcCategory}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-surface-900">{item.name}</p>
                          <p className="text-sm text-surface-500">{item.category}</p>
                        </td>
                        <td className="px-4 py-3 text-right text-surface-700">{item.sold_count}</td>
                        <td className="px-4 py-3 text-right font-medium text-surface-900">${item.revenue.toLocaleString()}</td>
                        <td className="px-4 py-3 text-right font-medium text-success-600">${item.profit.toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-surface-700">{(cumulativePercentage || 0).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-center">
                          {item.trend === 'up' && <span className="text-success-600">↑</span>}
                          {item.trend === 'down' && <span className="text-error-600">↓</span>}
                          {item.trend === 'stable' && <span className="text-surface-400">→</span>}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pricing Optimizer View */}
      {selectedView === 'pricing' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-primary-50 to-accent-50 rounded-xl border border-primary-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-surface-900 text-lg">Pricing Optimization Potential</h3>
                <p className="text-surface-600">Implement these changes to increase monthly profit</p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-primary-600">+${optimizationPotential}</p>
                <p className="text-sm text-surface-500">per month</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-surface-200">
              <h2 className="font-semibold text-surface-900">Recommended Price Changes</h2>
            </div>
            <div className="divide-y divide-surface-100">
              {pricingRecs.map((rec) => (
                <div key={rec.item_id} className="p-4 hover:bg-surface-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-surface-900">{rec.item_name}</h4>
                      <p className="text-sm text-surface-500">{rec.reason}</p>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-center">
                        <p className="text-sm text-surface-500">Current</p>
                        <p className="font-medium text-surface-900">${rec.current_price}</p>
                      </div>
                      <div className="text-2xl text-surface-400">→</div>
                      <div className="text-center">
                        <p className="text-sm text-surface-500">Recommended</p>
                        <p className="font-bold text-primary-600">${rec.recommended_price}</p>
                      </div>
                      <div className={`px-3 py-1 rounded-lg text-sm font-medium ${
                        rec.change_percentage > 0 ? 'bg-success-100 text-success-700' : 'bg-primary-100 text-primary-700'
                      }`}>
                        {rec.change_percentage > 0 ? '+' : ''}{(rec.change_percentage || 0).toFixed(1)}%
                      </div>
                      <div className="text-right w-32">
                        <p className="text-sm font-medium text-success-600">{rec.expected_impact}</p>
                      </div>
                      <button className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 text-sm">
                        Apply
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Category Analysis View */}
      {selectedView === 'categories' && (
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-surface-200">
            <h2 className="font-semibold text-surface-900">Category Performance Analysis</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Category</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Items</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Revenue</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Profit</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Avg FC%</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">⭐</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">🧩</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">🐴</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">🐕</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {categories.map((cat) => (
                  <tr key={cat.category} className="hover:bg-surface-50">
                    <td className="px-4 py-3 font-medium text-surface-900">{cat.category}</td>
                    <td className="px-4 py-3 text-center text-surface-700">{cat.items_count}</td>
                    <td className="px-4 py-3 text-right font-medium text-surface-900">${cat.total_revenue.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-medium text-success-600">${cat.total_profit.toLocaleString()}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`font-medium ${cat.avg_food_cost <= 30 ? 'text-success-600' : cat.avg_food_cost <= 35 ? 'text-warning-600' : 'text-error-600'}`}>
                        {cat.avg_food_cost}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-success-600 font-medium">{cat.stars}</td>
                    <td className="px-4 py-3 text-center text-primary-600 font-medium">{cat.puzzles}</td>
                    <td className="px-4 py-3 text-center text-warning-600 font-medium">{cat.plow_horses}</td>
                    <td className="px-4 py-3 text-center text-error-600 font-medium">{cat.dogs}</td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 h-2 bg-surface-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              cat.optimization_score >= 75 ? 'bg-success-500' :
                              cat.optimization_score >= 60 ? 'bg-warning-500' :
                              'bg-error-500'
                            }`}
                            style={{ width: `${cat.optimization_score}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-surface-700">{cat.optimization_score}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Item Detail Modal */}
      {showItemModal && selectedItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-lg mx-4 shadow-xl">
            <div className={`p-6 rounded-t-2xl ${QUADRANT_CONFIG[selectedItem.quadrant].color}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{QUADRANT_CONFIG[selectedItem.quadrant].icon}</span>
                  <div>
                    <h2 className="text-xl font-bold">{selectedItem.name}</h2>
                    <p className="text-sm opacity-80">{selectedItem.category}</p>
                  </div>
                </div>
                <button
                  onClick={() => { setShowItemModal(false); setSelectedItem(null); }}
                  className="p-2 hover:bg-gray-200 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500">Price</p>
                  <p className="text-xl font-bold">${selectedItem.price}</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500">Food Cost</p>
                  <p className="text-xl font-bold">{selectedItem.food_cost_percentage}%</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500">Profit Margin</p>
                  <p className="text-xl font-bold text-success-600">{selectedItem.profit_margin}%</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500">Sold ({selectedDays} days)</p>
                  <p className="text-lg font-bold">{selectedItem.sold_count}</p>
                </div>
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500">Revenue</p>
                  <p className="text-lg font-bold">${selectedItem.revenue.toLocaleString()}</p>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-surface-900 mb-2">Recommendations</h4>
                <ul className="space-y-2">
                  {selectedItem.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <span className="text-primary-500 mt-0.5">•</span>
                      <span className="text-surface-700">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => { setShowItemModal(false); setSelectedItem(null); }}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Close
              </button>
              <button className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700">
                Edit Item
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
