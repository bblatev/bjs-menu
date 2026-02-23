'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface VendorPrice {
  vendor_id: number;
  vendor_name: string;
  unit_price: number;
  pack_size: string;
  price_per_unit: number;
  last_updated: string;
  in_stock: boolean;
  delivery_days: number;
  minimum_order: number;
}

interface ItemPriceComparison {
  item_id: number;
  item_name: string;
  category: string;
  unit: string;
  current_vendor: string;
  current_price: number;
  vendor_prices: VendorPrice[];
  best_price: number;
  best_vendor: string;
  potential_savings: number;
  savings_pct: number;
}

interface BestPrice {
  item_id: number;
  item_name: string;
  best_vendor: string;
  best_price: number;
  current_price: number;
  savings: number;
}

interface VendorPricesResponse {
  items: ItemPriceComparison[];
  vendors: string[];
  total_potential_savings: number;
  categories: string[];
}

interface BestPricesResponse {
  recommendations: BestPrice[];
  total_savings: number;
}

// ============ COMPONENT ============

export default function VendorPriceComparisonPage() {
  const [data, setData] = useState<VendorPricesResponse | null>(null);
  const [bestPrices, setBestPrices] = useState<BestPricesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [showSavingsOnly, setShowSavingsOnly] = useState(false);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pricesRes, bestRes] = await Promise.all([
        api.get<VendorPricesResponse>('/inventory/vendor-prices'),
        api.get<BestPricesResponse>('/inventory/best-prices'),
      ]);
      setData(pricesRes);
      setBestPrices(bestRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load price data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredItems = data?.items.filter((item) => {
    const matchesSearch =
      !searchQuery ||
      item.item_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = filterCategory === 'all' || item.category === filterCategory;
    const matchesSavings = !showSavingsOnly || item.potential_savings > 0;
    return matchesSearch && matchesCategory && matchesSavings;
  }) || [];

  const isBestPrice = (itemId: number, vendorName: string) => {
    const item = data?.items.find((i) => i.item_id === itemId);
    return item?.best_vendor === vendorName;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading vendor prices...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">💲</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Price Data Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchData}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/stock/intelligence" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-surface-900">Vendor Price Comparison</h1>
          <p className="text-surface-500 mt-1">Compare prices across vendors and find the best deals</p>
        </div>
      </div>

      {/* Savings Summary */}
      {data && bestPrices && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-5 rounded-xl border border-green-200">
            <p className="text-sm text-green-700">Total Potential Savings</p>
            <p className="text-3xl font-bold text-green-700">
              ${data.total_potential_savings.toFixed(2)}
            </p>
            <p className="text-xs text-green-600 mt-1">By switching to best-price vendors</p>
          </div>
          <div className="bg-white p-5 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Items Compared</p>
            <p className="text-3xl font-bold text-surface-900">{data.items.length}</p>
            <p className="text-xs text-surface-400 mt-1">Across {data.vendors.length} vendors</p>
          </div>
          <div className="bg-white p-5 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Items with Savings</p>
            <p className="text-3xl font-bold text-primary-600">
              {data.items.filter((i) => i.potential_savings > 0).length}
            </p>
            <p className="text-xs text-surface-400 mt-1">Could be purchased cheaper</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <input
          type="text"
          placeholder="Search items..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 w-64"
        />
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Categories</option>
          {data?.categories.map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-surface-600">
          <input
            type="checkbox"
            checked={showSavingsOnly}
            onChange={(e) => setShowSavingsOnly(e.target.checked)}
            className="w-4 h-4 rounded text-primary-600"
          />
          Show savings opportunities only
        </label>
      </div>

      {/* Price Comparison Table */}
      <div className="bg-white rounded-xl border border-surface-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-surface-600 sticky left-0 bg-surface-50 z-10">Item</th>
                <th className="px-4 py-3 text-left font-medium text-surface-600">Category</th>
                <th className="px-4 py-3 text-right font-medium text-surface-600">Current Price</th>
                {data?.vendors.map((vendor) => (
                  <th key={vendor} className="px-4 py-3 text-right font-medium text-surface-600 whitespace-nowrap">
                    {vendor}
                  </th>
                ))}
                <th className="px-4 py-3 text-right font-medium text-surface-600">Best Price</th>
                <th className="px-4 py-3 text-right font-medium text-surface-600">Savings</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => (
                <tr
                  key={item.item_id}
                  className="border-t border-surface-100 hover:bg-surface-50 cursor-pointer"
                  onClick={() => setExpandedItem(expandedItem === item.item_id ? null : item.item_id)}
                >
                  <td className="px-4 py-3 font-medium text-surface-900 sticky left-0 bg-white z-10">
                    <div className="flex items-center gap-2">
                      <svg
                        className={`w-4 h-4 text-surface-400 transition-transform ${expandedItem === item.item_id ? 'rotate-90' : ''}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      {item.item_name}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-surface-600 capitalize">{item.category}</td>
                  <td className="px-4 py-3 text-right text-surface-700">
                    ${item.current_price.toFixed(2)}/{item.unit}
                  </td>
                  {data?.vendors.map((vendor) => {
                    const vp = item.vendor_prices.find((v) => v.vendor_name === vendor);
                    const best = isBestPrice(item.item_id, vendor);
                    return (
                      <td key={vendor} className="px-4 py-3 text-right">
                        {vp ? (
                          <span className={`${best ? 'font-bold text-green-600 bg-green-50 px-2 py-0.5 rounded' : vp.in_stock ? 'text-surface-700' : 'text-surface-400 line-through'}`}>
                            ${vp.price_per_unit.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-surface-300">-</span>
                        )}
                      </td>
                    );
                  })}
                  <td className="px-4 py-3 text-right font-bold text-green-600">
                    ${item.best_price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.potential_savings > 0 ? (
                      <span className="font-medium text-green-600">
                        -${item.potential_savings.toFixed(2)}
                        <span className="text-xs text-green-500 ml-1">({item.savings_pct.toFixed(0)}%)</span>
                      </span>
                    ) : (
                      <span className="text-surface-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Expanded Details */}
      {expandedItem && data && (() => {
        const item = data.items.find((i) => i.item_id === expandedItem);
        if (!item) return null;
        return (
          <div className="bg-surface-50 rounded-xl border border-surface-200 p-6">
            <h3 className="text-lg font-semibold text-surface-900 mb-4">{item.item_name} - Vendor Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {item.vendor_prices.map((vp) => (
                <div
                  key={vp.vendor_id}
                  className={`p-4 rounded-lg border ${
                    vp.vendor_name === item.best_vendor
                      ? 'border-green-300 bg-green-50'
                      : 'border-surface-200 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-surface-900">{vp.vendor_name}</span>
                    {vp.vendor_name === item.best_vendor && (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                        Best Price
                      </span>
                    )}
                  </div>
                  <p className="text-2xl font-bold text-surface-900">${vp.unit_price.toFixed(2)}</p>
                  <div className="text-xs text-surface-500 space-y-1 mt-2">
                    <p>Pack: {vp.pack_size}</p>
                    <p>Per unit: ${vp.price_per_unit.toFixed(2)}/{item.unit}</p>
                    <p>Delivery: {vp.delivery_days} days</p>
                    <p>Min order: {vp.minimum_order}</p>
                    <p className={vp.in_stock ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                      {vp.in_stock ? 'In Stock' : 'Out of Stock'}
                    </p>
                    <p className="text-surface-400">Updated: {new Date(vp.last_updated).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {filteredItems.length === 0 && (
        <div className="text-center py-12 text-surface-500">
          <p className="text-lg">No items match your filters</p>
          <p className="text-sm mt-1">Try a different search or category</p>
        </div>
      )}
    </div>
  );
}
