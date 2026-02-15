'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button, Card, CardBody } from '@/components/ui';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface CategoryData {
  category: string;
  actual_revenue: number;
  base_revenue: number;
  markup_amount: number;
  gross_margin_percentage: number;
  items_sold: number;
}

interface ItemData {
  name: string;
  actual_revenue: number;
  base_revenue: number;
  markup_amount: number;
  gross_margin_percentage: number;
  quantity_sold: number;
}

interface ReportData {
  period: {
    start_date: string;
    end_date: string;
  };
  summary: {
    actual_revenue: number;
    base_revenue: number;
    markup_amount: number;
    markup_percentage: number;
    gross_margin_percentage: number;
    total_items_sold: number;
    total_checks: number;
  };
  by_category: CategoryData[];
  by_item: ItemData[];
  generated_at: string;
}

export default function TurnoverBasePricesPage() {
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<ReportData | null>(null);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [viewMode, setViewMode] = useState<'category' | 'item'>('category');

  const loadReport = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      let url = `${API_URL}/reports/turnover-base-prices?start_date=${startDate}&end_date=${endDate}`;
      if (selectedCategory) {
        url += `&category=${encodeURIComponent(selectedCategory)}`;
      }

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setReport(data);
      }
    } catch (err) {
      console.error('Error loading report:', err);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, selectedCategory]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${(value ?? 0).toFixed(1)}%`;
  };

  const getMarginColor = (margin: number) => {
    if (margin >= 70) return 'text-green-600';
    if (margin >= 60) return 'text-blue-600';
    if (margin >= 50) return 'text-amber-600';
    return 'text-red-600';
  };

  const exportReport = () => {
    if (!report) return;

    const headers = ['Категория', 'Реална приходи', 'Базова цена', 'Марж', 'Марж %', 'Продадени'];
    const rows = report.by_category.map((c) => [
      c.category,
      (c.actual_revenue ?? 0).toFixed(2),
      (c.base_revenue ?? 0).toFixed(2),
      (c.markup_amount ?? 0).toFixed(2),
      (c.gross_margin_percentage ?? 0).toFixed(1),
      c.items_sold,
    ]);

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `turnover-base-prices-${startDate}-${endDate}.csv`;
    link.click();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/reports" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
            <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-display font-bold text-surface-900">
              Оборот по базови цени / Turnover at Base Prices
            </h1>
            <p className="text-surface-500 mt-1">
              Сравнение на приходите по продажна и базова цена
            </p>
          </div>
        </div>
        <Button onClick={exportReport} variant="secondary">
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Експорт CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardBody>
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-600 mb-1">
                От дата / Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-4 py-2 rounded-xl border border-surface-200 bg-white text-surface-900"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-600 mb-1">
                До дата / End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-4 py-2 rounded-xl border border-surface-200 bg-white text-surface-900"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-600 mb-1">
                Изглед / View
              </label>
              <div className="flex rounded-xl border border-surface-200 overflow-hidden">
                <button
                  onClick={() => setViewMode('category')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    viewMode === 'category'
                      ? 'bg-primary-500 text-white'
                      : 'bg-white text-surface-600 hover:bg-surface-50'
                  }`}
                >
                  По категории
                </button>
                <button
                  onClick={() => setViewMode('item')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    viewMode === 'item'
                      ? 'bg-primary-500 text-white'
                      : 'bg-white text-surface-600 hover:bg-surface-50'
                  }`}
                >
                  По артикули
                </button>
              </div>
            </div>
            <div className="flex items-end">
              <Button onClick={loadReport}>
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Обнови
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        </div>
      ) : report ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Реални приходи</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {formatCurrency(report.summary.actual_revenue)}
                  </p>
                  <p className="text-xs text-surface-400">Actual Revenue</p>
                </CardBody>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Базова стойност</p>
                  <p className="text-2xl font-bold text-amber-600">
                    {formatCurrency(report.summary.base_revenue)}
                  </p>
                  <p className="text-xs text-surface-400">Base/Cost Value</p>
                </CardBody>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Надценка / Markup</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(report.summary.markup_amount)}
                  </p>
                  <p className="text-xs text-surface-400">
                    {formatPercentage(report.summary.markup_percentage)} надценка
                  </p>
                </CardBody>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Брутен марж</p>
                  <p className={`text-2xl font-bold ${getMarginColor(report.summary.gross_margin_percentage)}`}>
                    {formatPercentage(report.summary.gross_margin_percentage)}
                  </p>
                  <p className="text-xs text-surface-400">Gross Margin</p>
                </CardBody>
              </Card>
            </motion.div>
          </div>

          {/* Visual Breakdown */}
          <Card>
            <CardBody>
              <h2 className="text-lg font-semibold text-surface-900 mb-4">
                Разпределение на приходите / Revenue Breakdown
              </h2>
              <div className="h-8 rounded-full overflow-hidden bg-surface-100 flex">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(report.summary.base_revenue / report.summary.actual_revenue) * 100}%` }}
                  transition={{ duration: 0.5 }}
                  className="bg-amber-500 h-full"
                  title={`Базова цена: ${formatCurrency(report.summary.base_revenue)}`}
                />
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(report.summary.markup_amount / report.summary.actual_revenue) * 100}%` }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  className="bg-green-500 h-full"
                  title={`Надценка: ${formatCurrency(report.summary.markup_amount)}`}
                />
              </div>
              <div className="flex justify-between mt-2 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                  <span className="text-surface-600">Базова цена / Cost ({formatPercentage(100 - report.summary.gross_margin_percentage)})</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-surface-600">Надценка / Markup ({formatPercentage(report.summary.gross_margin_percentage)})</span>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Data Table */}
          <Card>
            <CardBody>
              <h2 className="text-lg font-semibold text-surface-900 mb-4">
                {viewMode === 'category' ? 'По категории / By Category' : 'По артикули / By Item'}
              </h2>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-surface-200 bg-surface-50">
                      <th className="text-left py-3 px-4 text-sm font-semibold text-surface-900">
                        {viewMode === 'category' ? 'Категория' : 'Артикул'}
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Реални приходи
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Базова цена
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Надценка
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Марж %
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Брой
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {(viewMode === 'category' ? report.by_category : report.by_item).map((item, index) => (
                      <motion.tr
                        key={viewMode === 'category' ? (item as CategoryData).category : (item as ItemData).name}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="border-b border-surface-100 hover:bg-surface-50 transition-colors"
                      >
                        <td className="py-3 px-4 font-medium text-surface-900">
                          {viewMode === 'category' ? (item as CategoryData).category : (item as ItemData).name}
                        </td>
                        <td className="text-right py-3 px-4 text-blue-600 font-medium">
                          {formatCurrency(item.actual_revenue)}
                        </td>
                        <td className="text-right py-3 px-4 text-amber-600">
                          {formatCurrency(item.base_revenue)}
                        </td>
                        <td className="text-right py-3 px-4 text-green-600 font-medium">
                          {formatCurrency(item.markup_amount)}
                        </td>
                        <td className="text-right py-3 px-4">
                          <span className={`font-bold ${getMarginColor(item.gross_margin_percentage)}`}>
                            {formatPercentage(item.gross_margin_percentage)}
                          </span>
                        </td>
                        <td className="text-right py-3 px-4 text-surface-600">
                          {viewMode === 'category' ? (item as CategoryData).items_sold : (item as ItemData).quantity_sold}
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-surface-100 font-semibold">
                      <td className="py-3 px-4 text-surface-900">ОБЩО / TOTAL</td>
                      <td className="text-right py-3 px-4 text-blue-600">
                        {formatCurrency(report.summary.actual_revenue)}
                      </td>
                      <td className="text-right py-3 px-4 text-amber-600">
                        {formatCurrency(report.summary.base_revenue)}
                      </td>
                      <td className="text-right py-3 px-4 text-green-600">
                        {formatCurrency(report.summary.markup_amount)}
                      </td>
                      <td className="text-right py-3 px-4">
                        <span className={`font-bold ${getMarginColor(report.summary.gross_margin_percentage)}`}>
                          {formatPercentage(report.summary.gross_margin_percentage)}
                        </span>
                      </td>
                      <td className="text-right py-3 px-4 text-surface-600">
                        {report.summary.total_items_sold}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardBody>
          </Card>

          {/* Info Card */}
          <Card>
            <CardBody>
              <h3 className="text-sm font-semibold text-surface-900 mb-3">
                Обяснение / Explanation
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="bg-surface-50 rounded-lg p-4">
                  <h4 className="font-medium text-surface-900 mb-2">Формули / Formulas</h4>
                  <ul className="space-y-1 text-surface-600">
                    <li><strong>Надценка %:</strong> (Надценка / Базова цена) × 100</li>
                    <li><strong>Брутен марж %:</strong> (Надценка / Реални приходи) × 100</li>
                  </ul>
                </div>
                <div className="bg-surface-50 rounded-lg p-4">
                  <h4 className="font-medium text-surface-900 mb-2">Интерпретация / Interpretation</h4>
                  <ul className="space-y-1 text-surface-600">
                    <li><span className="text-green-600">≥70%</span> - Отличен марж</li>
                    <li><span className="text-blue-600">60-70%</span> - Добър марж</li>
                    <li><span className="text-amber-600">50-60%</span> - Приемлив марж</li>
                    <li><span className="text-red-600">&lt;50%</span> - Нисък марж</li>
                  </ul>
                </div>
              </div>
            </CardBody>
          </Card>
        </>
      ) : (
        <Card>
          <CardBody className="text-center py-12">
            <p className="text-surface-500">Няма данни за избрания период</p>
            <p className="text-surface-400 text-sm">No data for selected period</p>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
