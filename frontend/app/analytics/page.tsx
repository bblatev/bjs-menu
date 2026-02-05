"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { API_URL } from "@/lib/api";

interface AnalyticsData {
  summary: {
    total_orders: number;
    total_revenue: number;
    total_tips: number;
    avg_order_value: number;
    avg_tip_percentage: number;
  };
  orders_by_hour: { hour: number; count: number; revenue: number }[];
  orders_by_day: { date: string; count: number; revenue: number; tips: number }[];
  top_items: { id: number; name: string | { bg?: string; en?: string } | null; quantity: number; revenue: number }[];
  payment_methods: { method: string; count: number; amount: number }[];
  tips_by_method: { method: string; total_tips: number; avg_tip: number }[];
  station_performance: { station: string; orders: number; avg_time: number }[];
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState("today");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    loadAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange, startDate, endDate]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      let url = `${API_URL}/analytics/dashboard?range=${dateRange}`;

      if (dateRange === "custom" && startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
      }

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setData(await response.json());
      } else {
        console.error("Failed to load analytics data");
        setData(null);
      }
    } catch (error) {
      console.error("Error loading analytics:", error);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => `${amount.toFixed(2)} €`;

  const maxRevenue = data?.orders_by_hour
    ? Math.max(...data.orders_by_hour.map((h) => h.revenue))
    : 100;

  const maxDayRevenue = data?.orders_by_day
    ? Math.max(...data.orders_by_day.map((d) => d.revenue))
    : 100;

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading analytics...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">No Analytics Data</h2>
          <p className="text-gray-600 mb-4">Unable to load analytics data. Please try again later.</p>
          <button
            onClick={loadAnalytics}
            className="px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">📊 Analytics</h1>
            <p className="text-gray-600 mt-1">Revenue, tips & performance insights</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {["today", "week", "month", "custom"].map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={`px-4 py-2 rounded-lg capitalize ${
                  dateRange === range
                    ? "bg-orange-500 text-gray-900"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {dateRange === "custom" && (
          <div className="flex gap-4 mb-6">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg"
            />
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 rounded-2xl p-6 border border-blue-500/30"
          >
            <div className="text-blue-400 text-sm mb-1">Total Orders</div>
            <div className="text-3xl font-bold text-gray-900">
              {data?.summary?.total_orders || 0}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gradient-to-br from-green-500/20 to-green-600/20 rounded-2xl p-6 border border-green-500/30"
          >
            <div className="text-green-400 text-sm mb-1">Total Revenue</div>
            <div className="text-3xl font-bold text-gray-900">
              {formatCurrency(data?.summary?.total_revenue || 0)}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gradient-to-br from-yellow-500/20 to-yellow-600/20 rounded-2xl p-6 border border-yellow-500/30"
          >
            <div className="text-yellow-400 text-sm mb-1">💰 Total Tips</div>
            <div className="text-3xl font-bold text-gray-900">
              {formatCurrency(data?.summary?.total_tips || 0)}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-2xl p-6 border border-purple-500/30"
          >
            <div className="text-purple-400 text-sm mb-1">Avg Order</div>
            <div className="text-3xl font-bold text-gray-900">
              {formatCurrency(data?.summary?.avg_order_value || 0)}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-gradient-to-br from-orange-500/20 to-orange-600/20 rounded-2xl p-6 border border-orange-500/30"
          >
            <div className="text-orange-400 text-sm mb-1">Avg Tip %</div>
            <div className="text-3xl font-bold text-gray-900">
              {data?.summary?.avg_tip_percentage || 0}%
            </div>
          </motion.div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Orders by Hour */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-gray-50 rounded-2xl p-6 border border-gray-200"
          >
            <h3 className="text-xl font-bold text-gray-900 mb-4">📈 Orders by Hour</h3>
            <div className="flex items-end justify-between h-48 gap-1">
              {(data?.orders_by_hour || []).map((item, i) => (
                <div key={i} className="flex flex-col items-center flex-1">
                  <div
                    className="w-full bg-gradient-to-t from-blue-500 to-blue-400 rounded-t-sm transition-all hover:from-blue-400 hover:to-blue-300"
                    style={{
                      height: `${(item.revenue / maxRevenue) * 100}%`,
                      minHeight: "4px",
                    }}
                    title={`${item.count} orders - ${formatCurrency(item.revenue)}`}
                  />
                  <span className="text-xs text-gray-500 mt-1">{item.hour}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Revenue by Day */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-gray-50 rounded-2xl p-6 border border-gray-200"
          >
            <h3 className="text-xl font-bold text-gray-900 mb-4">📅 Weekly Revenue</h3>
            <div className="flex items-end justify-between h-48 gap-2">
              {(data?.orders_by_day || []).map((item, i) => (
                <div key={i} className="flex flex-col items-center flex-1">
                  <div className="w-full flex flex-col rounded-t-sm overflow-hidden"
                    style={{ height: `${(item.revenue / maxDayRevenue) * 100}%`, minHeight: "8px" }}
                  >
                    <div
                      className="w-full bg-yellow-500"
                      style={{ height: `${(item.tips / item.revenue) * 100}%` }}
                      title={`Tips: ${formatCurrency(item.tips)}`}
                    />
                    <div
                      className="w-full bg-green-500 flex-1"
                      title={`Revenue: ${formatCurrency(item.revenue - item.tips)}`}
                    />
                  </div>
                  <span className="text-xs text-gray-500 mt-1">{item.date}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-center gap-6 mt-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded" />
                <span className="text-gray-600 text-sm">Revenue</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-500 rounded" />
                <span className="text-gray-600 text-sm">Tips</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Top Items */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gray-50 rounded-2xl p-6 border border-gray-200"
          >
            <h3 className="text-xl font-bold text-gray-900 mb-4">🏆 Top Items</h3>
            <div className="space-y-3">
              {(data?.top_items || []).map((item, i) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">
                      {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : "•"}
                    </span>
                    <div>
                      <div className="text-gray-900 font-medium">{typeof item.name === 'object' && item.name ? (item.name.bg || item.name.en || 'Item') : String(item.name || 'Item')}</div>
                      <div className="text-gray-500 text-sm">{item.quantity} sold</div>
                    </div>
                  </div>
                  <div className="text-green-400 font-bold">
                    {formatCurrency(item.revenue)}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Payment Methods */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gray-50 rounded-2xl p-6 border border-gray-200"
          >
            <h3 className="text-xl font-bold text-gray-900 mb-4">💳 Payment Methods</h3>
            <div className="space-y-4">
              {(data?.payment_methods || []).map((pm) => {
                const total = (data?.payment_methods || []).reduce((a, b) => a + b.count, 0);
                const percentage = ((pm.count / total) * 100).toFixed(0);
                return (
                  <div key={pm.method} className="space-y-2">
                    <div className="flex justify-between text-gray-900">
                      <span className="capitalize flex items-center gap-2">
                        {pm.method === "cash" ? "💵" : "💳"} {pm.method}
                      </span>
                      <span>{pm.count} orders</span>
                    </div>
                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          pm.method === "cash" ? "bg-green-500" : "bg-blue-500"
                        }`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">{percentage}%</span>
                      <span className="text-gray-700">{formatCurrency(pm.amount)}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-200">
              <h4 className="text-gray-900 font-medium mb-3">💰 Tips by Method</h4>
              {(data?.tips_by_method || []).map((tm) => (
                <div
                  key={tm.method}
                  className="flex justify-between items-center py-2"
                >
                  <span className="text-gray-700 capitalize">
                    {tm.method === "cash" ? "💵" : "💳"} {tm.method}
                  </span>
                  <div className="text-right">
                    <div className="text-yellow-400 font-bold">
                      {formatCurrency(tm.total_tips)}
                    </div>
                    <div className="text-gray-500 text-sm">
                      avg {formatCurrency(tm.avg_tip)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Station Performance */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-gray-50 rounded-2xl p-6 border border-gray-200"
          >
            <h3 className="text-xl font-bold text-gray-900 mb-4">⚡ Station Performance</h3>
            <div className="space-y-4">
              {(data?.station_performance || []).map((station) => (
                <div
                  key={station.station}
                  className="p-4 bg-gray-50 rounded-xl"
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-900 font-bold text-lg">
                      {station.station === "Kitchen" ? "👨‍🍳" : "🍺"} {station.station}
                    </span>
                    <span className="text-gray-700">{station.orders} orders</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          station.avg_time <= 5
                            ? "bg-green-500"
                            : station.avg_time <= 10
                            ? "bg-yellow-500"
                            : "bg-red-500"
                        }`}
                        style={{
                          width: `${Math.min((station.avg_time / 20) * 100, 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-gray-700 text-sm w-16 text-right">
                      {station.avg_time} min
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-xl border border-yellow-500/30">
              <div className="text-yellow-400 font-bold mb-1">💡 Tip Insight</div>
              <div className="text-gray-800 text-sm">
                Tips account for{" "}
                <span className="text-yellow-400 font-bold">
                  {data?.summary?.total_revenue
                    ? ((data.summary.total_tips / data.summary.total_revenue) * 100).toFixed(1)
                    : 0}
                  %
                </span>{" "}
                of total revenue. Average tip is{" "}
                <span className="text-yellow-400 font-bold">
                  {data?.summary?.avg_tip_percentage}%
                </span>
                .
              </div>
            </div>
          </motion.div>
        </div>

        {/* Export Button */}
        <div className="mt-8 flex justify-center">
          <a
            href="/reports"
            className="px-8 py-4 bg-gradient-to-r from-orange-500 to-red-500 text-gray-900 font-bold rounded-xl hover:from-orange-600 hover:to-red-600 transition-all"
          >
            📄 Generate Detailed Report
          </a>
        </div>
      </div>
    </div>
  );
}
