"use client";

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import AdminLayout from '@/components/AdminLayout';
import { API_URL, getAuthHeaders } from '@/lib/api';

interface ForecastItem {
  item_id: number;
  item_name: string;
  current_value: number;
  forecast_values: number[];
  forecast_dates: string[];
  confidence_interval: [number, number];
  trend: string;
  accuracy_score: number;
  recommendations: string[];
}

interface DashboardData {
  sales_trend: {
    direction: string;
    change_percent: number;
    total_sales: number;
    average_daily: number;
  };
  demand_forecast: {
    next_7_days: number;
    trending_up: string[];
    trending_down: string[];
  };
  stock_alerts: {
    high_urgency_count: number;
    items_to_reorder: string[];
  };
  key_insights: string[];
}


export default function ForecastingPage() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [forecasts, setForecasts] = useState<ForecastItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [forecastDays, setForecastDays] = useState(7);
  const [method, setMethod] = useState('ensemble');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      const token = localStorage.getItem('access_token');

      try {
        // Use existing analytics dashboard endpoint
        const dashRes = await fetch(`${API_URL}/analytics/dashboard`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (dashRes.ok) setDashboardData(await dashRes.json());

        // Use daily metrics for forecast data
        const forecastRes = await fetch(
          `${API_URL}/analytics/daily-metrics/?days=${forecastDays}`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );
        if (forecastRes.ok) {
          const data = await forecastRes.json();
          // Transform daily metrics to forecast format
          setForecasts(data.metrics?.map((m: Record<string, unknown>) => ({
            date: m.date,
            predicted_revenue: m.revenue || 0,
            predicted_orders: m.order_count || 0,
            confidence: 0.85
          })) || []);
        }
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [forecastDays, method]);

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up': return 'bg-green-100 text-green-800';
      case 'down': return 'bg-red-100 text-red-800';
      case 'volatile': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Demand Forecasting</h1>
            <p className="text-surface-500 mt-1">AI-powered demand predictions</p>
          </div>
          <div className="flex gap-4">
            <select value={method} onChange={(e) => setMethod(e.target.value)}
              className="px-4 py-2 border rounded-lg text-sm">
              <option value="ensemble">Ensemble</option>
              <option value="moving_average">Moving Average</option>
              <option value="exponential_smoothing">Exponential</option>
              <option value="seasonal">Seasonal</option>
            </select>
            <select value={forecastDays} onChange={(e) => setForecastDays(parseInt(e.target.value))}
              className="px-4 py-2 border rounded-lg text-sm">
              <option value={7}>7 Days</option>
              <option value={14}>14 Days</option>
              <option value={30}>30 Days</option>
            </select>
          </div>
        </div>

        {dashboardData && (
          <div className="grid grid-cols-4 gap-4">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl p-6 shadow-sm border">
              <div className="text-sm text-surface-500">Sales Trend</div>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-2xl font-bold">
                  {dashboardData.sales_trend.direction === 'up' ? '↗' : dashboardData.sales_trend.direction === 'down' ? '↘' : '→'}
                </span>
                <span className={`text-lg font-semibold \${dashboardData.sales_trend.change_percent > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {dashboardData.sales_trend.change_percent > 0 ? '+' : ''}{dashboardData.sales_trend.change_percent.toFixed(1)}%
                </span>
              </div>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              className="bg-white rounded-xl p-6 shadow-sm border">
              <div className="text-sm text-surface-500">Next 7 Days</div>
              <div className="mt-2 text-2xl font-bold text-primary-600">{dashboardData.demand_forecast.next_7_days.toFixed(0)} units</div>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              className="bg-white rounded-xl p-6 shadow-sm border">
              <div className="text-sm text-surface-500">Trending Up</div>
              <div className="mt-2 text-2xl font-bold text-green-600">{dashboardData.demand_forecast.trending_up.length}</div>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
              className="bg-white rounded-xl p-6 shadow-sm border">
              <div className="text-sm text-surface-500">Stock Alerts</div>
              <div className="mt-2 text-2xl font-bold text-orange-600">{dashboardData.stock_alerts.high_urgency_count}</div>
            </motion.div>
          </div>
        )}

        {dashboardData?.key_insights && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <h3 className="font-semibold text-blue-800 mb-2">Key Insights</h3>
            <ul className="space-y-1">
              {dashboardData.key_insights.map((insight, idx) => (
                <li key={idx} className="text-sm text-blue-700">• {insight}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="px-6 py-4 border-b"><h2 className="text-lg font-semibold">Item Forecasts</h2></div>
          {loading ? (
            <div className="p-8 text-center text-surface-500">Loading...</div>
          ) : (
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Item</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Current</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Trend</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Forecast</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Accuracy</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Recommendation</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {forecasts.map((item) => (
                  <tr key={item.item_id} className="hover:bg-surface-50">
                    <td className="px-6 py-4 font-medium">{item.item_name}</td>
                    <td className="px-6 py-4">{item.current_value}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium \${getTrendColor(item.trend)}`}>{item.trend}</span>
                    </td>
                    <td className="px-6 py-4">{item.forecast_values.slice(0,3).map(v => v.toFixed(0)).join(', ')}...</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-surface-200 rounded-full overflow-hidden">
                          <div className={`h-full \${item.accuracy_score > 80 ? 'bg-green-500' : item.accuracy_score > 60 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{width: `\${item.accuracy_score}%`}}/>
                        </div>
                        <span className="text-sm">{item.accuracy_score}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm max-w-xs truncate">{item.recommendations[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
