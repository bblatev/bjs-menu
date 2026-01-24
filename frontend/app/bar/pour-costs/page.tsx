'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface PourCostItem {
  id: number;
  name: string;
  category: 'spirits' | 'beer' | 'wine' | 'cocktails' | 'non_alcoholic';
  size: string;
  bottle_cost: number;
  pour_size: string;
  pours_per_bottle: number;
  cost_per_pour: number;
  sell_price: number;
  pour_cost_percentage: number;
  ideal_pour_cost: number;
  variance: number;
  sold_today: number;
  revenue_today: number;
}

interface CategorySummary {
  category: string;
  items: number;
  avgPourCost: number;
  targetPourCost: number;
  variance: number;
  revenue: number;
  profit: number;
}

const CATEGORIES = [
  { value: 'spirits', label: 'Spirits', icon: '🥃', target: 22 },
  { value: 'beer', label: 'Beer', icon: '🍺', target: 20 },
  { value: 'wine', label: 'Wine', icon: '🍷', target: 30 },
  { value: 'cocktails', label: 'Cocktails', icon: '🍸', target: 25 },
  { value: 'non_alcoholic', label: 'Non-Alcoholic', icon: '🥤', target: 18 },
];

// Demo data for fallback
const DEMO_ITEMS: PourCostItem[] = [
  {
    id: 1, name: 'Grey Goose Vodka', category: 'spirits', size: '750ml', bottle_cost: 28.00,
    pour_size: '30ml', pours_per_bottle: 25, cost_per_pour: 1.12, sell_price: 8.00,
    pour_cost_percentage: 14.0, ideal_pour_cost: 18, variance: -4.0, sold_today: 18, revenue_today: 144.00
  },
  {
    id: 2, name: 'Bacardi White Rum', category: 'spirits', size: '750ml', bottle_cost: 16.00,
    pour_size: '30ml', pours_per_bottle: 25, cost_per_pour: 0.64, sell_price: 6.00,
    pour_cost_percentage: 10.7, ideal_pour_cost: 15, variance: -4.3, sold_today: 35, revenue_today: 210.00
  },
  {
    id: 3, name: 'Hendricks Gin', category: 'spirits', size: '750ml', bottle_cost: 32.00,
    pour_size: '30ml', pours_per_bottle: 25, cost_per_pour: 1.28, sell_price: 9.00,
    pour_cost_percentage: 14.2, ideal_pour_cost: 18, variance: -3.8, sold_today: 22, revenue_today: 198.00
  },
  {
    id: 4, name: 'Jack Daniels', category: 'spirits', size: '1L', bottle_cost: 28.00,
    pour_size: '30ml', pours_per_bottle: 33, cost_per_pour: 0.85, sell_price: 7.00,
    pour_cost_percentage: 12.1, ideal_pour_cost: 15, variance: -2.9, sold_today: 28, revenue_today: 196.00
  },
  {
    id: 5, name: 'Heineken Draft', category: 'beer', size: '50L Keg', bottle_cost: 120.00,
    pour_size: '500ml', pours_per_bottle: 100, cost_per_pour: 1.20, sell_price: 5.00,
    pour_cost_percentage: 24.0, ideal_pour_cost: 20, variance: 4.0, sold_today: 85, revenue_today: 425.00
  },
  {
    id: 6, name: 'Corona Extra', category: 'beer', size: '24 bottles', bottle_cost: 32.00,
    pour_size: '330ml', pours_per_bottle: 24, cost_per_pour: 1.33, sell_price: 5.50,
    pour_cost_percentage: 24.2, ideal_pour_cost: 22, variance: 2.2, sold_today: 42, revenue_today: 231.00
  },
  {
    id: 7, name: 'House Red Wine', category: 'wine', size: '750ml', bottle_cost: 8.00,
    pour_size: '150ml', pours_per_bottle: 5, cost_per_pour: 1.60, sell_price: 7.00,
    pour_cost_percentage: 22.9, ideal_pour_cost: 28, variance: -5.1, sold_today: 15, revenue_today: 105.00
  },
  {
    id: 8, name: 'Premium Prosecco', category: 'wine', size: '750ml', bottle_cost: 12.00,
    pour_size: '150ml', pours_per_bottle: 5, cost_per_pour: 2.40, sell_price: 9.00,
    pour_cost_percentage: 26.7, ideal_pour_cost: 30, variance: -3.3, sold_today: 18, revenue_today: 162.00
  },
  {
    id: 9, name: 'Mojito', category: 'cocktails', size: 'recipe', bottle_cost: 0,
    pour_size: 'single', pours_per_bottle: 1, cost_per_pour: 2.15, sell_price: 10.00,
    pour_cost_percentage: 21.5, ideal_pour_cost: 25, variance: -3.5, sold_today: 42, revenue_today: 420.00
  },
  {
    id: 10, name: 'Margarita', category: 'cocktails', size: 'recipe', bottle_cost: 0,
    pour_size: 'single', pours_per_bottle: 1, cost_per_pour: 2.30, sell_price: 10.00,
    pour_cost_percentage: 23.0, ideal_pour_cost: 25, variance: -2.0, sold_today: 38, revenue_today: 380.00
  },
  {
    id: 11, name: 'Long Island Iced Tea', category: 'cocktails', size: 'recipe', bottle_cost: 0,
    pour_size: 'single', pours_per_bottle: 1, cost_per_pour: 3.99, sell_price: 14.00,
    pour_cost_percentage: 28.5, ideal_pour_cost: 25, variance: 3.5, sold_today: 28, revenue_today: 392.00
  },
  {
    id: 12, name: 'Fresh Orange Juice', category: 'non_alcoholic', size: '1L', bottle_cost: 3.50,
    pour_size: '300ml', pours_per_bottle: 3, cost_per_pour: 1.17, sell_price: 4.50,
    pour_cost_percentage: 26.0, ideal_pour_cost: 20, variance: 6.0, sold_today: 24, revenue_today: 108.00
  },
];

const DEMO_SUMMARIES: CategorySummary[] = [
  { category: 'Spirits', items: 4, avgPourCost: 12.8, targetPourCost: 16.5, variance: -3.7, revenue: 748.00, profit: 652.40 },
  { category: 'Beer', items: 2, avgPourCost: 24.1, targetPourCost: 21.0, variance: 3.1, revenue: 656.00, profit: 498.00 },
  { category: 'Wine', items: 2, avgPourCost: 24.8, targetPourCost: 29.0, variance: -4.2, revenue: 267.00, profit: 200.80 },
  { category: 'Cocktails', items: 3, avgPourCost: 24.3, targetPourCost: 25.0, variance: -0.7, revenue: 1192.00, profit: 902.52 },
  { category: 'Non-Alcoholic', items: 1, avgPourCost: 26.0, targetPourCost: 20.0, variance: 6.0, revenue: 108.00, profit: 79.92 },
];

export default function PourCostsPage() {
  const [items, setItems] = useState<PourCostItem[]>([]);
  const [categorySummaries, setCategorySummaries] = useState<CategorySummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [sortBy, setSortBy] = useState<'name' | 'pour_cost' | 'variance' | 'revenue'>('pour_cost');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const [newItem, setNewItem] = useState({
    name: '',
    category: 'spirits' as PourCostItem['category'],
    size: '750ml',
    bottle_cost: 0,
    pour_size: '30ml',
    sell_price: 0,
    ideal_pour_cost: 22,
  });

  const fetchPourCosts = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('auth_token') || localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/bar/pour-costs/summary`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data && data.items && data.items.length > 0) {
          setItems(data.items);
          setCategorySummaries(data.summaries || DEMO_SUMMARIES);
        } else {
          setItems(DEMO_ITEMS);
          setCategorySummaries(DEMO_SUMMARIES);
        }
      } else {
        console.warn('API returned error, using demo data');
        setItems(DEMO_ITEMS);
        setCategorySummaries(DEMO_SUMMARIES);
      }
    } catch (err) {
      console.warn('Failed to fetch from API, using demo data:', err);
      setItems(DEMO_ITEMS);
      setCategorySummaries(DEMO_SUMMARIES);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPourCosts();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
            <p className="text-surface-600">Loading pour costs...</p>
          </div>
        </div>
      </div>
    );
  }

  const getPourCostColor = (cost: number, target?: number) => {
    if (target) {
      if (cost <= target - 3) return 'text-success-600';
      if (cost <= target) return 'text-primary-600';
      if (cost <= target + 3) return 'text-warning-600';
      return 'text-error-600';
    }
    if (cost <= 18) return 'text-success-600';
    if (cost <= 25) return 'text-primary-600';
    if (cost <= 30) return 'text-warning-600';
    return 'text-error-600';
  };

  const getVarianceColor = (variance: number) => {
    if (variance <= -3) return 'text-success-600 bg-success-50';
    if (variance < 0) return 'text-success-600 bg-success-50';
    if (variance <= 2) return 'text-warning-600 bg-warning-50';
    return 'text-error-600 bg-error-50';
  };

  const filteredItems = items
    .filter(item => selectedCategory === 'all' || item.category === selectedCategory)
    .filter(item => item.name.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'pour_cost':
          comparison = a.pour_cost_percentage - b.pour_cost_percentage;
          break;
        case 'variance':
          comparison = a.variance - b.variance;
          break;
        case 'revenue':
          comparison = a.revenue_today - b.revenue_today;
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  const handleAddItem = () => {
    const poursPerBottle = parseFloat(newItem.size) / parseFloat(newItem.pour_size.replace('ml', ''));
    const costPerPour = newItem.bottle_cost / poursPerBottle;
    const pourCostPercentage = (costPerPour / newItem.sell_price) * 100;

    const item: PourCostItem = {
      id: items.length + 1,
      name: newItem.name,
      category: newItem.category,
      size: newItem.size,
      bottle_cost: newItem.bottle_cost,
      pour_size: newItem.pour_size,
      pours_per_bottle: Math.floor(poursPerBottle),
      cost_per_pour: costPerPour,
      sell_price: newItem.sell_price,
      pour_cost_percentage: pourCostPercentage,
      ideal_pour_cost: newItem.ideal_pour_cost,
      variance: pourCostPercentage - newItem.ideal_pour_cost,
      sold_today: 0,
      revenue_today: 0,
    };

    setItems([...items, item]);
    setShowModal(false);
    setNewItem({
      name: '',
      category: 'spirits',
      size: '750ml',
      bottle_cost: 0,
      pour_size: '30ml',
      sell_price: 0,
      ideal_pour_cost: 22,
    });
  };

  const totalRevenue = filteredItems.reduce((sum, item) => sum + item.revenue_today, 0);
  const totalCost = filteredItems.reduce((sum, item) => sum + (item.cost_per_pour * item.sold_today), 0);
  const overallPourCost = totalRevenue > 0 ? (totalCost / totalRevenue) * 100 : 0;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link
            href="/bar"
            className="p-2 hover:bg-surface-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Pour Costs</h1>
            <p className="text-surface-600 mt-1">Track and optimize drink costs & margins</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Item
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Total Revenue</p>
          <p className="text-2xl font-bold text-success-600">${totalRevenue.toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Total Cost</p>
          <p className="text-2xl font-bold text-surface-900">${totalCost.toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Gross Profit</p>
          <p className="text-2xl font-bold text-success-600">${(totalRevenue - totalCost).toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Overall Pour Cost</p>
          <p className={`text-2xl font-bold ${getPourCostColor(overallPourCost)}`}>
            {overallPourCost.toFixed(1)}%
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Profit Margin</p>
          <p className="text-2xl font-bold text-primary-600">
            {(100 - overallPourCost).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Category Summary */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm mb-6 overflow-hidden">
        <div className="p-4 border-b border-surface-200">
          <h2 className="font-semibold text-surface-900">Category Performance</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Category</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Items</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Avg Pour Cost</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Target</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Variance</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Revenue</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Profit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {categorySummaries.map((cat) => (
                <tr key={cat.category} className="hover:bg-surface-50">
                  <td className="px-4 py-3 font-medium text-surface-900">
                    {CATEGORIES.find(c => c.label === cat.category)?.icon} {cat.category}
                  </td>
                  <td className="px-4 py-3 text-center text-surface-700">{cat.items}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-medium ${getPourCostColor(cat.avgPourCost, cat.targetPourCost)}`}>
                      {cat.avgPourCost.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-surface-500">{cat.targetPourCost.toFixed(1)}%</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getVarianceColor(cat.variance)}`}>
                      {cat.variance > 0 ? '+' : ''}{cat.variance.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-surface-900">
                    ${cat.revenue.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-success-600">
                    ${cat.profit.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === 'all'
                ? 'bg-primary-600 text-white'
                : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
            }`}
          >
            All Items
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                selectedCategory === cat.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
              }`}
            >
              <span>{cat.icon}</span>
              {cat.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <input
          type="text"
          placeholder="Search items..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 w-64"
        />
        <select
          value={`${sortBy}-${sortOrder}`}
          onChange={(e) => {
            const [by, order] = e.target.value.split('-');
            setSortBy(by as typeof sortBy);
            setSortOrder(order as typeof sortOrder);
          }}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="pour_cost-desc">Highest Pour Cost</option>
          <option value="pour_cost-asc">Lowest Pour Cost</option>
          <option value="variance-desc">Highest Variance</option>
          <option value="variance-asc">Lowest Variance</option>
          <option value="revenue-desc">Highest Revenue</option>
          <option value="name-asc">Name A-Z</option>
        </select>
      </div>

      {/* Items Table */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Item</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Size</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Bottle Cost</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Pour Size</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Pours/Bottle</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Cost/Pour</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Sell Price</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Pour Cost %</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Variance</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Revenue Today</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-surface-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">
                        {CATEGORIES.find(c => c.value === item.category)?.icon}
                      </span>
                      <div>
                        <p className="font-medium text-surface-900">{item.name}</p>
                        <p className="text-sm text-surface-500 capitalize">{item.category.replace('_', ' ')}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-surface-700">{item.size}</td>
                  <td className="px-4 py-3 text-right text-surface-900">
                    ${item.bottle_cost.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-center text-surface-700">{item.pour_size}</td>
                  <td className="px-4 py-3 text-center text-surface-700">{item.pours_per_bottle}</td>
                  <td className="px-4 py-3 text-right text-surface-900 font-medium">
                    ${item.cost_per_pour.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right text-success-600 font-medium">
                    ${item.sell_price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-bold ${getPourCostColor(item.pour_cost_percentage, item.ideal_pour_cost)}`}>
                      {item.pour_cost_percentage.toFixed(1)}%
                    </span>
                    <span className="text-xs text-surface-400 block">
                      target: {item.ideal_pour_cost}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getVarianceColor(item.variance)}`}>
                      {item.variance > 0 ? '+' : ''}{item.variance.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <p className="font-medium text-success-600">${item.revenue_today.toFixed(2)}</p>
                    <p className="text-xs text-surface-500">{item.sold_today} sold</p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Item Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-lg mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">Add Pour Cost Item</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Item Name</label>
                <input
                  type="text"
                  value={newItem.name}
                  onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Grey Goose Vodka"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Category</label>
                  <select
                    value={newItem.category}
                    onChange={(e) => setNewItem({ ...newItem, category: e.target.value as PourCostItem['category'] })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    {CATEGORIES.map((cat) => (
                      <option key={cat.value} value={cat.value}>{cat.icon} {cat.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Bottle Size</label>
                  <select
                    value={newItem.size}
                    onChange={(e) => setNewItem({ ...newItem, size: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="375ml">375ml</option>
                    <option value="750ml">750ml</option>
                    <option value="1L">1L (1000ml)</option>
                    <option value="1.5L">1.5L (1500ml)</option>
                    <option value="recipe">Recipe (Cocktail)</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Bottle Cost ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newItem.bottle_cost || ''}
                    onChange={(e) => setNewItem({ ...newItem, bottle_cost: parseFloat(e.target.value) || 0 })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Pour Size</label>
                  <select
                    value={newItem.pour_size}
                    onChange={(e) => setNewItem({ ...newItem, pour_size: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="30ml">30ml (1 oz)</option>
                    <option value="45ml">45ml (1.5 oz)</option>
                    <option value="60ml">60ml (2 oz)</option>
                    <option value="150ml">150ml (Wine Glass)</option>
                    <option value="330ml">330ml (Bottle Beer)</option>
                    <option value="500ml">500ml (Draft Beer)</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Sell Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newItem.sell_price || ''}
                    onChange={(e) => setNewItem({ ...newItem, sell_price: parseFloat(e.target.value) || 0 })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Target Pour Cost (%)</label>
                  <input
                    type="number"
                    value={newItem.ideal_pour_cost}
                    onChange={(e) => setNewItem({ ...newItem, ideal_pour_cost: parseInt(e.target.value) || 0 })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              {/* Preview Calculation */}
              {newItem.bottle_cost > 0 && newItem.sell_price > 0 && (
                <div className="bg-surface-50 rounded-lg p-4">
                  <h4 className="font-medium text-surface-900 mb-2">Calculated Pour Cost</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-surface-500">Cost per Pour</p>
                      <p className="font-medium text-surface-900">
                        ${(newItem.bottle_cost / (newItem.size === '750ml' ? 25 : newItem.size === '1L' ? 33 : 16)).toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-surface-500">Pour Cost %</p>
                      <p className={`font-medium ${getPourCostColor(
                        ((newItem.bottle_cost / (newItem.size === '750ml' ? 25 : newItem.size === '1L' ? 33 : 16)) / newItem.sell_price) * 100,
                        newItem.ideal_pour_cost
                      )}`}>
                        {(((newItem.bottle_cost / (newItem.size === '750ml' ? 25 : newItem.size === '1L' ? 33 : 16)) / newItem.sell_price) * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-surface-500">Profit per Pour</p>
                      <p className="font-medium text-success-600">
                        ${(newItem.sell_price - (newItem.bottle_cost / (newItem.size === '750ml' ? 25 : newItem.size === '1L' ? 33 : 16))).toFixed(2)}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddItem}
                disabled={!newItem.name || !newItem.bottle_cost || !newItem.sell_price}
                className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Item
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
