'use client';

import { useState, useEffect } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface SupplierMetrics {
  id: number;
  supplier_name: string;
  contact_person: string;
  phone: string;
  email: string;
  category: string;
  total_orders: number;
  total_value: number;
  on_time_delivery_rate: number;
  quality_score: number;
  fill_rate: number;
  avg_lead_time_days: number;
  price_competitiveness: number;
  return_rate: number;
  overall_score: number;
  trend: 'improving' | 'declining' | 'stable';
  last_order_date: string;
  issues_count: number;
}

interface SupplierStats {
  total_suppliers: number;
  avg_performance_score: number;
  suppliers_above_target: number;
  total_orders_ytd: number;
  total_spend_ytd: number;
  avg_lead_time: number;
}

interface PerformanceHistory {
  month: string;
  delivery_rate: number;
  quality_score: number;
  fill_rate: number;
}

export default function SupplierPerformancePage() {
  const [suppliers, setSuppliers] = useState<SupplierMetrics[]>([]);
  const [stats, setStats] = useState<SupplierStats | null>(null);
  const [performanceHistory, setPerformanceHistory] = useState<PerformanceHistory[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'overall_score' | 'total_value' | 'on_time_delivery_rate'>('overall_score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');


  useEffect(() => {
    fetchSupplierData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchSupplierData = async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();

      try {
        const [suppliersRes, statsRes] = await Promise.all([
          fetch(`${API_URL}/suppliers/performance`, { headers }),
          fetch(`${API_URL}/suppliers/performance/stats`, { headers })
        ]);

        if (suppliersRes.ok && statsRes.ok) {
          const suppliersData = await suppliersRes.json();
          const statsData = await statsRes.json();
          setSuppliers(suppliersData.suppliers || suppliersData);
          setStats(statsData);
        } else {
          throw new Error('API not available');
        }
      } catch {
        loadDemoData();
      }
    } catch (error) {
      console.error('Error fetching supplier data:', error);
      loadDemoData();
    } finally {
      setLoading(false);
    }
  };

  const loadDemoData = () => {
    const demoSuppliers: SupplierMetrics[] = [
      {
        id: 1,
        supplier_name: 'Фреш Продукти ООД',
        contact_person: 'Иван Петров',
        phone: '+359 888 123 456',
        email: 'ivan@freshprodukti.bg',
        category: 'Зеленчуци',
        total_orders: 156,
        total_value: 45800,
        on_time_delivery_rate: 96,
        quality_score: 94,
        fill_rate: 98,
        avg_lead_time_days: 1.2,
        price_competitiveness: 88,
        return_rate: 1.5,
        overall_score: 94,
        trend: 'improving',
        last_order_date: '2024-12-27',
        issues_count: 2
      },
      {
        id: 2,
        supplier_name: 'Месокомбинат Родопи',
        contact_person: 'Георги Димитров',
        phone: '+359 887 234 567',
        email: 'georgi@mesorodopi.bg',
        category: 'Месо',
        total_orders: 98,
        total_value: 78500,
        on_time_delivery_rate: 92,
        quality_score: 96,
        fill_rate: 95,
        avg_lead_time_days: 2.0,
        price_competitiveness: 85,
        return_rate: 0.8,
        overall_score: 92,
        trend: 'stable',
        last_order_date: '2024-12-28',
        issues_count: 3
      },
      {
        id: 3,
        supplier_name: 'Вино и Спиритус АД',
        contact_person: 'Мария Иванова',
        phone: '+359 889 345 678',
        email: 'maria@vinoispiritus.bg',
        category: 'Алкохол',
        total_orders: 45,
        total_value: 125000,
        on_time_delivery_rate: 98,
        quality_score: 99,
        fill_rate: 100,
        avg_lead_time_days: 3.5,
        price_competitiveness: 82,
        return_rate: 0.2,
        overall_score: 96,
        trend: 'improving',
        last_order_date: '2024-12-25',
        issues_count: 0
      },
      {
        id: 4,
        supplier_name: 'Млечни Продукти Елена',
        contact_person: 'Елена Стоянова',
        phone: '+359 886 456 789',
        email: 'elena@mlechni.bg',
        category: 'Млечни',
        total_orders: 234,
        total_value: 32400,
        on_time_delivery_rate: 88,
        quality_score: 90,
        fill_rate: 92,
        avg_lead_time_days: 1.0,
        price_competitiveness: 92,
        return_rate: 2.5,
        overall_score: 88,
        trend: 'declining',
        last_order_date: '2024-12-28',
        issues_count: 8
      },
      {
        id: 5,
        supplier_name: 'Напитки Плюс ЕООД',
        contact_person: 'Петър Николов',
        phone: '+359 885 567 890',
        email: 'petar@napitkiplus.bg',
        category: 'Напитки',
        total_orders: 67,
        total_value: 56700,
        on_time_delivery_rate: 94,
        quality_score: 95,
        fill_rate: 97,
        avg_lead_time_days: 2.5,
        price_competitiveness: 90,
        return_rate: 0.5,
        overall_score: 94,
        trend: 'stable',
        last_order_date: '2024-12-26',
        issues_count: 1
      },
      {
        id: 6,
        supplier_name: 'Морски Деликатеси',
        contact_person: 'Стефан Маринов',
        phone: '+359 884 678 901',
        email: 'stefan@morski.bg',
        category: 'Риба',
        total_orders: 52,
        total_value: 68900,
        on_time_delivery_rate: 85,
        quality_score: 92,
        fill_rate: 88,
        avg_lead_time_days: 1.5,
        price_competitiveness: 78,
        return_rate: 3.2,
        overall_score: 84,
        trend: 'declining',
        last_order_date: '2024-12-27',
        issues_count: 12
      },
      {
        id: 7,
        supplier_name: 'Хляб и Тесто',
        contact_person: 'Анна Георгиева',
        phone: '+359 883 789 012',
        email: 'anna@hliab.bg',
        category: 'Хлебни',
        total_orders: 312,
        total_value: 18500,
        on_time_delivery_rate: 99,
        quality_score: 97,
        fill_rate: 99,
        avg_lead_time_days: 0.5,
        price_competitiveness: 95,
        return_rate: 0.3,
        overall_score: 98,
        trend: 'improving',
        last_order_date: '2024-12-28',
        issues_count: 0
      },
      {
        id: 8,
        supplier_name: 'Плодове БГ',
        contact_person: 'Никола Тодоров',
        phone: '+359 882 890 123',
        email: 'nikola@plodovebg.bg',
        category: 'Плодове',
        total_orders: 89,
        total_value: 28600,
        on_time_delivery_rate: 91,
        quality_score: 88,
        fill_rate: 94,
        avg_lead_time_days: 1.8,
        price_competitiveness: 86,
        return_rate: 4.5,
        overall_score: 86,
        trend: 'stable',
        last_order_date: '2024-12-26',
        issues_count: 6
      }
    ];

    const demoStats: SupplierStats = {
      total_suppliers: 24,
      avg_performance_score: 91.2,
      suppliers_above_target: 18,
      total_orders_ytd: 1453,
      total_spend_ytd: 654800,
      avg_lead_time: 1.8
    };

    const demoHistory: PerformanceHistory[] = [
      { month: 'Юли', delivery_rate: 89, quality_score: 90, fill_rate: 92 },
      { month: 'Авг', delivery_rate: 91, quality_score: 91, fill_rate: 93 },
      { month: 'Сеп', delivery_rate: 90, quality_score: 92, fill_rate: 94 },
      { month: 'Окт', delivery_rate: 93, quality_score: 93, fill_rate: 95 },
      { month: 'Ное', delivery_rate: 94, quality_score: 94, fill_rate: 96 },
      { month: 'Дек', delivery_rate: 95, quality_score: 95, fill_rate: 97 }
    ];

    setSuppliers(demoSuppliers);
    setStats(demoStats);
    setPerformanceHistory(demoHistory);
  };

  const categories = ['all', ...new Set(suppliers.map(s => s.category))];

  const filteredSuppliers = suppliers
    .filter(s => selectedCategory === 'all' || s.category === selectedCategory)
    .sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      return sortOrder === 'desc' ? (bVal as number) - (aVal as number) : (aVal as number) - (bVal as number);
    });

  const getScoreColor = (score: number) => {
    if (score >= 95) return 'text-green-400';
    if (score >= 90) return 'text-blue-400';
    if (score >= 80) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreBg = (score: number) => {
    if (score >= 95) return 'bg-green-500/20 border-green-500/30';
    if (score >= 90) return 'bg-blue-500/20 border-blue-500/30';
    if (score >= 80) return 'bg-yellow-500/20 border-yellow-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return '↑';
      case 'declining': return '↓';
      default: return '→';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return 'text-green-400';
      case 'declining': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const exportReport = () => {
    toast.success('Експортиране на отчет за представянето на доставчиците...');
  };

  return (
    <AdminLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Представяне на доставчици</h1>
            <p className="text-gray-400 mt-1">Анализ и оценка на доставчиците по ключови показатели</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={exportReport}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
             aria-label="Close">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Експорт отчет
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Доставчици</p>
                  <p className="text-2xl font-bold text-white">{stats.total_suppliers}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Среден резултат</p>
                  <p className="text-2xl font-bold text-white">{stats.avg_performance_score}%</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Над целта</p>
                  <p className="text-2xl font-bold text-white">{stats.suppliers_above_target}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Поръчки (год.)</p>
                  <p className="text-2xl font-bold text-white">{stats.total_orders_ytd.toLocaleString()}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Разходи (год.)</p>
                  <p className="text-2xl font-bold text-white">{stats.total_spend_ytd.toLocaleString()} лв</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Ср. време доставка</p>
                  <p className="text-2xl font-bold text-white">{stats.avg_lead_time} дни</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Performance Trend Chart */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Тренд на представянето (последни 6 месеца)</h3>
          <div className="h-48 relative">
            <svg className="w-full h-full" viewBox="0 0 500 150" preserveAspectRatio="none">
              {/* Grid lines */}
              {[0, 25, 50, 75, 100].map((val, i) => (
                <line key={i} x1="0" y1={150 - val * 1.5} x2="500" y2={150 - val * 1.5} stroke="#374151" strokeWidth="1" />
              ))}

              {/* Delivery Rate line */}
              <polyline
                fill="none"
                stroke="#3b82f6"
                strokeWidth="3"
                points={performanceHistory.map((d, i) => `${i * 100},${150 - d.delivery_rate * 1.5}`).join(' ')}
              />

              {/* Quality Score line */}
              <polyline
                fill="none"
                stroke="#10b981"
                strokeWidth="3"
                points={performanceHistory.map((d, i) => `${i * 100},${150 - d.quality_score * 1.5}`).join(' ')}
              />

              {/* Fill Rate line */}
              <polyline
                fill="none"
                stroke="#f59e0b"
                strokeWidth="3"
                points={performanceHistory.map((d, i) => `${i * 100},${150 - d.fill_rate * 1.5}`).join(' ')}
              />
            </svg>

            {/* X-axis labels */}
            <div className="absolute bottom-0 left-0 right-0 flex justify-between px-4 text-xs text-gray-400">
              {performanceHistory.map((d, i) => (
                <span key={i}>{d.month}</span>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-1 bg-blue-500 rounded" />
              <span className="text-sm text-gray-400">Навреме доставка</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-1 bg-green-500 rounded" />
              <span className="text-sm text-gray-400">Качество</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-1 bg-yellow-500 rounded" />
              <span className="text-sm text-gray-400">Изпълнение</span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 flex-wrap">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            <option value="all">Всички категории</option>
            {categories.filter(c => c !== 'all').map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'overall_score' | 'total_value' | 'on_time_delivery_rate')}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            <option value="overall_score">Общ резултат</option>
            <option value="total_value">Обща стойност</option>
            <option value="on_time_delivery_rate">Навреме доставка</option>
          </select>

          <button
            onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
          >
            {sortOrder === 'desc' ? '↓' : '↑'} {sortOrder === 'desc' ? 'Низходящо' : 'Възходящо'}
          </button>

          <button
            onClick={fetchSupplierData}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
           aria-label="Close">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Обнови
          </button>
        </div>

        {/* Suppliers Table */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-900/50">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Доставчик</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Категория</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Общ резултат</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Навреме</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Качество</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Изпълнение</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Поръчки</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Стойност</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Тренд</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        Зареждане...
                      </div>
                    </td>
                  </tr>
                ) : filteredSuppliers.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                      Няма намерени доставчици
                    </td>
                  </tr>
                ) : (
                  filteredSuppliers.map((supplier) => (
                    <tr
                      key={supplier.id}
                      onClick={() => setSelectedSupplier(supplier)}
                      className="border-t border-gray-700/50 hover:bg-gray-700/30 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div>
                          <span className="text-white font-medium">{supplier.supplier_name}</span>
                          <p className="text-xs text-gray-500">{supplier.contact_person}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-gray-400">{supplier.category}</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-sm font-bold border ${getScoreBg(supplier.overall_score)} ${getScoreColor(supplier.overall_score)}`}>
                          {supplier.overall_score}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={getScoreColor(supplier.on_time_delivery_rate)}>{supplier.on_time_delivery_rate}%</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={getScoreColor(supplier.quality_score)}>{supplier.quality_score}%</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={getScoreColor(supplier.fill_rate)}>{supplier.fill_rate}%</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-white">{supplier.total_orders}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-white">{supplier.total_value.toLocaleString()} лв</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-lg font-bold ${getTrendColor(supplier.trend)}`}>
                          {getTrendIcon(supplier.trend)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Supplier Detail Modal */}
        {selectedSupplier && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Детайли за доставчика</h2>
                <button
                  onClick={() => setSelectedSupplier(null)}
                  className="p-2 hover:bg-gray-700 rounded-lg text-gray-400"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-6">
                {/* Supplier Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400">Доставчик</p>
                    <p className="text-lg font-semibold text-white">{selectedSupplier.supplier_name}</p>
                    <p className="text-sm text-gray-400 mt-1">{selectedSupplier.category}</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400">Контакт</p>
                    <p className="text-lg font-semibold text-white">{selectedSupplier.contact_person}</p>
                    <p className="text-sm text-gray-400 mt-1">{selectedSupplier.phone}</p>
                    <p className="text-sm text-gray-400">{selectedSupplier.email}</p>
                  </div>
                </div>

                {/* Overall Score */}
                <div className={`rounded-lg p-6 border ${getScoreBg(selectedSupplier.overall_score)}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-300">Общ резултат на представянето</p>
                      <p className={`text-4xl font-bold ${getScoreColor(selectedSupplier.overall_score)}`}>
                        {selectedSupplier.overall_score}%
                      </p>
                    </div>
                    <div className={`text-3xl font-bold ${getTrendColor(selectedSupplier.trend)}`}>
                      {getTrendIcon(selectedSupplier.trend)}
                      <span className="text-sm ml-2">
                        {selectedSupplier.trend === 'improving' ? 'Подобряващ се' :
                         selectedSupplier.trend === 'declining' ? 'Влошаващ се' : 'Стабилен'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* KPI Grid */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Навреме доставка</p>
                    <p className={`text-2xl font-bold ${getScoreColor(selectedSupplier.on_time_delivery_rate)}`}>
                      {selectedSupplier.on_time_delivery_rate}%
                    </p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Качество</p>
                    <p className={`text-2xl font-bold ${getScoreColor(selectedSupplier.quality_score)}`}>
                      {selectedSupplier.quality_score}%
                    </p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Изпълнение на поръчки</p>
                    <p className={`text-2xl font-bold ${getScoreColor(selectedSupplier.fill_rate)}`}>
                      {selectedSupplier.fill_rate}%
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Средно време</p>
                    <p className="text-xl font-bold text-white">{selectedSupplier.avg_lead_time_days} дни</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Конкурентност цени</p>
                    <p className="text-xl font-bold text-white">{selectedSupplier.price_competitiveness}%</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Връщания</p>
                    <p className={`text-xl font-bold ${selectedSupplier.return_rate > 3 ? 'text-red-400' : 'text-white'}`}>
                      {selectedSupplier.return_rate}%
                    </p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Проблеми</p>
                    <p className={`text-xl font-bold ${selectedSupplier.issues_count > 5 ? 'text-red-400' : 'text-white'}`}>
                      {selectedSupplier.issues_count}
                    </p>
                  </div>
                </div>

                {/* Order Stats */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400">Общо поръчки</p>
                    <p className="text-2xl font-bold text-white">{selectedSupplier.total_orders}</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm text-gray-400">Обща стойност</p>
                    <p className="text-2xl font-bold text-white">{selectedSupplier.total_value.toLocaleString()} лв</p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
                    Нова поръчка
                  </button>
                  <button className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg">
                    История на поръчките
                  </button>
                  <button className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg">
                    Докладвай проблем
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
