'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface LiquorItem {
  id: number;
  name: string;
  brand: string;
  category: string;
  sku: string;
  size: string;
  full_bottles: number;
  partial_bottles: number;
  partial_percentage: number;
  total_volume_ml: number;
  par_level: number;
  reorder_point: number;
  cost_per_bottle: number;
  total_value: number;
  last_count_date: string;
  counted_by: string;
  variance_from_expected: number;
  location: string;
  supplier: string;
}

const CATEGORIES = [
  { value: 'vodka', label: 'Vodka', icon: '🍸' },
  { value: 'gin', label: 'Gin', icon: '🫒' },
  { value: 'rum', label: 'Rum', icon: '🏝️' },
  { value: 'tequila', label: 'Tequila', icon: '🌵' },
  { value: 'whiskey', label: 'Whiskey', icon: '🥃' },
  { value: 'wine', label: 'Wine', icon: '🍷' },
  { value: 'beer', label: 'Beer', icon: '🍺' },
  { value: 'liqueur', label: 'Liqueurs', icon: '🍹' },
  { value: 'mixers', label: 'Mixers', icon: '🧊' },
];

const LOCATIONS = ['Main Bar', 'Back Bar', 'Service Bar', 'Storage Room', 'Wine Cellar'];

export default function BarInventoryPage() {
  const [items, setItems] = useState<LiquorItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedLocation, setSelectedLocation] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCountModal, setShowCountModal] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<LiquorItem | null>(null);
  const [countData, setCountData] = useState({ full_bottles: 0, partial_percentage: 0 });
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [isFullCountMode, setIsFullCountMode] = useState(false);
  const [fullCountItems, setFullCountItems] = useState<{[key: number]: {full: number, partial: number}}>({});
  const [newItem, setNewItem] = useState({
    name: '', brand: '', category: 'vodka', size: '750ml',
    cost_per_bottle: 20, par_level: 6, location: 'Main Bar', supplier: ''
  });

  const fetchInventory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_URL}/bar/inventory`, {
        credentials: 'include',
        headers,
      });

      if (response.ok) {
        const data = await response.json();
        // Transform API data to match component interface if needed
        if (data && data.length > 0) {
          setItems(data.map((item: Record<string, unknown>) => ({
            id: item.id,
            name: item.item_name || item.name,
            brand: item.brand || 'Unknown',
            category: item.category || 'spirits',
            sku: item.sku || `SKU-${item.id}`,
            size: item.size || '750ml',
            full_bottles: Math.floor(Number(item.current_stock) || 0),
            partial_bottles: (Number(item.current_stock) || 0) % 1 > 0 ? 1 : 0,
            partial_percentage: Math.round(((Number(item.current_stock) || 0) % 1) * 100),
            total_volume_ml: (Number(item.current_stock) || 0) * 750,
            par_level: Number(item.par_level) || 6,
            reorder_point: Math.floor((Number(item.par_level) || 6) / 2),
            cost_per_bottle: Number(item.cost_per_unit) || Number(item.cost) || 20,
            total_value: (Number(item.current_stock) || 0) * (Number(item.cost_per_unit) || Number(item.cost) || 20),
            last_count_date: new Date().toISOString().split('T')[0],
            counted_by: 'System',
            variance_from_expected: 0,
            location: item.location || 'Main Bar',
            supplier: item.supplier || 'Unknown',
          })));
        }
      } else {
        console.error('Failed to load bar inventory:', response.status);
      }
    } catch (err) {
      console.error('Failed to fetch bar inventory:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInventory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getStockStatus = (item: LiquorItem) => {
    const totalBottles = item.full_bottles + (item.partial_percentage / 100);
    if (totalBottles <= item.reorder_point * 0.5) return { status: 'critical', color: 'bg-error-100 text-error-700 border-error-300' };
    if (totalBottles <= item.reorder_point) return { status: 'low', color: 'bg-warning-100 text-warning-700 border-warning-300' };
    if (totalBottles <= item.par_level * 0.7) return { status: 'reorder', color: 'bg-primary-100 text-primary-700 border-primary-300' };
    return { status: 'ok', color: 'bg-success-100 text-success-700 border-success-300' };
  };

  const getVarianceColor = (variance: number) => {
    if (Math.abs(variance) < 0.2) return 'text-success-600';
    if (Math.abs(variance) < 0.5) return 'text-warning-600';
    return 'text-error-600';
  };

  const filteredItems = items
    .filter(item => selectedCategory === 'all' || item.category === selectedCategory)
    .filter(item => selectedLocation === 'all' || item.location === selectedLocation)
    .filter(item =>
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.brand.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.sku.toLowerCase().includes(searchQuery.toLowerCase())
    );

  const totalInventoryValue = items.reduce((sum, item) => sum + item.total_value, 0);
  const lowStockItems = items.filter(item => getStockStatus(item).status !== 'ok');
  const itemsNeedingCount = items.filter(item => {
    const lastCount = new Date(item.last_count_date);
    const daysSinceCount = Math.floor((Date.now() - lastCount.getTime()) / (1000 * 60 * 60 * 24));
    return daysSinceCount > 7;
  });

  const handleCount = (item: LiquorItem) => {
    setSelectedItem(item);
    setCountData({
      full_bottles: item.full_bottles,
      partial_percentage: item.partial_percentage
    });
    setShowCountModal(true);
  };

  const submitCount = () => {
    if (!selectedItem) return;

    const updatedItems = items.map(item => {
      if (item.id === selectedItem.id) {
        const newTotalVolume = (countData.full_bottles * parseInt(item.size)) +
          ((countData.partial_percentage / 100) * parseInt(item.size));
        return {
          ...item,
          full_bottles: countData.full_bottles,
          partial_bottles: countData.partial_percentage > 0 ? 1 : 0,
          partial_percentage: countData.partial_percentage,
          total_volume_ml: newTotalVolume,
          total_value: (countData.full_bottles + (countData.partial_percentage / 100)) * item.cost_per_bottle,
          last_count_date: new Date().toISOString().split('T')[0],
          counted_by: 'Current User',
        };
      }
      return item;
    });

    setItems(updatedItems);
    setShowCountModal(false);
    setSelectedItem(null);
  };

  const handleAddItem = async () => {
    try {
      const response = await fetch(`${API_URL}/stock/`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: newItem.name,
          sku: `BAR-${Date.now()}`,
          quantity: 0,
          unit: 'bottles',
          low_stock_threshold: newItem.par_level / 2,
          cost_per_unit: newItem.cost_per_bottle,
        }),
      });

      if (response.ok) {
        const created = await response.json();
        const newLiquorItem: LiquorItem = {
          id: created.id || Date.now(),
          name: newItem.name,
          brand: newItem.brand,
          category: newItem.category,
          sku: `BAR-${created.id || Date.now()}`,
          size: newItem.size,
          full_bottles: 0,
          partial_bottles: 0,
          partial_percentage: 0,
          total_volume_ml: 0,
          par_level: newItem.par_level,
          reorder_point: Math.floor(newItem.par_level / 2),
          cost_per_bottle: newItem.cost_per_bottle,
          total_value: 0,
          last_count_date: new Date().toISOString().split('T')[0],
          counted_by: 'New',
          variance_from_expected: 0,
          location: newItem.location,
          supplier: newItem.supplier,
        };
        setItems([...items, newLiquorItem]);
      } else {
        // Add locally if API fails
        const newLiquorItem: LiquorItem = {
          id: Date.now(),
          name: newItem.name,
          brand: newItem.brand,
          category: newItem.category,
          sku: `BAR-${Date.now()}`,
          size: newItem.size,
          full_bottles: 0,
          partial_bottles: 0,
          partial_percentage: 0,
          total_volume_ml: 0,
          par_level: newItem.par_level,
          reorder_point: Math.floor(newItem.par_level / 2),
          cost_per_bottle: newItem.cost_per_bottle,
          total_value: 0,
          last_count_date: new Date().toISOString().split('T')[0],
          counted_by: 'New',
          variance_from_expected: 0,
          location: newItem.location,
          supplier: newItem.supplier,
        };
        setItems([...items, newLiquorItem]);
      }
    } catch {
      // Add locally on error
      const newLiquorItem: LiquorItem = {
        id: Date.now(),
        name: newItem.name,
        brand: newItem.brand,
        category: newItem.category,
        sku: `BAR-${Date.now()}`,
        size: newItem.size,
        full_bottles: 0,
        partial_bottles: 0,
        partial_percentage: 0,
        total_volume_ml: 0,
        par_level: newItem.par_level,
        reorder_point: Math.floor(newItem.par_level / 2),
        cost_per_bottle: newItem.cost_per_bottle,
        total_value: 0,
        last_count_date: new Date().toISOString().split('T')[0],
        counted_by: 'New',
        variance_from_expected: 0,
        location: newItem.location,
        supplier: newItem.supplier,
      };
      setItems([...items, newLiquorItem]);
    }
    setShowAddModal(false);
    setNewItem({ name: '', brand: '', category: 'vodka', size: '750ml', cost_per_bottle: 20, par_level: 6, location: 'Main Bar', supplier: '' });
  };

  const startFullCount = () => {
    const initialCounts: {[key: number]: {full: number, partial: number}} = {};
    items.forEach(item => {
      initialCounts[item.id] = { full: item.full_bottles, partial: item.partial_percentage };
    });
    setFullCountItems(initialCounts);
    setIsFullCountMode(true);
  };

  const saveFullCount = () => {
    const updatedItems = items.map(item => {
      const countData = fullCountItems[item.id];
      if (countData) {
        const newTotalVolume = (countData.full * parseInt(item.size)) + ((countData.partial / 100) * parseInt(item.size));
        return {
          ...item,
          full_bottles: countData.full,
          partial_bottles: countData.partial > 0 ? 1 : 0,
          partial_percentage: countData.partial,
          total_volume_ml: newTotalVolume,
          total_value: (countData.full + (countData.partial / 100)) * item.cost_per_bottle,
          last_count_date: new Date().toISOString().split('T')[0],
          counted_by: 'Full Count',
        };
      }
      return item;
    });
    setItems(updatedItems);
    setIsFullCountMode(false);
    setFullCountItems({});
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
            <p className="text-surface-600">Loading inventory...</p>
          </div>
        </div>
      </div>
    );
  }

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
            <h1 className="text-2xl font-bold text-surface-900">Bar Inventory</h1>
            <p className="text-surface-600 mt-1">Track bottles, par levels & counts</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50 flex items-center gap-2"
           aria-label="Close">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export
          </button>
          <button
            onClick={startFullCount}
            className="px-4 py-2 bg-accent-600 text-gray-900 rounded-lg hover:bg-accent-700 flex items-center gap-2"
           aria-label="Close">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Start Full Count
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Item
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-surface-500">Total Items</p>
            <span className="text-2xl">🍾</span>
          </div>
          <p className="text-2xl font-bold text-surface-900">{items.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-surface-500">Inventory Value</p>
            <span className="text-2xl">💰</span>
          </div>
          <p className="text-2xl font-bold text-success-600">${(totalInventoryValue || 0).toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-surface-500">Low Stock</p>
            <span className="text-2xl">⚠️</span>
          </div>
          <p className="text-2xl font-bold text-warning-600">{lowStockItems.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm text-surface-500">Need Counting</p>
            <span className="text-2xl">📋</span>
          </div>
          <p className="text-2xl font-bold text-primary-600">{itemsNeedingCount.length}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedCategory === 'all'
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
              }`}
            >
              All
            </button>
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setSelectedCategory(cat.value)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
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
          <select
            value={selectedLocation}
            onChange={(e) => setSelectedLocation(e.target.value)}
            className="px-3 py-1.5 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Locations</option>
            {LOCATIONS.map((loc) => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Search inventory..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 w-64"
          />
          <div className="flex items-center border border-surface-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-2 ${viewMode === 'list' ? 'bg-primary-100 text-primary-700' : 'text-surface-600 hover:bg-surface-100'}`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-2 ${viewMode === 'grid' ? 'bg-primary-100 text-primary-700' : 'text-surface-600 hover:bg-surface-100'}`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Inventory Table */}
      {viewMode === 'list' ? (
        <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-surface-500 uppercase">Item</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Location</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Full</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Partial</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Par Level</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase">Value</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Variance</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Last Count</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-surface-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {filteredItems.map((item) => {
                  const stockStatus = getStockStatus(item);
                  const totalBottles = item.full_bottles + (item.partial_percentage / 100);

                  return (
                    <tr key={item.id} className="hover:bg-surface-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <span className="text-xl">
                            {CATEGORIES.find(c => c.value === item.category)?.icon}
                          </span>
                          <div>
                            <p className="font-medium text-surface-900">{item.name}</p>
                            <p className="text-sm text-surface-500">{item.sku} • {item.size}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="px-2 py-1 bg-surface-100 text-surface-700 rounded text-sm">
                          {item.location}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-lg font-bold text-surface-900">{item.full_bottles}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {item.partial_bottles > 0 ? (
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-8 h-8 border-2 border-surface-300 rounded relative overflow-hidden">
                              <div
                                className="absolute bottom-0 left-0 right-0 bg-primary-400"
                                style={{ height: `${item.partial_percentage}%` }}
                              />
                            </div>
                            <span className="text-sm text-surface-600">{item.partial_percentage}%</span>
                          </div>
                        ) : (
                          <span className="text-surface-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex flex-col items-center">
                          <span className="font-medium text-surface-700">{item.par_level}</span>
                          <div className="w-16 h-2 bg-surface-200 rounded-full overflow-hidden mt-1">
                            <div
                              className={`h-full rounded-full ${
                                totalBottles >= item.par_level ? 'bg-success-500' :
                                totalBottles >= item.reorder_point ? 'bg-warning-500' :
                                'bg-error-500'
                              }`}
                              style={{ width: `${Math.min((totalBottles / item.par_level) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${stockStatus.color}`}>
                          {stockStatus.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-surface-900">
                        ${(item.total_value || 0).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-medium ${getVarianceColor(item.variance_from_expected)}`}>
                          {item.variance_from_expected > 0 ? '+' : ''}{(item.variance_from_expected || 0).toFixed(1)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="text-sm">
                          <p className="text-surface-900">{item.last_count_date}</p>
                          <p className="text-surface-500">{item.counted_by}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => handleCount(item)}
                          className="px-3 py-1 bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200 text-sm font-medium"
                        >
                          Count
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredItems.map((item) => {
            const stockStatus = getStockStatus(item);
            const totalBottles = item.full_bottles + (item.partial_percentage / 100);

            return (
              <div key={item.id} className="bg-white rounded-xl border border-surface-200 shadow-sm p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">
                      {CATEGORIES.find(c => c.value === item.category)?.icon}
                    </span>
                    <div>
                      <h3 className="font-semibold text-surface-900">{item.name}</h3>
                      <p className="text-sm text-surface-500">{item.brand}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${stockStatus.color}`}>
                    {stockStatus.status}
                  </span>
                </div>

                <div className="flex items-center gap-4 mb-4">
                  {/* Full bottles visualization */}
                  <div className="flex items-end gap-1">
                    {Array.from({ length: Math.min(item.full_bottles, 5) }).map((_, i) => (
                      <div
                        key={i}
                        className="w-4 h-8 bg-primary-400 rounded-t-lg border border-primary-500"
                      />
                    ))}
                    {item.full_bottles > 5 && (
                      <span className="text-sm text-surface-500">+{item.full_bottles - 5}</span>
                    )}
                    {item.partial_bottles > 0 && (
                      <div className="w-4 h-8 border border-surface-300 rounded-t-lg relative overflow-hidden">
                        <div
                          className="absolute bottom-0 left-0 right-0 bg-primary-300"
                          style={{ height: `${item.partial_percentage}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 text-right">
                    <p className="text-2xl font-bold text-surface-900">{(totalBottles || 0).toFixed(1)}</p>
                    <p className="text-sm text-surface-500">of {item.par_level} par</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-sm mb-4">
                  <div className="bg-surface-50 rounded-lg p-2">
                    <p className="text-surface-500">Location</p>
                    <p className="font-medium text-surface-900">{item.location}</p>
                  </div>
                  <div className="bg-surface-50 rounded-lg p-2">
                    <p className="text-surface-500">Value</p>
                    <p className="font-medium text-success-600">${(item.total_value || 0).toFixed(2)}</p>
                  </div>
                </div>

                <button
                  onClick={() => handleCount(item)}
                  className="w-full py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 font-medium"
                >
                  Count Bottle
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Count Modal */}
      {showCountModal && selectedItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-md mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <h2 className="text-xl font-semibold text-surface-900">Count Bottle</h2>
              <p className="text-surface-600 mt-1">{selectedItem.name}</p>
            </div>
            <div className="p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-2">Full Bottles</label>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setCountData({ ...countData, full_bottles: Math.max(0, countData.full_bottles - 1) })}
                    className="w-12 h-12 rounded-lg border border-surface-300 flex items-center justify-center text-xl font-bold hover:bg-surface-100"
                  >
                    -
                  </button>
                  <input
                    type="number"
                    value={countData.full_bottles}
                    onChange={(e) => setCountData({ ...countData, full_bottles: parseInt(e.target.value) || 0 })}
                    className="flex-1 text-center text-3xl font-bold border border-surface-300 rounded-lg py-2"
                  />
                  <button
                    onClick={() => setCountData({ ...countData, full_bottles: countData.full_bottles + 1 })}
                    className="w-12 h-12 rounded-lg border border-surface-300 flex items-center justify-center text-xl font-bold hover:bg-surface-100"
                  >
                    +
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-2">
                  Partial Bottle ({countData.partial_percentage}%)
                </label>
                <div className="flex items-center gap-4">
                  <div className="w-16 h-32 border-2 border-surface-300 rounded-lg relative overflow-hidden">
                    <div
                      className="absolute bottom-0 left-0 right-0 bg-primary-400 transition-all"
                      style={{ height: `${countData.partial_percentage}%` }}
                    />
                    {[25, 50, 75].map((line) => (
                      <div
                        key={line}
                        className="absolute left-0 right-0 border-t border-dashed border-surface-400"
                        style={{ bottom: `${line}%` }}
                      />
                    ))}
                  </div>
                  <div className="flex-1 space-y-2">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={countData.partial_percentage}
                      onChange={(e) => setCountData({ ...countData, partial_percentage: parseInt(e.target.value) })}
                      className="w-full"
                    />
                    <div className="grid grid-cols-5 gap-1">
                      {[0, 25, 50, 75, 100].map((val) => (
                        <button
                          key={val}
                          onClick={() => setCountData({ ...countData, partial_percentage: val })}
                          className={`py-1 text-xs rounded ${
                            countData.partial_percentage === val
                              ? 'bg-primary-600 text-white'
                              : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                          }`}
                        >
                          {val}%
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-surface-50 rounded-lg p-4">
                <h4 className="font-medium text-surface-900 mb-2">Summary</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-surface-500">Total Volume</p>
                    <p className="font-medium">
                      {(countData.full_bottles * parseInt(selectedItem.size) +
(                        (countData.partial_percentage / 100) * parseInt(selectedItem.size)) || 0).toFixed(0)}ml
                    </p>
                  </div>
                  <div>
                    <p className="text-surface-500">Estimated Value</p>
                    <p className="font-medium text-success-600">
                      ${(((countData.full_bottles + (countData.partial_percentage / 100)) * selectedItem.cost_per_bottle) || 0).toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-surface-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowCountModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={submitCount}
                className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700"
              >
                Save Count
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Item Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl w-full max-w-md mx-4 shadow-xl">
            <div className="p-6 border-b border-surface-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-surface-900">Add New Item</h2>
                <button onClick={() => setShowAddModal(false)} className="p-2 hover:bg-surface-100 rounded-lg">
                  <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Name *</label>
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
                  <label className="block text-sm font-medium text-surface-700 mb-1">Brand</label>
                  <input
                    type="text"
                    value={newItem.brand}
                    onChange={(e) => setNewItem({ ...newItem, brand: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    placeholder="e.g., Grey Goose"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Category</label>
                  <select
                    value={newItem.category}
                    onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    {CATEGORIES.map(cat => (
                      <option key={cat.value} value={cat.value}>{cat.icon} {cat.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Size</label>
                  <select
                    value={newItem.size}
                    onChange={(e) => setNewItem({ ...newItem, size: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="375ml">375ml</option>
                    <option value="750ml">750ml</option>
                    <option value="1L">1L</option>
                    <option value="1.5L">1.5L</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Cost/Bottle ($)</label>
                  <input
                    type="number"
                    value={newItem.cost_per_bottle}
                    onChange={(e) => setNewItem({ ...newItem, cost_per_bottle: parseFloat(e.target.value) || 0 })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Par Level</label>
                  <input
                    type="number"
                    value={newItem.par_level}
                    onChange={(e) => setNewItem({ ...newItem, par_level: parseInt(e.target.value) || 1 })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Location</label>
                  <select
                    value={newItem.location}
                    onChange={(e) => setNewItem({ ...newItem, location: e.target.value })}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    {LOCATIONS.map(loc => (
                      <option key={loc} value={loc}>{loc}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Supplier</label>
                <input
                  type="text"
                  value={newItem.supplier}
                  onChange={(e) => setNewItem({ ...newItem, supplier: e.target.value })}
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Premium Spirits Co"
                />
              </div>
            </div>
            <div className="p-6 border-t border-surface-200 flex gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleAddItem}
                disabled={!newItem.name}
                className="flex-1 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                Add Item
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Full Count Mode Banner */}
      {isFullCountMode && (
        <div className="fixed bottom-0 left-0 right-0 bg-accent-600 text-gray-900 p-4 z-40 shadow-lg">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-2xl">📋</span>
              <div>
                <p className="font-bold">Full Count Mode Active</p>
                <p className="text-sm opacity-80">Update counts for all items, then save</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => { setIsFullCountMode(false); setFullCountItems({}); }}
                className="px-4 py-2 bg-white/20 rounded-lg hover:bg-white/30"
              >
                Cancel
              </button>
              <button
                onClick={saveFullCount}
                className="px-4 py-2 bg-white text-accent-700 font-bold rounded-lg hover:bg-white/90"
              >
                Save All Counts
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
