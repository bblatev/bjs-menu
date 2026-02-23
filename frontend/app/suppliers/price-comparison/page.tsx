'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface PriceComparison {
  item_name: string;
  unit: string;
  suppliers: { name: string; price: number; lead_days: number; min_order: number }[];
  best_value: string;
}

export default function PriceComparisonPage() {
  const [comparisons, setComparisons] = useState<PriceComparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const data = await api.get<PriceComparison[]>('/purchase-order-advanced/price-comparison');
      setComparisons(Array.isArray(data) ? data : []);
    } catch { setComparisons([]); }
    finally { setLoading(false); }
  }

  const filtered = comparisons.filter(c => c.item_name.toLowerCase().includes(search.toLowerCase()));

  return (
    <AdminLayout>
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Supplier Price Comparison</h1>
          <input
            type="text"
            placeholder="Search items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white w-64"
          />
        </div>
        {loading ? (
          <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-500">No price comparison data available</div>
        ) : (
          <div className="space-y-4">
            {filtered.map((item, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 dark:text-white">{item.item_name} <span className="text-sm text-gray-500">({item.unit})</span></h3>
                  <span className="text-sm bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200 px-2 py-1 rounded">Best: {item.best_value}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {item.suppliers.map((s, j) => (
                    <div key={j} className={`p-3 rounded-lg border ${s.name === item.best_value ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-200 dark:border-gray-700'}`}>
                      <div className="font-medium text-gray-900 dark:text-white">{s.name}</div>
                      <div className="text-lg font-bold text-gray-900 dark:text-white">${s.price.toFixed(2)}/{item.unit}</div>
                      <div className="text-sm text-gray-500">Lead: {s.lead_days}d | Min: {s.min_order}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
