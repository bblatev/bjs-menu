'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface ABCItem {
  product_id: number;
  product_name: string;
  sku: string | null;
  category: string;
  total_value: number;
  cumulative_pct: number;
  annual_usage: number;
  unit_cost: number;
}

interface ABCAnalysis {
  location_id: number;
  period_days: number;
  total_inventory_value: number;
  a_items: number;
  b_items: number;
  c_items: number;
  a_value_pct: number;
  b_value_pct: number;
  c_value_pct: number;
  items: ABCItem[];
}

interface TurnoverItem {
  product_id: number;
  product_name: string;
  sku: string | null;
  turnover_ratio: number;
  days_on_hand: number | null;
  avg_stock: number;
  total_usage: number;
  status: string;
}

interface TurnoverData {
  location_id: number;
  period_days: number;
  avg_turnover: number;
  items: TurnoverItem[];
}

interface DeadStockItem {
  product_id: number;
  product_name: string;
  current_qty: number;
  current_value: number;
  days_since_movement: number;
  last_movement_date: string | null;
}

interface COGSData {
  cogs: number;
  opening_stock_value: number;
  purchases_value: number;
  closing_stock_value: number;
  cogs_pct_of_revenue: number | null;
  revenue: number | null;
  by_category: { category: string; opening: number; purchases: number; closing: number; cogs: number }[];
}

interface FoodCostVarianceItem {
  product_id: number;
  product_name: string;
  theoretical_usage: number;
  actual_usage: number;
  variance: number;
  variance_pct: number;
  variance_value: number;
}

interface EOQData {
  product_id: number;
  product_name: string;
  annual_demand: number;
  eoq: number;
  reorder_point: number;
  safety_stock: number;
  orders_per_year: number;
  total_annual_cost: number;
  unit_cost: number;
}

interface CycleCountItem {
  product_id: number;
  product_name: string;
  abc_category: string;
  frequency: string;
  next_count_date: string;
  last_counted: string | null;
}

type Tab = 'abc' | 'turnover' | 'dead-stock' | 'cogs' | 'variance' | 'eoq' | 'snapshots' | 'cycle-count';

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'abc', label: 'ABC Analysis', icon: 'A' },
  { key: 'turnover', label: 'Turnover', icon: 'T' },
  { key: 'dead-stock', label: 'Dead Stock', icon: 'D' },
  { key: 'cogs', label: 'COGS', icon: '$' },
  { key: 'variance', label: 'Food Cost Variance', icon: 'V' },
  { key: 'eoq', label: 'EOQ Calculator', icon: 'E' },
  { key: 'snapshots', label: 'Snapshots', icon: 'S' },
  { key: 'cycle-count', label: 'Cycle Count', icon: 'C' },
];

export default function InventoryIntelligencePage() {
  const [activeTab, setActiveTab] = useState<Tab>('abc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [abcData, setAbcData] = useState<ABCAnalysis | null>(null);
  const [turnoverData, setTurnoverData] = useState<TurnoverData | null>(null);
  const [deadStock, setDeadStock] = useState<DeadStockItem[]>([]);
  const [deadStockValue, setDeadStockValue] = useState(0);
  const [cogsData, setCogsData] = useState<COGSData | null>(null);
  const [varianceItems, setVarianceItems] = useState<FoodCostVarianceItem[]>([]);
  const [varianceTotals, setVarianceTotals] = useState({ theoretical: 0, actual: 0, variance: 0, pct: 0 });
  const [eoqProductId, setEoqProductId] = useState('1');
  const [eoqData, setEoqData] = useState<EOQData | null>(null);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [cycleCount, setCycleCount] = useState<{ total_items: number; weekly_count: number; biweekly_count: number; monthly_count: number; quarterly_count: number; schedule: CycleCountItem[] } | null>(null);

  const fetchData = useCallback(async (tab: Tab) => {
    setLoading(true);
    setError(null);
    try {
      const headers = getAuthHeaders();
      switch (tab) {
        case 'abc': {
          const res = await fetch(`${API_URL}/inventory-intelligence/abc-analysis`, { headers });
          const data = await res.json();
          setAbcData(data);
          break;
        }
        case 'turnover': {
          const res = await fetch(`${API_URL}/inventory-intelligence/turnover`, { headers });
          const data = await res.json();
          setTurnoverData(data);
          break;
        }
        case 'dead-stock': {
          const res = await fetch(`${API_URL}/inventory-intelligence/dead-stock`, { headers });
          const data = await res.json();
          setDeadStock(data.items || []);
          setDeadStockValue(data.total_dead_value || 0);
          break;
        }
        case 'cogs': {
          const res = await fetch(`${API_URL}/inventory-intelligence/cogs`, { headers });
          const data = await res.json();
          setCogsData(data);
          break;
        }
        case 'variance': {
          const res = await fetch(`${API_URL}/inventory-intelligence/food-cost-variance`, { headers });
          const data = await res.json();
          setVarianceItems(data.items || []);
          setVarianceTotals({ theoretical: data.total_theoretical_cost, actual: data.total_actual_cost, variance: data.total_variance, pct: data.total_variance_pct });
          break;
        }
        case 'eoq': {
          if (eoqProductId) {
            const res = await fetch(`${API_URL}/inventory-intelligence/eoq/${eoqProductId}`, { headers });
            const data = await res.json();
            setEoqData(data);
          }
          break;
        }
        case 'snapshots': {
          const res = await fetch(`${API_URL}/inventory-intelligence/snapshots`, { headers });
          const data = await res.json();
          setSnapshots(data);
          break;
        }
        case 'cycle-count': {
          const res = await fetch(`${API_URL}/inventory-intelligence/cycle-count-schedule`, { headers });
          const data = await res.json();
          setCycleCount(data);
          break;
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [eoqProductId]);

  useEffect(() => {
    fetchData(activeTab);
  }, [activeTab, fetchData]);

  const fmt = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtPct = (n: number) => `${n.toFixed(1)}%`;

  const categoryColor = (cat: string) => {
    switch (cat) {
      case 'A': return 'bg-red-100 text-red-800';
      case 'B': return 'bg-amber-100 text-amber-800';
      case 'C': return 'bg-green-100 text-green-800';
      case 'D': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'fast': return 'bg-green-100 text-green-800';
      case 'normal': return 'bg-blue-100 text-blue-800';
      case 'slow': return 'bg-amber-100 text-amber-800';
      case 'dead': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const createSnapshot = async () => {
    try {
      const headers = getAuthHeaders();
      await fetch(`${API_URL}/inventory-intelligence/snapshots`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ location_id: 1, name: `Snapshot ${new Date().toLocaleString()}` }),
      });
      fetchData('snapshots');
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/stock" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">Inventory Intelligence</h1>
            <p className="text-surface-500 mt-1">Advanced analytics: ABC, turnover, COGS, food cost variance, EOQ</p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-surface-200 overflow-x-auto">
        <div className="flex gap-1 min-w-max">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-surface-500 hover:text-surface-700 hover:border-surface-300'
              }`}
            >
              <span className="inline-flex items-center gap-1.5">
                <span className="w-5 h-5 rounded text-xs font-bold flex items-center justify-center bg-surface-100">{tab.icon}</span>
                {tab.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
          {error}
          <button onClick={() => fetchData(activeTab)} className="ml-2 underline">Retry</button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-amber-500"></div>
        </div>
      )}

      {/* ========== ABC Analysis ========== */}
      {!loading && activeTab === 'abc' && abcData && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Total Inventory Value</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">${fmt(abcData.total_inventory_value)}</div>
            </div>
            <div className="bg-red-50 rounded-xl border border-red-200 p-4">
              <div className="text-sm text-red-600">A Items (Top Value)</div>
              <div className="text-2xl font-bold text-red-800 mt-1">{abcData.a_items}</div>
              <div className="text-xs text-red-500">{fmtPct(abcData.a_value_pct)} of value</div>
            </div>
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-4">
              <div className="text-sm text-amber-600">B Items (Medium)</div>
              <div className="text-2xl font-bold text-amber-800 mt-1">{abcData.b_items}</div>
              <div className="text-xs text-amber-500">{fmtPct(abcData.b_value_pct)} of value</div>
            </div>
            <div className="bg-green-50 rounded-xl border border-green-200 p-4">
              <div className="text-sm text-green-600">C Items (Low Value)</div>
              <div className="text-2xl font-bold text-green-800 mt-1">{abcData.c_items}</div>
              <div className="text-xs text-green-500">{fmtPct(abcData.c_value_pct)} of value</div>
            </div>
          </div>

          {/* Items Table */}
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="font-semibold text-surface-900">ABC Classification ({abcData.items.length} items)</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Product</th>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">SKU</th>
                    <th className="text-center px-4 py-3 font-medium text-surface-600">Class</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Total Value</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Cumulative %</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Annual Usage</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Unit Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {abcData.items.map((item) => (
                    <tr key={item.product_id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{item.product_name}</td>
                      <td className="px-4 py-3 text-surface-500 font-mono text-xs">{item.sku || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${categoryColor(item.category)}`}>{item.category}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">${fmt(item.total_value)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-surface-100 rounded-full h-1.5">
                            <div className="bg-amber-500 h-1.5 rounded-full" style={{ width: `${Math.min(item.cumulative_pct, 100)}%` }}></div>
                          </div>
                          <span className="text-xs text-surface-500 w-12 text-right">{fmtPct(item.cumulative_pct)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{fmt(item.annual_usage)}</td>
                      <td className="px-4 py-3 text-right font-mono">${fmt(item.unit_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========== Turnover ========== */}
      {!loading && activeTab === 'turnover' && turnoverData && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Average Turnover Ratio</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">{turnoverData.avg_turnover.toFixed(1)}x</div>
            </div>
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Total Items Tracked</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">{turnoverData.items.length}</div>
            </div>
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Period</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">{turnoverData.period_days} days</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="font-semibold text-surface-900">Turnover by Product</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Product</th>
                    <th className="text-center px-4 py-3 font-medium text-surface-600">Status</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Turnover Ratio</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Days on Hand</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Avg Stock</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Total Usage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {turnoverData.items.slice(0, 50).map((item) => (
                    <tr key={item.product_id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{item.product_name}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${statusColor(item.status)}`}>{item.status}</span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{item.turnover_ratio.toFixed(1)}x</td>
                      <td className="px-4 py-3 text-right font-mono">{item.days_on_hand?.toFixed(0) || '-'}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmt(item.avg_stock)}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmt(item.total_usage)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========== Dead Stock ========== */}
      {!loading && activeTab === 'dead-stock' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Dead Stock Items</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">{deadStock.length}</div>
            </div>
            <div className="bg-red-50 rounded-xl border border-red-200 p-4">
              <div className="text-sm text-red-600">Dead Stock Value</div>
              <div className="text-2xl font-bold text-red-800 mt-1">${fmt(deadStockValue)}</div>
            </div>
          </div>

          {deadStock.length === 0 ? (
            <div className="bg-white rounded-xl border border-surface-200 p-12 text-center">
              <div className="text-4xl mb-3">&#10003;</div>
              <h3 className="text-lg font-bold text-surface-900">No Dead Stock</h3>
              <p className="text-surface-500 mt-1">All inventory items have recent movement. Great job!</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Product</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Qty</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Value</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Days Since Movement</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Last Movement</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {deadStock.map((item) => (
                    <tr key={item.product_id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{item.product_name}</td>
                      <td className="px-4 py-3 text-right font-mono">{fmt(item.current_qty)}</td>
                      <td className="px-4 py-3 text-right font-mono text-red-600">${fmt(item.current_value)}</td>
                      <td className="px-4 py-3 text-right font-mono">{item.days_since_movement}</td>
                      <td className="px-4 py-3 text-right text-xs text-surface-500">{item.last_movement_date ? new Date(item.last_movement_date).toLocaleDateString() : 'Never'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========== COGS ========== */}
      {!loading && activeTab === 'cogs' && cogsData && (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Opening Stock</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">${fmt(cogsData.opening_stock_value)}</div>
            </div>
            <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
              <div className="text-sm text-blue-600">+ Purchases</div>
              <div className="text-2xl font-bold text-blue-800 mt-1">${fmt(cogsData.purchases_value)}</div>
            </div>
            <div className="bg-green-50 rounded-xl border border-green-200 p-4">
              <div className="text-sm text-green-600">- Closing Stock</div>
              <div className="text-2xl font-bold text-green-800 mt-1">${fmt(cogsData.closing_stock_value)}</div>
            </div>
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-4">
              <div className="text-sm text-amber-600">= COGS</div>
              <div className="text-2xl font-bold text-amber-800 mt-1">${fmt(cogsData.cogs)}</div>
              {cogsData.cogs_pct_of_revenue !== null && (
                <div className="text-xs text-amber-500">{fmtPct(cogsData.cogs_pct_of_revenue)} of revenue</div>
              )}
            </div>
          </div>

          {cogsData.revenue !== null && (
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Revenue (Period)</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">${fmt(cogsData.revenue)}</div>
            </div>
          )}

          {cogsData.by_category.length > 0 && (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <div className="p-4 border-b border-surface-100">
                <h3 className="font-semibold text-surface-900">COGS by Category</h3>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Category</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Opening</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Purchases</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Closing</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">COGS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {cogsData.by_category.map((cat) => (
                    <tr key={cat.category} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{cat.category}</td>
                      <td className="px-4 py-3 text-right font-mono">${fmt(cat.opening)}</td>
                      <td className="px-4 py-3 text-right font-mono">${fmt(cat.purchases)}</td>
                      <td className="px-4 py-3 text-right font-mono">${fmt(cat.closing)}</td>
                      <td className="px-4 py-3 text-right font-mono font-bold">${fmt(cat.cogs)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========== Food Cost Variance ========== */}
      {!loading && activeTab === 'variance' && (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Theoretical Cost</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">${fmt(varianceTotals.theoretical)}</div>
            </div>
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Actual Cost</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">${fmt(varianceTotals.actual)}</div>
            </div>
            <div className={`rounded-xl border p-4 ${varianceTotals.variance > 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
              <div className="text-sm text-surface-500">Variance</div>
              <div className={`text-2xl font-bold mt-1 ${varianceTotals.variance > 0 ? 'text-red-800' : 'text-green-800'}`}>${fmt(varianceTotals.variance)}</div>
            </div>
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Variance %</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">{fmtPct(varianceTotals.pct)}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="font-semibold text-surface-900">Variance by Product ({varianceItems.length} items)</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Product</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Theoretical</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Actual</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Variance</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Variance %</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Variance $</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {varianceItems.slice(0, 50).map((item) => (
                    <tr key={item.product_id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{item.product_name}</td>
                      <td className="px-4 py-3 text-right font-mono">{item.theoretical_usage.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right font-mono">{item.actual_usage.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right font-mono">{item.variance.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${item.variance_pct > 10 ? 'bg-red-100 text-red-800' : item.variance_pct > 0 ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'}`}>
                          {fmtPct(item.variance_pct)}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-bold ${item.variance_value > 0 ? 'text-red-600' : 'text-green-600'}`}>${fmt(item.variance_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========== EOQ Calculator ========== */}
      {!loading && activeTab === 'eoq' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-surface-200 p-6">
            <h3 className="font-semibold text-surface-900 mb-4">Economic Order Quantity (Wilson Formula)</h3>
            <div className="flex items-end gap-4">
              <div className="flex-1">
                <label className="text-sm text-surface-600 mb-1 block">Product ID</label>
                <input
                  type="number"
                  value={eoqProductId}
                  onChange={(e) => setEoqProductId(e.target.value)}
                  className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                  min={1}
                />
              </div>
              <button
                onClick={() => fetchData('eoq')}
                className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600"
              >
                Calculate
              </button>
            </div>
          </div>

          {eoqData && (
            <div className="space-y-4">
              <div className="bg-amber-50 rounded-xl border border-amber-200 p-6 text-center">
                <div className="text-sm text-amber-600 mb-1">Optimal Order Quantity</div>
                <div className="text-4xl font-bold text-amber-800">{fmt(eoqData.eoq)} units</div>
                <div className="text-sm text-amber-600 mt-1">{eoqData.product_name}</div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-surface-200 p-4">
                  <div className="text-sm text-surface-500">Annual Demand</div>
                  <div className="text-xl font-bold text-surface-900 mt-1">{fmt(eoqData.annual_demand)} units</div>
                </div>
                <div className="bg-white rounded-xl border border-surface-200 p-4">
                  <div className="text-sm text-surface-500">Orders per Year</div>
                  <div className="text-xl font-bold text-surface-900 mt-1">{eoqData.orders_per_year.toFixed(1)}</div>
                </div>
                <div className="bg-white rounded-xl border border-surface-200 p-4">
                  <div className="text-sm text-surface-500">Total Annual Cost</div>
                  <div className="text-xl font-bold text-surface-900 mt-1">${fmt(eoqData.total_annual_cost)}</div>
                </div>
                <div className="bg-white rounded-xl border border-surface-200 p-4">
                  <div className="text-sm text-surface-500">Reorder Point</div>
                  <div className="text-xl font-bold text-surface-900 mt-1">{fmt(eoqData.reorder_point)} units</div>
                </div>
                <div className="bg-white rounded-xl border border-surface-200 p-4">
                  <div className="text-sm text-surface-500">Safety Stock</div>
                  <div className="text-xl font-bold text-surface-900 mt-1">{fmt(eoqData.safety_stock)} units</div>
                </div>
                <div className="bg-white rounded-xl border border-surface-200 p-4">
                  <div className="text-sm text-surface-500">Unit Cost</div>
                  <div className="text-xl font-bold text-surface-900 mt-1">${fmt(eoqData.unit_cost)}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========== Snapshots ========== */}
      {!loading && activeTab === 'snapshots' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-surface-900">Inventory Snapshots</h3>
            <button
              onClick={createSnapshot}
              className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 text-sm"
            >
              + Take Snapshot
            </button>
          </div>

          {snapshots.length === 0 ? (
            <div className="bg-white rounded-xl border border-surface-200 p-12 text-center">
              <div className="text-4xl mb-3">&#128247;</div>
              <h3 className="text-lg font-bold text-surface-900">No Snapshots Yet</h3>
              <p className="text-surface-500 mt-1">Take a snapshot to record your current inventory for comparison</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">ID</th>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Name</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Items</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Value</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {snapshots.map((s: any) => (
                    <tr key={s.id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-mono text-surface-500">#{s.id}</td>
                      <td className="px-4 py-3 font-medium text-surface-900">{s.name}</td>
                      <td className="px-4 py-3 text-right font-mono">{s.total_items}</td>
                      <td className="px-4 py-3 text-right font-mono">${fmt(s.total_value)}</td>
                      <td className="px-4 py-3 text-right text-xs text-surface-500">{new Date(s.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========== Cycle Count Schedule ========== */}
      {!loading && activeTab === 'cycle-count' && cycleCount && (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-surface-200 p-4">
              <div className="text-sm text-surface-500">Total Items</div>
              <div className="text-2xl font-bold text-surface-900 mt-1">{cycleCount.total_items}</div>
            </div>
            <div className="bg-red-50 rounded-xl border border-red-200 p-4">
              <div className="text-sm text-red-600">Weekly (A-Items)</div>
              <div className="text-2xl font-bold text-red-800 mt-1">{cycleCount.weekly_count}</div>
            </div>
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-4">
              <div className="text-sm text-amber-600">Biweekly (B-Items)</div>
              <div className="text-2xl font-bold text-amber-800 mt-1">{cycleCount.biweekly_count}</div>
            </div>
            <div className="bg-green-50 rounded-xl border border-green-200 p-4">
              <div className="text-sm text-green-600">Monthly (C-Items)</div>
              <div className="text-2xl font-bold text-green-800 mt-1">{cycleCount.monthly_count}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100">
              <h3 className="font-semibold text-surface-900">Count Schedule</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-surface-600">Product</th>
                    <th className="text-center px-4 py-3 font-medium text-surface-600">ABC Class</th>
                    <th className="text-center px-4 py-3 font-medium text-surface-600">Frequency</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Next Count</th>
                    <th className="text-right px-4 py-3 font-medium text-surface-600">Last Counted</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {cycleCount.schedule.map((item) => (
                    <tr key={item.product_id} className="hover:bg-surface-50">
                      <td className="px-4 py-3 font-medium text-surface-900">{item.product_name}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${categoryColor(item.abc_category)}`}>{item.abc_category}</span>
                      </td>
                      <td className="px-4 py-3 text-center capitalize">{item.frequency}</td>
                      <td className="px-4 py-3 text-right text-xs">{item.next_count_date}</td>
                      <td className="px-4 py-3 text-right text-xs text-surface-500">{item.last_counted ? new Date(item.last_counted).toLocaleDateString() : 'Never'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
