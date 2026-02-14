'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button, Card, CardBody } from '@/components/ui';

import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface PreviewEntry {
  document_number: string;
  document_date: string;
  description: string;
  net_amount: number;
  vat_amount: number;
  gross_amount: number;
}

interface PreviewData {
  period: {
    start_date: string;
    end_date: string;
  };
  summary: {
    total_documents: number;
    total_net: number;
    total_vat: number;
    total_gross: number;
  };
  preview_entries: PreviewEntry[];
  showing: number;
}

export default function AccountingExportPage() {
  const [loading, setLoading] = useState(false);
  const [exportType, setExportType] = useState<'sales' | 'purchases' | 'vat'>('sales');
  const [format, setFormat] = useState('csv');
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(1); // First of month
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [vatMonth, setVatMonth] = useState(() => new Date().getMonth() + 1);
  const [vatYear, setVatYear] = useState(() => new Date().getFullYear());

  useEffect(() => {
    const loadPreview = async () => {
      if (exportType === 'vat') return;

      setLoading(true);
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(
          `${API_URL}/accounting-export/sales-journal/preview?start_date=${startDate}&end_date=${endDate}&limit=5`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (response.ok) {
          const data = await response.json();
          setPreview(data);
        }
      } catch (err) {
        console.error('Error loading preview:', err);
      } finally {
        setLoading(false);
      }
    };
    loadPreview();
  }, [startDate, endDate, exportType]);

  const handleExport = async () => {
    const token = localStorage.getItem('access_token');

    let url = '';
    if (exportType === 'sales') {
      url = `${API_URL}/accounting-export/sales-journal?start_date=${startDate}&end_date=${endDate}&format=${format}`;
    } else if (exportType === 'purchases') {
      url = `${API_URL}/accounting-export/purchase-journal?start_date=${startDate}&end_date=${endDate}&format=${format}`;
    } else if (exportType === 'vat') {
      url = `${API_URL}/accounting-export/vat-declaration?month=${vatMonth}&year=${vatYear}`;
    }

    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        if (exportType === 'vat') {
          // VAT declaration returns JSON
          const data = await response.json();
          const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
          const downloadUrl = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.download = `vat_declaration_${vatMonth}_${vatYear}.json`;
          link.click();
        } else {
          // Download file
          const blob = await response.blob();
          const downloadUrl = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = downloadUrl;

          const contentDisposition = response.headers.get('Content-Disposition');
          const filename = contentDisposition
            ? contentDisposition.split('filename=')[1]
            : `export.${format}`;
          link.download = filename;
          link.click();
        }
      }
    } catch (err) {
      console.error('Error exporting:', err);
      toast.error('Грешка при експортиране / Export error');
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(value);
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
              Счетоводен експорт / Accounting Export
            </h1>
            <p className="text-surface-500 mt-1">
              Експорт за AtomS3 и други счетоводни програми
            </p>
          </div>
        </div>
      </div>

      {/* Export Type Selection */}
      <Card>
        <CardBody>
          <h2 className="text-lg font-semibold text-surface-900 mb-4">
            Тип експорт / Export Type
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setExportType('sales')}
              className={`cursor-pointer rounded-xl border-2 p-4 transition-all ${
                exportType === 'sales'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-surface-200 hover:border-surface-300'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  exportType === 'sales' ? 'bg-primary-500 text-white' : 'bg-surface-100 text-surface-500'
                }`}>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-surface-900">Дневник продажби</h3>
              </div>
              <p className="text-sm text-surface-500">Sales Journal</p>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setExportType('purchases')}
              className={`cursor-pointer rounded-xl border-2 p-4 transition-all ${
                exportType === 'purchases'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-surface-200 hover:border-surface-300'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  exportType === 'purchases' ? 'bg-primary-500 text-white' : 'bg-surface-100 text-surface-500'
                }`}>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-surface-900">Дневник покупки</h3>
              </div>
              <p className="text-sm text-surface-500">Purchase Journal</p>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setExportType('vat')}
              className={`cursor-pointer rounded-xl border-2 p-4 transition-all ${
                exportType === 'vat'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-surface-200 hover:border-surface-300'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  exportType === 'vat' ? 'bg-primary-500 text-white' : 'bg-surface-100 text-surface-500'
                }`}>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-surface-900">ДДС декларация</h3>
              </div>
              <p className="text-sm text-surface-500">VAT Declaration Data</p>
            </motion.div>
          </div>
        </CardBody>
      </Card>

      {/* Date Selection */}
      <Card>
        <CardBody>
          <h2 className="text-lg font-semibold text-surface-900 mb-4">
            {exportType === 'vat' ? 'Период / Period' : 'Период и формат / Period & Format'}
          </h2>

          {exportType === 'vat' ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">
                  Месец / Month
                </label>
                <select
                  value={vatMonth}
                  onChange={(e) => setVatMonth(parseInt(e.target.value))}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900"
                >
                  {[...Array(12)].map((_, i) => (
                    <option key={i + 1} value={i + 1}>
                      {new Date(2000, i).toLocaleString('bg-BG', { month: 'long' })}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">
                  Година / Year
                </label>
                <select
                  value={vatYear}
                  onChange={(e) => setVatYear(parseInt(e.target.value))}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900"
                >
                  {[2024, 2025, 2026].map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">
                  От дата / Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">
                  До дата / End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-600 mb-2">
                  Формат / Format
                </label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-surface-200 bg-white text-surface-900"
                >
                  <option value="csv">CSV (AtomS3)</option>
                  <option value="xml">XML</option>
                  <option value="json">JSON</option>
                </select>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Preview */}
      {preview && exportType !== 'vat' && (
        <Card>
          <CardBody>
            <h2 className="text-lg font-semibold text-surface-900 mb-4">
              Преглед / Preview
            </h2>

            {/* Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-surface-50 rounded-lg p-4 text-center">
                <p className="text-sm text-surface-500">Документи</p>
                <p className="text-2xl font-bold text-surface-900">{preview.summary.total_documents}</p>
              </div>
              <div className="bg-surface-50 rounded-lg p-4 text-center">
                <p className="text-sm text-surface-500">Нето / Net</p>
                <p className="text-2xl font-bold text-blue-600">{formatCurrency(preview.summary.total_net)}</p>
              </div>
              <div className="bg-surface-50 rounded-lg p-4 text-center">
                <p className="text-sm text-surface-500">ДДС / VAT</p>
                <p className="text-2xl font-bold text-amber-600">{formatCurrency(preview.summary.total_vat)}</p>
              </div>
              <div className="bg-surface-50 rounded-lg p-4 text-center">
                <p className="text-sm text-surface-500">Бруто / Gross</p>
                <p className="text-2xl font-bold text-green-600">{formatCurrency(preview.summary.total_gross)}</p>
              </div>
            </div>

            {/* Preview Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-200 bg-surface-50">
                    <th className="text-left py-2 px-3 font-semibold">№ Документ</th>
                    <th className="text-left py-2 px-3 font-semibold">Дата</th>
                    <th className="text-left py-2 px-3 font-semibold">Описание</th>
                    <th className="text-right py-2 px-3 font-semibold">Нето</th>
                    <th className="text-right py-2 px-3 font-semibold">ДДС</th>
                    <th className="text-right py-2 px-3 font-semibold">Бруто</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.preview_entries.map((entry, idx) => (
                    <tr key={idx} className="border-b border-surface-100">
                      <td className="py-2 px-3 font-mono text-xs">{entry.document_number}</td>
                      <td className="py-2 px-3">{entry.document_date}</td>
                      <td className="py-2 px-3">{entry.description}</td>
                      <td className="text-right py-2 px-3">{formatCurrency(entry.net_amount)}</td>
                      <td className="text-right py-2 px-3">{formatCurrency(entry.vat_amount)}</td>
                      <td className="text-right py-2 px-3 font-medium">{formatCurrency(entry.gross_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {preview.summary.total_documents > preview.showing && (
              <p className="text-sm text-surface-500 mt-3 text-center">
                Показани {preview.showing} от {preview.summary.total_documents} записа
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {/* Export Button */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-surface-900">
                {exportType === 'sales' && 'Експорт дневник продажби'}
                {exportType === 'purchases' && 'Експорт дневник покупки'}
                {exportType === 'vat' && 'Експорт ДДС данни'}
              </h3>
              <p className="text-sm text-surface-500">
                {exportType === 'vat'
                  ? `Период: ${vatMonth.toString().padStart(2, '0')}.${vatYear}`
                  : `Период: ${startDate} - ${endDate}`}
              </p>
            </div>
            <Button onClick={handleExport} size="lg">
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Изтегли / Download
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Info */}
      <Card>
        <CardBody>
          <h3 className="font-semibold text-surface-900 mb-3">
            Информация за AtomS3 формат
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="bg-surface-50 rounded-lg p-4">
              <h4 className="font-medium text-surface-900 mb-2">CSV формат</h4>
              <ul className="space-y-1 text-surface-600">
                <li>• Разделител: точка и запетая (;)</li>
                <li>• Кодировка: UTF-8</li>
                <li>• Дати: ДД.ММ.ГГГГ</li>
                <li>• Числа: 2 десетични знака</li>
              </ul>
            </div>
            <div className="bg-surface-50 rounded-lg p-4">
              <h4 className="font-medium text-surface-900 mb-2">Съвместимост</h4>
              <ul className="space-y-1 text-surface-600">
                <li>• AtomS3 (Microinvest)</li>
                <li>• Бизнес Навигатор</li>
                <li>• Ajur</li>
                <li>• Microsoft Excel</li>
              </ul>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
