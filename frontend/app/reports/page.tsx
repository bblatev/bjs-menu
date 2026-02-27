'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { api, isAuthenticated } from '@/lib/api';

interface SalesReportItem {
  date: string;
  total_orders: number;
  total_revenue: number;
  average_order_value: number;
}

interface TopSellingItem {
  item_id: number;
  item_name: string;
  quantity_sold: number;
  total_revenue: number;
}

interface CategorySalesReport {
  category_id: number;
  category_name: string;
  total_orders: number;
  total_revenue: number;
}

interface SalesReport {
  period: string;
  start_date: string;
  end_date: string;
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  daily_breakdown: SalesReportItem[];
  top_items: TopSellingItem[];
  category_breakdown: CategorySalesReport[];
}

interface StockReport {
  item_id: number;
  item_name: string;
  current_quantity: number;
  unit: string;
  min_stock: number;
  reorder_needed: boolean;
  total_value: number;
}

interface StaffPerformance {
  staff_id: number;
  staff_name: string;
  total_orders: number;
  total_revenue: number;
  average_order_value: number;
}

interface CustomerInsight {
  total_customers: number;
  new_customers: number;
  returning_customers: number;
  average_spending: number;
  top_customers: {
    id: number;
    name: string;
    total_orders: number;
    total_spent: number;
    loyalty_points: number;
  }[];
}

export default function ReportsPage() {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState<'sales' | 'stock' | 'staff' | 'customers'>('sales');
  const [period, setPeriod] = useState<string>('week');
  const [loading, setLoading] = useState(false);

  // Data states
  const [salesReport, setSalesReport] = useState<SalesReport | null>(null);
  const [stockReport, setStockReport] = useState<StockReport[]>([]);
  const [staffReport, setStaffReport] = useState<StaffPerformance[]>([]);
  const [customerReport, setCustomerReport] = useState<CustomerInsight | null>(null);
  const [lowStockOnly, setLowStockOnly] = useState(false);

  // Custom date range states
  const [dateFrom, setDateFrom] = useState<string>(new Date().toISOString().split('T')[0]);
  const [dateTo, setDateTo] = useState<string>(new Date().toISOString().split('T')[0]);
  const [hourFrom, setHourFrom] = useState<string>('00');
  const [hourTo, setHourTo] = useState<string>('23');

  const fetchSalesReport = async () => {
    setLoading(true);
    try {
      let url = `/reports/sales?period=${period}`;
      if (period === 'custom') {
        url = `/reports/sales?period=custom&date_from=${dateFrom}&date_to=${dateTo}&hour_from=${hourFrom}&hour_to=${hourTo}`;
      }
      const data = await api.get<SalesReport>(url);
      setSalesReport(data);
    } catch (err) {
      console.error('Error fetching sales report:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStockReport = async () => {
    setLoading(true);
    try {
      const data = await api.get<StockReport[]>(`/reports/stock?low_stock_only=${lowStockOnly}`);
      setStockReport(data);
    } catch (err) {
      console.error('Error fetching stock report:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStaffReport = async () => {
    setLoading(true);
    try {
      const data = await api.get<StaffPerformance[]>(`/reports/staff-performance?period=${period}`);
      setStaffReport(data);
    } catch (err) {
      console.error('Error fetching staff report:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCustomerReport = async () => {
    setLoading(true);
    try {
      const data = await api.get<CustomerInsight>(`/reports/customer-insights?period=${period}`);
      setCustomerReport(data);
    } catch (err) {
      console.error('Error fetching customer report:', err);
    } finally {
      setLoading(false);
    }
  };

  // Check authentication on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }
    setAuthenticated(true);
  }, [router]);

  useEffect(() => {
    if (!authenticated) return;
    if (activeTab === 'sales') fetchSalesReport();
    else if (activeTab === 'stock') fetchStockReport();
    else if (activeTab === 'staff') fetchStaffReport();
    else if (activeTab === 'customers') fetchCustomerReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, period, lowStockOnly, authenticated, dateFrom, dateTo, hourFrom, hourTo]);

  const formatCurrency = (val: number) => `${(val || 0).toFixed(2)} лв`;
  const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString('bg-BG');

  const tabs = [
    { key: 'sales', label: 'Продажби', icon: '💰' },
    { key: 'stock', label: 'Склад', icon: '📦' },
    { key: 'staff', label: 'Персонал', icon: '👥' },
    { key: 'customers', label: 'Клиенти', icon: '🧑‍🤝‍🧑' }
  ];

  const periods = [
    { value: 'day', label: 'Днес' },
    { value: 'week', label: 'Седмица' },
    { value: 'month', label: 'Месец' },
    { value: 'quarter', label: 'Тримесечие' },
    { value: 'year', label: 'Година' },
    { value: 'custom', label: 'По избор' }
  ];

  const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'));

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">📊 Отчети</h1>
              <p className="text-gray-600 mt-1">Анализ на продажби, склад и персонал</p>
            </div>
            <Link
              href="/reports/comprehensive"
              className="px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white font-bold rounded-xl hover:from-orange-600 hover:to-red-600 transition-all shadow-lg"
            >
              🚀 Comprehensive Reports (NEW)
            </Link>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map(tab => (
            <motion.button
              key={tab.key}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveTab(tab.key as typeof activeTab)}
              className={`px-5 py-3 rounded-xl font-medium flex items-center gap-2 whitespace-nowrap ${
                activeTab === tab.key
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </motion.button>
          ))}
        </div>

        {/* Period selector (not for stock) */}
        {activeTab !== 'stock' && (
          <div className="mb-6 space-y-4">
            <div className="flex flex-wrap gap-2">
              {periods.map(p => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`px-4 py-2 rounded-lg ${
                    period === p.value
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Custom date/time range picker */}
            {period === 'custom' && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-blue-50 p-4 rounded-xl border border-blue-200"
              >
                <h4 className="font-medium text-gray-900 mb-3">Персонализиран период</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Date From */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">От дата
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    </label>
                  </div>
                  {/* Date To */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">До дата
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    </label>
                  </div>
                  {/* Hour From */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">От час
                    <select
                      value={hourFrom}
                      onChange={(e) => setHourFrom(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {hours.map(h => (
                        <option key={h} value={h}>{h}:00</option>
                      ))}
                    </select>
                    </label>
                  </div>
                  {/* Hour To */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">До час
                    <select
                      value={hourTo}
                      onChange={(e) => setHourTo(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {hours.map(h => (
                        <option key={h} value={h}>{h}:59</option>
                      ))}
                    </select>
                    </label>
                  </div>
                </div>
                <p className="mt-3 text-sm text-gray-500">
                  Показване на данни от {dateFrom} {hourFrom}:00 до {dateTo} {hourTo}:59
                </p>
              </motion.div>
            )}
          </div>
        )}

        {/* Stock filter */}
        {activeTab === 'stock' && (
          <div className="mb-6">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={lowStockOnly}
                onChange={(e) => setLowStockOnly(e.target.checked)}
                className="w-5 h-5 rounded"
              />
              <span className="text-gray-900">Показване само на ниска наличност</span>
            </label>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
              <p className="text-gray-600">Зареждане...</p>
            </div>
          </div>
        )}

        {/* Sales Report */}
        {activeTab === 'sales' && salesReport && !loading && (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-green-500/20 to-green-600/10 p-6 rounded-2xl border border-green-500/20"
              >
                <div className="text-green-400 text-sm font-medium">Общо приходи</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {formatCurrency(salesReport.total_revenue)}
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 p-6 rounded-2xl border border-blue-500/20"
              >
                <div className="text-blue-400 text-sm font-medium">Общо поръчки</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {salesReport.total_orders}
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 p-6 rounded-2xl border border-purple-500/20"
              >
                <div className="text-purple-400 text-sm font-medium">Средна стойност</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {formatCurrency(salesReport.average_order_value)}
                </div>
              </motion.div>
            </div>

            {/* Top items */}
            {salesReport.top_items.length > 0 && (
              <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
                <h3 className="text-xl font-bold text-gray-900 mb-4">🏆 Най-продавани продукти</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 text-gray-600 font-medium">#</th>
                        <th className="text-left py-3 text-gray-600 font-medium">Продукт</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Количество</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Приходи</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesReport.top_items.map((item, idx) => (
                        <tr key={idx} className="border-b border-white/5">
                          <td className="py-3 text-gray-500">{idx + 1}</td>
                          <td className="py-3 text-gray-900">{item.item_name}</td>
                          <td className="text-right py-3 text-gray-900">{item.quantity_sold}</td>
                          <td className="text-right py-3 text-green-400">{formatCurrency(item.total_revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Category breakdown */}
            {salesReport.category_breakdown.length > 0 && (
              <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
                <h3 className="text-xl font-bold text-gray-900 mb-4">📂 Продажби по категории</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 text-gray-600 font-medium">Категория</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Поръчки</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Приходи</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesReport.category_breakdown.map((cat, idx) => (
                        <tr key={idx} className="border-b border-white/5">
                          <td className="py-3 text-gray-900">{cat.category_name}</td>
                          <td className="text-right py-3 text-gray-900">{cat.total_orders}</td>
                          <td className="text-right py-3 text-green-400">{formatCurrency(cat.total_revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Daily breakdown */}
            {salesReport.daily_breakdown.length > 0 && (
              <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
                <h3 className="text-xl font-bold text-gray-900 mb-4">📅 Дневен отчет</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 text-gray-600 font-medium">Дата</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Поръчки</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Приходи</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Средна стойност</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesReport.daily_breakdown.map((day, idx) => (
                        <tr key={idx} className="border-b border-white/5">
                          <td className="py-3 text-gray-900">{formatDate(day.date)}</td>
                          <td className="text-right py-3 text-gray-900">{day.total_orders}</td>
                          <td className="text-right py-3 text-green-400">{formatCurrency(day.total_revenue)}</td>
                          <td className="text-right py-3 text-purple-400">{formatCurrency(day.average_order_value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {salesReport.total_orders === 0 && (
              <div className="text-center py-12 bg-gray-50 rounded-2xl border border-gray-200">
                <div className="text-4xl mb-4">📭</div>
                <p className="text-gray-600">Няма данни за избрания период</p>
              </div>
            )}
          </div>
        )}

        {/* Stock Report */}
        {activeTab === 'stock' && !loading && (
          <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
            <h3 className="text-xl font-bold text-gray-900 mb-4">📦 Наличности в склада</h3>
            {stockReport.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">📭</div>
                <p className="text-gray-600">Няма данни за склада</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 text-gray-600 font-medium">Продукт</th>
                      <th className="text-right py-3 text-gray-600 font-medium">Наличност</th>
                      <th className="text-right py-3 text-gray-600 font-medium">Мин. ниво</th>
                      <th className="text-right py-3 text-gray-600 font-medium">Стойност</th>
                      <th className="text-center py-3 text-gray-600 font-medium">Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stockReport.map((item) => (
                      <tr key={item.item_id} className="border-b border-white/5">
                        <td className="py-3 text-gray-900">{item.item_name}</td>
                        <td className="text-right py-3 text-gray-900">
                          {item.current_quantity} {item.unit}
                        </td>
                        <td className="text-right py-3 text-gray-600">
                          {item.min_stock} {item.unit}
                        </td>
                        <td className="text-right py-3 text-green-400">{formatCurrency(item.total_value)}</td>
                        <td className="text-center py-3">
                          {item.reorder_needed ? (
                            <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm">
                              Поръчай!
                            </span>
                          ) : (
                            <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                              OK
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Staff Report */}
        {activeTab === 'staff' && !loading && (
          <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
            <h3 className="text-xl font-bold text-gray-900 mb-4">👥 Представяне на персонала</h3>
            {staffReport.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">📭</div>
                <p className="text-gray-600">Няма данни за периода</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 text-gray-600 font-medium">#</th>
                      <th className="text-left py-3 text-gray-600 font-medium">Служител</th>
                      <th className="text-right py-3 text-gray-600 font-medium">Поръчки</th>
                      <th className="text-right py-3 text-gray-600 font-medium">Приходи</th>
                      <th className="text-right py-3 text-gray-600 font-medium">Средна стойност</th>
                    </tr>
                  </thead>
                  <tbody>
                    {staffReport.map((staff, idx) => (
                      <tr key={staff.staff_id} className="border-b border-white/5">
                        <td className="py-3 text-gray-500">{idx + 1}</td>
                        <td className="py-3 text-gray-900">{staff.staff_name}</td>
                        <td className="text-right py-3 text-gray-900">{staff.total_orders}</td>
                        <td className="text-right py-3 text-green-400">{formatCurrency(staff.total_revenue)}</td>
                        <td className="text-right py-3 text-purple-400">{formatCurrency(staff.average_order_value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Customer Report */}
        {activeTab === 'customers' && customerReport && !loading && (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 p-6 rounded-2xl border border-blue-500/20"
              >
                <div className="text-blue-400 text-sm font-medium">Общо клиенти</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {customerReport.total_customers}
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gradient-to-br from-green-500/20 to-green-600/10 p-6 rounded-2xl border border-green-500/20"
              >
                <div className="text-green-400 text-sm font-medium">Нови клиенти</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {customerReport.new_customers}
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 p-6 rounded-2xl border border-purple-500/20"
              >
                <div className="text-purple-400 text-sm font-medium">Връщащи се</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {customerReport.returning_customers}
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-gradient-to-br from-orange-500/20 to-orange-600/10 p-6 rounded-2xl border border-orange-500/20"
              >
                <div className="text-orange-400 text-sm font-medium">Средно харчене</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {formatCurrency(customerReport.average_spending)}
                </div>
              </motion.div>
            </div>

            {/* Top customers */}
            {customerReport.top_customers.length > 0 && (
              <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200">
                <h3 className="text-xl font-bold text-gray-900 mb-4">🌟 Топ клиенти</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 text-gray-600 font-medium">#</th>
                        <th className="text-left py-3 text-gray-600 font-medium">Име</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Поръчки</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Общо похарчено</th>
                        <th className="text-right py-3 text-gray-600 font-medium">Точки лоялност</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customerReport.top_customers.map((customer, idx) => (
                        <tr key={customer.id} className="border-b border-white/5">
                          <td className="py-3 text-gray-500">{idx + 1}</td>
                          <td className="py-3 text-gray-900">{customer.name}</td>
                          <td className="text-right py-3 text-gray-900">{customer.total_orders}</td>
                          <td className="text-right py-3 text-green-400">{formatCurrency(customer.total_spent || 0)}</td>
                          <td className="text-right py-3 text-yellow-400">{customer.loyalty_points || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {customerReport.total_customers === 0 && (
              <div className="text-center py-12 bg-gray-50 rounded-2xl border border-gray-200">
                <div className="text-4xl mb-4">📭</div>
                <p className="text-gray-600">Няма данни за клиенти</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'customers' && !customerReport && !loading && (
          <div className="text-center py-12 bg-gray-50 rounded-2xl border border-gray-200">
            <div className="text-4xl mb-4">📭</div>
            <p className="text-gray-600">Няма данни за клиенти</p>
          </div>
        )}
      </div>
    </div>
  );
}
