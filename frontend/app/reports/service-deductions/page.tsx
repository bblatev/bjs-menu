'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button, Card, CardBody } from '@/components/ui';

import { api } from '@/lib/api';

interface StaffReport {
  staff_id: number;
  staff_name: string;
  role: string;
  hours_worked: number;
  hourly_rate: number;
  base_pay: number;
  gross_sales: number;
  commission_percentage: number;
  commission_earned: number;
  tips_received: number;
  service_fee_percentage: number;
  service_fee_deducted: number;
  net_earnings: number;
}

interface ReportSummary {
  total_staff: number;
  total_gross_sales: number;
  total_commission_paid: number;
  total_service_fees_collected: number;
  total_net_earnings: number;
}

interface ReportData {
  period: {
    start_date: string;
    end_date: string;
  };
  summary: ReportSummary;
  staff_reports: StaffReport[];
}

export default function ServiceDeductionsPage() {
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<ReportData | null>(null);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [selectedStaff] = useState<number | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    try {
      let url = `/staff/reports/service-deductions?start_date=${startDate}&end_date=${endDate}`;
      if (selectedStaff) {
        url += `&staff_id=${selectedStaff}`;
      }

      const data = await api.get<ReportData>(url);
      setReport(data);
    } catch (err) {
      console.error('Error loading report:', err);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, selectedStaff]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(value);
  };

  const getRoleBadge = (role: string) => {
    const colors: Record<string, string> = {
      admin: 'bg-purple-100 text-purple-700',
      manager: 'bg-blue-100 text-blue-700',
      waiter: 'bg-green-100 text-green-700',
      bar: 'bg-amber-100 text-amber-700',
      kitchen: 'bg-red-100 text-red-700',
    };
    return colors[role] || 'bg-gray-100 text-gray-700';
  };

  const exportReport = () => {
    if (!report) return;

    const headers = [
      'Служител',
      'Роля',
      'Часове',
      'Ставка/час',
      'Основна заплата',
      'Продажби',
      'Комисионна %',
      'Комисионна',
      'Бакшиши',
      'Такса обслужване %',
      'Такса обслужване',
      'Нетна печалба',
    ];

    const rows = report.staff_reports.map((s) => [
      s.staff_name,
      s.role,
      s.hours_worked,
      s.hourly_rate,
      s.base_pay,
      s.gross_sales,
      s.commission_percentage,
      s.commission_earned,
      s.tips_received,
      s.service_fee_percentage,
      s.service_fee_deducted,
      s.net_earnings,
    ]);

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `service-deductions-${startDate}-${endDate}.csv`;
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
              Отчет за удръжки / Service Deductions
            </h1>
            <p className="text-surface-500 mt-1">
              Комисионни, такси за обслужване и нетни приходи на персонала
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

      {/* Date Filters */}
      <Card>
        <CardBody>
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-600 mb-1">
                От дата / Start Date
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-4 py-2 rounded-xl border border-surface-200 bg-white text-surface-900"
              />
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-600 mb-1">
                До дата / End Date
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-4 py-2 rounded-xl border border-surface-200 bg-white text-surface-900"
              />
              </label>
            </div>
            <div className="flex items-end">
              <Button onClick={loadReport}>
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Обнови / Refresh
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
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Персонал</p>
                  <p className="text-2xl font-bold text-surface-900">{report.summary.total_staff}</p>
                  <p className="text-xs text-surface-400">служители</p>
                </CardBody>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Общи продажби</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {formatCurrency(report.summary.total_gross_sales)}
                  </p>
                  <p className="text-xs text-surface-400">gross sales</p>
                </CardBody>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Изплатени комисионни</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(report.summary.total_commission_paid)}
                  </p>
                  <p className="text-xs text-surface-400">commission paid</p>
                </CardBody>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Такси за обслужване</p>
                  <p className="text-2xl font-bold text-amber-600">
                    {formatCurrency(report.summary.total_service_fees_collected)}
                  </p>
                  <p className="text-xs text-surface-400">service fees</p>
                </CardBody>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card>
                <CardBody className="text-center">
                  <p className="text-sm text-surface-500 mb-1">Нетни приходи</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {formatCurrency(report.summary.total_net_earnings)}
                  </p>
                  <p className="text-xs text-surface-400">net earnings</p>
                </CardBody>
              </Card>
            </motion.div>
          </div>

          {/* Staff Reports Table */}
          <Card>
            <CardBody>
              <h2 className="text-lg font-semibold text-surface-900 mb-4">
                Детайлен отчет по служители / Staff Details
              </h2>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-surface-200 bg-surface-50">
                      <th className="text-left py-3 px-4 text-sm font-semibold text-surface-900">
                        Служител
                      </th>
                      <th className="text-center py-3 px-4 text-sm font-semibold text-surface-900">
                        Роля
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Часове
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Основна заплата
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Продажби
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Комисионна
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Бакшиши
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Такса обсл.
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-semibold text-surface-900">
                        Нето
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.staff_reports.map((staff, index) => (
                      <motion.tr
                        key={staff.staff_id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="border-b border-surface-100 hover:bg-surface-50 transition-colors"
                      >
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-medium text-sm">
                              {staff.staff_name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                            </div>
                            <span className="font-medium text-surface-900">{staff.staff_name}</span>
                          </div>
                        </td>
                        <td className="text-center py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadge(staff.role)}`}>
                            {staff.role}
                          </span>
                        </td>
                        <td className="text-right py-3 px-4 text-surface-600">
                          {staff.hours_worked}h
                        </td>
                        <td className="text-right py-3 px-4 text-surface-900">
                          {formatCurrency(staff.base_pay)}
                        </td>
                        <td className="text-right py-3 px-4 text-blue-600 font-medium">
                          {formatCurrency(staff.gross_sales)}
                        </td>
                        <td className="text-right py-3 px-4">
                          <div className="text-green-600 font-medium">
                            {formatCurrency(staff.commission_earned)}
                          </div>
                          <div className="text-xs text-surface-400">
                            {staff.commission_percentage}%
                          </div>
                        </td>
                        <td className="text-right py-3 px-4 text-amber-600">
                          {formatCurrency(staff.tips_received)}
                        </td>
                        <td className="text-right py-3 px-4">
                          <div className="text-red-600 font-medium">
                            -{formatCurrency(staff.service_fee_deducted)}
                          </div>
                          <div className="text-xs text-surface-400">
                            {staff.service_fee_percentage}%
                          </div>
                        </td>
                        <td className="text-right py-3 px-4">
                          <span className="text-lg font-bold text-purple-600">
                            {formatCurrency(staff.net_earnings)}
                          </span>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-surface-100 font-semibold">
                      <td colSpan={3} className="py-3 px-4 text-surface-900">
                        ОБЩО / TOTAL
                      </td>
                      <td className="text-right py-3 px-4 text-surface-900">
                        {formatCurrency(report.staff_reports.reduce((sum, s) => sum + s.base_pay, 0))}
                      </td>
                      <td className="text-right py-3 px-4 text-blue-600">
                        {formatCurrency(report.summary.total_gross_sales)}
                      </td>
                      <td className="text-right py-3 px-4 text-green-600">
                        {formatCurrency(report.summary.total_commission_paid)}
                      </td>
                      <td className="text-right py-3 px-4 text-amber-600">
                        {formatCurrency(report.staff_reports.reduce((sum, s) => sum + s.tips_received, 0))}
                      </td>
                      <td className="text-right py-3 px-4 text-red-600">
                        -{formatCurrency(report.summary.total_service_fees_collected)}
                      </td>
                      <td className="text-right py-3 px-4 text-purple-600">
                        {formatCurrency(report.summary.total_net_earnings)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardBody>
          </Card>

          {/* Explanation Card */}
          <Card>
            <CardBody>
              <h3 className="text-sm font-semibold text-surface-900 mb-3">
                Формула за изчисление / Calculation Formula
              </h3>
              <div className="bg-surface-50 rounded-lg p-4 font-mono text-sm">
                <p className="text-surface-700">
                  <span className="text-purple-600 font-bold">Нетна печалба</span> =
                  <span className="text-blue-600"> Основна заплата</span> +
                  <span className="text-green-600"> Комисионна</span> +
                  <span className="text-amber-600"> Бакшиши</span> -
                  <span className="text-red-600"> Такса обслужване</span>
                </p>
                <p className="text-surface-500 mt-2 text-xs">
                  Net Earnings = Base Pay + Commission + Tips - Service Fee
                </p>
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
