'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface SupplierMetrics {
  delivery_reliability: number;
  price_competitiveness: number;
  quality_score: number;
  fill_rate: number;
  communication: number;
  payment_terms_score: number;
}

interface SupplierScorecard {
  id: number;
  name: string;
  category: string;
  overall_score: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  metrics: SupplierMetrics;
  total_orders: number;
  total_spend: number;
  avg_delivery_days: number;
  on_time_delivery_pct: number;
  defect_rate_pct: number;
  last_order_date: string;
  trend: 'improving' | 'declining' | 'stable';
  notes?: string;
}

interface ScorecardsResponse {
  scorecards: SupplierScorecard[];
  avg_overall_score: number;
  top_supplier: string;
  total_suppliers: number;
}

// ============ COMPONENT ============

export default function SupplierScorecardsPage() {
  const [data, setData] = useState<ScorecardsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierScorecard | null>(null);
  const [sortBy, setSortBy] = useState<'overall_score' | 'name' | 'total_spend'>('overall_score');

  const fetchScorecards = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<ScorecardsResponse>('/suppliers/scorecards');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scorecards');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScorecards();
  }, [fetchScorecards]);

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A': return 'bg-green-100 text-green-700 border-green-300';
      case 'B': return 'bg-blue-100 text-blue-700 border-blue-300';
      case 'C': return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'D': return 'bg-orange-100 text-orange-700 border-orange-300';
      case 'F': return 'bg-red-100 text-red-700 border-red-300';
      default: return 'bg-surface-100 text-surface-700';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return '#22c55e';
    if (score >= 75) return '#3b82f6';
    if (score >= 60) return '#eab308';
    if (score >= 40) return '#f97316';
    return '#ef4444';
  };

  const getTrendInfo = (trend: string) => {
    switch (trend) {
      case 'improving': return { symbol: '\u2191', color: 'text-green-600', label: 'Improving' };
      case 'declining': return { symbol: '\u2193', color: 'text-red-600', label: 'Declining' };
      default: return { symbol: '\u2192', color: 'text-surface-500', label: 'Stable' };
    }
  };

  const renderRadarChart = (metrics: SupplierMetrics, size: number = 200) => {
    const metricEntries = [
      { key: 'delivery_reliability', label: 'Delivery' },
      { key: 'price_competitiveness', label: 'Price' },
      { key: 'quality_score', label: 'Quality' },
      { key: 'fill_rate', label: 'Fill Rate' },
      { key: 'communication', label: 'Comms' },
      { key: 'payment_terms_score', label: 'Terms' },
    ];

    const cx = size / 2;
    const cy = size / 2;
    const maxRadius = size / 2 - 30;
    const angleStep = (2 * Math.PI) / metricEntries.length;

    const rings = [0.25, 0.5, 0.75, 1.0];

    const dataPoints = metricEntries.map((entry, i) => {
      const value = (metrics[entry.key as keyof SupplierMetrics] || 0) / 100;
      const angle = i * angleStep - Math.PI / 2;
      return {
        x: cx + Math.cos(angle) * maxRadius * value,
        y: cy + Math.sin(angle) * maxRadius * value,
      };
    });

    return (
      <svg width={size} height={size} className="mx-auto">
        {rings.map((r) => (
          <polygon
            key={r}
            points={metricEntries
              .map((_, i) => {
                const angle = i * angleStep - Math.PI / 2;
                return `${cx + Math.cos(angle) * maxRadius * r},${cy + Math.sin(angle) * maxRadius * r}`;
              })
              .join(' ')}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="1"
          />
        ))}

        {metricEntries.map((_, i) => {
          const angle = i * angleStep - Math.PI / 2;
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={cx + Math.cos(angle) * maxRadius}
              y2={cy + Math.sin(angle) * maxRadius}
              stroke="#e5e7eb"
              strokeWidth="1"
            />
          );
        })}

        <polygon
          points={dataPoints.map((p) => `${p.x},${p.y}`).join(' ')}
          fill="rgba(59, 130, 246, 0.2)"
          stroke="#3b82f6"
          strokeWidth="2"
        />

        {dataPoints.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="4" fill="#3b82f6" />
        ))}

        {metricEntries.map((entry, i) => {
          const angle = i * angleStep - Math.PI / 2;
          const labelRadius = maxRadius + 20;
          const lx = cx + Math.cos(angle) * labelRadius;
          const ly = cy + Math.sin(angle) * labelRadius;
          return (
            <text
              key={entry.key}
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[10px] fill-surface-600"
            >
              {entry.label}
            </text>
          );
        })}
      </svg>
    );
  };

  const sortedScorecards = data?.scorecards
    .slice()
    .sort((a, b) => {
      switch (sortBy) {
        case 'overall_score': return b.overall_score - a.overall_score;
        case 'name': return a.name.localeCompare(b.name);
        case 'total_spend': return b.total_spend - a.total_spend;
        default: return 0;
      }
    }) || [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading supplier scorecards...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Scorecards Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchScorecards}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/suppliers/management" className="p-2 rounded-lg hover:bg-surface-100 transition-colors">
          <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-surface-900">Supplier Scorecards</h1>
          <p className="text-surface-500 mt-1">Performance metrics and grading for all suppliers</p>
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="overall_score">Sort by Score</option>
          <option value="name">Sort by Name</option>
          <option value="total_spend">Sort by Spend</option>
        </select>
      </div>

      {/* Summary */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Total Suppliers</p>
            <p className="text-2xl font-bold text-surface-900">{data.total_suppliers}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Avg Score</p>
            <p className="text-2xl font-bold" style={{ color: getScoreColor(data.avg_overall_score) }}>
              {data.avg_overall_score.toFixed(1)}
            </p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
            <p className="text-sm text-surface-500">Top Supplier</p>
            <p className="text-2xl font-bold text-surface-900 truncate">{data.top_supplier}</p>
          </div>
        </div>
      )}

      {/* Scorecard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {sortedScorecards.map((supplier) => {
          const trend = getTrendInfo(supplier.trend);
          return (
            <div
              key={supplier.id}
              onClick={() => setSelectedSupplier(supplier)}
              className="bg-white rounded-xl border border-surface-200 shadow-sm hover:shadow-md transition-all cursor-pointer overflow-hidden"
            >
              <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-surface-900 truncate">{supplier.name}</h3>
                    <p className="text-sm text-surface-500 capitalize">{supplier.category}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${trend.color}`}>{trend.symbol}</span>
                    <span className={`w-10 h-10 rounded-lg border-2 flex items-center justify-center text-lg font-bold ${getGradeColor(supplier.grade)}`}>
                      {supplier.grade}
                    </span>
                  </div>
                </div>

                {renderRadarChart(supplier.metrics, 180)}

                <div className="text-center mt-2">
                  <span className="text-3xl font-bold" style={{ color: getScoreColor(supplier.overall_score) }}>
                    {supplier.overall_score.toFixed(0)}
                  </span>
                  <span className="text-surface-400 text-sm"> / 100</span>
                </div>

                <div className="grid grid-cols-3 gap-2 mt-4 text-xs text-center">
                  <div className="p-2 bg-surface-50 rounded-lg">
                    <p className="font-bold text-surface-900">{supplier.total_orders}</p>
                    <p className="text-surface-500">Orders</p>
                  </div>
                  <div className="p-2 bg-surface-50 rounded-lg">
                    <p className="font-bold text-surface-900">{supplier.on_time_delivery_pct.toFixed(0)}%</p>
                    <p className="text-surface-500">On-Time</p>
                  </div>
                  <div className="p-2 bg-surface-50 rounded-lg">
                    <p className="font-bold text-surface-900">${(supplier.total_spend / 1000).toFixed(1)}k</p>
                    <p className="text-surface-500">Spend</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {sortedScorecards.length === 0 && (
        <div className="text-center py-12 text-surface-500">
          No supplier data available yet. Scorecards are generated from purchase order history.
        </div>
      )}

      {/* Detail Modal */}
      {selectedSupplier && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-surface-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-surface-900">{selectedSupplier.name}</h2>
                <p className="text-surface-500 capitalize">{selectedSupplier.category}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`w-12 h-12 rounded-lg border-2 flex items-center justify-center text-2xl font-bold ${getGradeColor(selectedSupplier.grade)}`}>
                  {selectedSupplier.grade}
                </span>
                <button
                  onClick={() => setSelectedSupplier(null)}
                  className="p-2 hover:bg-surface-100 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="p-6">
              {renderRadarChart(selectedSupplier.metrics, 260)}

              <div className="grid grid-cols-2 gap-4 mt-6">
                {[
                  { label: 'Delivery Reliability', value: selectedSupplier.metrics.delivery_reliability },
                  { label: 'Price Competitiveness', value: selectedSupplier.metrics.price_competitiveness },
                  { label: 'Quality Score', value: selectedSupplier.metrics.quality_score },
                  { label: 'Fill Rate', value: selectedSupplier.metrics.fill_rate },
                  { label: 'Communication', value: selectedSupplier.metrics.communication },
                  { label: 'Payment Terms', value: selectedSupplier.metrics.payment_terms_score },
                ].map((m) => (
                  <div key={m.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-surface-600">{m.label}</span>
                      <span className="font-bold" style={{ color: getScoreColor(m.value) }}>
                        {m.value.toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${m.value}%`, backgroundColor: getScoreColor(m.value) }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-4 gap-4 mt-6">
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-lg font-bold text-surface-900">{selectedSupplier.total_orders}</p>
                  <p className="text-xs text-surface-500">Total Orders</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-lg font-bold text-surface-900">${selectedSupplier.total_spend.toLocaleString()}</p>
                  <p className="text-xs text-surface-500">Total Spend</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-lg font-bold text-surface-900">{selectedSupplier.avg_delivery_days.toFixed(1)}d</p>
                  <p className="text-xs text-surface-500">Avg Delivery</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-lg font-bold text-surface-900">{selectedSupplier.defect_rate_pct.toFixed(1)}%</p>
                  <p className="text-xs text-surface-500">Defect Rate</p>
                </div>
              </div>

              {selectedSupplier.notes && (
                <div className="mt-4 p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-600">{selectedSupplier.notes}</p>
                </div>
              )}

              <p className="text-xs text-surface-400 mt-4">
                Last order: {new Date(selectedSupplier.last_order_date).toLocaleDateString()}
              </p>
            </div>

            <div className="p-6 border-t border-surface-200 flex justify-end">
              <button
                onClick={() => setSelectedSupplier(null)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
