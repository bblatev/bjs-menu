'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api } from '@/lib/api';

interface PlatformProfit {
  platform: string;
  orders: number;
  gross_revenue: number;
  commission_pct: number;
  commission_amount: number;
  delivery_cost: number;
  net_profit: number;
  margin_pct: number;
}

interface ProfitSummary {
  total_orders: number;
  total_revenue: number;
  total_commissions: number;
  total_delivery_costs: number;
  total_net_profit: number;
  avg_margin_pct: number;
  platforms: PlatformProfit[];
  period: string;
}

export default function DeliveryProfitabilityPage() {
  const [data, setData] = useState<ProfitSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('30d');

  useEffect(() => {
    loadData();
  }, [period]);

  async function loadData() {
    setLoading(true);
    try {
      const result = await api.get<ProfitSummary>(`/delivery/profitability?period=${period}`);
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  const formatCurrency = (val: number) => `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const marginColor = (pct: number) => {
    if (pct >= 20) return 'text-green-600 dark:text-green-400';
    if (pct >= 10) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const platformIcon = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.includes('doordash')) return '🔴';
    if (lower.includes('uber')) return '🟢';
    if (lower.includes('grubhub')) return '🟠';
    if (lower.includes('direct')) return '🔵';
    return '📦';
  };

  return (
    <AdminLayout>
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Delivery Profitability</h1>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
          </select>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
          </div>
        ) : !data ? (
          <div className="text-center py-12 text-gray-500">No delivery data available</div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Orders</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">{data.total_orders.toLocaleString()}</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">Gross Revenue</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">{formatCurrency(data.total_revenue)}</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Commissions</div>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">-{formatCurrency(data.total_commissions)}</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="text-sm text-gray-500 dark:text-gray-400">Net Profit</div>
                <div className={`text-2xl font-bold ${marginColor(data.avg_margin_pct)}`}>{formatCurrency(data.total_net_profit)}</div>
                <div className={`text-sm ${marginColor(data.avg_margin_pct)}`}>{data.avg_margin_pct.toFixed(1)}% margin</div>
              </div>
            </div>

            {/* Platform Breakdown */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Platform Breakdown</h2>
              </div>
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Platform</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Orders</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Revenue</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Commission</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Delivery Cost</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Net Profit</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Margin</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {data.platforms.map((p) => (
                    <tr key={p.platform} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                        {platformIcon(p.platform)} {p.platform}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300">{p.orders.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300">{formatCurrency(p.gross_revenue)}</td>
                      <td className="px-4 py-3 text-right text-red-600 dark:text-red-400">
                        -{formatCurrency(p.commission_amount)} ({p.commission_pct}%)
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300">{formatCurrency(p.delivery_cost)}</td>
                      <td className={`px-4 py-3 text-right font-medium ${marginColor(p.margin_pct)}`}>
                        {formatCurrency(p.net_profit)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`px-2 py-1 text-sm font-medium rounded ${marginColor(p.margin_pct)}`}>
                          {p.margin_pct.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Recommendations */}
            <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <h3 className="font-semibold text-blue-800 dark:text-blue-200 mb-2">Optimization Recommendations</h3>
              <ul className="space-y-1 text-sm text-blue-700 dark:text-blue-300">
                {data.platforms.filter(p => p.margin_pct < 10).map(p => (
                  <li key={p.platform}>Consider renegotiating {p.platform} commission rates ({p.commission_pct}%) or increasing menu prices for that platform.</li>
                ))}
                {data.platforms.some(p => p.platform.toLowerCase().includes('direct')) ? (
                  <li>Push direct ordering to increase margin — promote your branded ordering page.</li>
                ) : (
                  <li>Enable commission-free direct ordering to capture more margin.</li>
                )}
              </ul>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
